"""Coordinator/host protocol fixtures, NOT live SSH, Docker or cloud tests."""
import copy,datetime,hashlib,json,pathlib,sys,tempfile,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops import rollout,worker_upgrade,readiness
from werftops.common import Blocked,read_json,write_json
C='a'*32;OP='b'*32;N='c'*32;N2='d'*32;I='e'*32;I2='f'*32

def plan():
 return {'format':'werftkern-worker-rollout/v1','clusterId':C,'operationId':OP,'workers':[
  {'nodeId':N,'address':'10.2.0.11','sshUser':'ubuntu'}, {'nodeId':N2,'address':'10.2.0.12','sshUser':'ubuntu'}],
  'drainTimeoutSeconds':30,'observationSeconds':12}

class Fixture:
 def __init__(self,root):
  self.root=root;self.calls=[];self.remote_calls=[];self.t=0;self.fail='';self.receipts={};self.halted=False
  self.plan=plan()
  self.files={k:root/k for k in ('package','manifest','signature','public_key','known_hosts')}
  for k,p in self.files.items():p.write_bytes(k.encode());p.chmod(0o600)
  self.m={'format':'werftkern-release/v1','version':rollout.VERSION,'packageVersion':'0.2.0~dev4','packageSha256':hashlib.sha256(b'package').hexdigest(),'stateSchema':2,'architecture':'amd64','sources':['0.2.0~dev3']}
  self.s={'clusterId':C,'schema':2,'maintenanceId':'','nodes':{},'workloads':{},'allocations':{}}
  for n,i,addr in ((N,I,'10.2.0.11'),(N2,I2,'10.2.0.12')):
   self.s['nodes'][n]={'id':n,'instanceId':i,'address':addr,'version':'0.2.0-dev.3','healthy':True,'heartbeatSequence':10,'drain':False,'revoked':False,'lastSeen':self.now()}
 def now(self):return datetime.datetime.now(datetime.timezone.utc).isoformat()
 def sleep(self,s):self.t+=s
 def monotonic(self):return self.t
 def runner(self,a,**k):
  self.calls.append(a)
  if a[:3]==['werft','release','verify']:return json.dumps(self.m).encode()
  if a[:2]==['werft','health']:
   version='old' if self.fail=='controller' else rollout.VERSION
   return json.dumps({'clusterId':C,'controllers':[{'endpoint':'https://10.2.0.10:7443','status':'ready','clusterId':C,'version':version,'stateSchema':2,'supportedAgentVersions':[rollout.VERSION,'0.2.0-dev.3']}]}).encode()
  if a[:2]==['werft','status']:
   for n in self.s['nodes'].values():
    if self.fail!='stale':n['heartbeatSequence']+=1
    n['lastSeen']=self.now()
   wire=copy.deepcopy(self.s)
   # Exact Go State JSON: maintenanceId has omitempty, so an unlocked cluster
   # omits the key rather than emitting an empty string.
   if wire.get('maintenanceId')=='':wire.pop('maintenanceId')
   return json.dumps(wire).encode()
  if a[:2]==['werft','maintenance']:
   if a[2]=='on':
    self.s['maintenanceId']=OP
    if self.fail=='lost-freeze':self.fail='';raise Blocked('LOST_FREEZE_ACK')
   else:
    self.s['maintenanceId']=''
    if self.fail=='lost-unlock':self.fail='';raise Blocked('LOST_UNLOCK_ACK')
   return b'{}'
  if a[:2]==['werft','maintenance-node']:
   node=a[a.index('--node')+1];n=self.s['nodes'][node]
   if a[2]=='drain':
    n['drain']=True
    return json.dumps({'nodeId':node,'clusterId':C,'maintenanceId':OP,'drain':True,'unconfirmedAllocations':1 if self.fail=='capacity' else 0,'heartbeatSequence':n['heartbeatSequence']}).encode()
   n['drain']=False
   if self.fail=='lost-uncordon':self.fail='';raise Blocked('LOST_UNCORDON_ACK')
   return b'{}'
  raise AssertionError(a)
 def preflight(self,w,p,m):self.remote_calls.append(('preflight',w['nodeId']))
 def install(self,w,p,m):
  self.remote_calls.append(('install',w['nodeId']))
  if self.fail=='before-remote':raise Blocked('SSH_UNCERTAIN_NO_RECEIPT')
  node=w['nodeId'];n=self.s['nodes'][node];n['version']=rollout.VERSION
  r={'format':'werftkern-worker-update/v1','operationId':OP,'clusterId':C,'nodeId':node,'instanceId':n['instanceId'],'packageSha256':m['packageSha256'],'packageVersion':m['packageVersion'],'version':rollout.VERSION,'phase':'installed-awaiting-controller'}
  self.receipts[node]=r
  if self.fail=='lost-install':self.fail='';raise Blocked('LOST_INSTALL_ACK')
  return r
 def receipt(self,w,p):
  self.remote_calls.append(('receipt',w['nodeId']))
  if w['nodeId'] not in self.receipts:raise Blocked('NO_REMOTE_RECEIPT')
  return self.receipts[w['nodeId']]
 def smoke(self,w,p):
  self.remote_calls.append(('smoke',w['nodeId']))
  return {'clusterId':C,'nodeId':w['nodeId'],'operationId':OP,'version':rollout.VERSION,'httpReady':self.fail!='smoke','cleanupConfirmed':True}
 def apply(self):
  return rollout.apply(self.plan,self.root/'journal',**self.files,confirm=rollout.validate(self.plan),runner=self.runner,remote=self,sleeper=self.sleep,monotonic=self.monotonic)

