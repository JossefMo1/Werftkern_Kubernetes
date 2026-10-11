import base64, copy, json, os, pathlib, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops import cloud, network, postgres, bootstrap
from werftops.common import Blocked, fingerprint, private_read, read_json, write_json

def plan():return {'format':'werftkern-hetzner/v1','name':'lab','location':'nbg1','networkId':1,'firewallId':2,'sshKeyId':3,'servers':[{'name':'node-one','serverType':'cx23','imageId':999}]}
class Provider:
    def __init__(self,lose=False):self.items=[];self.creates=0;self.lose=lose;self.calls=[]
    def call(self,method,path,payload=None):
        self.calls.append((method,path,payload))
        if path.startswith('/networks/'):return {'network':{'subnets':[{}]}}
        if path.startswith('/firewalls/') or path.startswith('/ssh_keys/'):return {}
        if method=='POST':
            self.creates+=1
            self.items=[{'id':123,'name':payload['name'],'labels':payload['labels'],'image':{'id':payload['image']},'server_type':{'name':payload['server_type']},'datacenter':{'location':{'name':payload['location']}},'status':'running','private_net':[{'network':1,'ip':'10.10.0.2'}]}]
            if self.lose:raise cloud.Ambiguous('LOST_ACK')
            return {'server':self.items[0]}
        return {'servers':self.items} if path.startswith('/servers?') else {'server':self.items[0]}
class CloudTests(unittest.TestCase):
    def test_replay_never_recreates(self):
        with tempfile.TemporaryDirectory() as d:
            p=plan();api=Provider();journal=pathlib.Path(d)/'journal'
            cloud.apply(p,journal,fingerprint(p),True,api);cloud.apply(p,journal,fingerprint(p),True,api)
            self.assertEqual(api.creates,1)
    def test_lost_ack_adopts_only_verified_resource(self):
        with tempfile.TemporaryDirectory() as d:
            p=plan();api=Provider(True);j=pathlib.Path(d)/'j'
            with self.assertRaises(cloud.Ambiguous):cloud.apply(p,j,fingerprint(p),True,api)
            cloud.apply(p,j,fingerprint(p),True,api);self.assertEqual(api.creates,1)
    def test_ambiguous_absent_does_not_retry_create(self):
        with tempfile.TemporaryDirectory() as d:
            p=plan();api=Provider(True);j=pathlib.Path(d)/'j'
            with self.assertRaises(cloud.Ambiguous):cloud.apply(p,j,fingerprint(p),True,api)
            api.items=[]
            with self.assertRaises(cloud.Ambiguous):cloud.apply(p,j,fingerprint(p),True,api)
            self.assertEqual(api.creates,1)
    def test_wrong_configuration_and_no_cost_approval_block(self):
        p=plan();api=Provider()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Blocked):cloud.apply(p,pathlib.Path(d)/'j',fingerprint(p),False,api)
            self.assertEqual(api.calls,[])
            p['servers']*=21
            with self.assertRaises(Blocked):cloud.validate(p)
    def test_name_collision_not_adopted(self):
        p=plan();api=Provider();api.items=[{'id':7,'name':'node-one'}]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Blocked):cloud.apply(p,pathlib.Path(d)/'j',fingerprint(p),True,api)
            self.assertEqual(api.creates,0)
class NetworkTests(unittest.TestCase):
    def topology(self):return {'name':'lab','hosts':[{'name':'one','address':'10.87.0.1','endpoint':'10.10.0.1','podCidr':'10.88.1.0/24'},{'name':'two','address':'10.87.0.2','endpoint':'10.10.0.2','podCidr':'10.88.2.0/24'}]}
    def test_mesh_records_and_key_permissions(self):
        key=base64.b64encode(bytes(range(32)))
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'mesh';network.prepare(self.topology(),p,lambda *a,**kw:key+b'\n')
            k=read_json(p/'one.mesh.json',private=True);text=network.render(k).decode()
            self.assertIn('AllowedIPs = 10.87.0.2/32, 10.88.2.0/24',text)
            self.assertIn('Endpoint = 10.10.0.2:51820',text)
    def test_overlap_rejected(self):
        t=self.topology();t['hosts'][1]['podCidr']=t['hosts'][0]['podCidr']
        with self.assertRaises(Blocked):network.validate(t)
    def test_injection_rejected(self):
        t=self.topology();t['hosts'][0]['name']='bad\nPostUp=evil'
        with self.assertRaises(Blocked):network.validate(t)
class FileTests(unittest.TestCase):
    def test_private_files_reject_symlinks_and_public_modes(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'private';write_json(p,{'x':1});link=pathlib.Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):private_read(link)
            p.chmod(0o644)
            with self.assertRaises(Blocked):private_read(p)
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'j';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(Blocked):read_json(p)
    def test_existing_backup_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'j';write_json(p,{'original':True},exclusive=True)
            with self.assertRaises(FileExistsError):write_json(p,{'original':False},exclusive=True)
            self.assertTrue(read_json(p)['original'])
class PostgreSQLTests(unittest.TestCase):
    def config(self):return {'host':'127.0.0.1','port':5432,'user':'postgres','database':'app','transport':'loopback'}
    def test_backup_and_isolated_restore_commands(self):
        calls=[]
        def runner(args,**kw):
            calls.append(args)
            if '--version' in args:return b'pg_dump (PostgreSQL) 17.6\n'
            if args[0]=='pg_dump':pathlib.Path(args[args.index('--file')+1]).write_bytes(b'PGDMP synthetic fixture');return b''
            if args[0]=='psql' and '--tuples-only' in args:return b'0\n'
            return b''
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'pass';p.write_text('127.0.0.1:5432:*:postgres:test-fixture');p.chmod(0o600)
            archive=pathlib.Path(d)/'backup';postgres.backup(self.config(),p,archive,runner)
            c=self.config();c['database']='restored'
            postgres.restore(c,p,archive,'restored',runner)
            restore=[a for a in calls if a[0]=='pg_restore' and '--single-transaction' in a];self.assertEqual(len(restore),1)
            self.assertFalse(any('test-fixture' in ' '.join(a) for a in calls))
            with self.assertRaises(Blocked):postgres.restore(self.config(),p,archive,'app',runner)
    def test_plain_remote_or_injected_identifier_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'pass';p.write_text('test');p.chmod(0o600);c=self.config();c['host']='10.0.0.2'
            with self.assertRaises(Blocked):
                with postgres.connection(c,p):pass
            c=self.config();c['database']='app\npassword=bad'
            with self.assertRaises(Blocked):
                with postgres.connection(c,p):pass
if __name__=='__main__':unittest.main()
