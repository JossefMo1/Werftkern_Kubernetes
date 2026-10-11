"""Explicit API fixtures; only ProbeExecutionTests execute actual file readers."""
import copy
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from werftops.common import Blocked, fingerprint
from werftops.kube_data_restore import DataRestore, PROBE, probe_job, validate_spec


def spec():
    return {'format':'werftkern-data-restore/v1','operationId':'exercise-one','sourceClusterUID':'source-uid',
        'targetClusterUID':'target-uid','veleroNamespace':'velero','backupName':'backup-one','backupUID':'backup-uid',
        'backupSpecHash':fingerprint({'includedNamespaces':['app']}),'namespaceMapping':{'app':'restore-app'},
        'volumes':[{'namespace':'app','pvc':'data','sourcePVUID':'pv-old','sourceVolumeHandle':'disk-old',
                    'driver':'snapshot.test.csi','storageClass':'snapshots','runAsUser':1000,
                    'checks':[{'path':'proof/data','sha256':hashlib.sha256(b'correct').hexdigest()}]}],
        'probeImage':'registry.example.test/verify@sha256:'+'a'*64}


class API:
    def __init__(self,root):
        self.root=pathlib.Path(root);self.assets=SimpleNamespace(fingerprint='test-assets');self.objects={};self.events=[];self.holder=None
        self.restore_phase='Completed';self.job_succeeded=True;self.lost_post=False
        s=spec();self.objects['/apis/velero.io/v1/namespaces/velero/backups/backup-one']={
            'metadata':{'uid':'backup-uid','annotations':{'werftkern.io/source-cluster-uid':'source-uid'}},
            'spec':{'includedNamespaces':['app']},'status':{'phase':'Completed','csiVolumeSnapshotsCompleted':1,'errors':0,'warnings':0}}
        self.objects['/apis/storage.k8s.io/v1/storageclasses/snapshots']={'provisioner':'snapshot.test.csi','volumeBindingMode':'Immediate'}
        self.uid_value='target-uid'
    def uid(self):return self.uid_value
    def distributed_lock(self,op,uid):
        if self.holder and self.holder!=op:raise Blocked('FOREIGN_LOCK')
        self.holder=op
    def unlock(self,op,uid):
        if self.holder and self.holder!=op:raise Blocked('FOREIGN_LOCK')
        self.holder=None
    def bindings(self):
        self.objects['/api/v1/namespaces/restore-app/persistentvolumeclaims/data']={'metadata':{'uid':'pvc-new'},
            'spec':{'storageClassName':'snapshots','volumeName':'pv-new','dataSource':{'name':'snap','kind':'VolumeSnapshot','apiGroup':'snapshot.storage.k8s.io'}},
            'status':{'phase':'Bound'}}
        self.objects['/apis/snapshot.storage.k8s.io/v1/namespaces/restore-app/volumesnapshots/snap']={'metadata':{},'status':{'readyToUse':True}}
        self.objects['/api/v1/persistentvolumes/pv-new']={'metadata':{'name':'pv-new','uid':'pv-new'},'spec':{
            'claimRef':{'uid':'pvc-new'},'csi':{'driver':'snapshot.test.csi','volumeHandle':'disk-new'}}}
    def request(self,method,path,payload=None,notfound=False):
        self.events.append((method,path))
        if method=='GET' and '/pods?labelSelector=' in path:
            nm=path.split('%3D')[1];job=self.objects['/apis/batch/v1/namespaces/restore-app/jobs/'+nm]
            return {'items':[copy.deepcopy(self.objects.get('test-pod',{
                'metadata':{'uid':'probe-pod','ownerReferences':[{'uid':job['metadata']['uid'],'controller':True}]},
                'spec':job['spec']['template']['spec'],'status':{'phase':'Succeeded'}}))]}
        if method=='GET':
            if path not in self.objects and not notfound:raise Blocked('FIXTURE_NOT_FOUND:'+path)
            return copy.deepcopy(self.objects.get(path))
        if method!='POST':raise AssertionError((method,path))
        obj=copy.deepcopy(payload);target=path+'/'+obj['metadata']['name']
        if target in self.objects:raise Blocked('ALREADY_EXISTS')
        obj['metadata']['uid']='uid-'+str(len(self.objects));obj['metadata']['resourceVersion']='1'
        if obj['kind']=='Restore':
            obj['status']={'phase':self.restore_phase};self.bindings()
        if obj['kind']=='Job':obj['status']={'succeeded':1} if self.job_succeeded else {}
        self.objects[target]=obj
        if self.lost_post:self.lost_post=False;raise Blocked('RESPONSE_LOST')
        return copy.deepcopy(obj)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=API(self.tmp.name);self.s=spec();self.r=DataRestore(self.d)
    def step(self):return self.r.step(self.s,validate_spec(self.s))
    def test_success_and_no_fresh_claim_on_replay(self):
        result=self.step();self.assertEqual(result['volumesChecked'],1);self.assertFalse(result['databaseConsistencyVerified'])
        self.assertFalse(result['productionTrafficEnabled']);n=len([x for x in self.d.events if x[0]=='POST'])
        self.assertTrue(self.step()['historicallyCompleted']);self.assertEqual(n,len([x for x in self.d.events if x[0]=='POST']))
    def test_wrong_confirmation_no_mutation(self):
        with self.assertRaises(Blocked):self.r.step(self.s,'0'*64)
        self.assertEqual(self.d.events,[])
    def test_hetzner_snapshots_rejected_before_any_api_call(self):
        self.s['volumes'][0]['driver']='csi.hetzner.cloud'
        with self.assertRaisesRegex(Blocked,'HETZNER_VOLUME_SNAPSHOTS_NOT_SUPPORTED'):self.step()
        self.assertEqual(self.d.events,[])
    def test_same_cluster_refused(self):
        self.s['targetClusterUID']=self.s['sourceClusterUID']
        with self.assertRaises(Blocked):self.step()
    def test_source_digest_mismatch(self):
        self.s['backupSpecHash']='1'*64
        with self.assertRaisesRegex(Blocked,'BACKUP_IDENTITY'):self.step()
    def test_new_namespace_required(self):
        self.d.objects['/api/v1/namespaces/restore-app']={'metadata':{'uid':'foreign'}}
        with self.assertRaisesRegex(Blocked,'MUST_BE_NEW'):self.step()
    def test_backup_warning_blocks(self):
        self.d.objects['/apis/velero.io/v1/namespaces/velero/backups/backup-one']['status']['warnings']=1
        with self.assertRaisesRegex(Blocked,'ERROR_FREE'):self.step()
    def test_backup_inventory_count_exact(self):
        self.d.objects['/apis/velero.io/v1/namespaces/velero/backups/backup-one']['status']['csiVolumeSnapshotsCompleted']=2
        with self.assertRaisesRegex(Blocked,'CSI_SNAPSHOT'):self.step()
    def test_delayed_binding_rejected_before_restore(self):
        self.d.objects['/apis/storage.k8s.io/v1/storageclasses/snapshots']['volumeBindingMode']='WaitForFirstConsumer'
        with self.assertRaisesRegex(Blocked,'IMMEDIATE'):self.step()
        self.assertFalse(any(e[0]=='POST' for e in self.d.events))
    def test_lost_post_adopts_only_owned_created_object(self):
        self.d.lost_post=True;self.assertEqual(self.step()['stage'],'completed')
    def test_wait_restore_and_resume(self):
        self.d.restore_phase='InProgress';self.assertEqual(self.step()['stage'],'waiting-velero')
        self.d.objects[self.restore_path()]['status']['phase']='Completed';self.assertEqual(self.step()['stage'],'completed')
    def restore_path(self):return '/apis/velero.io/v1/namespaces/velero/restores/werft-exercise-one'
    def begin(self):
        self.d.restore_phase='InProgress';self.step();self.d.objects[self.restore_path()]['status']['phase']='Completed'
    def test_partial_restore_blocks(self):
        self.d.restore_phase='PartiallyFailed'
        with self.assertRaisesRegex(Blocked,'RESTORE_FAILED'):self.step()
    def test_restore_resource_filter_mutation(self):
        self.begin();self.d.objects[self.restore_path()]['spec']['includedResources'].append('pods')
        with self.assertRaisesRegex(Blocked,'CONTRACT_CHANGED'):self.step()
    def test_restore_hooks_mutation(self):
        self.begin();self.d.objects[self.restore_path()]['spec']['hooks']={'resources':[{}]}
        with self.assertRaisesRegex(Blocked,'UNREVIEWED_OVERRIDE'):self.step()
    def test_policy_mutation_not_hidden_by_annotations(self):
        self.begin();self.d.objects['/apis/networking.k8s.io/v1/namespaces/restore-app/networkpolicies/werft-restore-isolation']['spec']['egress']=[{}]
        with self.assertRaisesRegex(Blocked,'QUARANTINE_POLICY_CHANGED'):self.step()
    def test_namespace_security_checked_every_iteration(self):
        self.begin();self.d.objects['/api/v1/namespaces/restore-app']['metadata']['labels']['pod-security.kubernetes.io/enforce']='privileged'
        with self.assertRaisesRegex(Blocked,'NAMESPACE_SECURITY'):self.step()
    def test_restored_source_disk_refused(self):
        self.begin();self.d.objects['/api/v1/persistentvolumes/pv-new']['spec']['csi']['volumeHandle']='disk-old'
        with self.assertRaisesRegex(Blocked,'REUSED_SOURCE'):self.step()
    def test_snapshot_not_ready(self):
        self.begin();self.d.objects['/apis/snapshot.storage.k8s.io/v1/namespaces/restore-app/volumesnapshots/snap']['status']['readyToUse']=False
        with self.assertRaisesRegex(Blocked,'SNAPSHOT_NOT_READY'):self.step()
    def test_path_traversal(self):
        self.s['volumes'][0]['checks'][0]['path']='../secret'
        with self.assertRaisesRegex(Blocked,'TRAVERSAL'):self.step()
    def test_job_wait_then_wrong_file_failure(self):
        self.d.job_succeeded=False;self.assertEqual(self.step()['stage'],'waiting-file-integrity')
        job=next(v for k,v in self.d.objects.items() if '/jobs/' in k);job['status']={'failed':1}
        with self.assertRaisesRegex(Blocked,'FILE_INTEGRITY_FAILED'):self.step()
    def test_job_env_injection(self):
        self.d.job_succeeded=False;self.step();job=next(v for k,v in self.d.objects.items() if '/jobs/' in k)
        job['spec']['template']['spec']['containers'][0]['env']=[{'name':'PYTHONPATH','value':'/data'}]
        with self.assertRaisesRegex(Blocked,'CONTAINER_INJECTION'):self.step()
    def test_injected_pod_security_or_volume_refused(self):
        self.d.job_succeeded=False;self.step();job=next(v for k,v in self.d.objects.items() if '/jobs/' in k);job['status']={'succeeded':1}
        pod={'metadata':{'ownerReferences':[{'uid':job['metadata']['uid'],'controller':True}]},'spec':copy.deepcopy(job['spec']['template']['spec']),'status':{'phase':'Succeeded'}}
        pod['spec']['volumes'][0]['persistentVolumeClaim']['claimName']='other';self.d.objects['test-pod']=pod
        with self.assertRaisesRegex(Blocked,'INTEGRITY'):self.step()
    def test_deleted_resource_is_not_recreated(self):
        self.begin();del self.d.objects[self.restore_path()]
        with self.assertRaisesRegex(Blocked,'EXTERNALLY_DELETED'):self.step()
    def test_changed_request_idempotency_conflict(self):
        self.begin();self.s['probeImage']='registry.example.test/verify@sha256:'+'b'*64
        with self.assertRaisesRegex(Blocked,'IDEMPOTENCY'):self.step()


class ProbeExecutionTests(unittest.TestCase):
    def check(self,kind):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'proof').mkdir();target=root/'proof/data'
            if kind=='symlink':target.symlink_to('/etc/hostname')
            else:target.write_bytes(b'correct' if kind=='good' else b'wrong')
            script=PROBE.replace("'/data'",repr(td))
            import json
            p=subprocess.run([sys.executable,'-c',script,json.dumps(spec()['volumes'][0]['checks'])],capture_output=True,timeout=5)
            return p.returncode,p.stdout
    def test_actual_bytes_match(self):
        code,out=self.check('good');self.assertEqual(code,0);self.assertIn(b'passed',out)
    def test_actual_wrong_bytes_fail(self):self.assertNotEqual(self.check('wrong')[0],0)
    def test_actual_symlink_fail(self):self.assertNotEqual(self.check('symlink')[0],0)

if __name__=='__main__':unittest.main()
