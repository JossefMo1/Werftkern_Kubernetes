"""Opt-in single-writer recovery for retained Hetzner CSI volumes.

This does not infer that replicas of a database are interchangeable. It supports
explicitly enrolled one-replica StatefulSets only. Provider deletion is observed
before out-of-service eviction; CSI finalizers are NEVER removed by this code.
"""
from __future__ import annotations

import copy
import re
import time
from .common import Blocked, fingerprint, lock, read_json, write_json, sha
from .kube_spec import fields, name, integer, validate
from .kube_repair import ready
from .kube_fencing import Fence
from .kube_provider_identity import assert_identity
from .kube_controller_recovery import validate_request as validate_controller_request

FORMAT = 'werftkern-stateful-recovery/v1'
CSI = 'csi.hetzner.cloud'
TAINT = 'node.kubernetes.io/out-of-service'


def validate_request(r):
    fields(r, ('format', 'clusterUID', 'sourcePlanHash', 'worker', 'nodeUID', 'template',
               'statefulSets', 'acceptDeleteAndCosts'))
    if r['format'] != FORMAT or not isinstance(r['nodeUID'], str) or not r['nodeUID']:
        raise Blocked('STATEFUL_RECOVERY_CONTRACT_INVALID')
    validate_controller_request({'format': 'werftkern-controller-recovery/v1', 'clusterUID': r['clusterUID'],
        'sourcePlanHash': r['sourcePlanHash'], 'controller': r['worker'], 'expectedPeerURL': 'https://10.0.0.1:2380',
        'template': r['template'], 'acceptDeleteAndCosts': r['acceptDeleteAndCosts']})
    if not isinstance(r['statefulSets'], list) or not 1 <= len(r['statefulSets']) <= 20:
        raise Blocked('EXPLICIT_STATEFULSET_ALLOWLIST_REQUIRED')
    seen = set()
    for item in r['statefulSets']:
        fields(item, ('namespace', 'name', 'uid'))
        for key in ('namespace', 'name'): name(item[key])
        if not isinstance(item['uid'], str) or not item['uid'] or (item['namespace'], item['name']) in seen:
            raise Blocked('STATEFULSET_ALLOWLIST_IDENTITY_INVALID')
        seen.add((item['namespace'], item['name']))
    return fingerprint(r)


