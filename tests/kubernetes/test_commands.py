"""Real Python command construction and journals with EXPLICIT external test adapters."""
import copy,hashlib,json,os,pathlib,tempfile,unittest
from unittest.mock import patch
from test_backend import plan,node,identity,KEY,IMG,TEMPLATE,FakeAssets,FakeDriver
from werftops.common import Blocked,atomic,canonical,fingerprint,write_json,read_json
from werftops.kube_driver import Driver
from werftops.kube_addons import Addons
from werftops.kube_lifecycle import Lifecycle
from werftops.kube_cloudscale import CloudScale
from werftops.kube_machines import Machines
from werftops.cloud import Ambiguous

class ToolAssets(FakeAssets):
    def __init__(self,root):
        super().__init__();self.root=pathlib.Path(root);atomic(self.root/'chart.tgz',b'FIXTURE-NOT-A-CHART')
        atomic(self.root/'operator.yaml',('kind: Deployment\nspec:\n template:\n  spec:\n   containers:\n   - image: '+IMG+'\n').encode())
    def tool(self,k):return '/reviewed/'+k
    def get(self,g,k,*a):return str(self.root/('operator.yaml' if g=='manifests' else 'chart.tgz'))

class AddonDriver(FakeDriver):
    def __init__(self,root):
        super().__init__(root);self.assets=ToolAssets(root);self.releases={};self.lose_ack=False;self.secret_missing=False
    def command(self,tool,args,data=None,timeout=120,**kw):
        args=list(map(str,args));self.calls.append(('cmd',tool,args))
        if tool=='kubectl':return b''
        if tool=='helm':
            if args[0]=='template':return ('kind: Pod\nspec:\n containers:\n - image: '+IMG+'\n').encode()
            item=args[1] if args[0] in ('status','upgrade') else args[args.index('--filter')+1][1:-1]
            if args[0]=='list':return canonical([{'name':item}] if item in self.releases else [])
            if args[0]=='status':return canonical(self.releases[item])
            if args[0]=='upgrade':
                item=args[2] # upgrade --install NAME ...
                marker=args[args.index('--description')+1]
                self.releases[item]={'info':{'status':'deployed','description':marker},'version':self.releases.get(item,{}).get('version',0)+1}
                if self.lose_ack:self.lose_ack=False;raise Blocked('LOST_HELM_ACK')
                return b'fixture-install-success'
        raise AssertionError((tool,args))

class AddonExecutionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=AddonDriver(self.tmp.name);self.a=Addons(self.d,{'clusterUID':'cluster-uid'});self.spec={'format':'werftkern-addons/v1','addons':['traefik'],'values':{}}
    def tearDown(self):self.tmp.cleanup()
    def test_real_command_builder_installs_pinned_chart(self):
        r=self.a.apply(self.spec,fingerprint(self.spec));self.assertEqual(r['deployed'],['traefik'])
        calls=[c for c in self.d.calls if c[0]=='cmd' and c[1]=='helm' and c[2][0]=='upgrade']
        self.assertEqual(len(calls),1);self.assertIn('--atomic',calls[0][2]);self.assertNotIn('--force',calls[0][2])
    def test_lost_helm_ack_only_observes_deployed_matching_release(self):
        self.d.lose_ack=True
        with self.assertRaises(Blocked):self.a.apply(self.spec,fingerprint(self.spec))
        self.a.apply(self.spec,fingerprint(self.spec))
        self.assertEqual(sum(c[:2]==('cmd','helm') and c[2][0]=='upgrade' for c in self.d.calls),1)
    def test_failed_previous_helm_release_never_blind_retried(self):
        self.d.lose_ack=True
        with self.assertRaises(Blocked):self.a.apply(self.spec,fingerprint(self.spec))
        self.d.releases['traefik']['info']['status']='pending-upgrade'
        with self.assertRaisesRegex(Blocked,'UNCERTAIN'):self.a.apply(self.spec,fingerprint(self.spec))
        self.assertEqual(sum(c[:2]==('cmd','helm') and c[2][0]=='upgrade' for c in self.d.calls),1)
    def test_refuses_foreign_helm_release(self):
        self.d.releases['traefik']={'info':{'description':'operator-other','status':'deployed'},'version':1}
        with self.assertRaisesRegex(Blocked,'FOREIGN'):self.a.apply(self.spec,fingerprint(self.spec))
    def test_completed_replay_does_not_upgrade(self):
        self.a.apply(self.spec,fingerprint(self.spec));self.a.apply(self.spec,fingerprint(self.spec))
        self.assertEqual(sum(c[:2]==('cmd','helm') and c[2][0]=='upgrade' for c in self.d.calls),1)
    def test_new_changed_spec_can_upgrade_managed_release(self):
        self.a.apply(self.spec,fingerprint(self.spec));self.spec['values']={'traefik':{'service':{'type':'NodePort'}}}
        self.a.apply(self.spec,fingerprint(self.spec));self.assertEqual(self.d.releases['traefik']['version'],2)
    def test_identity_change_is_not_silently_skipped_by_realm_import(self):
        write_json(self.d.root/'identity-state.json',{'configuration':'other'})
        with self.assertRaisesRegex(Blocked,'REALM_IMPORT_NOT'):self.a.identity(identity(),{},self.d.root/'journal.json')

