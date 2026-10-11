import copy,datetime,json,pathlib,sys,tempfile,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops import readiness, upgrade
from werftops.common import Blocked,write_json,read_json
C='a'*32; O='b'*32; N='c'*32; A='d'*32; W='e'*32; V='0.2.0-dev.3'
def snapshot():
 t=datetime.datetime.now(datetime.timezone.utc).isoformat()
 spec={'replicas':1}
 return {'clusterId':C,'schema':2,'maintenanceId':O,'nodes':{N:{'id':N,'lastSeen':t,'healthy':True,'version':V,'heartbeatSequence':1}},'workloads':{'web':{'name':'web','uid':W,'generation':1,'spec':spec}},'allocations':{A:{'id':A,'name':'web','workloadUid':W,'generation':1,'spec':spec,'nodeId':N,'desired':'run','phase':'ready','updatedAt':t}}}
class ReadinessTests(unittest.TestCase):
 def test_good_runtime(self): self.assertEqual(readiness.check(snapshot(),C,O,V,2),{N:1})
 def test_rejects_cached_liveness_and_wrong_version_and_lock(self):
  for change in ('clock','version','owner','healthy','generation','unknown','missing','duplicate','unadvanced'):
   with self.subTest(change=change):
    s=snapshot()
    if change=='clock':s['nodes'][N]['lastSeen']='2000-01-01T00:00:00Z'
    if change=='version':s['nodes'][N]['version']='0.2.0-dev.2'
    if change=='owner':s['maintenanceId']='f'*32
    if change=='healthy':s['nodes'][N]['healthy']=False
    if change=='generation':s['allocations'][A]['generation']=0
    if change=='unknown':s['allocations'][A]['phase']='unknown'
    if change=='missing':s['allocations']={}
    if change=='duplicate':s['allocations']['f'*32]={**s['allocations'][A],'id':'f'*32}
    with self.assertRaises(Blocked):
     v=readiness.check(s,C,O,V,2)
     if change=='unadvanced':readiness.advanced(v,v)
 def test_no_running_process_when_paused(self):
  s=snapshot();s['workloads']['web']['spec']={'replicas':0}
  with self.assertRaises(Blocked):readiness.check(s,C,O,V,2)
  s['allocations'][A]['phase']='stopped';s['allocations'][A]['desired']='stop'
  readiness.check(s,C,O,V,2)
 def test_finish_unlocks_only_after_three_advancing_observations(self):
  self.finish_case(False)
 def test_finish_keeps_lock_on_cached_heartbeat(self):self.finish_case(True)
 def finish_case(self, stale):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'journal';state=snapshot();calls=[]
   write_json(path,{'format':'werftkern-host-update/v1','id':O,'clusterId':C,'phase':'awaiting-runtime-qualification','services':['werftkern-control'],'target':{'version':V,'packageVersion':'0.2.0~dev3','stateSchema':2}})
   def runner(a,**kw):
    calls.append(a)
    if a[0]=='dpkg-query':return b'0.2.0~dev3'
    if a[:2]==['werft','version']:return ('Werftkern '+V+'\n').encode()
    if a[:2]==['werft','health']:return json.dumps({'clusterId':C,'controllers':[{'status':'ready','clusterId':C,'version':V,'stateSchema':2}]}).encode()
    if a[:3]==['werft','status','--json']:
     if not stale:state['nodes'][N]['heartbeatSequence']+=1
     return json.dumps(state).encode()
    return b'{}'
   with mock.patch.object(upgrade,'ROOT',pathlib.Path(d)),mock.patch.object(upgrade,'host_preflight',lambda:None):
    if stale:
     with self.assertRaises(Blocked):upgrade.finish(path,O,runner,lambda _:None)
    else:self.assertEqual(upgrade.finish(path,O,runner,lambda _:None)['phase'],'completed-runtime-verified')
   off=[c for c in calls if c[:3]==['werft','maintenance','off']]
   self.assertEqual(len(off),0 if stale else 1)
   self.assertEqual(read_json(path,True)['phase'],'awaiting-runtime-qualification' if stale else 'completed-runtime-verified')
 def test_lost_unlock_ack_is_reconciled_without_repeated_unlock(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);j=root/'j';s=snapshot();off=[0]
   write_json(j,{'format':'werftkern-host-update/v1','id':O,'clusterId':C,'phase':'awaiting-runtime-qualification','services':[], 'target':{'version':V,'packageVersion':'0.2.0~dev3','stateSchema':2}})
   def run(a,**k):
    if a[0]=='dpkg-query':return b'0.2.0~dev3'
    if a[:2]==['werft','version']:return ('Werftkern '+V).encode()
    if a[:2]==['werft','health']:return json.dumps({'clusterId':C,'controllers':[{'status':'ready','clusterId':C,'version':V,'stateSchema':2}]}).encode()
    if a[:2]==['werft','status']:
     s['nodes'][N]['heartbeatSequence']+=1
     return json.dumps(s).encode()
    if a[:3]==['werft','maintenance','off']:
     off[0]+=1;s['maintenanceId']='';raise Blocked('LOST_UNLOCK_ACK')
    return b'{}'
   with mock.patch.object(upgrade,'ROOT',root),mock.patch.object(upgrade,'host_preflight',lambda:None):
    with self.assertRaises(Blocked):upgrade.finish(j,O,run,lambda _:None)
    self.assertEqual(read_json(j,True)['phase'],'runtime-verified-unlock-pending')
    s['maintenanceId']='f'*32
    with self.assertRaisesRegex(Blocked,'OWNER_CHANGED'):upgrade.finish(j,O,run,lambda _:None)
    s['maintenanceId']=''
    result=upgrade.finish(j,O,run,lambda _:None)
    self.assertTrue(result['unlockAcknowledgementRecovered'])
    upgrade.finish(j,O,lambda *a,**k:self.fail('historical replay should not execute'),lambda _:None)
   self.assertEqual(off[0],1)
