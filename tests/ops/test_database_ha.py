import copy,datetime,json,pathlib,sys,tempfile,time,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops import database_ha as db
from werftops.common import Blocked,read_json,write_json,digest_file

def plan():return {'format':db.FORMAT,'name':'shop','postgresMajor':17,'clientCIDRs':['10.70.0.0/24'],'hosts':[{'name':'db-one','address':'10.80.0.1'},{'name':'db-two','address':'10.80.0.2'},{'name':'db-three','address':'10.80.0.3'}]}
class API:
 def __init__(self):self.primary='db-one';self.posts=0;self.lose=False;self.change=None
 def call(self,host,method,path,body=None):
  if method=='POST':
   self.posts+=1;self.primary=body['candidate']
   if self.lose:raise Blocked('LOST_ACK_TEST_FIXTURE')
   return 200,{}
  if path=='/config':return 200,{'synchronous_mode':True,'synchronous_mode_strict':True,'synchronous_node_count':1,'check_timeline':True,'maximum_lag_on_failover':0,'failsafe_mode':False}
  if path=='/primary':return (200 if host==self.primary else 503),{}
  other='db-two' if self.primary=='db-one' else 'db-one'
  s={'patroni':{'scope':'shop','name':host},'state':'running','role':'primary' if host==self.primary else 'replica','dcs_last_seen':time.time(),'database_system_identifier':'7500000000000000001','replication':[{'application_name':other,'state':'streaming','sync_state':'sync'}]}
  if self.change:self.change(host,s)
  return 200,s
class DatabaseHATests(unittest.TestCase):
 def test_three_dedicated_hosts_and_private_clients_required(self):
  for field,value in [('postgresMajor',16),('clientCIDRs',['0.0.0.0/0']),('hosts',plan()['hosts'][:2]),('name','x\nExecStart=bad')]:
   with self.subTest(field=field):
    p=plan();p[field]=value
    with self.assertRaises(Blocked):db.validate(p)
  p=plan();p['hosts'][1]['address']='10.80.0.1'
  with self.assertRaises(Blocked):db.validate(p)
 def test_real_openssl_kit_and_security_profile(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)/'kits';db.prepare(plan(),out)
   roots=[]
   for host in plan()['hosts']:
    kit=out/host['name'];k=db.load_kit(kit);db.verify_certificates(kit,host)
    p=read_json(kit/'patroni/patroni.json',True)
    self.assertTrue(p['bootstrap']['dcs']['synchronous_mode_strict'])
    self.assertEqual(p['watchdog'],{'mode':'required','device':'/dev/watchdog','safety_margin':-1})
    self.assertEqual(p['restapi']['verify_client'],'required')
    self.assertFalse(any('root.key' in name for name in k['files']))
    self.assertEqual((kit/'patroni/node.key').stat().st_mode&0o777,0o600)
    roots.append((kit/'patroni/db-ca.crt').read_bytes())
   self.assertEqual(len(set(roots)),1)
   with self.assertRaises(FileExistsError):db.prepare(plan(),out)
 def test_mutated_watchdog_even_with_recomputed_hash_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)/'kits';db.prepare(plan(),out);kit=out/'db-one'
   p=read_json(kit/'patroni/patroni.json',True);p['watchdog']['mode']='off';write_json(kit/'patroni/patroni.json',p)
   k=read_json(kit/'kit.json',True);k['files']['patroni/patroni.json']=digest_file(kit/'patroni/patroni.json');write_json(kit/'kit.json',k)
   with self.assertRaisesRegex(Blocked,'SECURITY_PROFILE'):db.load_kit(kit)
 def test_live_inspection_contract_and_rejections(self):
  self.assertEqual(db.inspect(plan(),API())['primary'],'db-one')
  for mode in ('double-primary','wrong-id','stale','paused'):
   with self.subTest(mode=mode):
    api=API()
    def change(host,s):
     if host!='db-two':return
     if mode=='double-primary':s['role']='primary'
     if mode=='wrong-id':s['database_system_identifier']='7500000000000000002'
     if mode=='stale':s['dcs_last_seen']=0
     if mode=='paused':s['pause']=True
    api.change=change
    with self.assertRaises(Blocked):db.inspect(plan(),api)
 def test_switchover_lost_ack_is_observed_not_reposted(self):
  with tempfile.TemporaryDirectory() as d:
   api=API();api.lose=True;j=pathlib.Path(d)/'operation.json'
   with self.assertRaises(Blocked):db.switchover(plan(),api,'db-two',j,'shop:db-two')
   self.assertEqual(db.switchover(plan(),api,'db-two',j,'shop:db-two')['phase'],'observed-new-primary')
   self.assertEqual(api.posts,1)
 def test_non_synchronous_candidate_not_promoted(self):
  with tempfile.TemporaryDirectory() as d:
   api=API()
   with self.assertRaises(Blocked):db.switchover(plan(),api,'db-three',pathlib.Path(d)/'j','shop:db-three')
   self.assertEqual(api.posts,0)
 def test_systemd_owns_database_outside_scheduler(self):
  units=db.units('shop');p=units['werft-db-shop-patroni.service']
  self.assertIn('DeviceAllow=/dev/watchdog rw',p);self.assertIn('KillMode=process',p)
  self.assertIn('User=postgres',p);self.assertNotIn('docker',p)
