import hashlib,json,pathlib,sys,tempfile,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'ops'))
from werftops import upgrade
from werftops.common import Blocked,read_json
class Upgrades(unittest.TestCase):
 def exercise(self, fail=False):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);cfg=root/'etc';cfg.mkdir();(cfg/'admin.json').write_text('{}');pkg=root/'test.deb';pkg.write_bytes(b'fixture-package');sha=hashlib.sha256(pkg.read_bytes()).hexdigest()
   manifest={'format':'werftkern-release/v1','version':'0.2.1-dev.1','packageVersion':'0.2.1~dev1','packageSha256':sha,'stateSchema':2,'architecture':'amd64','sources':['0.2.0~dev2']}
   calls=[];installed=['0.2.0~dev2']
   def runner(args,**kw):
    calls.append(args)
    if args[:3]==['werft','release','verify']:return json.dumps(manifest).encode()
    if args[:3]==['werft','status','--json']:return json.dumps({'clusterId':'a'*32}).encode()
    if args[0]=='dpkg-query':return installed[0].encode()
    if args[0]=='dpkg-deb':return ('werftkern' if args[-1]=='Package' else manifest['packageVersion']).encode()
    if args[:3]==['werft','backup','create']:pathlib.Path(args[args.index('--out')+1]).write_bytes(b'private-test-backup')
    if args[0]=='dpkg':
     if fail:raise Blocked('SIMULATED_PACKAGE_INSTALL_FAILURE')
     installed[0]=manifest['packageVersion']
    return b'{}'
   with mock.patch.object(upgrade,'ROOT',root/'var'),mock.patch.object(upgrade,'CONFIG',cfg),mock.patch.object(upgrade,'host_preflight',lambda:None):
    if fail:
     with self.assertRaises(Blocked):upgrade.apply(pkg,'manifest','sig','key',manifest['version'],runner)
     journal=read_json(root/'var'/'updates'/sha/'journal.json',private=True)
     self.assertEqual(journal['phase'],'installing')
     self.assertFalse(any(a[:3]==['werft','maintenance','off'] for a in calls))
    else:
     result=upgrade.apply(pkg,'manifest','sig','key',manifest['version'],runner)
     self.assertEqual(result['phase'],'awaiting-runtime-qualification')
     self.assertFalse(any(a[:3]==['werft','maintenance','off'] for a in calls))
 def test_signed_controller_update_flow_with_command_fixture(self):self.exercise()
 def test_install_failure_retains_maintenance_lock_and_journal(self):self.exercise(True)
 def test_wrong_confirmation_has_no_mutation(self):
  calls=[]
  def runner(args,**kw):calls.append(args);return json.dumps({'version':'0.2.1-dev.1'}).encode()
  with mock.patch.object(upgrade,'host_preflight',lambda:None):
   with self.assertRaises(Blocked):upgrade.apply('pkg','m','s','k','wrong',runner)
   self.assertEqual(len(calls),1)