class CloudAPI:
    credential_fingerprint='c'*64
    def __init__(self):self.servers=[];self.calls=[];self.price='5.00';self.lose=False
    def call(self,m,p,payload=None):
        self.calls.append((m,p,copy.deepcopy(payload)))
        if p=='/networks/200':return {'network':{'subnets':[{'type':'cloud'}]}}
        if p=='/firewalls/300' or p=='/ssh_keys/400':return {}
        if p=='/images/100':return {'image':{'os_flavor':'ubuntu','os_version':'24.04'}}
        if p.startswith('/server_types?'):return {'server_types':[{'name':'cx22','prices':[{'location':'fsn1','price_monthly':{'gross':self.price}}]}]}
        if p.startswith('/servers?'):return {'servers':copy.deepcopy(self.servers)}
        if p=='/servers' and m=='POST':
            server={'id':77,'name':payload['name'],'labels':payload['labels'],'status':'running','private_net':[{'network':200,'ip':'10.20.0.99'}],
                    'server_type':{'name':'cx22'},'image':{'id':100},'datacenter':{'location':{'name':'fsn1'}}}
            self.servers=[server]
            if self.lose:raise Ambiguous('PROVIDER_RESPONSE_UNKNOWN')
            return {'server':server}
        if p=='/servers/77':return {'server':copy.deepcopy(self.servers[0])}
        if p=='/servers/999':raise Ambiguous('PROVIDER_HTTP_404')
        raise AssertionError((m,p))
class CloudDriver(FakeDriver):
    def command(self,tool,args,**kw):
        self.calls.append((tool,args));kp=pathlib.Path(args[-1]);atomic(kp,b'not-real-private-key-FIXTURE');atomic(kp.with_suffix('.pub'),KEY.encode())
        return b''
class MachineExecutionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=CloudDriver(self.tmp.name);self.api=CloudAPI();self.m=Machines(self.api,self.d);self.j={};self.op='a'*64
    def tearDown(self):self.tmp.cleanup()
    def create(self):return self.m.create('lab','worker','default',self.op,TEMPLATE,self.d.root/'m',self.j,lambda:write_json(self.d.root/'intent.json',self.j))
    def test_create_has_no_public_ip_and_explicit_pinned_hostkey(self):
        h=self.create();payload=next(c[2] for c in self.api.calls if c[0]=='POST')
        self.assertEqual(payload['public_net'],{'enable_ipv4':False,'enable_ipv6':False});self.assertIn('ssh_keys',payload['user_data'])
        self.assertEqual(h['hostKey'],KEY);self.assertEqual(h['serverId'],77)
    def test_lost_create_ack_adopts_only_matching_owned_server(self):
        self.api.lose=True
        with self.assertRaises(Ambiguous):self.create()
        h=self.create();self.assertEqual(h['serverId'],77);self.assertEqual(sum(c[0]=='POST' for c in self.api.calls),1)
    def test_absence_after_ambiguous_create_never_creates_twice(self):
        self.api.lose=True
        with self.assertRaises(Ambiguous):self.create()
        self.api.servers=[]
        with self.assertRaisesRegex(Blocked,'NO_BLIND_RETRY'):self.create()
        self.assertEqual(sum(c[0]=='POST' for c in self.api.calls),1)
    def test_cost_cap_before_paid_action(self):
        self.api.price='500'
        with self.assertRaises(Blocked):self.create()
        self.assertFalse(any(c[0]=='POST' for c in self.api.calls))
    def test_mutated_provider_owner_refused(self):
        self.create();self.api.servers[0]['labels']['werftkern-cluster']='foreign'
        with self.assertRaises(Blocked):self.create()
    def test_only_definite_404_counts_as_missing(self):
        self.assertIsNone(self.m.get(999))
        with patch.object(self.api,'call',side_effect=Ambiguous('PROVIDER_HTTP_500')):
            with self.assertRaises(Ambiguous):self.m.get(999)


class CloudScaleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=FakeDriver(self.tmp.name);self.life=Lifecycle(self.d)
        with patch('werftops.kube_lifecycle.time.sleep'):self.life.apply(plan(),fingerprint(plan()))
        from test_backend import FakeMachines
        self.m=FakeMachines();self.c=CloudScale(self.d,self.m,self.life)
    def tearDown(self):self.tmp.cleanup()
    def req(self,n,create=True,delete=True):
        return {'format':'werftkern-kube-cloud-scale/v1','desiredWorkers':n,'template':copy.deepcopy(TEMPLATE),
            'acceptCreateCosts':create,'acceptDelete':delete,'maxAddedMonthlyEUR':100}
    def test_cloud_scale_up_creates_then_joins_worker(self):
        r=self.req(4);op,_,_=self.c.plan(r)
        with patch('werftops.kube_lifecycle.time.sleep'):out=self.c.apply(r,op)
        self.assertEqual(out['stage'],'completed');self.assertEqual(len([h for h in self.life.state()['plan']['hosts'] if h['role']=='worker']),4)
        self.assertEqual(sum(c[0]=='create' for c in self.m.calls),1)
    def test_cloud_scale_down_removes_kubernetes_before_provider_delete(self):
        r=self.req(2);op,_,_=self.c.plan(r)
        with patch('werftops.kube_lifecycle.time.sleep'):out=self.c.apply(r,op)
        self.assertEqual(out['stage'],'completed');self.assertEqual(len([h for h in self.life.state()['plan']['hosts'] if h['role']=='worker']),2)
        # Lifecycle drain/apply has happened before provider DELETE is issued.
        self.assertTrue(any(c[0]=='drain' for c in self.d.calls));self.assertIn(('DELETE','/servers/3'),self.m.calls)
    def test_cloud_scale_delete_ambiguity_never_repeats_delete(self):
        r=self.req(2);op,_,_=self.c.plan(r);self.m.delete_error=True
        with patch('werftops.kube_lifecycle.time.sleep'):
            with self.assertRaises(Blocked):self.c.apply(r,op)
        first=sum(c==('DELETE','/servers/3') for c in self.m.calls)
        with self.assertRaises(Blocked):self.c.apply(r,op)
        self.assertEqual(sum(c==('DELETE','/servers/3') for c in self.m.calls),first)
    def test_lost_delete_answer_can_complete_after_cluster_commit(self):
        r=self.req(2);op,_,_=self.c.plan(r);self.m.delete_error=True
        with patch('werftops.kube_lifecycle.time.sleep'):
            with self.assertRaises(Blocked):self.c.apply(r,op)
        self.m.gone=True
        out=self.c.apply(r,op);self.assertEqual(out['stage'],'completed')
        self.assertEqual(sum(c==('DELETE','/servers/3') for c in self.m.calls),1)
    def test_completed_request_replay_is_historical(self):
        r=self.req(2);op,_,_=self.c.plan(r)
        with patch('werftops.kube_lifecycle.time.sleep'):self.c.apply(r,op)
        self.assertTrue(self.c.apply(r,op)['historicallyCompleted'])
    def test_second_different_scale_is_not_old_completion(self):
        first=self.req(2);op,_,_=self.c.plan(first)
        with patch('werftops.kube_lifecycle.time.sleep'):self.c.apply(first,op)
        second=self.req(3);newop,_,_=self.c.plan(second)
        with patch('werftops.kube_lifecycle.time.sleep'):out=self.c.apply(second,newop)
        self.assertFalse(out.get('historicallyCompleted',False))
        self.assertEqual(len([h for h in self.life.state()['plan']['hosts'] if h['role']=='worker']),3)
    def test_changed_provider_credential_blocks_cleanup(self):
        r=self.req(2);op,_,_=self.c.plan(r);self.m.delete_error=True
        with patch('werftops.kube_lifecycle.time.sleep'):
            with self.assertRaises(Blocked):self.c.apply(r,op)
        self.m.gone=True;self.m.api.credential_fingerprint='d'*64
        with self.assertRaisesRegex(Blocked,'CREDENTIAL_CHANGED'):self.c.apply(r,op)
    def test_cleanup_remains_under_local_coordinator_lock(self):
        from werftops.common import lock
        r=self.req(2);op,_,_=self.c.plan(r);original=self.m.api.call
        def call(method,path,payload=None):
            if method=='DELETE':
                with self.assertRaisesRegex(Blocked,'ANOTHER_OPERATION'):
                    with lock(self.d.root/'cloud-scale.lock'):pass
            return original(method,path,payload)
        self.m.api.call=call
        with patch('werftops.kube_lifecycle.time.sleep'):self.c.apply(r,op)
    def test_cloud_scale_requires_cost_and_delete_acceptance(self):
        with self.assertRaises(Blocked):self.c.plan(self.req(4,create=False))
        with self.assertRaises(Blocked):self.c.plan(self.req(2,delete=False))

