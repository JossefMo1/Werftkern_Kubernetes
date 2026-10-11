"""Synthetic infrastructure contracts. These tests do NOT create a real cluster."""
import base64,copy,hashlib,io,json,os,pathlib,stat,struct,sys,tarfile,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops.common import Blocked,atomic,canonical,fingerprint,read_json,write_json
from werftops.kube_spec import *
from werftops.kube_lifecycle import Lifecycle
from werftops.kube_driver import Driver,KubeHTTP,NoRedirect
from werftops.kube_addons import Addons,order,identity_resources,grafana_values,validate_rendered
from werftops.kube_repair import Repair,choose,safe_workloads
from werftops.kube_machines import Machines
from werftops.kube_provision import Provision,validate_blueprint
from werftops.kube_conformance import results,archive_version,Conformance
from werftops.kube_restore import Restore
from werftops.cloud import Ambiguous

KEY='ssh-ed25519 '+base64.b64encode(struct.pack('>I',11)+b'ssh-ed25519'+struct.pack('>I',32)+b'X'*32).decode()
IMG='registry.example.invalid/test@sha256:'+'a'*64
TEMPLATE={'location':'fsn1','serverType':'cx22','imageId':100,'networkId':200,'firewallId':300,'sshKeyId':400,'maxMonthlyEUR':50}

def plan():
    hosts=[{'name':'cp1','role':'controller','address':'10.20.0.10','user':'root','port':22,'hostKey':KEY}]
    hosts +=[{'name':'w'+str(i),'role':'worker','address':'10.20.0.'+str(10+i),'user':'root','port':22,'hostKey':KEY,'pool':'default','serverId':i} for i in range(1,4)]
    return {'format':FORMAT,'name':'lab','profile':'lab','version':'v1.35.1+k0s.0','apiEndpoint':'api.example.invalid','podCIDR':'10.244.0.0/16',
            'serviceCIDR':'10.96.0.0/12','sshKeyPath':'/secure/test-key','backupRecipient':'age1'+'q'*58,'hosts':hosts,
            'repair':{'enabled':True,'unhealthySeconds':300,'observations':3,'minHealthyWorkers':2,'maxUnhealthyPercent':40,
                'maxPerDay':1,'cooldownSeconds':600,'acceptDeleteAndCosts':True,'template':copy.deepcopy(TEMPLATE)}}

def node(h,good=True):
    return {'metadata':{'name':h['name'],'uid':'uid-'+h['name'],'resourceVersion':'1','labels':{'werftkern.io/cluster':'lab','werftkern.io/pool':'default'}},'spec':{},
            'status':{'conditions':[{'type':'Ready','status':'True' if good else 'False'}], 'addresses':[{'type':'InternalIP','address':h['address']}],
                      'nodeInfo':{'kubeletVersion':'v1.35.1+k0s'}}}

def identity():return {'domain':'example.invalid','realm':'staff','databaseHost':'db.example.invalid','databaseName':'keycloak',
    'databaseSecret':'db-secret','databaseCASecret':'db-ca','acmeEmail':'ops@example.invalid','acmeProduction':True}

class FakeAssets:
    fingerprint='assets-1'
    def __init__(self):
        self.data={'upgradeEdges':[{'from':'v1.35.1+k0s.0','to':'v1.36.0+k0s.0'}],
            'images':{'keycloak':IMG,'sonobuoy':IMG,'conformance:v1.35.1':IMG},'tools':{},'k0s':{},'manifests':{}}