class RolloutTests(unittest.TestCase):
 def exercise(self,kind):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root);f.fail=kind
   with mock.patch.object(rollout,'ROOT',root):
    if kind:
     with self.assertRaises(Blocked):f.apply()
     if kind=='controller':self.assertFalse((root/'journal').exists());return
     self.assertEqual(f.s['maintenanceId'],'' if kind=='lost-unlock' else OP)
     if kind=='before-remote':
      with self.assertRaisesRegex(Blocked,'NO_REMOTE_RECEIPT'):f.apply()
      self.assertEqual(f.remote_calls.count(('install',N)),1);return
     if kind=='capacity':
      self.assertFalse(any(x[0]=='install' for x in f.remote_calls));return
     if kind=='smoke':
      self.assertFalse(any(a[:3]==['werft','maintenance-node','uncordon'] for a in f.calls));return
     if kind=='stale':
      self.assertFalse(any(a[:3]==['werft','maintenance','off'] for a in f.calls));return
    result=f.apply()
    self.assertEqual(result['phase'],'completed')
    self.assertEqual(f.s['maintenanceId'],'')
    for n in (N,N2):
     self.assertEqual(f.remote_calls.count(('install',n)),1)
     self.assertFalse(f.s['nodes'][n]['drain'])
     self.assertGreaterEqual(result['workers'][n]['observations'],3)
    if kind=='lost-install':self.assertIn(('receipt',N),f.remote_calls)
    if kind=='lost-unlock':self.assertTrue(result['unlockAcknowledgementRecovered'])
 def test_two_sequential_workers(self):self.exercise('')
 def test_lost_freeze_response_reuses_own_lock(self):self.exercise('lost-freeze')
 def test_lost_install_response_never_reinstalls(self):self.exercise('lost-install')
 def test_uncertain_absent_remote_receipt_stays_blocked(self):self.exercise('before-remote')
 def test_lost_uncordon_response_is_reconciled(self):self.exercise('lost-uncordon')
 def test_lost_unlock_response_is_reconciled(self):self.exercise('lost-unlock')
 def test_no_capacity_never_force_evicts_or_installs(self):self.exercise('capacity')
 def test_smoke_failure_leaves_node_drained(self):self.exercise('smoke')
 def test_nonadvancing_heartbeats_prevent_finish(self):self.exercise('stale')
 def test_old_controller_blocks_before_mutation(self):self.exercise('controller')
 def test_replay_changes_trust_or_plan_are_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root);f.fail='before-remote'
   with mock.patch.object(rollout,'ROOT',root):
    with self.assertRaises(Blocked):f.apply()
    f.files['known_hosts'].write_bytes(b'new hostkey')
    with self.assertRaisesRegex(Blocked,'REPLAY_CONFLICT'):f.apply()
 def test_pinned_workload_blocks_before_lock(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root)
   spec={'replicas':1,'node':N}
   f.s['workloads']['db']={'name':'db','uid':'1'*32,'generation':1,'spec':spec}
   f.s['allocations']['2'*32]={'id':'2'*32,'name':'db','workloadUid':'1'*32,'generation':1,'spec':spec,'nodeId':N,'desired':'run','phase':'ready','updatedAt':f.now()}
   with mock.patch.object(rollout,'ROOT',root):
    with self.assertRaisesRegex(Blocked,'PINNED'):f.apply()
   self.assertFalse((root/'journal').exists());self.assertEqual(f.s['maintenanceId'],'')
 def test_new_lock_never_unlocked_by_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root);f.fail='lost-unlock'
   with mock.patch.object(rollout,'ROOT',root):
    with self.assertRaises(Blocked):f.apply()
    f.s['maintenanceId']='9'*32
    with self.assertRaisesRegex(Blocked,'NEW_MAINTENANCE_OWNER'):f.apply()
    self.assertEqual(f.s['maintenanceId'],'9'*32)
 def test_omitted_old_worker_blocks_before_cluster_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root);f.plan['workers']=f.plan['workers'][:1]
   with mock.patch.object(rollout,'ROOT',root):
    with self.assertRaisesRegex(Blocked,'PLAN_MUST_COVER_ALL'):f.apply()
   self.assertFalse((root/'journal').exists())
   self.assertFalse(any(a[:2]==['werft','maintenance'] for a in f.calls))
 def test_lost_unlock_cannot_hide_replaced_node_identity(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root);f.fail='lost-unlock'
   with mock.patch.object(rollout,'ROOT',root):
    with self.assertRaises(Blocked):f.apply()
    f.s['nodes'][N]['instanceId']='8'*32
    with self.assertRaisesRegex(Blocked,'NODE_IDENTITY_CHANGED'):f.apply()
   self.assertNotEqual(read_json(root/'journal',private=True)['phase'],'completed')
 def test_unknown_journal_phase_refuses_resume_before_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);f=Fixture(root);f.fail='before-remote'
   with mock.patch.object(rollout,'ROOT',root):
    with self.assertRaises(Blocked):f.apply()
    j=read_json(root/'journal',private=True);j['phase']='invented-success';write_json(root/'journal',j)
    count=len(f.remote_calls)
    with self.assertRaisesRegex(Blocked,'JOURNAL_STATE_INVALID'):f.apply()
    self.assertEqual(len(f.remote_calls),count)
    self.assertEqual(f.s['maintenanceId'],OP)
 def test_plan_rejects_injection_duplicate_nodes_and_unbounded_times(self):
  for field,value in [('sshUser','root;id'),('address','127.0.0.1'),('nodeId','not-id')]:
   p=plan();p['workers'][0][field]=value
   with self.assertRaises(Blocked):rollout.validate(p)
  p=plan();p['workers'][1]=copy.deepcopy(p['workers'][0])
  with self.assertRaises(Blocked):rollout.validate(p)
  p=plan();p['observationSeconds']=True
  with self.assertRaises(Blocked):rollout.validate(p)
 def test_paused_workload_can_finish_only_without_live_allocations(self):
  s={'clusterId':C,'schema':2,'maintenanceId':OP,'nodes':{},'allocations':{},'workloads':{'db':{'name':'db','spec':{'replicas':1},'paused':True}}}
  self.assertEqual(readiness.check(s,C,OP,rollout.VERSION,2),{})

