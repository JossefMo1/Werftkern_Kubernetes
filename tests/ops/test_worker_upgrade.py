import hashlib,json,pathlib,sys,tempfile,unittest
from unittest import mock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/"ops"))
from werftops import worker_upgrade
from werftops.common import Blocked,fingerprint,read_json,write_json

class WorkerUpgradeTests(unittest.TestCase):
 def setup_fixture(self,root):
  cfg=root/"etc";cfg.mkdir()
  agent={"nodeId":"c"*32,"instanceId":"d"*32,"address":"10.0.0.7","socket":"/run/werftkern/docker.sock","client":{"clusterId":"b"*32}}
  write_json(cfg/"agent.json",agent)
  package=root/"target.deb";package.write_bytes(b"worker-package")
  manifest={"format":"werftkern-release/v1","version":worker_upgrade.VERSION,"packageVersion":"0.2.0~dev4","packageSha256":hashlib.sha256(package.read_bytes()).hexdigest(),"stateSchema":2,"architecture":"amd64","sources":["0.2.0~dev3"]}
  return cfg,package,manifest,agent

 def test_scope_change_after_stop_blocks_install_and_restart(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);cfg,package,manifest,agent=self.setup_fixture(root)
   operation="a"*32;cluster=agent["client"]["clusterId"];node=agent["nodeId"]
   good={"clusterId":cluster,"nodeId":node,"instanceId":agent["instanceId"],"address":agent["address"],"maintenanceId":operation,"drain":True,"unconfirmedAllocations":0,"stateSchema":2,"controllerVersion":worker_upgrade.VERSION,"healthy":True,"heartbeatSequence":7}
   changed={**good,"maintenanceId":"e"*32}
   statuses=[good,changed];calls=[];installed=["0.2.0~dev3"]
   def runner(args,**kw):
    calls.append(args)
    if args[:3]==["werft","release","verify"]:return json.dumps(manifest).encode()
    if args[0]=="dpkg-deb":return ("werftkern" if args[-1]=="Package" else manifest["packageVersion"]).encode()
    if args[0]=="dpkg-query":return installed[0].encode()
    if args[0]=="/tmp/staged-worker":return json.dumps(statuses.pop(0)).encode()
    if args[0]=="docker":return b""
    if args[:2]==["systemctl","stop"]:return b""
    raise AssertionError(args)
   with mock.patch.object(worker_upgrade,"ROOT",root/"var"),mock.patch.object(worker_upgrade,"CONFIG",cfg),mock.patch.object(worker_upgrade,"TRUST",root/"trust/releases.pem"),mock.patch.object(worker_upgrade,"host_preflight",lambda:None):
    with self.assertRaisesRegex(Blocked,"OWNED_DRAINED_EMPTY_NODE_REQUIRED"):
     worker_upgrade.install(package,"manifest","sig",operation,cluster,node,"/tmp/staged-worker",runner)
   journal=read_json(root/"var"/"worker-updates"/operation/"host.json",private=True)
   self.assertEqual(journal["phase"],"stop-intent")
   self.assertTrue(any(a[:2]==["systemctl","stop"] for a in calls))
   self.assertFalse(any(a[0]=="dpkg" for a in calls))
   self.assertFalse(any(a[:2]==["systemctl","start"] for a in calls))

 def test_replay_receipt_does_not_reinstall_or_restart(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);cfg,package,manifest,agent=self.setup_fixture(root)
   operation="f"*32;cluster=agent["client"]["clusterId"];node=agent["nodeId"]
   request=fingerprint({"operation":operation,"cluster":cluster,"node":node,"instance":agent["instanceId"],"manifest":manifest})
   journal=root/"var"/"worker-updates"/operation/"host.json"
   write_json(journal,{"format":"werftkern-worker-update/v1","requestHash":request,"operationId":operation,"clusterId":cluster,"nodeId":node,"instanceId":agent["instanceId"],"packageSha256":manifest["packageSha256"],"packageVersion":manifest["packageVersion"],"version":worker_upgrade.VERSION,"from":"0.2.0~dev3","beforeSequence":4,"phase":"installed-awaiting-controller"})
   calls=[];installed=["0.2.0~dev4"]
   def runner(args,**kw):
    calls.append(args)
    if args[:3]==["werft","release","verify"]:return json.dumps(manifest).encode()
    if args[0]=="dpkg-deb":return ("werftkern" if args[-1]=="Package" else manifest["packageVersion"]).encode()
    if args[0]=="dpkg-query":return installed[0].encode()
    raise AssertionError(args)
   with mock.patch.object(worker_upgrade,"ROOT",root/"var"),mock.patch.object(worker_upgrade,"CONFIG",cfg),mock.patch.object(worker_upgrade,"TRUST",root/"trust/releases.pem"),mock.patch.object(worker_upgrade,"host_preflight",lambda:None):
    result=worker_upgrade.install(package,"manifest","sig",operation,cluster,node,"/tmp/staged-worker",runner)
   self.assertEqual(result["phase"],"installed-awaiting-controller")
   self.assertFalse(any(a[0]=="dpkg" for a in calls))
   self.assertFalse(any(a[:2] in (["systemctl","stop"],["systemctl","start"]) for a in calls))

if __name__=="__main__":
 unittest.main()
