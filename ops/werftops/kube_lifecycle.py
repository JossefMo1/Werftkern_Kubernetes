"""Serialized, resumable Kubernetes lifecycle; explicit acceptance of host changes."""
from __future__ import annotations
import copy, pathlib, time
from .common import Blocked, fingerprint, lock, read_json, write_json
from .kube_spec import validate,validate_change

class Lifecycle:
    def __init__(self,driver):
        self.d=driver;self.root=driver.root;self.state_path=self.root/'cluster.json'
    def state(self):return read_json(self.state_path,private=True) if self.state_path.exists() else None
    def apply(self,plan,confirm):
        digest=validate(plan)
        if confirm!=digest:raise Blocked('EXACT_PLAN_CONFIRMATION_REQUIRED')
        with lock(self.root/'manager.lock'):
            old=self.state();edges=self.d.assets.data['upgradeEdges']
            removed,added=validate_change(old['plan'],plan,edges) if old else ([],[])
            operation=fingerprint({'plan':plan,'assets':self.d.assets.fingerprint})
            jp=self.root/'active.json';j=read_json(jp,private=True) if jp.exists() else None
            if j and j['operation']!=operation and j['stage']!='completed':raise Blocked('UNFINISHED_OTHER_OPERATION')
            if not j or j['operation']!=operation:
                j={'format':'werftkern-kube-operation/v1','operation':operation,'plan':plan,
                   'sourceUID':old['clusterUID'] if old else None,'stage':'prepared','startedAt':time.time(),
                   'sourcePlan':old['plan'] if old else None,'resetDone':[]}
                write_json(jp,j)
            if j['stage']=='completed':
                return {'operation':operation,'historicallyCompleted':True,'current':self.d.verify(plan,old['clusterUID'] if old else None)}
            uid=j['sourceUID']
            if uid:self.d.distributed_lock(operation,uid)
            if j['stage']=='prepared':
                if not old:self.d.fresh_hosts(plan)
                elif added:self.d.fresh_hosts(plan,added)
                if old:
                    self.d.verify(old['plan'],uid)
                    if old['plan']['version']!=plan['version']:
                        j['backup']=self.d.backup(old['plan'],self.root/'backups'/operation)
                j['stage']='backup-ready';write_json(jp,j)
            if j['stage']=='backup-ready':
                # Removal is never a bare deletion of a host from a config. Ask
                # the Kubernetes eviction API first; PDB/local-data errors stop.
                if removed and j['resetDone']!=removed:
                    for node in removed:
                        self.d.drain(node,old['nodeUIDs'][node])
                    reset_plan=copy.deepcopy(old['plan'])
                    self.d.apply(reset_plan,reset=removed)
                    j['resetDone']=removed;write_json(jp,j)
                j['stage']='applying';write_json(jp,j)
            if j['stage']=='applying':
                # k0sctl is a declarative reconciler. Its own host state is read on
                # replay; we do not replay arbitrary remote shell or create VMs.
                self.d.apply(plan)
                j['stage']='observing';write_json(jp,j)
            if j['stage']=='observing':
                self.d.capture_kubeconfig(plan)
                result=self.d.verify(plan,uid)
                for _ in range(2):
                    time.sleep(1)
                    result=self.d.verify(plan,result['clusterUID'])
                if not uid:
                    uid=result['clusterUID'];j['sourceUID']=uid;write_json(jp,j)
                    self.d.distributed_lock(operation,uid)
                write_json(self.state_path,{'format':'werftkern-kube-state/v1','plan':plan,**result})
                j['stage']='unlocking';write_json(jp,j)
            if j['stage']=='unlocking':
                self.d.unlock(operation,j['sourceUID'])
                j['stage']='completed';j['completedAt']=time.time();write_json(jp,j)
            return {'operation':operation,'stage':j['stage'],'productionQualified':False}
    def backup(self):
        with lock(self.root/'manager.lock'):
            s=self.state()
            if not s:raise Blocked('CLUSTER_NOT_CREATED')
            op='backup-'+str(time.time_ns());self.d.distributed_lock(op,s['clusterUID'])
            # Intentionally leave a lock if a backup fails; operators investigate.
            r=self.d.backup(s['plan'],self.root/'backups'/op)
            self.d.unlock(op,s['clusterUID']);return r
    def inspect(self):
        s=self.state()
        if not s:raise Blocked('CLUSTER_NOT_CREATED')
        result=self.d.verify(s['plan'],s['clusterUID'])
        return {**result,'productionQualified':False,'engine':'kubernetes-k0s'}
