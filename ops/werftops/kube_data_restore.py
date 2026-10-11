"""Quarantined CSI snapshot restore through an existing, trusted Velero install.

Only volume resources are restored; backed-up Pods/controllers/RBAC/hooks are not
executed. A separate restricted Job reads restored data and checks operator-pinned
file digests. This proves the checked files, NOT database consistency or PITR.
"""
from __future__ import annotations

import copy
import re
import time
from .common import Blocked, canonical, fingerprint, lock, read_json, write_json, sha
from .kube_spec import fields, name, image, integer

FORMAT = 'werftkern-data-restore/v1'
PROBE = """import hashlib,json,os,stat,sys
checks=json.loads(sys.argv[1])
for item in checks:
 fd=os.open('/data',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  parts=item['path'].split('/')
  for part in parts[:-1]:
   nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
  f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
  with os.fdopen(f,'rb') as stream:
   st=os.fstat(stream.fileno())
   if not stat.S_ISREG(st.st_mode) or st.st_size>1073741824:raise ValueError('FILE_TYPE_OR_SIZE')
   h=hashlib.sha256()
   for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
   if h.hexdigest()!=item['sha256']:raise ValueError('HASH_MISMATCH')
 finally:os.close(fd)
print(json.dumps({'checkedFiles':len(checks),'result':'passed'}))
"""


def validate_spec(s):
    fields(s, ('format', 'operationId', 'sourceClusterUID', 'targetClusterUID', 'veleroNamespace',
               'backupName', 'backupUID', 'backupSpecHash', 'namespaceMapping', 'volumes', 'probeImage'))
    if s['format'] != FORMAT or s['sourceClusterUID'] == s['targetClusterUID']:
        raise Blocked('DATA_RESTORE_REQUIRES_DIFFERENT_TARGET_CLUSTER')
    for k in ('operationId', 'veleroNamespace', 'backupName'): name(s[k])
    for k in ('sourceClusterUID', 'targetClusterUID', 'backupUID'):
        if not isinstance(s[k], str) or not 1 <= len(s[k]) <= 128: raise Blocked('DATA_RESTORE_IDENTITY_INVALID')
    sha(s['backupSpecHash']); image(s['probeImage'])
    mapping = s['namespaceMapping']
    if not isinstance(mapping, dict) or not 1 <= len(mapping) <= 20 or len(set(mapping.values())) != len(mapping):
        raise Blocked('RESTORE_NAMESPACE_MAPPING_INVALID')
    for src, dst in mapping.items():
        name(src); name(dst)
        if not dst.startswith('restore-') or src.startswith('kube-') or src == s['veleroNamespace'] or dst in mapping:
            raise Blocked('QUARANTINED_NEW_NAMESPACES_REQUIRED')
    if not isinstance(s['volumes'], list) or not 1 <= len(s['volumes']) <= 30:
        raise Blocked('EXPLICIT_VOLUME_INVENTORY_REQUIRED')
    seen=set()
    for v in s['volumes']:
        fields(v, ('namespace', 'pvc', 'sourcePVUID', 'sourceVolumeHandle', 'driver', 'storageClass', 'runAsUser', 'checks'))
        name(v['namespace']); name(v['pvc']); name(v['storageClass']); integer(v['runAsUser'], 1, 2**31-1)
        if v['namespace'] not in mapping or (v['namespace'],v['pvc']) in seen:
            raise Blocked('VOLUME_MAPPING_AMBIGUOUS')
        seen.add((v['namespace'],v['pvc']))
        if not isinstance(v['driver'], str) or not re.fullmatch(r'[a-z0-9.-]+',v['driver']):raise Blocked('CSI_DRIVER_REQUIRED')
        if v['driver'] == 'csi.hetzner.cloud':raise Blocked('HETZNER_VOLUME_SNAPSHOTS_NOT_SUPPORTED_USE_SEPARATE_BACKUP')
        for k in ('sourcePVUID','sourceVolumeHandle'):
            if not isinstance(v[k], str) or not v[k]:raise Blocked('SOURCE_VOLUME_IDENTITY_REQUIRED')
        if not isinstance(v['checks'], list) or not 1 <= len(v['checks']) <= 20:raise Blocked('FILE_INTEGRITY_CHECKS_REQUIRED')
        for c in v['checks']:
            fields(c, ('path', 'sha256'));sha(c['sha256'])
            if (not isinstance(c['path'],str) or not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*',c['path']) or
                any(p in ('.','..') for p in c['path'].split('/'))):
                raise Blocked('INTEGRITY_PATH_MUST_BE_RELATIVE_NO_TRAVERSAL')
    return fingerprint(s)