class StatefulRecovery:
    def __init__(self, driver, machines, clock=time.time):
        self.d, self.m, self.clock = driver, machines, clock
        self.fence = Fence(machines, clock)

    def _volume(self, volume_id):
        integer(volume_id, 1, 2**63 - 1)
        obj = self.m.api.call('GET', '/volumes/' + str(volume_id)).get('volume')
        if not obj or obj.get('id') != volume_id:
            raise Blocked('PROVIDER_VOLUME_MISSING_OR_REPLACED')
        return obj

    def inventory(self, p, host, node_uid, cluster_uid, allowlist, template):
        n = self.d.request('GET', '/api/v1/nodes/' + host['name'])
        if n['metadata']['uid'] != node_uid or n.get('spec', {}).get('providerID') != 'hcloud://' + str(host['serverId']):
            raise Blocked('STATEFUL_NODE_PROVIDER_IDENTITY_MISMATCH')
        if ready(n):
            raise Blocked('STATEFUL_SOURCE_NOT_FAILED')
        if any(t.get('key') == TAINT for t in n.get('spec', {}).get('taints', [])):
            raise Blocked('SOURCE_ALREADY_OUT_OF_SERVICE_WITHOUT_OUR_FENCE')
        self.d.verify_detach_policy(p)  # Inspect live controller arguments, not only desired config.
        driver = self.d.request('GET', '/apis/storage.k8s.io/v1/csidrivers/' + CSI)
        if driver.get('spec', {}).get('attachRequired') is not True:
            raise Blocked('CSI_ATTACHMENT_CONTRACT_REQUIRED')
        pods = self.d.request('GET', '/api/v1/pods?fieldSelector=spec.nodeName%3D' + host['name'])['items']
        pvs = self.d.request('GET', '/api/v1/persistentvolumes')['items']
        if any(v.get('spec', {}).get('local') or v.get('spec', {}).get('hostPath') for v in pvs):
            raise Blocked('LOCAL_PV_DATA_PREVENTS_AUTOMATIC_HOST_DELETION')
        allowed = {(x['namespace'], x['name']): x['uid'] for x in allowlist}
        workloads, volumes, claim_writers = {}, {}, {}
        for pod in pods:
            if pod.get('status', {}).get('phase') in ('Succeeded', 'Failed'): continue
            meta = pod['metadata']; ns = meta['namespace']; spec = pod.get('spec', {})
            owners = [o for o in meta.get('ownerReferences', []) if o.get('controller') is True]
            if len(owners) == 1 and owners[0].get('kind') == 'DaemonSet' and ns == 'kube-system':
                if any('persistentVolumeClaim' in v for v in spec.get('volumes', [])):
                    raise Blocked('SYSTEM_DAEMON_HAS_UNREVIEWED_PVC')
                continue
            if len(owners) != 1 or owners[0].get('kind') != 'StatefulSet':
                raise Blocked('ALL_USER_PODS_MUST_BE_ENROLLED_STATEFULSETS')
            o = owners[0]; key = (ns, o['name'])
            if allowed.get(key) != o['uid']:
                raise Blocked('STATEFULSET_NOT_IN_EXPLICIT_ALLOWLIST')
            path = '/apis/apps/v1/namespaces/' + ns + '/statefulsets/' + o['name']
            sts = self.d.request('GET', path)
            if (sts['metadata']['uid'] != o['uid'] or sts.get('spec', {}).get('replicas') != 1 or
                sts['metadata'].get('annotations', {}).get('werftkern.io/recovery-profile') != 'hetzner-csi-single-writer'):
                raise Blocked('STATEFULSET_SINGLE_WRITER_ENROLLMENT_REQUIRED')
            if spec.get('hostNetwork') or spec.get('hostPID') or spec.get('hostIPC'):
                raise Blocked('HOST_NAMESPACE_WORKLOAD_NOT_SUPPORTED')
            for t in spec.get('tolerations', []):
                if t.get('key') in (None, '', TAINT) and t.get('operator', 'Equal') == 'Exists':
                    raise Blocked('OUT_OF_SERVICE_TOLERATION_PREVENTS_RECOVERY')
                if t.get('key') == TAINT:
                    raise Blocked('OUT_OF_SERVICE_TOLERATION_PREVENTS_RECOVERY')
            refs = []
            for vol in spec.get('volumes', []):
                if any(k in vol for k in ('emptyDir', 'hostPath', 'ephemeral', 'csi', 'nfs')):
                    raise Blocked('UNMANAGED_LOCAL_OR_INLINE_VOLUME')
                if 'persistentVolumeClaim' not in vol: continue
                pvc_name = vol['persistentVolumeClaim']['claimName']
                pvc = self.d.request('GET', '/api/v1/namespaces/' + ns + '/persistentvolumeclaims/' + pvc_name)
                if pvc.get('status', {}).get('phase') != 'Bound' or pvc['metadata'].get('deletionTimestamp'):
                    raise Blocked('PVC_NOT_BOUND_OR_DELETING')
                pv_name = pvc.get('spec', {}).get('volumeName')
                pv = next((v for v in pvs if v['metadata']['name'] == pv_name), None)
                if not pv: raise Blocked('BOUND_PV_MISSING')
                ps = pv.get('spec', {}); csi = ps.get('csi', {}); handle = csi.get('volumeHandle', '')
                if (csi.get('driver') != CSI or not re.fullmatch(r'[1-9][0-9]*', handle) or
                    ps.get('claimRef', {}).get('uid') != pvc['metadata']['uid'] or
                    ps.get('claimRef', {}).get('name') != pvc_name or ps.get('claimRef', {}).get('namespace') != ns or
                    ps.get('persistentVolumeReclaimPolicy') != 'Retain' or
                    ps.get('accessModes') not in (['ReadWriteOnce'], ['ReadWriteOncePod']) or
                    ps.get('volumeMode', 'Filesystem') != 'Filesystem' or pv['metadata'].get('deletionTimestamp')):
                    raise Blocked('RETAINED_EXCLUSIVE_HETZNER_CSI_VOLUME_REQUIRED')
                if pv['metadata'].get('annotations', {}).get('werftkern.io/recovery-cluster-uid') != cluster_uid:
                    raise Blocked('PV_NOT_ENROLLED_FOR_THIS_CLUSTER')
                provider = self._volume(int(handle))
                if (provider.get('server') not in (None, host['serverId']) or
                    provider.get('location', {}).get('name') != template['location'] or
                    provider.get('labels', {}).get('werftkern-cluster') != p['name'] or
                    provider.get('labels', {}).get('werftkern-pv-uid') != pv['metadata']['uid']):
                    raise Blocked('PROVIDER_VOLUME_TOPOLOGY_OR_OWNERSHIP_MISMATCH')
                record = {'namespace': ns, 'pvc': pvc_name, 'pvcUID': pvc['metadata']['uid'],
                          'pv': pv_name, 'pvUID': pv['metadata']['uid'], 'volumeId': int(handle),
                          'size': provider.get('size'), 'location': template['location']}
                claim=(ns,pvc_name)
                if claim in claim_writers and claim_writers[claim]!=meta['uid']:
                    raise Blocked('MULTIPLE_PODS_SHARE_SINGLE_WRITER_VOLUME')
                claim_writers[claim]=meta['uid']
                existing = volumes.get(handle)
                if existing and existing != record: raise Blocked('VOLUME_HANDLE_ALIASED')
                volumes[handle] = record; refs.append(handle)
            if not refs: raise Blocked('STATEFUL_RECOVERY_REQUIRES_PERSISTENT_CLAIMS')
            workloads[path] = {'path': path, 'uid': o['uid'], 'specHash': fingerprint(sts['spec']),
                               'oldPodUID': meta['uid'], 'podName': meta['name'], 'namespace': ns, 'volumeRefs':refs}
        if set((x['namespace'], x['path'].rsplit('/', 1)[1]) for x in workloads.values()) != set(allowed):
            raise Blocked('ALLOWLIST_MUST_EXACTLY_MATCH_FAILED_NODE_WORKLOADS')
        for other in self.d.request('GET','/api/v1/pods')['items']:
            if other.get('status',{}).get('phase') in ('Succeeded','Failed'):continue
            for volume in other.get('spec',{}).get('volumes',[]):
                claim=(other['metadata']['namespace'],volume.get('persistentVolumeClaim',{}).get('claimName'))
                if claim in claim_writers and claim_writers[claim]!=other['metadata']['uid']:
                    raise Blocked('MULTIPLE_PODS_SHARE_SINGLE_WRITER_VOLUME')
        attachments = self.d.request('GET', '/apis/storage.k8s.io/v1/volumeattachments')['items']
        known = {v['pv'] for v in volumes.values()}
        if any(a.get('spec', {}).get('nodeName') == host['name'] and
               (a['spec'].get('attacher') != CSI or a['spec'].get('source', {}).get('persistentVolumeName') not in known)
               for a in attachments):
            raise Blocked('UNKNOWN_VOLUME_ATTACHMENT_ON_SOURCE')
        return {'volumes': sorted(volumes.values(), key=lambda v: v['pv']),
                'workloads': sorted(workloads.values(), key=lambda v: v['path'])}

    def _verify_volumes(self, inventory, old_server, cluster, target):
        allowed_servers = {h['serverId'] for h in target['hosts'] if h['role'] == 'worker' and 'serverId' in h}
        for v in inventory['volumes']:
            current = self._volume(v['volumeId'])
            if (current.get('server') == old_server or current.get('server') not in ({None} | allowed_servers) or
                current.get('size') != v['size'] or current.get('location', {}).get('name') != v['location'] or
                current.get('labels', {}).get('werftkern-cluster') != cluster or
                current.get('labels', {}).get('werftkern-pv-uid') != v['pvUID']):
                raise Blocked('VOLUME_IDENTITY_OR_ATTACHMENT_CHANGED_UNEXPECTEDLY')
            pvc = self.d.request('GET', '/api/v1/namespaces/' + v['namespace'] + '/persistentvolumeclaims/' + v['pvc'])
            pv = self.d.request('GET', '/api/v1/persistentvolumes/' + v['pv'])
            if (pvc['metadata']['uid'] != v['pvcUID'] or pv['metadata']['uid'] != v['pvUID'] or
                pvc.get('spec', {}).get('volumeName') != v['pv'] or pv.get('spec', {}).get('csi', {}).get('volumeHandle') != str(v['volumeId'])):
                raise Blocked('PVC_PV_IDENTITY_CHANGED_DURING_RECOVERY')

    def step(self, r, confirm):
        if validate_request(r) != confirm: raise Blocked('EXACT_STATEFUL_RECOVERY_CONFIRMATION_REQUIRED')
        root = self.d.root
        operation = fingerprint({'request': r, 'assets': self.d.assets.fingerprint})
        with lock(root / 'manager.lock'):
            state = read_json(root / 'cluster.json', private=True)
            jp = root / 'stateful-recovery.json'
            j = read_json(jp, private=True) if jp.exists() else None
            if j and j['operation'] != operation:
                if j['stage'] != 'completed': raise Blocked('OTHER_STATEFUL_RECOVERY_IN_PROGRESS')
                j = None
            if j and j['stage'] == 'completed':
                return {'stage': 'completed', 'operation': operation, 'historicallyCompleted': True}
            if not j:
                p = state['plan']; validate(p)
                if state['clusterUID'] != r['clusterUID'] or fingerprint(p) != r['sourcePlanHash']:
                    raise Blocked('STATEFUL_RECOVERY_SOURCE_CHANGED')
                if state['nodeUIDs'].get(r['worker']) != r['nodeUID']:
                    raise Blocked('SOURCE_NODE_UID_CHANGED')
                old = next((h for h in p['hosts'] if h['name'] == r['worker'] and h['role'] == 'worker'), None)
                if not old or 'serverId' not in old: raise Blocked('MANAGED_HETZNER_WORKER_REQUIRED')
                self.d.verify_detach_policy(p)
                inventory = self.inventory(p, old, r['nodeUID'], r['clusterUID'], r['statefulSets'], r['template'])
                self.m.preflight(r['template'])
                self.d.distributed_lock('stateful-' + operation, state['clusterUID'])
                j = {'operation': operation, 'stage': 'fencing', 'source': state, 'old': old, 'inventory': inventory, 'request': r,
                     'fence': {}, 'machine': {}, 'startedAt': self.clock()}
                write_json(jp, j)
            p, old, uid = j['source']['plan'], j['old'], j['source']['clusterUID']
            if state['clusterUID'] != uid or (state['plan'] != p and state['plan'] != j.get('target')):
                raise Blocked('STATEFUL_RECOVERY_SOURCE_CHANGED')
            if j['fence']:assert_identity(self.m,j['fence'])
            if self.clock() < j['startedAt']: raise Blocked('RECOVERY_CLOCK_ROLLBACK')
            if j['stage'] != 'unlocking': self.d.distributed_lock('stateful-' + operation, uid)
            def save(): write_json(jp, j)
            volumes = [v['volumeId'] for v in j['inventory']['volumes']]
            nodepath = '/api/v1/nodes/' + old['name']
            if j['stage'] == 'fencing':
                if not j['fence']:
                    if self.inventory(p, old, r['nodeUID'], uid, r['statefulSets'], r['template']) != j['inventory']:
                        raise Blocked('STATEFUL_INVENTORY_CHANGED_BEFORE_DELETION')
                    node = self.d.request('GET', nodepath)
                    if node['metadata']['uid'] != r['nodeUID']: raise Blocked('SOURCE_NODE_UID_CHANGED')
                    node.setdefault('spec', {})['unschedulable'] = True
                    self.d.request('PUT', nodepath, node)
                if not self.fence.step(p['name'], old, operation, volumes, j['fence'], save):
                    return {'stage': 'waiting-provider-fence', 'operation': operation}
                j['stage'] = 'creating'; save()
            if j['stage'] == 'creating':
                replacement = self.m.create(p['name'], 'worker', old.get('pool', 'default'), operation, r['template'],
                                            root / 'stateful-machines' / operation, j['machine'], save)
                target = copy.deepcopy(p); target['hosts'] = [h for h in p['hosts'] if h['name'] != old['name']] + [replacement]
                validate(target)
                if replacement['serverId'] == old['serverId']: raise Blocked('REPLACEMENT_ID_REUSED')
                j.update(new=replacement, target=target, stage='preparing'); save()
            if j['stage'] == 'preparing':
                self.d.fresh_hosts(j['target'], [j['new']['name']]); j['stage'] = 'joining'; save()
            if j['stage'] == 'joining':
                self.d.apply(j['target']); self.d.verify(j['target'], uid)
                j['stage'] = 'evicting'; save()
            if j['stage'] == 'evicting':
                if not self.fence.step(p['name'], old, operation, volumes, j['fence'], save):
                    raise Blocked('PERMANENT_FENCE_REQUIRED_BEFORE_EVICTION')
                self.d.verify_detach_policy(j['target'])
                current = self.d.request('GET', nodepath)
                if current['metadata']['uid'] != r['nodeUID']: raise Blocked('REFUSING_TAINT_OF_NEW_NODE_UID')
                taints = current.setdefault('spec', {}).setdefault('taints', [])
                expected = {'key': TAINT, 'value': 'werftkern-fenced', 'effect': 'NoExecute'}
                existing = [x for x in taints if x.get('key') == TAINT]
                if existing and existing != [expected]: raise Blocked('FOREIGN_OUT_OF_SERVICE_TAINT')
                if not existing: taints.append(expected)
                self.d.request('PUT', nodepath, current)
                j['stage'] = 'observing-detach'; save()
            if j['stage'] == 'observing-detach':
                attachments = self.d.request('GET', '/apis/storage.k8s.io/v1/volumeattachments')['items']
                if any(a.get('spec', {}).get('nodeName') == old['name'] for a in attachments):
                    return {'stage': 'waiting-csi-detach', 'operation': operation}
                self._verify_volumes(j['inventory'], old['serverId'], p['name'], j['target'])
                for w in j['inventory']['workloads']:
                    pod = self.d.request('GET', '/api/v1/namespaces/' + w['namespace'] + '/pods/' + w['podName'], notfound=True)
                    if pod and pod['metadata']['uid'] == w['oldPodUID']:
                        return {'stage': 'waiting-old-pod-removal', 'operation': operation}
                oldnode = self.d.request('GET', nodepath, notfound=True)
                if oldnode:
                    if oldnode['metadata']['uid'] != r['nodeUID']: raise Blocked('REFUSING_DELETE_OF_NEW_NODE_UID')
                    self.d.request('DELETE', nodepath, {'apiVersion': 'v1', 'kind': 'DeleteOptions',
                        'preconditions': {'uid': r['nodeUID'], 'resourceVersion': oldnode['metadata']['resourceVersion']}})
                j['stage'] = 'verifying'; save()
            if j['stage'] == 'verifying':
                self._verify_volumes(j['inventory'], old['serverId'], p['name'], j['target'])
                mounted_nodes={}
                for w in j['inventory']['workloads']:
                    sts = self.d.request('GET', w['path']); status = sts.get('status', {})
                    if sts['metadata']['uid'] != w['uid'] or fingerprint(sts['spec']) != w['specHash']:
                        raise Blocked('STATEFULSET_CHANGED_DURING_RECOVERY')
                    pod = self.d.request('GET', '/api/v1/namespaces/' + w['namespace'] + '/pods/' + w['podName'], notfound=True)
                    if (status.get('observedGeneration') != sts['metadata'].get('generation') or status.get('readyReplicas') != 1 or
                        not pod or pod['metadata']['uid'] == w['oldPodUID'] or pod.get('spec', {}).get('nodeName') == old['name'] or
                        not any(c.get('type') == 'Ready' and c.get('status') == 'True' for c in pod.get('status', {}).get('conditions', []))):
                        return {'stage': 'waiting-stateful-readiness', 'operation': operation}
                    if not any(owner.get('uid')==w['uid'] and owner.get('controller') is True for owner in pod['metadata'].get('ownerReferences',[])):
                        raise Blocked('REPLACEMENT_POD_OWNER_CHANGED')
                    for handle in w['volumeRefs']:mounted_nodes[handle]=pod['spec']['nodeName']
                attachments = self.d.request('GET', '/apis/storage.k8s.io/v1/volumeattachments')['items']
                for v in j['inventory']['volumes']:
                    attached = [a for a in attachments if a.get('spec', {}).get('source', {}).get('persistentVolumeName') == v['pv']]
                    if len(attached) != 1 or attached[0].get('status', {}).get('attached') is not True or attached[0].get('metadata', {}).get('deletionTimestamp'):
                        return {'stage': 'waiting-new-csi-attachment', 'operation': operation}
                    va = attached[0]; target_host = next((h for h in j['target']['hosts'] if h['name'] == va['spec'].get('nodeName')), None)
                    if (va['spec'].get('nodeName')!=mounted_nodes.get(str(v['volumeId'])) or not target_host or target_host.get('role') != 'worker' or 'serverId' not in target_host or
                        self._volume(v['volumeId']).get('server') != target_host['serverId'] or va['spec'].get('attacher') != CSI):
                        raise Blocked('NEW_CSI_ATTACHMENT_PROVIDER_MISMATCH')
                result = self.d.verify(j['target'], uid)
                j['result'] = result; j['stage'] = 'commit'; save()
            if j['stage'] == 'commit':
                write_json(root / 'cluster.json', {'format': 'werftkern-kube-state/v1', 'plan': j['target'], **j['result']})
                j['stage'] = 'unlocking'; save()
            if j['stage'] == 'unlocking':
                self.d.unlock('stateful-' + operation, uid)
                j['stage'] = 'completed'; j['completedAt'] = self.clock(); save()
                write_json(root / 'stateful-history' / (operation + '.json'), j)
            return {'stage': j['stage'], 'operation': operation, 'applicationIntegrityVerified': False, 'productionQualified': False}
