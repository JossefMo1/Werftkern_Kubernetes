"""Conservative control-plane disaster recovery from an encrypted k0s backup.

A restore is not a retryable ordinary mutation. Once k0sctl may have started a
restore, a second invocation observes the target and never blindly replays it.
Application PersistentVolumes are outside this workflow by design.
"""
from __future__ import annotations
import pathlib, tempfile, time
from .common import Blocked, digest_file, fingerprint, lock, private_read, read_json, write_json
from .kube_spec import validate

FORMAT='werftkern-kube-backup/v2'

class Restore:
    def __init__(self, driver):
        self.d=driver; self.root=driver.root

    def plan(self, target_plan, backup_dir):
        validate(target_plan)
        backup_dir=pathlib.Path(backup_dir).absolute()
        receipt=read_json(backup_dir/'receipt.json', private=True)
        if receipt.get('format')!=FORMAT: raise Blocked('BACKUP_RECEIPT_V2_REQUIRED')
        required=('clusterUID','version','apiEndpoint','sha256','sourcePlanHash','sourceControllerAddresses')
        if any(k not in receipt for k in required): raise Blocked('BACKUP_RECEIPT_INCOMPLETE')
        archive=backup_dir/'control-plane.tar.gz.age'
        if archive.is_symlink() or not archive.is_file(): raise Blocked('ENCRYPTED_BACKUP_ARCHIVE_REQUIRED')
        if digest_file(archive)!=receipt['sha256']: raise Blocked('BACKUP_ARCHIVE_HASH_MISMATCH')
        if target_plan['version']!=receipt['version']: raise Blocked('RESTORE_VERSION_MUST_MATCH_BACKUP')
        if target_plan['apiEndpoint']!=receipt['apiEndpoint']: raise Blocked('RESTORE_API_ENDPOINT_MUST_NOT_CHANGE')
        target_controllers=sorted(h['address'] for h in target_plan['hosts'] if h['role']=='controller')
        if set(target_controllers)&set(receipt['sourceControllerAddresses']):
            raise Blocked('RESTORE_REQUIRES_NEW_CONTROLLER_HOSTS')
        operation=fingerprint({'receipt':receipt,'targetPlan':target_plan,'assets':self.d.assets.fingerprint})
        return operation,receipt,archive

    def apply(self,target_plan,backup_dir,identity_file,confirm):
        operation,receipt,archive=self.plan(target_plan,backup_dir)
        if confirm!=operation: raise Blocked('EXACT_RESTORE_CONFIRMATION_REQUIRED')
        identity=pathlib.Path(identity_file).absolute(); private_read(identity,1024*1024)
        with lock(self.root/'manager.lock'):
            jp=self.root/'restore.json'
            j=read_json(jp,private=True) if jp.exists() else None
            if j and j.get('operation')!=operation:
                raise Blocked('UNFINISHED_OTHER_RESTORE')
            if (self.root/'cluster.json').exists():
                committed=read_json(self.root/'cluster.json',private=True)
                expected={'format':'werftkern-kube-state/v1','plan':target_plan,**(j or {}).get('observed',{})}
                if not j or j['stage'] not in ('observed','completed') or committed!=expected:
                    raise Blocked('RESTORE_TARGET_MANAGER_ALREADY_HAS_CLUSTER')
                if j['stage']=='observed':
                    j['stage']='completed';j['completedAt']=time.time();write_json(jp,j)
                return {'operation':operation,'stage':'completed','historicallyCompleted':True,
                        'clusterUID':receipt['clusterUID'],'applicationVolumesRestored':False,'productionQualified':False}
            if not j:
                self.d.fresh_hosts(target_plan)
                j={'format':'werftkern-kube-restore/v1','operation':operation,'stage':'prepared',
                   'clusterUID':receipt['clusterUID'],'targetPlan':target_plan,'backupSHA256':receipt['sha256'],
                   'startedAt':time.time()}
                write_json(jp,j,exclusive=True)
            if j['stage']=='completed':
                return {'operation':operation,'stage':'completed','historicallyCompleted':True,
                        'clusterUID':receipt['clusterUID'],'applicationVolumesRestored':False,'productionQualified':False}
            if j['stage']=='prepared':
                # Persist intent before any command that can mutate remote hosts.
                j['stage']='restoring';write_json(jp,j)
                with tempfile.TemporaryDirectory(dir=self.root,prefix='restore-') as td:
                    plain=pathlib.Path(td)/'control-plane.tar.gz'
                    self.d.command('age',['--decrypt','--identity',identity,'--output',plain,archive],timeout=1800)
                    if plain.is_symlink() or not plain.is_file() or plain.stat().st_size==0:
                        raise Blocked('DECRYPTED_BACKUP_INVALID')
                    # k0sctl owns restore semantics. This call MUST NOT be blindly
                    # replayed after an ambiguous transport/process result.
                    self.d.apply(target_plan,restore=str(plain))
                j['stage']='observing';write_json(jp,j)
            elif j['stage']=='restoring':
                # A previous k0sctl invocation may already have restored the cluster.
                # Only observation is allowed here; another restore could corrupt it.
                try:
                    self.d.capture_kubeconfig(target_plan)
                    observed=self.d.verify(target_plan,receipt['clusterUID'])
                except Exception:
                    raise Blocked('RESTORE_OUTCOME_AMBIGUOUS_REQUIRES_OPERATOR_REVIEW') from None
                j['observed']=observed;j['stage']='observed';write_json(jp,j)
            if j['stage']=='observing':
                self.d.capture_kubeconfig(target_plan)
                observed=self.d.verify(target_plan,receipt['clusterUID'])
                j['observed']=observed;j['stage']='observed';write_json(jp,j)
            if j['stage']=='observed':
                write_json(self.root/'cluster.json',{'format':'werftkern-kube-state/v1','plan':target_plan,**j['observed']},exclusive=True)
                j['stage']='completed';j['completedAt']=time.time();write_json(jp,j)
            return {'operation':operation,'stage':j['stage'],'clusterUID':receipt['clusterUID'],
                    'applicationVolumesRestored':False,
                    'warning':'k0s control-plane state restored. PersistentVolumes and external databases require separate restore/verification.',
                    'productionQualified':False}
