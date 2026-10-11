import datetime,json,pathlib,sys,tempfile,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops import pitr
from werftops.common import Blocked,atomic,read_json
LABEL='20260901-010203F';SYSID='7500000000000000001';TIME='2026-09-02T12:00:00+00:00'
def info():return [{'name':'shop','cipher':'aes-256-cbc','status':{'code':0},'db':[{'id':1,'repo-key':1,'system-id':int(SYSID),'version':'17'}],'backup':[{'label':LABEL,'database':{'id':1,'repo-key':1},'timestamp':{'start':1788220000,'stop':1788220800},'error':False}]}]
class PITRTests(unittest.TestCase):
 def config(self,root):
  secret=root/'cipher';atomic(secret,b'A'*48)
  file=root/'pgbackrest.conf';pitr.prepare({'format':'werftkern-pitr/v1','name':'shop','pgPath':str(root/'source'),'socketDir':str(root/'socket'),'pgPort':5432,'repositoryPath':str(root/'repository')},secret,file)
  return file
 def test_config_preserves_encryption_and_archive_checks(self):
  with tempfile.TemporaryDirectory() as d:
   file=self.config(pathlib.Path(d));pitr.configuration(file,'shop')
   self.assertEqual(file.stat().st_mode&0o777,0o600)
   atomic(file,file.read_bytes().replace(b'archive-check=y',b'archive-check=n'))
   with self.assertRaises(Blocked):pitr.configuration(file,'shop')
 def test_system_id_uses_integer_without_float_rounding(self):
  self.assertEqual(pitr.backup_identity(info()[0],LABEL)['systemId'],SYSID)
 def test_restore_never_promotes_or_overwrites_source(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(pitr,'owned_actor',lambda:None):
   root=pathlib.Path(d);file=self.config(root);calls=[];target=root/'restored';journal=root/'restore.json'
   def runner(args,**kw):
    calls.append(args)
    if args[-1]=='info':return json.dumps(info()).encode()
    if args[-1]=='restore':(target/'PG_VERSION').write_text('17\n');(target/'recovery.signal').touch()
    return b''
   result=pitr.restore(file,'shop',LABEL,TIME,target,SYSID,journal,'shop:'+str(target),runner)
   self.assertEqual(result['phase'],'files-restored-wal-replay-required')
   self.assertIn('--target-action=pause',calls[-1]);self.assertIn('--archive-mode=off',calls[-1])
   self.assertNotIn('--force',calls[-1]);self.assertNotIn('--delta',calls[-1]);self.assertIn('--tablespace-map-all='+str(target)+'.tablespaces',calls[-1])
   with self.assertRaises(Blocked):pitr.restore(file,'shop',LABEL,TIME,target,SYSID,journal,'shop:'+str(target),runner)
   self.assertEqual(len([a for a in calls if a[-1]=='restore']),1)
 def test_restore_interruption_preserves_intent_and_refuses_blind_retry(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(pitr,'owned_actor',lambda:None):
   root=pathlib.Path(d);file=self.config(root);target=root/'restored';journal=root/'j'
   def runner(a,**kw):
    if a[-1]=='info':return json.dumps(info()).encode()
    raise Blocked('SIMULATED_INTERRUPTION')
   with self.assertRaises(Blocked):pitr.restore(file,'shop',LABEL,TIME,target,SYSID,journal,'shop:'+str(target),runner)
   self.assertEqual(read_json(journal,True)['phase'],'restore-intent')
 def test_wrong_database_and_early_timestamp_block_before_restore(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(pitr,'owned_actor',lambda:None):
   root=pathlib.Path(d);file=self.config(root);target=root/'new';j=root/'j';calls=[]
   def runner(a,**kw):calls.append(a);return json.dumps(info()).encode()
   for when,system in [(TIME,'7500000000000000002'),('2020-01-01T00:00:00Z',SYSID)]:
    with self.assertRaises(Blocked):pitr.restore(file,'shop',LABEL,when,target,system,j,'shop:'+str(target),runner)
   self.assertFalse(target.exists());self.assertFalse(any(a[-1]=='restore' for a in calls))
 def test_time_requires_timezone_and_past(self):
  for v in ('2026-09-01','nonsense','2999-01-01T00:00:00Z'):
   with self.assertRaises(Blocked):pitr.target_time(v)
 def test_replay_verification_rejects_writable_or_wrong_instance(self):
  from werftops.common import write_json
  with tempfile.TemporaryDirectory() as d,mock.patch.object(pitr,'owned_actor',lambda:None):
   root=pathlib.Path(d);j=root/'j';target=root/'new'
   record={'format':'werftkern-pitr-restore/v1','target':str(target),'systemId':SYSID,'time':TIME,'phase':'files-restored-wal-replay-required'}
   write_json(j,record)
   good={'data':str(target),'systemId':SYSID,'recovering':True,'paused':True,'target':TIME,'action':'pause','listen':'127.0.0.1','archive':'off'}
   for field,value in [('data','/source'),('recovering',False),('paused',False),('listen','*'),('archive','on')]:
    with self.subTest(field=field):
     bad={**good,field:value}
     with self.assertRaises(Blocked):pitr.verify_replay(j,root/'socket',5555,lambda *a,**k:json.dumps(bad).encode())
   self.assertEqual(pitr.verify_replay(j,root/'socket',5555,lambda *a,**k:json.dumps(good).encode())['phase'],'replay-paused-application-validation-required')
 def test_first_backup_permits_only_initialized_empty_encrypted_stanza(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(pitr,'owned_actor',lambda:None):
   root=pathlib.Path(d);file=self.config(root);j=root/'backup.json';infos=[0];calls=[]
   def runner(a,**kw):
    calls.append((a,kw))
    self.assertNotIn('PGBACKREST_REPO1_PATH',kw.get('env',{}))
    self.assertIn('--config-include-path='+str(file)+'.d',a)
    if a[-1]=='info':
     s=info()
     if infos[0]==0:s[0]['status']['code']=2;s[0]['backup']=[]
     infos[0]+=1
     return json.dumps(s).encode()
    return b''
   with mock.patch.dict('os.environ',{'PGBACKREST_REPO1_PATH':'/wrong'}):
    result=pitr.backup(file,'shop',j,runner)
   self.assertEqual(result['label'],LABEL)
   self.assertEqual(len([a for a,k in calls if a[-1]=='backup']),1)
   s=info();s[0]['status']['code']=1;s[0]['backup']=[]
   with self.assertRaises(Blocked):pitr.catalog(file,'shop',lambda *a,**k:json.dumps(s).encode(),allow_empty=True)
   s[0]['status']['code']=2
   with self.assertRaises(Blocked):pitr.catalog(file,'shop',lambda *a,**k:json.dumps(s).encode())
 def test_restore_refuses_existing_source_and_journal_overlaps(self):
  with tempfile.TemporaryDirectory() as d,mock.patch.object(pitr,'owned_actor',lambda:None):
   root=pathlib.Path(d);file=self.config(root);target=root/'new'
   (root/'source').mkdir()
   with self.assertRaisesRegex(Blocked,'QUARANTINE'):
    pitr.restore(file,'shop',LABEL,TIME,target,SYSID,root/'journal','shop:'+str(target),lambda *a,**k:self.fail('unexpected command'))
   (root/'source').rmdir()
   for j in (target/'journal',root/'repository'/'journal'):
    with self.assertRaisesRegex(Blocked,'JOURNAL'):
     pitr.restore(file,'shop',LABEL,TIME,target,SYSID,j,'shop:'+str(target),lambda *a,**k:self.fail('unexpected command'))
 def test_included_configuration_cannot_override_policy(self):
  with tempfile.TemporaryDirectory() as d:
   file=self.config(pathlib.Path(d))
   (pathlib.Path(str(file)+'.d')/'bad.conf').write_text('[global]\narchive-check=n\n')
   with self.assertRaisesRegex(Blocked,'INCLUDE'):pitr.configuration(file,'shop')