class FakeDriver:
    """Explicit test adapter: no Docker, Kubernetes, Raft, SSH, DNS or cloud IO."""
    def __init__(self,root,p=None):
        self.root=pathlib.Path(root);self.assets=FakeAssets();self.p=copy.deepcopy(p or plan());self.calls=[];self.holder=None
        self.nodes=[node(h) for h in self.p['hosts'] if h['role']=='worker'];self.uid_value='cluster-uid';self.pods=[];self.volumes=[];self.attachments=[]
        self.fail=None;self.restore_pending=False
    def snapshot(self):return {'uid':self.uid_value,'nodes':copy.deepcopy(self.nodes),'version':'v1.35.1+k0s'}
    def uid(self):return self.uid_value
    def verify(self,p,expected_uid=None):
        self.calls.append(('verify',copy.deepcopy(p)))
        if expected_uid and expected_uid!=self.uid_value:raise Blocked('KUBE_CLUSTER_IDENTITY_CHANGED')
        if self.fail=='verify':raise Blocked('TEST_NOT_READY')
        return {'clusterUID':self.uid_value,'version':'v1.%d.%d'%version(p['version'])[:2],
                'nodeUIDs':{h['name']:'uid-'+h['name'] for h in p['hosts'] if h['role']=='worker'}}
    def distributed_lock(self,op,uid):
        self.calls.append(('lock',op))
        if uid!=self.uid_value:raise Blocked('KUBE_CLUSTER_IDENTITY_CHANGED')
        if self.holder and self.holder!=op:raise Blocked('OTHER_CLUSTER_OPERATION_HOLDS_LOCK')
        self.holder=op
    def unlock(self,op,uid):
        self.calls.append(('unlock',op))
        if self.holder not in (None,op):raise Blocked('REFUSING_FOREIGN_OPERATION_UNLOCK')
        self.holder=None
    def fresh_hosts(self,p,selected=None):self.calls.append(('fresh',selected))
    def apply(self,p,reset=(),restore=None):
        self.calls.append(('apply',copy.deepcopy(p),list(reset),restore))
        if self.fail=='apply':raise Blocked('TEST_LOST_SSH')
        self.p=copy.deepcopy(p);self.nodes=[node(h) for h in p['hosts'] if h['role']=='worker' and h['name'] not in reset]
    def backup(self,p,out):self.calls.append(('backup',p['version']));return {'sha256':'a'*64}
    def capture_kubeconfig(self,p):self.calls.append(('capture',p['version']))
    def drain(self,name_,uid):
        self.calls.append(('drain',name_,uid))
        if self.fail=='drain':raise Blocked('PDB_PREVENTS_DRAIN')
    def request(self,method,url,payload=None,notfound=False):
        self.calls.append(('api',method,url,copy.deepcopy(payload)))
        if url=='/api/v1/nodes':return {'items':copy.deepcopy(self.nodes)}
        if url.startswith('/api/v1/nodes/'):
            n=next((n for n in self.nodes if n['metadata']['name']==url.rsplit('/',1)[1]),None)
            if method=='GET':
                if n is None and not notfound:raise Blocked('KUBE_HTTP_404')
                return copy.deepcopy(n)
            if method=='PUT':self.nodes=[payload if x['metadata']['name']==payload['metadata']['name'] else x for x in self.nodes];return payload
            if method=='DELETE':
                if n['metadata']['uid']!=payload['preconditions']['uid']:raise Blocked('PRECONDITION_FAILED')
                self.nodes.remove(n);return {}
        if '/pods?' in url:return {'items':copy.deepcopy(self.pods)}
        if 'volumeattachments' in url:return {'items':copy.deepcopy(self.attachments)}
        if 'persistentvolumes' in url:return {'items':copy.deepcopy(self.volumes)}
        raise AssertionError(('unhandled-test-api',method,url))
    def command(self,*args,**kwargs):self.calls.append(('command',args,kwargs));return b''
    def close(self):pass