class WireProjectionTests(unittest.TestCase):
 def test_absent_unlocked_field_is_accepted_but_null_is_not(self):
  s={'clusterId':C,'schema':2,'nodes':{},'allocations':{},'workloads':{}}
  self.assertEqual(readiness.check(s,C,'',rollout.VERSION,2),{})
  s['maintenanceId']=None
  with self.assertRaisesRegex(Blocked,'MAINTENANCE_MISMATCH'):
   readiness.check(s,C,'',rollout.VERSION,2)

class WorkerHostTests(unittest.TestCase):
 def case(self,fail):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);cfg=root/'etc';cfg.mkdir();f=Fixture(root)
   write_json(cfg/'agent.json',{'nodeId':N,'instanceId':I,'address':'10.2.0.11','client':{'clusterId':C},'socket':'/run/test-docker.sock'})
   status={'nodeId':N,'instanceId':I,'address':'10.2.0.11','clusterId':C,'maintenanceId':OP,'drain':True,'healthy':True,'unconfirmedAllocations':0,'stateSchema':2,'controllerVersion':rollout.VERSION,'heartbeatSequence':10}
   calls=[];installed=['0.2.0~dev3']
   def runner(a,**kw):
    calls.append(a)
    if a[:3]==['werft','release','verify']:return json.dumps(f.m).encode()
    if a[0]=='dpkg-deb':return ('werftkern' if a[-1]=='Package' else '0.2.0~dev4').encode()
    if a[0]=='dpkg-query':return installed[0].encode()
    if a[1:]==['worker-status','--json']:return json.dumps(status).encode()
    if a[0]=='docker':return b'foreign-active-container' if fail=='container' else b''
    if a[0]=='dpkg':
     if fail=='install':raise Blocked('SIMULATED_DPKG_FAILURE')
     installed[0]='0.2.0~dev4'
    if a[:2]==['/usr/bin/werft','version']:return ('Werftkern '+rollout.VERSION).encode()
    return b''
   args=(f.files['package'],f.files['manifest'],f.files['signature'],OP,C,N,'target/werft')
   with mock.patch.object(worker_upgrade,'ROOT',root),mock.patch.object(worker_upgrade,'CONFIG',cfg),mock.patch.object(worker_upgrade,'host_preflight',lambda:None):
    if fail:
     with self.assertRaises(Blocked):worker_upgrade.install(*args,runner)
     if fail=='install':
      self.assertEqual(read_json(root/'worker-updates'/OP/'host.json',True)['phase'],'install-intent')
      with self.assertRaisesRegex(Blocked,'REQUIRES_INSPECTION'):worker_upgrade.install(*args,runner)
      self.assertEqual(sum(a[0]=='dpkg' for a in calls),1)
     else:self.assertFalse(any(a[:2]==['systemctl','stop'] for a in calls))
    else:
     out=worker_upgrade.install(*args,runner)
     self.assertEqual(out['phase'],'installed-awaiting-controller')
     worker_upgrade.install(*args,runner)
     self.assertEqual(sum(a[0]=='dpkg' for a in calls),1)
    self.assertFalse(any(a[:2]==['werft','maintenance'] for a in calls))
 def test_worker_signed_update_does_not_unlock_cluster(self):self.case('')
 def test_uncertain_dpkg_is_not_retried(self):self.case('install')
 def test_existing_container_prevents_host_mutation(self):self.case('container')
if __name__=='__main__':unittest.main()
