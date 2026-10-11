"""Recovery contracts with explicit Kubernetes/Hetzner/SSH adapters, not VM tests."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'ops'))
from werftops.common import Blocked, fingerprint, write_json, read_json
from werftops.kube_fencing import Fence
from werftops.kube_controller_recovery import ControllerRecovery, validate_request as controller_validate
from werftops.kube_stateful_recovery import StatefulRecovery, validate_request as stateful_validate, CSI, TAINT
from werftops.kube_driver import Driver
from werftops.kube_spec import render, validate, validate_change
from test_backend import plan, node, KEY, TEMPLATE, FakeDriver


def ha_plan():
    p = plan(); p['profile'] = 'ha'; p['haControlPlane'] = {'mode': 'external'}
    p['hosts'][0].update(serverId=101, pool='default')
    for i in (2, 3):
        p['hosts'].append({'name': 'cp'+str(i), 'role': 'controller', 'address': '10.20.0.'+str(10*i),
                           'user': 'root', 'port': 22, 'hostKey': KEY, 'serverId': 100+i, 'pool': 'default'})
    return p


def source_server(h):
    return {'id': h['serverId'], 'name': h['name'], 'created': '2026-09-01T00:00:00Z',
            'labels': {'werftkern-cluster': 'lab', 'werftkern-engine': 'kubernetes', 'werftkern-role': h['role'],
                       'werftkern-pool': h.get('pool', 'default')},
            'private_net': [{'network': 200, 'ip': h['address']}], 'volumes': [],
            'datacenter': {'location': {'name': 'fsn1'}}, 'status': 'running'}


class Clock:
    def __init__(self): self.now = 1000.0
    def __call__(self): return self.now
    def advance(self): self.now += 2


class MachineFixture:
    credential_fingerprint='c'*64
    def __init__(self, d, h):
        self.d, self.api = d, self
        self.servers = {h['serverId']: source_server(h)}
        self.calls = []; self.keep_deleted = False; self.delete_lost = False; self.volumes = {}
    def get(self, ident): return copy.deepcopy(self.servers.get(ident))
    def ownership(self, server, cluster, role, pool=None, expected_name=None):
        if not server: raise Blocked('SOURCE_VM_MISSING_WITHOUT_FENCING_RECEIPT')
        if server['name'] != expected_name or server['labels']['werftkern-role'] != role or server['labels']['werftkern-cluster'] != cluster:
            raise Blocked('PROVIDER_VM_OWNERSHIP_MISMATCH')
    def preflight(self, t): self.calls.append(('preflight',)); return '10'
    def call(self, method, path, payload=None):
        self.calls.append((method, path)); self.d.calls.append(('provider', method, path))
        if method == 'DELETE':
            ident = int(path.rsplit('/', 1)[1])
            if not self.keep_deleted:
                self.servers.pop(ident, None)
                for v in self.volumes.values():
                    if v['server'] == ident: v['server'] = None
            if self.delete_lost: raise Blocked('PROVIDER_RESPONSE_UNKNOWN')
            return {'action': {'status': 'running'}}
        if method == 'GET' and path.startswith('/volumes/'):
            return {'volume': copy.deepcopy(self.volumes[int(path.rsplit('/', 1)[1])])}
        raise AssertionError((method, path))
    def create(self, cluster, role, pool, op, t, directory, j, save):
        self.calls.append(('create', role)); self.d.calls.append(('machine-create', role))
        h = {'name': 'replacement', 'role': role, 'address': '10.20.0.91', 'user': 'root', 'port': 22,
             'hostKey': KEY, 'pool': pool, 'serverId': 991}
        self.servers[991] = source_server(h); return h


class RecoveryDriver(FakeDriver):
    def __init__(self, root, p):
        super().__init__(root, p)
        self.members = {h['name']: 'https://'+h['address']+':2380' for h in p['hosts'] if h['role']=='controller'}
        self.old_healthy = False; self.lost_leave = False; self.do_leave = True; self.bad_survivor = None
    def controller_observe(self, h, uid, release):
        if h['name'] == self.bad_survivor: raise Blocked('CONTROLLER_NOT_READY')
        if uid != self.uid_value: raise Blocked('CONTROLLER_CLUSTER_UID_MISMATCH')
        self.calls.append(('observe-controller', h['name'])); return True
    def controller_reachable(self, h, uid, release): return self.old_healthy
    def etcd_members(self, p, h): return copy.deepcopy(self.members)
    def etcd_leave(self, p, h, peer):
        self.calls.append(('leave', peer))
        if self.do_leave: self.members = {n:u for n,u in self.members.items() if u != peer}
        if self.lost_leave: raise Blocked('COMMAND_TIMEOUT:ssh')
    def control_node(self, n):
        return {'apiVersion':'autopilot.k0sproject.io/v1beta2','metadata':{'name':n,'uid':'control-'+n,'resourceVersion':'1'}}
    def delete_control_node(self, receipt): self.calls.append(('delete-control',receipt['metadata']['uid']))
    def backup_survivor(self, p, h, out):
        self.calls.append(('backup-survivor',h['name']))
        if self.fail=='backup': raise Blocked('BACKUP_FAILED')
        return {'clusterUID':self.uid_value,'sha256':'a'*64}
    def apply(self, p, reset=(), restore=None):
        super().apply(p, reset, restore)
        self.members = {h['name']:'https://'+h['address']+':2380' for h in p['hosts'] if h['role']=='controller'}


class FenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.d = FakeDriver(self.temp.name)
        self.old = plan()['hosts'][1]; self.m = MachineFixture(self.d,self.old); self.clock=Clock()
        self.f = Fence(self.m,self.clock); self.j={}; self.saves=[]
    def tearDown(self): self.temp.cleanup()
    def step(self, vols=None): return self.f.step('lab',self.old,'op',vols or [],self.j,lambda:self.saves.append(copy.deepcopy(self.j)))
    def test_no_fence_from_initial_404(self):
        self.m.servers.clear()
        with self.assertRaises(Blocked): self.step()
        self.assertFalse(self.saves)
    def test_intent_is_durable_before_delete_and_requires_two_observations(self):
        self.assertFalse(self.step());self.assertEqual(self.saves[0]['stage'],'delete-intent')
        self.assertFalse(self.step());self.clock.advance();self.assertFalse(self.step())
        self.clock.advance();self.assertTrue(self.step())
    def test_lost_delete_response_is_not_repeated(self):
        self.m.delete_lost=True;self.step();self.clock.advance();self.step();self.clock.advance();self.assertTrue(self.step())
        self.assertEqual(sum(c[0]=='DELETE' for c in self.m.calls),1)
    def test_server_still_present_never_authorizes_fence_or_retry(self):
        self.m.keep_deleted=True;self.step()
        for _ in range(5):self.clock.advance();self.assertFalse(self.step())
        self.assertEqual(sum(c[0]=='DELETE' for c in self.m.calls),1)
    def test_changed_server_identity_rejected(self):
        self.m.keep_deleted=True;self.step();self.m.servers[1]['created']='different'
        with self.assertRaises(Blocked):self.step()
    def test_unapproved_volume_blocks_deletion(self):
        self.m.servers[1]['volumes']=[87]
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(any(c[0]=='DELETE' for c in self.m.calls))
    def test_delete_protection_not_disabled(self):
        self.m.servers[1]['protection']={'delete':True}
        with self.assertRaises(Blocked):self.step()
    def test_rotated_or_foreign_token_cannot_turn_404_into_fence(self):
        self.step();self.clock.advance();self.m.credential_fingerprint='d'*64
        with self.assertRaisesRegex(Blocked,'CREDENTIAL_CHANGED'):self.step()
    def test_journal_without_provider_binding_cannot_be_replayed(self):
        self.step();self.j.pop('providerCredential');self.clock.advance()
        with self.assertRaisesRegex(Blocked,'CREDENTIAL_CHANGED'):self.step()
    def test_clock_rollback_blocks(self):
        self.step();self.clock.now-=1
        with self.assertRaises(Blocked):self.step()
    def test_volume_scope_cannot_change_after_intent(self):
        self.step()
        with self.assertRaises(Blocked):self.step([33])
    def test_private_address_must_match(self):
        self.m.servers[1]['private_net'][0]['ip']='10.20.0.99'
        with self.assertRaises(Blocked):self.step()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=ha_plan();self.d=RecoveryDriver(self.temp.name,self.p)
        self.old=self.p['hosts'][0];self.m=MachineFixture(self.d,self.old);self.clock=Clock()
        self.r={'format':'werftkern-controller-recovery/v1','clusterUID':'cluster-uid','sourcePlanHash':fingerprint(self.p),
                'controller':'cp1','expectedPeerURL':'https://10.20.0.10:2380','template':copy.deepcopy(TEMPLATE),'acceptDeleteAndCosts':True}
        write_json(self.d.root/'cluster.json',{'format':'werftkern-kube-state/v1','plan':self.p,**self.d.verify(self.p)})
        self.c=ControllerRecovery(self.d,self.m,self.clock)
    def tearDown(self):self.temp.cleanup()
    def step(self):return self.c.step(self.r,fingerprint(self.r))
    def finish(self):
        for _ in range(8):
            self.clock.advance();result=self.step()
            if result['stage']=='completed':return result
        self.fail('did not finish')
    def test_complete_flow_order_and_new_membership(self):
        self.finish();k=[x[0] for x in self.d.calls]
        self.assertLess(k.index('backup-survivor'),k.index('provider'));self.assertLess(k.index('provider'),k.index('leave'))
        self.assertLess(k.index('leave'),k.index('machine-create'));self.assertNotIn('cp1',self.d.members)
        self.assertEqual(len(self.d.members),3);self.assertIsNone(self.d.holder)
    def test_quorum_lost_blocks_all_mutations(self):
        self.d.bad_survivor='cp2'
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(self.m.calls)
    def test_missing_or_foreign_members_block(self):
        self.d.members['unexpected']='https://10.20.0.98:2380'
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(self.m.calls)
    def test_healthy_source_never_deleted(self):
        self.d.old_healthy=True
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(self.m.calls)
    def test_backup_failure_never_deletes(self):
        self.d.fail='backup'
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(any(x[0]=='DELETE' for x in self.m.calls))
    def test_lost_leave_ack_observes_then_continues(self):
        self.d.lost_leave=True
        self.step();self.clock.advance();self.step();self.clock.advance()
        with self.assertRaises(Blocked):self.step()
        self.d.lost_leave=False;self.finish()
        self.assertEqual(sum(x[0]=='leave' for x in self.d.calls),1)
    def test_unknown_leave_result_not_replayed(self):
        self.d.do_leave=False;self.step();self.clock.advance();self.step();self.clock.advance();self.step();self.clock.advance()
        with self.assertRaisesRegex(Blocked,'NO_BLIND_RETRY'):self.step()
        self.assertEqual(sum(x[0]=='leave' for x in self.d.calls),1)
    def test_wrong_confirmation_is_read_only(self):
        with self.assertRaises(Blocked):self.c.step(self.r,'yes')
        self.assertFalse(self.m.calls)
    def test_source_plan_and_peer_cannot_be_swapped(self):
        for key,val in [('sourcePlanHash','b'*64),('expectedPeerURL','https://10.20.0.20:2380')]:
            r=copy.deepcopy(self.r);r[key]=val
            with self.assertRaises(Blocked):self.c.step(r,fingerprint(r))
    def test_replay_completed_does_not_delete_again(self):
        self.finish();before=copy.deepcopy(self.m.calls);r=self.step()
        self.assertTrue(r['historicallyCompleted']);self.assertEqual(before,self.m.calls)
    def test_foreign_lock_retained(self):
        self.d.holder='other'
        with self.assertRaises(Blocked):self.step()
        self.assertEqual(self.d.holder,'other')
    def test_no_combined_controller_worker_repair(self):
        self.d.nodes.append(node(self.old,False))
        with self.assertRaises(Blocked):self.step()
    def test_unknown_request_fields_are_rejected(self):
        r=copy.deepcopy(self.r);r['force']=True
        with self.assertRaises(Blocked):controller_validate(r)


class StatefulDriver(FakeDriver):
    def __init__(self,root,p):
        super().__init__(root,p);self.nodes[0]=node(p['hosts'][1],False);self.nodes[0]['spec']['providerID']='hcloud://1'
        self.sts={'metadata':{'name':'database','namespace':'app','uid':'sts-uid','generation':1,
                  'annotations':{'werftkern.io/recovery-profile':'hetzner-csi-single-writer'}},
                  'spec':{'replicas':1},'status':{'observedGeneration':1,'readyReplicas':1}}
        self.pod={'metadata':{'name':'database-0','namespace':'app','uid':'old-pod',
                  'ownerReferences':[{'kind':'StatefulSet','name':'database','uid':'sts-uid','controller':True}]},
                  'spec':{'nodeName':'w1','volumes':[{'name':'data','persistentVolumeClaim':{'claimName':'data'}}]},
                  'status':{'phase':'Running','conditions':[{'type':'Ready','status':'True'}]}}
        self.pods=[self.pod]
        self.pvc={'metadata':{'name':'data','namespace':'app','uid':'pvc-uid'},'spec':{'volumeName':'pv-data'},'status':{'phase':'Bound'}}
        self.pv={'metadata':{'name':'pv-data','uid':'pv-uid','annotations':{'werftkern.io/recovery-cluster-uid':'cluster-uid'}},
                 'spec':{'claimRef':{'uid':'pvc-uid','namespace':'app','name':'data'},'csi':{'driver':CSI,'volumeHandle':'501'},
                         'accessModes':['ReadWriteOnce'],'persistentVolumeReclaimPolicy':'Retain','volumeMode':'Filesystem'}}
        self.volumes=[self.pv];self.detach=True;self.machine=None;self.policy=True
        self.attachments=[{'metadata':{'uid':'va-uid'},'spec':{'nodeName':'w1','attacher':CSI,'source':{'persistentVolumeName':'pv-data'}}}]
    def verify_detach_policy(self,p):
        if not self.policy or p.get('storageRecovery')!={'disableForceDetachOnTimeout':True}:raise Blocked('LIVE_POLICY_MISSING')
    def request(self,method,url,payload=None,notfound=False):
        if url.endswith('/statefulsets/database'):return copy.deepcopy(self.sts)
        if url.endswith('/persistentvolumeclaims/data'):return copy.deepcopy(self.pvc)
        if url=='/api/v1/persistentvolumes/pv-data':return copy.deepcopy(self.pv)
        if url.endswith('/csidrivers/'+CSI):return {'spec':{'attachRequired':True}}
        if url=='/api/v1/pods':return {'items':copy.deepcopy(self.pods)}
        if url.endswith('/pods/database-0'):return copy.deepcopy(self.pod)
        if method=='PUT' and url.endswith('/nodes/w1') and any(t.get('key')==TAINT for t in payload['spec'].get('taints',[])):
            if self.detach:
                self.attachments=[{'metadata':{'uid':'new-va'},'spec':{'nodeName':'w2','attacher':CSI,'source':{'persistentVolumeName':'pv-data'}},'status':{'attached':True}}];self.pod=copy.deepcopy(self.pod);self.pod['metadata']['uid']='new-pod';self.pod['spec']['nodeName']='w2'
                self.machine.volumes[501]['server']=2
        return super().request(method,url,payload,notfound)
    def apply(self,p,reset=(),restore=None):
        old=next((x for x in self.nodes if x['metadata']['name']=='w1'),None)
        super().apply(p,reset,restore)
        if old:self.nodes.append(old)


class StatefulTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=plan();self.p['storageRecovery']={'disableForceDetachOnTimeout':True}
        self.d=StatefulDriver(self.temp.name,self.p);self.old=self.p['hosts'][1];self.m=MachineFixture(self.d,self.old);self.d.machine=self.m
        self.m.servers[1]['volumes']=[501];self.m.volumes[501]={'id':501,'server':1,'size':10,'location':{'name':'fsn1'},
            'labels':{'werftkern-cluster':'lab','werftkern-pv-uid':'pv-uid'}}
        self.clock=Clock();self.c=StatefulRecovery(self.d,self.m,self.clock)
        self.r={'format':'werftkern-stateful-recovery/v1','clusterUID':'cluster-uid','sourcePlanHash':fingerprint(self.p),
                'worker':'w1','nodeUID':'uid-w1','template':copy.deepcopy(TEMPLATE),'acceptDeleteAndCosts':True,
                'statefulSets':[{'namespace':'app','name':'database','uid':'sts-uid'}]}
        write_json(self.d.root/'cluster.json',{'format':'werftkern-kube-state/v1','plan':self.p,**self.d.verify(self.p)})
    def tearDown(self):self.temp.cleanup()
    def step(self):return self.c.step(self.r,fingerprint(self.r))
    def inventory(self):return self.c.inventory(self.p,self.old,'uid-w1','cluster-uid',self.r['statefulSets'],TEMPLATE)
    def finish(self):
        for _ in range(8):
            self.clock.advance();r=self.step()
            if r['stage']=='completed':return r
        self.fail('did not finish')
    def test_complete_flow_preserves_volume_and_fences_before_taint(self):
        result=self.finish();self.assertFalse(result['applicationIntegrityVerified']);self.assertEqual(self.m.volumes[501]['id'],501)
        delete=next(i for i,c in enumerate(self.d.calls) if c[:2]==('provider','DELETE'))
        taint=next(i for i,c in enumerate(self.d.calls) if c[:2]==('api','PUT') and any(t.get('key')==TAINT for t in c[3].get('spec',{}).get('taints',[])))
        self.assertLess(delete,taint);self.assertIsNone(self.d.holder)
    def test_no_automatic_detach_while_source_still_exists(self):
        self.m.keep_deleted=True
        for _ in range(5):self.clock.advance();self.assertEqual(self.step()['stage'],'waiting-provider-fence')
        self.assertFalse(any(c[0]=='machine-create' for c in self.d.calls))
    def test_live_policy_required_before_mutation(self):
        self.d.policy=False
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(self.m.calls)
    def test_csi_finalizers_never_force_removed(self):
        self.d.detach=False;self.step();self.clock.advance();self.step();self.clock.advance()
        self.assertEqual(self.step()['stage'],'waiting-csi-detach')
        self.assertFalse(any(c[:2]==('api','DELETE') and 'volumeattachment' in c[2] for c in self.d.calls))
    def test_wrong_provider_id_blocks(self):
        self.d.nodes[0]['spec']['providerID']='hcloud://99'
        with self.assertRaises(Blocked):self.step()
    def test_statefulset_must_be_single_writer_and_enrolled(self):
        self.d.sts['spec']['replicas']=3
        with self.assertRaises(Blocked):self.inventory()
    def test_pv_reclaim_delete_is_not_accepted(self):
        self.d.pv['spec']['persistentVolumeReclaimPolicy']='Delete'
        with self.assertRaises(Blocked):self.inventory()
    def test_foreign_claim_uid_blocks(self):
        self.d.pv['spec']['claimRef']['uid']='other'
        with self.assertRaises(Blocked):self.inventory()
    def test_foreign_provider_volume_blocks(self):
        self.m.volumes[501]['labels']['werftkern-pv-uid']='other'
        with self.assertRaises(Blocked):self.inventory()
    def test_inline_or_local_data_blocks(self):
        self.d.pod['spec']['volumes'].append({'name':'local','emptyDir':{}})
        with self.assertRaises(Blocked):self.inventory()
    def test_unknown_attachment_blocks(self):
        self.d.attachments[0]['spec']['source']['persistentVolumeName']='foreign'
        with self.assertRaises(Blocked):self.inventory()
    def test_out_of_service_toleration_blocks(self):
        self.d.pod['spec']['tolerations']=[{'operator':'Exists'}]
        with self.assertRaises(Blocked):self.inventory()
    def test_new_node_uid_cannot_be_deleted(self):
        self.step();self.clock.advance();self.step();self.clock.advance()
        self.d.nodes[0]['metadata']['uid']='other-node'
        with self.assertRaises(Blocked):self.step()
    def test_missing_volume_never_recreated(self):
        self.step();self.clock.advance();self.step();self.clock.advance();self.m.volumes[501]['labels']['werftkern-pv-uid']='other'
        with self.assertRaises(Blocked):self.step()
        self.assertFalse(any(c[0]=='POST' and '/volumes' in c[1] for c in self.m.calls))
    def test_replay_completed_is_not_new_health_claim(self):
        self.finish();before=len(self.m.calls);self.assertTrue(self.step()['historicallyCompleted']);self.assertEqual(before,len(self.m.calls))
    def test_storage_policy_render_and_non_removal(self):
        cfg=render(self.p,'/tmp/k0s','/tmp/known')
        self.assertEqual(cfg['spec']['k0s']['config']['spec']['controllerManager']['extraArgs']['disable-force-detach-on-timeout'],'true')
        q=copy.deepcopy(self.p);q.pop('storageRecovery')
        with self.assertRaises(Blocked):validate_change(self.p,q,[])
    def test_shared_pvc_on_another_pod_blocks(self):
        other=copy.deepcopy(self.d.pod);other['metadata']['uid']='second-writer';other['spec']['nodeName']='w2';self.d.pods.append(other)
        with self.assertRaisesRegex(Blocked,'MULTIPLE_PODS'):self.inventory()
    def test_integer_is_not_storage_policy_boolean(self):
        p=copy.deepcopy(self.p);p['storageRecovery']['disableForceDetachOnTimeout']=1
        with self.assertRaises(Blocked):validate(p)
    def test_extra_request_flags_forbidden(self):
        r=copy.deepcopy(self.r);r['force']=True
        with self.assertRaises(Blocked):stateful_validate(r)



from werftops.kube_recovery_watch import RecoveryWatch, validate_policy

class WatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.p=ha_plan();self.d=RecoveryDriver(self.temp.name,self.p);self.m=MachineFixture(self.d,self.p['hosts'][0]);self.clock=Clock()
        self.d.controller_reachable=lambda h,u,v:h['name']!='cp1'
        self.policy={'format':'werftkern-recovery-policy/v1','clusterUID':'cluster-uid','enabled':True,'acceptDeleteAndCosts':True,
            'kinds':['controller'],'unhealthySeconds':300,'observations':3,'maxPerDay':1,'cooldownSeconds':600,'minHealthyWorkers':2,
            'maxUnhealthyPercent':40,'maxAdditionalMonthlyEUR':50,'controllerTemplate':copy.deepcopy(TEMPLATE),
            'workerTemplate':copy.deepcopy(TEMPLATE),'statefulSets':[]}
        write_json(self.d.root/'cluster.json',{'format':'werftkern-kube-state/v1','plan':self.p,**self.d.verify(self.p)})
        self.w=RecoveryWatch(self.d,self.m,self.clock)
    def tearDown(self):self.temp.cleanup()
    def select(self):
        for _ in range(11):r=self.w.tick(self.policy);self.clock.now+=30
        return r
    def test_durable_observations_before_any_provider_action(self):
        r=self.select();self.assertEqual(r['stage'],'recovery-selected');self.assertFalse(self.m.calls)
    def test_gap_resets_failure_window(self):
        self.w.tick(self.policy);self.clock.now+=200;self.assertEqual(self.w.tick(self.policy)['stage'],'observing')
    def test_quorum_loss_does_not_delete_a_controller(self):
        self.d.controller_reachable=lambda h,u,v:False
        self.assertEqual(self.w.tick(self.policy)['stage'],'quorum-unavailable-no-repair');self.assertFalse(self.m.calls)
    def test_disabled_policy_never_starts_mutation(self):
        self.policy['enabled']=False;self.assertEqual(self.w.tick(self.policy)['stage'],'disabled')
    def test_unknown_policy_flags_block(self):
        self.policy['force']=True
        with self.assertRaises(Blocked):validate_policy(self.policy)
    def test_cost_cap_is_reserved_before_mutation(self):
        self.policy['maxAdditionalMonthlyEUR']=1
        self.assertEqual(self.select()['stage'],'monthly-cost-cap');self.assertFalse(self.m.calls)
    def test_changed_policy_blocks_active_operation(self):
        self.select();self.policy['maxPerDay']=2
        with self.assertRaisesRegex(Blocked,'POLICY_CHANGED'):self.w.tick(self.policy)
    def test_clock_rollback_blocks_observation(self):
        self.w.tick(self.policy);self.clock.now-=1
        with self.assertRaises(Blocked):self.w.tick(self.policy)
    def test_new_identity_does_not_inherit_failure_age(self):
        for _ in range(9):self.w.tick(self.policy);self.clock.now+=30
        s=read_json(self.d.root/'cluster.json',private=True);s['plan']['hosts'][0]['serverId']=199
        write_json(self.d.root/'cluster.json',s)
        self.assertEqual(self.w.tick(self.policy)['stage'],'observing')
    def test_controller_policy_binding_is_cluster_specific(self):
        self.policy['clusterUID']='other'
        with self.assertRaises(Blocked):self.w.tick(self.policy)

if __name__ == '__main__': unittest.main()