class HTTPFixture:
    def __init__(self,p):self.p=p;self.base='https://api.example.invalid:6443';self.objects={};self.directs=[];self.bad_cp=False
    def direct(self,address,method,path):
        self.directs.append((address,path))
        if self.bad_cp and path=='/version':return {'gitVersion':'v1.34.9'}
        return self.call(method,path)
    def call(self,m,p,payload=None,notfound=False):
        if p=='/readyz':return 'ok'
        if p=='/version':return {'gitVersion':'v1.35.1+k0s'}
        if p=='/api/v1/namespaces/kube-system':return {'metadata':{'uid':'cluster-uid'}}
        if p=='/api/v1/nodes':return {'items':[node(h) for h in plan()['hosts'] if h['role']=='worker']}
        base='/api/v1/namespaces/kube-system/configmaps';key=base+'/werftkern-operation'
        if m=='POST' and p==base:
            if key in self.objects:raise Blocked('CONFLICT')
            payload=copy.deepcopy(payload);payload['metadata'].update(uid='lock-uid',resourceVersion='1');self.objects[key]=payload;return payload
        if p==key:
            if m=='GET':return copy.deepcopy(self.objects.get(p))
            if m=='DELETE':
                pre=payload['preconditions'];v=self.objects[p]
                if pre!={'uid':v['metadata']['uid'],'resourceVersion':v['metadata']['resourceVersion']}:raise Blocked('PRECONDITION')
                del self.objects[p];return {}
        raise AssertionError((m,p))
    def close(self):pass
class ActualDriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.calls=[]
        self.d=Driver(self.root,ToolAssets(self.root),executor=lambda argv,**kw:self.calls.append((argv,kw)) or b'',api_factory=HTTPFixture)
    def tearDown(self):self.d.close();self.tmp.cleanup()
    def test_direct_controller_checks_not_hidden_by_LB(self):
        result=self.d.verify(plan(),'cluster-uid');self.assertEqual(result['clusterUID'],'cluster-uid')
        self.assertEqual(len(self.d.load_api().directs),3)
        self.d.load_api().bad_cp=True
        with self.assertRaisesRegex(Blocked,'CONTROLLER_VERSION'):self.d.verify(plan(),'cluster-uid')
    def test_distributed_lock_ownership(self):
        self.d.distributed_lock('a','cluster-uid');self.d.distributed_lock('a','cluster-uid')
        with self.assertRaises(Blocked):self.d.distributed_lock('b','cluster-uid')
        with self.assertRaises(Blocked):self.d.unlock('b','cluster-uid')
        self.d.unlock('a','cluster-uid');self.d.unlock('a','cluster-uid')
    def test_drain_respects_pdb_and_no_force(self):
        # Separate fixture for node identity.
        self.d.request=lambda *a,**kw:node(plan()['hosts'][1])
        self.d.drain('w1','uid-w1');argv=self.calls[-1][0]
        self.assertIn('drain',argv);self.assertNotIn('--force',argv);self.assertNotIn('--delete-emptydir-data',argv)
    def test_execution_env_does_not_inherit_proxy_or_helm_plugin(self):
        self.d.command('helm',['version']);env=self.calls[-1][1]['env']
        self.assertNotIn('HTTPS_PROXY',env);self.assertNotIn('HELM_DRIVER',env);self.assertEqual(env['KUBECONFIG'],str(self.root/'kubeconfig.json'))

if __name__=='__main__':unittest.main()