class ContractTests(unittest.TestCase):
    def test_valid_plan_and_strict_ssh(self):
        p=plan();validate(p);r=render(p,'/safe/k0s','/safe/known')
        h=r['spec']['hosts'][1]
        self.assertEqual(h['openSSH']['options']['StrictHostKeyChecking'],'yes');self.assertFalse(r['spec']['k0s']['dynamicConfig'])
        self.assertTrue(h['uploadBinary']);self.assertIn('--labels=werftkern.io/cluster=lab,werftkern.io/pool=default',h['installFlags'])
    def test_ha_external_strategy_required(self):
        p=plan();p['profile']='ha';p['hosts'].insert(1,copy.deepcopy(p['hosts'][0]));p['hosts'][1].update(name='cp2',address='10.20.0.20');p['hosts'].insert(2,copy.deepcopy(p['hosts'][0]));p['hosts'][2].update(name='cp3',address='10.20.0.30')
        with self.assertRaises(Blocked):validate(p)
        p['haControlPlane']={'mode':'external'};validate(p);r=render(p,'/safe/k0s','/safe/known')
        self.assertNotIn('controlPlaneLoadBalancing',r['spec']['k0s']['config']['spec']['network'])
    def test_ha_embedded_vip_renders_k0s_cplb_and_nllb(self):
        with tempfile.TemporaryDirectory() as td:
            secret=pathlib.Path(td)/'vrrp';atomic(secret,b'A1b2C3',mode=0o600)
            p=plan();p['profile']='ha';p['hosts'].insert(1,copy.deepcopy(p['hosts'][0]));p['hosts'][1].update(name='cp2',address='10.20.0.20');p['hosts'].insert(2,copy.deepcopy(p['hosts'][0]));p['hosts'][2].update(name='cp3',address='10.20.0.30')
            p['haControlPlane']={'mode':'k0s-vip','vipCIDR':'10.20.0.5/24','authPassFile':str(secret),'virtualRouterID':73}
            validate(p);r=render(p,'/safe/k0s','/safe/known');net=r['spec']['k0s']['config']['spec']['network']
            self.assertTrue(net['controlPlaneLoadBalancing']['enabled']);self.assertTrue(net['nodeLocalLoadBalancing']['enabled'])
            v=net['controlPlaneLoadBalancing']['keepalived']['vrrpInstances'][0]
            self.assertEqual(v['virtualIPs'],['10.20.0.5/24']);self.assertEqual(v['authPass'],'A1b2C3');self.assertEqual(v['virtualRouterID'],73)
    def test_ha_vip_collision_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            secret=pathlib.Path(td)/'vrrp';atomic(secret,b'abc123',mode=0o600)
            p=plan();p['profile']='ha';p['hosts'].insert(1,copy.deepcopy(p['hosts'][0]));p['hosts'][1].update(name='cp2',address='10.20.0.20');p['hosts'].insert(2,copy.deepcopy(p['hosts'][0]));p['hosts'][2].update(name='cp3',address='10.20.0.30')
            p['haControlPlane']={'mode':'k0s-vip','vipCIDR':'10.20.0.10/24','authPassFile':str(secret),'virtualRouterID':73}
            with self.assertRaises(Blocked):validate(p)
    def test_reject_bad_host_key(self):
        for v in ('ssh-rsa ABC','ssh-ed25519 BAD','ssh-ed25519 '+base64.b64encode(b'not a key').decode()):
            with self.subTest(v=v),self.assertRaises(Blocked):host_key(v)
    def test_ha_requires_exactly_three_controllers(self):
        p=plan();p['profile']='ha'
        with self.assertRaises(Blocked):validate(p)
    def test_no_public_or_loopback_worker(self):
        for ip in ('127.0.0.1','169.254.169.254','8.8.8.8','::1'):
            p=plan();p['hosts'][0]['address']=ip
            with self.subTest(ip=ip),self.assertRaises(Blocked):validate(p)
    def test_cidr_overlap(self):
        p=plan();p['podCIDR']='10.20.0.0/16'
        with self.assertRaises(Blocked):validate(p)
    def test_unknown_fields_and_bool_integer(self):
        p=plan();p['hosts'][1]['port']=True
        with self.assertRaises(Blocked):validate(p)
        p=plan();p['force']=True
        with self.assertRaises(Blocked):validate(p)
    def test_automatic_repair_needs_explicit_cost_permission(self):
        p=plan();p['repair']['acceptDeleteAndCosts']=False
        with self.assertRaises(Blocked):validate(p)
    def test_upgrade_only_reviewed_edge(self):
        p=plan();q=copy.deepcopy(p);q['version']='v1.36.0+k0s.0'
        with self.assertRaises(Blocked):validate_change(p,q,[])
        self.assertEqual(validate_change(p,q,[{'from':p['version'],'to':q['version']}]),([],[]))
    def test_no_upgrade_with_topology_change(self):
        p=plan();q=copy.deepcopy(p);q['version']='v1.36.0+k0s.0';q['hosts'].pop()
        with self.assertRaises(Blocked):validate_change(p,q,[{'from':p['version'],'to':q['version']}])
    def test_controller_replacement_needs_separate_recovery(self):
        p=plan();q=copy.deepcopy(p);q['hosts'][0]['address']='10.20.0.99'
        with self.assertRaises(Blocked):validate_change(p,q,[])
    def test_assets_digest_checked_at_every_execution(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);binary=p/'tool';atomic(binary,b'test',mode=0o700)
            m={'format':'werftkern-kube-assets/v1','tools':{'tool':{'path':str(binary),'sha256':hashlib.sha256(b'test').hexdigest(),'version':'1'}},'k0s':{},'upgradeEdges':[],'charts':{},'manifests':{},'images':{}}
            write_json(p/'assets.json',m);a=Assets(p/'assets.json');self.assertEqual(a.tool('tool'),str(binary))
            binary.write_bytes(b'evil')
            with self.assertRaises(Blocked):a.tool('tool')
    def test_assets_symlink_or_writable_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);binary=p/'tool';atomic(binary,b'x',mode=0o777)
            m={'format':'werftkern-kube-assets/v1','tools':{'tool':{'path':str(binary),'sha256':hashlib.sha256(b'x').hexdigest(),'version':'1'}},'k0s':{},'upgradeEdges':[],'charts':{},'manifests':{},'images':{}}
            write_json(p/'a.json',m)
            with self.assertRaises(Blocked):Assets(p/'a.json').tool('tool')
    def test_cannot_use_kubeconfig_plugin_or_disable_tls(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'k.json';write_json(p,{'apiVersion':'v1','kind':'Config','current-context':'x','contexts':[{'name':'x','context':{'cluster':'x','user':'x'}}],
                'clusters':[{'name':'x','cluster':{'server':'https://api.example.invalid:6443','insecure-skip-tls-verify':True}}],
                'users':[{'name':'x','user':{'exec':{'command':'anything'}}}]})
            with self.assertRaises(Blocked):KubeHTTP(p)

class LifecycleTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=FakeDriver(self.tmp.name);self.life=Lifecycle(self.d)
    def tearDown(self):self.tmp.cleanup()
    def initial(self):
        with patch('werftops.kube_lifecycle.time.sleep'):self.life.apply(plan(),fingerprint(plan()))
    def test_create_persists_uid_and_requires_confirmation(self):
        with self.assertRaises(Blocked):self.life.apply(plan(),'yes')
        self.initial();self.assertEqual(self.life.state()['clusterUID'],'cluster-uid');self.assertIsNone(self.d.holder)
    def test_upgrade_backup_precedes_remote_apply(self):
        self.initial();p=plan();p['version']='v1.36.0+k0s.0';self.d.calls=[]
        with patch('werftops.kube_lifecycle.time.sleep'):self.life.apply(p,fingerprint(p))
        calls=[x[0] for x in self.d.calls];self.assertLess(calls.index('backup'),calls.index('apply'))
    def test_all_scale_down_nodes_drain_before_reset(self):
        self.initial();p=plan();p['hosts']=p['hosts'][:2];self.d.calls=[]
        with patch('werftops.kube_lifecycle.time.sleep'):self.life.apply(p,fingerprint(p))
        first=next(i for i,c in enumerate(self.d.calls) if c[0]=='apply')
        self.assertEqual([c[1] for c in self.d.calls[:first] if c[0]=='drain'],['w2','w3'])
        self.assertEqual(self.d.calls[first][2],['w2','w3'])
    def test_pdb_failure_prevents_reset(self):
        self.initial();p=plan();p['hosts'].pop();self.d.fail='drain';self.d.calls=[]
        with self.assertRaises(Blocked):self.life.apply(p,fingerprint(p))
        self.assertFalse(any(c[0]=='apply' for c in self.d.calls));self.assertIsNotNone(self.d.holder)
    def test_ambiguous_apply_resumes_same_operation_not_other_plan(self):
        self.d.fail='apply'
        with self.assertRaises(Blocked):self.life.apply(plan(),fingerprint(plan()))
        p=plan();p['repair']['enabled']=False
        with self.assertRaises(Blocked):self.life.apply(p,fingerprint(p))
        self.d.fail=None;self.initial();self.assertEqual(read_json(self.d.root/'active.json',private=True)['stage'],'completed')
    def test_failed_observation_never_commits_ready_state(self):
        self.d.fail='verify'
        with self.assertRaises(Blocked):self.life.apply(plan(),fingerprint(plan()))
        self.assertFalse(self.life.state_path.exists())
    def test_replay_completed_read_only_health(self):
        self.initial();self.d.calls=[];self.initial()
        self.assertFalse(any(c[0] in ('apply','backup') for c in self.d.calls))
    def test_foreign_lock_blocks(self):
        self.initial();self.d.holder='somebody-else';p=plan();p['repair']['enabled']=False
        with self.assertRaises(Blocked):self.life.apply(p,fingerprint(p))


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.d=FakeDriver(self.root);self.r=Restore(self.d)
        self.target=plan();self.target['hosts'][0]['address']='10.20.0.99'
        self.backup=self.root/'external-backup';self.backup.mkdir()
        self.archive=self.backup/'control-plane.tar.gz.age';self.archive.write_bytes(b'encrypted-backup-bytes')
        self.identity=self.root/'age.key';atomic(self.identity,b'AGE-SECRET-KEY-TEST',mode=0o600)
        receipt={'format':'werftkern-kube-backup/v2','clusterUID':'cluster-uid','version':self.target['version'],
            'apiEndpoint':self.target['apiEndpoint'],'sha256':hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            'sourcePlanHash':'b'*64,'sourceControllerAddresses':['10.20.0.10'],'createdAt':1}
        write_json(self.backup/'receipt.json',receipt)
        self.d.command=lambda tool,args,**kwargs: (pathlib.Path(args[args.index('--output')+1]).write_bytes(b'plain-backup') if tool=='age' and '--output' in args else b'')
    def tearDown(self):self.tmp.cleanup()
    def test_restore_requires_exact_confirmation_before_mutation(self):
        with self.assertRaises(Blocked):self.r.apply(self.target,self.backup,self.identity,'wrong')
        self.assertFalse(any(c[0] in ('fresh','apply') for c in self.d.calls))
    def test_restore_to_new_hosts_persists_original_cluster_uid(self):
        op,_,_=self.r.plan(self.target,self.backup)
        out=self.r.apply(self.target,self.backup,self.identity,op)
        self.assertEqual(out['clusterUID'],'cluster-uid');self.assertEqual(out['stage'],'completed')
        self.assertEqual(read_json(self.root/'cluster.json',private=True)['clusterUID'],'cluster-uid')
        apply=next(c for c in self.d.calls if c[0]=='apply');self.assertTrue(apply[3])
        self.assertLess(next(i for i,c in enumerate(self.d.calls) if c[0]=='fresh'),next(i for i,c in enumerate(self.d.calls) if c[0]=='apply'))
    def test_ambiguous_restore_is_never_replayed(self):
        op,_,_=self.r.plan(self.target,self.backup);self.d.fail='apply'
        with self.assertRaises(Blocked):self.r.apply(self.target,self.backup,self.identity,op)
        self.assertEqual(read_json(self.root/'restore.json',private=True)['stage'],'restoring')
        first=sum(c[0]=='apply' for c in self.d.calls);self.d.fail=None
        out=self.r.apply(self.target,self.backup,self.identity,op)
        self.assertEqual(out['stage'],'completed');self.assertEqual(sum(c[0]=='apply' for c in self.d.calls),first)
    def test_restore_rejects_same_controller_or_bad_archive(self):
        old=plan()
        with self.assertRaises(Blocked):self.r.plan(old,self.backup)
        self.archive.write_bytes(b'tampered')
        with self.assertRaises(Blocked):self.r.plan(self.target,self.backup)
    def test_completed_restore_replay_does_not_restore_twice(self):
        op,_,_=self.r.plan(self.target,self.backup)
        self.r.apply(self.target,self.backup,self.identity,op)
        count=sum(c[0]=='apply' for c in self.d.calls)
        self.assertTrue(self.r.apply(self.target,self.backup,self.identity,op)['historicallyCompleted'])
        self.assertEqual(count,sum(c[0]=='apply' for c in self.d.calls))
    def test_crash_after_state_commit_reconciles_without_remote_restore(self):
        op,_,_=self.r.plan(self.target,self.backup)
        self.r.apply(self.target,self.backup,self.identity,op)
        j=read_json(self.root/'restore.json',private=True);j['stage']='observed';write_json(self.root/'restore.json',j)
        count=sum(c[0]=='apply' for c in self.d.calls)
        self.assertTrue(self.r.apply(self.target,self.backup,self.identity,op)['historicallyCompleted'])
        self.assertEqual(count,sum(c[0]=='apply' for c in self.d.calls))
    def test_replay_refuses_different_committed_cluster(self):
        op,_,_=self.r.plan(self.target,self.backup)
        self.r.apply(self.target,self.backup,self.identity,op)
        state=read_json(self.root/'cluster.json',private=True);state['clusterUID']='different';write_json(self.root/'cluster.json',state)
        with self.assertRaisesRegex(Blocked,'ALREADY_HAS_CLUSTER'):self.r.apply(self.target,self.backup,self.identity,op)
    def test_restore_refuses_manager_with_existing_cluster(self):
        op,_,_=self.r.plan(self.target,self.backup);write_json(self.root/'cluster.json',{'anything':True})
        with self.assertRaises(Blocked):self.r.apply(self.target,self.backup,self.identity,op)

class AddonTests(unittest.TestCase):
    def test_order_includes_prerequisites(self):self.assertEqual(order(['keycloak-operator']),['cert-manager','traefik','keycloak-operator'])
    def test_unknown_addon_rejected(self):
        with self.assertRaises(Blocked):order(['ingress-nginx'])
    def test_render_rejects_unpinned_image_and_chart_secret(self):
        for raw in (b'kind: Pod\nspec:\n containers:\n - image: nginx:latest',b'kind: Secret\nstringData: {password: nope}'):
            with self.assertRaises(Blocked):validate_rendered(raw)
    def test_render_rejects_alias_cycles(self):
        with self.assertRaises(Blocked):validate_rendered(b'x: &x\n - *x\n')
    def test_render_accepts_digest_image(self):self.assertEqual(validate_rendered(('kind: Pod\nspec:\n containers:\n - image: '+IMG).encode()),1)
    def test_keycloak_tls_pkce_and_no_default_users(self):
        r=identity_resources(identity(),IMG);kc=next(x for x in r if x['kind']=='Keycloak');realm=r[-1]['spec']['realm']
        self.assertEqual(kc['spec']['db']['vendor'],'postgres');self.assertIn({'name':'db-tls-mode','value':'verify-server'},kc['spec']['additionalOptions'])
        self.assertEqual(realm['clients'][0]['attributes']['pkce.code.challenge.method'],'S256');self.assertNotIn('users',realm)
        self.assertFalse(realm['clients'][0]['directAccessGrantsEnabled'])
    def test_oidc_never_grants_clusteradmin(self):
        r=identity_resources(identity(),IMG);rb=next(x for x in r if x['kind']=='ClusterRoleBinding')
        self.assertEqual(rb['roleRef']['name'],'view');self.assertEqual(rb['subjects'][0]['name'],'oidc:viewers')
    def test_grafana_uses_secrets_and_does_not_grant_admin(self):
        v=grafana_values(identity())['grafana'];self.assertIn('secretKeyRef',v['envValueFrom']['GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET'])
        self.assertFalse(v['grafana.ini']['auth.generic_oauth']['allow_assign_grafana_admin'])
    def test_production_acme_requires_opt_in(self):
        c=identity();c['acmeProduction']=False
        with self.assertRaises(Blocked):identity_resources(c,IMG)

class ConformanceTests(unittest.TestCase):
    def detail(self,pairs):return b'\n'.join(canonical({'name':n,'status':s}) for n,s in pairs)
    def test_filtered_skips_are_not_conformance_skips(self):
        r=results(self.detail([('test [Conformance]','passed'),('other','skipped')]))
        self.assertTrue(r['allReportedConformancePassed']);self.assertFalse(r['cncfCertified']);self.assertFalse(r['fullInventoryVerified'])
    def test_skipped_conformance_not_pass(self):
        r=results(self.detail([('test [Conformance]','skipped')]))
        self.assertFalse(r['allReportedConformancePassed'])
    def test_expected_inventory_prevents_partial_success(self):
        with self.assertRaises(Blocked):results(self.detail([('one [Conformance]','passed')]),['one [Conformance]','two [Conformance]'])
    def test_empty_duplicate_unknown_status(self):
        for pairs in ([],[('x [Conformance]','complete')],[('x [Conformance]','passed')]*2):
            with self.subTest(pairs=pairs),self.assertRaises(Blocked):results(self.detail(pairs))
    def test_exact_inventory(self):
        r=results(self.detail([('x [Conformance]','passed')]),['x [Conformance]']);self.assertTrue(r['expectedInventoryMatched']);self.assertFalse(r['fullInventoryVerified']);self.assertFalse(r['cncfCertified'])
    def test_archive_version_read_without_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/'x.tar.gz'
            with tarfile.open(f,'w:gz') as t:
                b=canonical({'gitVersion':'v1.35.1'});i=tarfile.TarInfo('serverversion.json');i.size=len(b);t.addfile(i,io.BytesIO(b))
            self.assertEqual(archive_version(f),'v1.35.1');self.assertFalse((pathlib.Path(td)/'serverversion.json').exists())
    def test_disruptive_requires_confirmation_before_mutations(self):
        with tempfile.TemporaryDirectory() as td:
            d=FakeDriver(td)
            with self.assertRaises(Blocked):Conformance(d,{'plan':plan(),'clusterUID':'cluster-uid'}).start('a','certified-conformance',False)
            self.assertEqual(d.calls,[])

class FakeMachineAPI:
    credential_fingerprint='c'*64
    def __init__(self,m):self.m=m;self.calls=[]
    def call(self,method,path,payload=None):
        self.calls.append((method,path));self.m.calls.append((method,path))
        if method=='DELETE':
            if self.m.delete_error:raise Ambiguous('PROVIDER_RESPONSE_UNKNOWN')
            self.m.gone=True;return {}
        raise AssertionError(path)
class FakeMachines:
    def __init__(self):self.calls=[];self.api=FakeMachineAPI(self);self.gone=False;self.delete_error=False;self.create_error=False
    def get(self,id_):return None if self.gone else {'id':id_}
    def ownership(self,*a):self.calls.append(('ownership',))
    def preflight(self,*a):self.calls.append(('preflight',));return '5.00'
    def create(self,*a):
        self.calls.append(('create',))
        if self.create_error:raise Blocked('CREATE_AMBIGUOUS_NO_BLIND_RETRY')
        h=copy.deepcopy(plan()['hosts'][1]);h.update(name='replacement',address='10.20.0.50',serverId=50);return h

class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.d=FakeDriver(self.tmp.name);self.m=FakeMachines();self.now=1000.;self.p=plan()
        result=self.d.verify(self.p);write_json(self.d.root/'cluster.json',{'plan':self.p,**result});self.d.nodes[0]['status']['conditions'][0]['status']='False'
        self.r=Repair(self.d,self.m,clock=lambda:self.now)
    def tearDown(self):self.tmp.cleanup()
    def qualify(self):
        for _ in range(10):self.r.tick();self.now+=30
    def test_observation_requires_time_not_tight_loop(self):
        for _ in range(50):self.r.tick()
        self.assertFalse(self.m.api.calls)
    def test_mass_failure_does_not_destroy_nodes(self):
        self.d.nodes[1]['status']['conditions'][0]['status']='False';self.qualify();self.r.tick();self.assertFalse(self.m.api.calls)
    def test_success_deletes_old_before_creating_new(self):
        self.qualify();r=self.r.tick();self.assertEqual(r['state'],'replacement-ready')
        self.assertLess(self.m.calls.index(('DELETE','/servers/1')),self.m.calls.index(('create',)))
        s=read_json(self.d.root/'cluster.json',private=True);self.assertIn('replacement',s['nodeUIDs']);self.assertNotIn('w1',s['nodeUIDs'])
    def test_lost_delete_response_never_repeated_never_create_until_absent(self):
        self.m.delete_error=True;self.qualify();self.r.tick();self.now+=30;self.r.tick()
        self.assertEqual(self.m.api.calls.count(('DELETE','/servers/1')),1);self.assertNotIn(('create',),self.m.calls)
        self.m.gone=True;self.now+=30;self.assertEqual(self.r.tick()['state'],'replacement-ready')
    def test_provider_token_change_after_delete_intent_blocks_false_absence(self):
        self.m.delete_error=True;self.qualify();self.r.tick();self.m.gone=True;self.m.api.credential_fingerprint='d'*64;self.now+=30
        with self.assertRaisesRegex(Blocked,'CREDENTIAL_CHANGED'):self.r.tick()
        self.assertNotIn(('create',),self.m.calls)
    def test_persistent_pods_block_before_deletion(self):
        self.d.pods=[{'metadata':{'namespace':'app','ownerReferences':[{'kind':'ReplicaSet'}]},'spec':{'volumes':[{'persistentVolumeClaim':{'claimName':'data'}}]}}]
        self.qualify()
        with self.assertRaises(Blocked):self.r.tick()
        self.assertFalse(self.m.api.calls)
    def test_volume_attachment_blocks_even_if_pod_was_evicted(self):
        self.d.attachments=[{'spec':{'nodeName':'w1'}}];self.qualify()
        with self.assertRaises(Blocked):self.r.tick()
        self.assertFalse(self.m.api.calls)
    def test_node_uid_change_blocks(self):
        self.d.nodes[0]['metadata']['uid']='foreign';self.qualify()
        with self.assertRaises(Blocked):self.r.tick()
        self.assertFalse(self.m.api.calls)
    def test_clock_rollback_keeps_budget(self):
        with self.assertRaises(Blocked):choose(self.p,self.d.nodes,{'starts':[1200]},1000)
    def test_max_daily_replacements(self):
        book={'starts':[500.]};h,reason=choose(self.p,self.d.nodes,book,1000)
        self.assertIsNone(h);self.assertEqual(reason,'replacement-budget-or-cooldown')
    def test_missing_node_object_not_fencing_evidence(self):
        self.d.nodes.pop(0);self.qualify();self.r.tick();self.assertFalse(self.m.api.calls)
    def test_foreign_operation_prevents_delete(self):
        self.d.holder='other';self.qualify()
        with self.assertRaises(Blocked):self.r.tick()
        self.assertFalse(self.m.api.calls)
    def test_repaired_healthy_node_never_selected(self):
        self.d.nodes[0]['status']['conditions'][0]['status']='True';self.qualify();self.r.tick();self.assertFalse(self.m.api.calls)

if __name__=='__main__':unittest.main()