def probe_job(s, volume, index, operation):
    ns=s['namespaceMapping'][volume['namespace']]; nm='werft-data-'+str(index)+'-'+operation[:12]
    security={'runAsNonRoot':True,'runAsUser':volume['runAsUser'],'seccompProfile':{'type':'RuntimeDefault'}}
    pod={'restartPolicy':'Never','automountServiceAccountToken':False,'enableServiceLinks':False,'securityContext':security,
         'containers':[{'name':'verify','image':s['probeImage'],
             'command':['python3','-c',PROBE,canonical(volume['checks']).decode()],
             'securityContext':{'readOnlyRootFilesystem':True,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},
             'resources':{'requests':{'cpu':'50m','memory':'64Mi'},'limits':{'cpu':'500m','memory':'128Mi'}},
             'volumeMounts':[{'name':'data','mountPath':'/data','readOnly':True}]}],
         'volumes':[{'name':'data','persistentVolumeClaim':{'claimName':volume['pvc'],'readOnly':True}}]}
    return {'apiVersion':'batch/v1','kind':'Job','metadata':{'name':nm,'namespace':ns},
            'spec':{'backoffLimit':0,'activeDeadlineSeconds':600,'template':{'spec':pod}}}


def contract_subset(actual, expected):
    """Compare pinned fields while admitting API-added defaults, never list entries."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and contract_subset(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(contract_subset(a, b) for a, b in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def check_probe_spec(actual, expected):
    if not contract_subset(actual, expected):
        raise Blocked('INTEGRITY_JOB_MUTATED')
    if any(actual.get(k) for k in ('hostNetwork', 'hostPID', 'hostIPC', 'shareProcessNamespace', 'initContainers', 'ephemeralContainers')):
        raise Blocked('INTEGRITY_POD_INJECTION')
    if len(actual.get('volumes', [])) != 1 or actual.get('volumes') != expected['volumes']:
        raise Blocked('INTEGRITY_VOLUME_INJECTION')
    if actual.get('securityContext', {}).get('sysctls'):
        raise Blocked('INTEGRITY_SECURITY_CONTEXT_CHANGED')
    container = actual['containers'][0]
    default_fields = {'imagePullPolicy', 'terminationMessagePath', 'terminationMessagePolicy'}
    if set(container) - set(expected['containers'][0]) - default_fields:
        raise Blocked('INTEGRITY_CONTAINER_INJECTION')
    if container.get('securityContext', {}).get('privileged') or container.get('securityContext', {}).get('capabilities', {}).get('add'):
        raise Blocked('INTEGRITY_SECURITY_CONTEXT_CHANGED')
    if container.get('imagePullPolicy', 'IfNotPresent') not in ('IfNotPresent', 'Always'):
        raise Blocked('INTEGRITY_IMAGE_POLICY_CHANGED')


class DataRestore:
    def __init__(self, driver):self.d=driver

    def _backup(self,s):
        path='/apis/velero.io/v1/namespaces/'+s['veleroNamespace']+'/backups/'+s['backupName']
        b=self.d.request('GET',path);status=b.get('status',{})
        if (b['metadata']['uid']!=s['backupUID'] or fingerprint(b.get('spec',{}))!=s['backupSpecHash'] or
            b['metadata'].get('annotations',{}).get('werftkern.io/source-cluster-uid')!=s['sourceClusterUID']):
            raise Blocked('DATA_BACKUP_IDENTITY_MISMATCH')
        if status.get('phase')!='Completed' or status.get('errors',0)!=0 or status.get('warnings',0)!=0:
            raise Blocked('ONLY_COMPLETED_ERROR_FREE_BACKUPS_ACCEPTED')
        if b['spec'].get('snapshotMoveData') or status.get('csiVolumeSnapshotsCompleted',0)!=len(s['volumes']):
            raise Blocked('QUALIFIED_CSI_SNAPSHOT_BACKUP_REQUIRED_NOT_FSB_OR_DATA_MOVER')
        if b['spec'].get('hooks',{}).get('resources'):
            raise Blocked('BACKUP_HOOKS_REQUIRE_SEPARATE_REVIEW')
        for v in s['volumes']:
            sc=self.d.request('GET','/apis/storage.k8s.io/v1/storageclasses/'+v['storageClass'])
            if sc.get('provisioner')!=v['driver'] or sc.get('volumeBindingMode','Immediate')!='Immediate':
                raise Blocked('CSI_RESTORE_REQUIRES_MATCHED_IMMEDIATE_STORAGE_CLASS')
        return b

    def _ensure(self, path, obj, operation, j, save):
        """Name+UID ownership and lost-POST recovery. No blind recreation after deletion."""
        obj=copy.deepcopy(obj);meta=obj['metadata']
        metadata=meta.setdefault('annotations',{})
        metadata['werftkern.io/operation']=operation
        metadata['werftkern.io/desired-sha256']=fingerprint(obj)
        record=j.setdefault('resources',{}).get(path)
        current=self.d.request('GET',path,notfound=True)
        if record:
            if current is None:raise Blocked('RESTORE_RESOURCE_OUTCOME_UNKNOWN_OR_EXTERNALLY_DELETED')
        else:
            if current is not None:raise Blocked('REFUSING_EXISTING_RESTORE_RESOURCE')
            j['resources'][path]={'stage':'create-intent'};save()
            try:self.d.request('POST',path.rsplit('/',1)[0],obj)
            except Blocked:pass
            current=self.d.request('GET',path,notfound=True)
            if current is None:raise Blocked('RESTORE_CREATE_OUTCOME_UNKNOWN_NO_RECREATE')
        if current.get('metadata', {}).get('deletionTimestamp'):
            raise Blocked('RESTORE_RESOURCE_DELETING')
        if current.get('kind') != obj['kind'] or current.get('apiVersion') != obj['apiVersion']:
            raise Blocked('RESTORE_RESOURCE_TYPE_CHANGED')
        if obj['kind'] == 'Namespace':
            if not contract_subset(current['metadata'].get('labels', {}), obj['metadata']['labels']):
                raise Blocked('RESTORE_NAMESPACE_SECURITY_CHANGED')
        elif obj['kind'] == 'NetworkPolicy':
            if current.get('spec') != obj['spec']:
                raise Blocked('RESTORE_QUARANTINE_POLICY_CHANGED')
        elif obj['kind'] == 'Restore':
            if not contract_subset(current.get('spec', {}), obj['spec']):
                raise Blocked('VELERO_RESTORE_CONTRACT_CHANGED')
            if any(current['spec'].get(k) for k in ('hooks', 'resourceModifier', 'labelSelector', 'orLabelSelectors',
                                                   'excludedNamespaces', 'excludedResources', 'restoreStatus')):
                raise Blocked('VELERO_RESTORE_UNREVIEWED_OVERRIDE')
        elif obj['kind'] == 'Job':
            if not contract_subset(current.get('spec', {}), obj['spec']):
                raise Blocked('INTEGRITY_JOB_MUTATED')
            check_probe_spec(current['spec']['template']['spec'], obj['spec']['template']['spec'])
        ann=current.get('metadata',{}).get('annotations',{})
        if ann.get('werftkern.io/operation')!=operation or ann.get('werftkern.io/desired-sha256')!=metadata['werftkern.io/desired-sha256']:
            raise Blocked('RESTORE_RESOURCE_NOT_OWNED')
        if record and record.get('uid') and record['uid']!=current['metadata']['uid']:
            raise Blocked('RESTORE_RESOURCE_UID_CHANGED')
        j['resources'][path]={'stage':'observed','uid':current['metadata']['uid']};save()
        return current

    def _bindings(self,s):
        bindings=[]
        for v in s['volumes']:
            ns=s['namespaceMapping'][v['namespace']]
            pvc=self.d.request('GET','/api/v1/namespaces/'+ns+'/persistentvolumeclaims/'+v['pvc'],notfound=True)
            if not pvc or pvc.get('status',{}).get('phase')!='Bound':raise Blocked('RESTORED_PVC_NOT_BOUND')
            if pvc.get('spec',{}).get('storageClassName')!=v['storageClass']:raise Blocked('RESTORE_STORAGE_CLASS_CHANGED')
            source=pvc.get('spec', {}).get('dataSource', {})
            if source.get('kind') != 'VolumeSnapshot' or source.get('apiGroup') != 'snapshot.storage.k8s.io' or not source.get('name'):
                raise Blocked('RESTORED_PVC_REQUIRES_CSI_SNAPSHOT_SOURCE')
            snapshot=self.d.request('GET','/apis/snapshot.storage.k8s.io/v1/namespaces/'+ns+'/volumesnapshots/'+source['name'])
            if snapshot.get('status',{}).get('readyToUse') is not True or snapshot.get('metadata',{}).get('deletionTimestamp'):
                raise Blocked('RESTORED_SNAPSHOT_NOT_READY')
            pv=self.d.request('GET','/api/v1/persistentvolumes/'+pvc['spec']['volumeName']);csi=pv.get('spec',{}).get('csi',{})
            if (pv['metadata']['uid']==v['sourcePVUID'] or csi.get('volumeHandle')==v['sourceVolumeHandle'] or
                csi.get('driver')!=v['driver'] or not csi.get('volumeHandle') or
                pv.get('spec',{}).get('claimRef',{}).get('uid')!=pvc['metadata']['uid']):
                raise Blocked('RESTORE_REUSED_SOURCE_VOLUME_OR_WRONG_DRIVER')
            if pv.get('metadata',{}).get('deletionTimestamp') or pvc['metadata'].get('deletionTimestamp'):
                raise Blocked('RESTORED_VOLUME_DELETING')
            bindings.append({'namespace':ns,'pvc':v['pvc'],'pvcUID':pvc['metadata']['uid'],
                             'pv':pv['metadata']['name'],'pvUID':pv['metadata']['uid'],'handle':csi['volumeHandle']})
        return bindings

    def step(self,s,confirm):
        digest=validate_spec(s)
        if digest!=confirm:raise Blocked('EXACT_DATA_RESTORE_CONFIRMATION_REQUIRED')
        root=self.d.root;op=fingerprint({'spec':s,'assets':self.d.assets.fingerprint})
        with lock(root/'manager.lock'):
            if self.d.uid()!=s['targetClusterUID']:raise Blocked('RESTORE_TARGET_CLUSTER_CHANGED')
            jp=root/'data-restores'/(s['operationId']+'.json')
            j=read_json(jp,private=True) if jp.exists() else None
            if j and j['operation']!=op:raise Blocked('DATA_RESTORE_IDEMPOTENCY_CONFLICT')
            if j and j['stage']=='completed':return {**j['result'],'historicallyCompleted':True}
            self._backup(s)
            if not j:
                for ns in s['namespaceMapping'].values():
                    if self.d.request('GET','/api/v1/namespaces/'+ns,notfound=True):raise Blocked('RESTORE_NAMESPACE_MUST_BE_NEW')
                j={'operation':op,'spec':s,'stage':'quarantine','resources':{},'startedAt':time.time()}
                write_json(jp,j)
            if j['stage']!='unlocking':self.d.distributed_lock('data-'+op,s['targetClusterUID'])
            def save():write_json(jp,j)
            if j['stage'] in ('quarantine', 'restoring', 'integrity'):
                for ns in s['namespaceMapping'].values():
                    namespace={'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,
                        'labels':{'pod-security.kubernetes.io/enforce':'restricted'}}}
                    self._ensure('/api/v1/namespaces/'+ns,namespace,op,j,save)
                    policy={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'werft-restore-isolation','namespace':ns},
                            'spec':{'podSelector':{},'policyTypes':['Ingress','Egress'],'ingress':[],'egress':[]}}
                    self._ensure('/apis/networking.k8s.io/v1/namespaces/'+ns+'/networkpolicies/werft-restore-isolation',policy,op,j,save)
                if j['stage'] == 'quarantine':j['stage']='restoring';save()
            restore_name='werft-'+s['operationId'];restore_path='/apis/velero.io/v1/namespaces/'+s['veleroNamespace']+'/restores/'+restore_name
            if j['stage']=='restoring':
                obj={'apiVersion':'velero.io/v1','kind':'Restore','metadata':{'name':restore_name,'namespace':s['veleroNamespace']},
                     'spec':{'backupName':s['backupName'],'includedNamespaces':sorted(s['namespaceMapping']),
                         'namespaceMapping':s['namespaceMapping'],'includeClusterResources':True,
                         'includedResources':['persistentvolumes','persistentvolumeclaims','volumesnapshots.snapshot.storage.k8s.io',
                                              'volumesnapshotcontents.snapshot.storage.k8s.io'],
                         'restorePVs':True,'existingResourcePolicy':'none'}}
                current=self._ensure(restore_path,obj,op,j,save);st=current.get('status',{})
                if st.get('phase') in ('Failed','FailedValidation','PartiallyFailed'):raise Blocked('VELERO_RESTORE_FAILED_OR_PARTIAL')
                if st.get('phase')!='Completed':return {'stage':'waiting-velero','operation':op}
                if st.get('errors',0)!=0 or st.get('warnings',0)!=0:raise Blocked('RESTORE_WARNINGS_OR_ERRORS_REQUIRE_REVIEW')
                j['bindings']=self._bindings(s);j['stage']='integrity';save()
            if j['stage']=='integrity':
                if self._bindings(s)!=j['bindings']:raise Blocked('RESTORED_BINDING_CHANGED')
                for index,v in enumerate(s['volumes']):
                    desired=probe_job(s,v,index,op);ns=desired['metadata']['namespace'];nm=desired['metadata']['name']
                    current=self._ensure('/apis/batch/v1/namespaces/'+ns+'/jobs/'+nm,desired,op,j,save)
                    actual=current.get('spec',{}).get('template',{}).get('spec',{})
                    expected=desired['spec']['template']['spec']
                    check_probe_spec(actual, expected)
                    status=current.get('status',{})
                    if status.get('failed',0):raise Blocked('RESTORED_FILE_INTEGRITY_FAILED')
                    if status.get('succeeded')!=1:return {'stage':'waiting-file-integrity','operation':op}
                    pods=self.d.request('GET','/api/v1/namespaces/'+ns+'/pods?labelSelector=job-name%3D'+nm)['items']
                    if len(pods)!=1:raise Blocked('INTEGRITY_POD_COUNT_INVALID')
                    pod=pods[0]
                    if not any(o.get('uid')==current['metadata']['uid'] and o.get('controller') is True for o in pod['metadata'].get('ownerReferences',[])):
                        raise Blocked('INTEGRITY_POD_OWNER_CHANGED')
                    if pod.get('status',{}).get('phase')!='Succeeded':raise Blocked('INTEGRITY_POD_NOT_SUCCEEDED')
                    check_probe_spec(pod.get('spec', {}), expected)
                j['result']={'stage':'completed','operation':op,'volumesChecked':len(s['volumes']),
                    'databaseConsistencyVerified':False,'productionTrafficEnabled':False,'cncfCertified':False,
                    'scope':'CSI restore plus exact selected-file SHA256 checks; no database promotion or full application DR'}
                j['stage']='unlocking';save()
            if j['stage']=='unlocking':
                self.d.unlock('data-'+op,s['targetClusterUID']);j['stage']='completed';j['completedAt']=time.time();save()
            return j['result']
