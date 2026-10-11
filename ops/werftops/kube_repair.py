"""Budgeted automatic worker replacement. No controller or stateful-node repair.

Poller steps are durable and restartable. A successful DELETE request is not
fencing: permanent provider absence must be observed before new execution.
"""
from __future__ import annotations
import copy, datetime, pathlib, time
from .common import Blocked, fingerprint, lock, read_json, write_json
from .kube_spec import validate
from .kube_provider_identity import identity, assert_identity


def ready(node):
    return bool(node) and any(c.get('type')=='Ready' and c.get('status')=='True' for c in node.get('status',{}).get('conditions',[]))

def safe_workloads(pods):
    for pod in pods:
        if pod.get('status',{}).get('phase') in ('Succeeded','Failed'):continue
        owners=pod.get('metadata',{}).get('ownerReferences',[])
        # Platform daemons necessarily have host mounts; they do not carry user
        # persistent volumes. Only kube-system daemonsets get this exemption.
        if pod['metadata'].get('namespace')=='kube-system' and any(o.get('kind')=='DaemonSet' for o in owners):continue
        if not any(o.get('kind') in ('ReplicaSet','DaemonSet') for o in owners):raise Blocked('UNMANAGED_OR_STATEFUL_POD_REQUIRES_OPERATOR')
        for v in pod.get('spec',{}).get('volumes',[]):
            if any(k in v for k in ('persistentVolumeClaim','hostPath','emptyDir','ephemeral')):
                raise Blocked('NODE_LOCAL_OR_PERSISTENT_DATA_BLOCKS_AUTOREPAIR')

def choose(plan,node_items,book,now):
    r=plan['repair'];workers=[h for h in plan['hosts'] if h['role']=='worker'];nodes={n['metadata']['name']:n for n in node_items}
    if any(t>now for t in book.get('starts',[])) or book.get('lastSample',0)>now:
        raise Blocked('CLOCK_ROLLBACK_BLOCKS_AUTOREPAIR')
    bad=[h for h in workers if not ready(nodes.get(h['name']))]
    if len(workers)-len(bad)<r['minHealthyWorkers'] or len(bad)*100>len(workers)*r['maxUnhealthyPercent']:
        book['observations']={};return None,'mass-failure-or-minimum-capacity'
    if book.get('lastSample',0)>now or now-book.get('lastSample',now)>120:
        book['observations']={}
    if now-book.get('lastSample',0)<30:return None,'observation-interval'
    book['lastSample']=now
    obs=book.setdefault('observations',{})
    for h in workers:
        if ready(nodes.get(h['name'])):obs.pop(h['name'],None)
    recent=[t for t in book.get('starts',[]) if 0<=now-t<86400];book['starts']=recent
    if len(recent)>=r['maxPerDay'] or recent and now-max(recent)<r['cooldownSeconds']:return None,'replacement-budget-or-cooldown'
    candidate=None
    for h in sorted(bad,key=lambda h:h['name']):
        n=nodes.get(h['name'])
        # An absent node object has no current identity and cannot prove ownership.
        if not n or 'serverId' not in h:continue
        uid=n['metadata']['uid'];v=obs.get(h['name'])
        if not v or v['uid']!=uid:v={'uid':uid,'first':now,'count':0};obs[h['name']]=v
        v['count']+=1
        if now-v['first']>=r['unhealthySeconds'] and v['count']>=r['observations'] and candidate is None:candidate=h
    return candidate,'candidate' if candidate else 'observing'

class Repair:
    def __init__(self,driver,machines,clock=time.time):self.d=driver;self.m=machines;self.clock=clock
    def tick(self):
        root=self.d.root
        with lock(root/'manager.lock'):
            state=read_json(root/'cluster.json',private=True);p=state['plan'];validate(p);policy=p['repair'];now=self.clock()
            if not policy['enabled']:return {'state':'disabled'}
            active=read_json(root/'active.json',private=True) if (root/'active.json').exists() else None
            if active and active['stage']!='completed':raise Blocked('LIFECYCLE_OPERATION_IN_PROGRESS')
            snapshot=self.d.snapshot()
            if snapshot['uid']!=state['clusterUID']:raise Blocked('KUBE_CLUSTER_IDENTITY_CHANGED')
            bp=root/'repair.json';book=read_json(bp,private=True) if bp.exists() else {'observations':{},'starts':[]}
            if 'operation' not in book:
                host,reason=choose(p,snapshot['nodes'],book,now);write_json(bp,book)
                if host is None:return {'state':reason,'mutations':False}
                node=next(n for n in snapshot['nodes'] if n['metadata']['name']==host['name'])
                if state['nodeUIDs'].get(host['name'])!=node['metadata']['uid']:raise Blocked('NODE_REUSED_OR_REPLACED_OUTSIDE_MANAGER')
                op=fingerprint({'clusterUID':state['clusterUID'],'nodeUID':node['metadata']['uid'],'providerID':host['serverId']})
                # No automatic expiry: a stuck destructive operation needs review.
                self.d.distributed_lock('repair-'+op,state['clusterUID'])
                book['operation']={'providerCredential':identity(self.m),'id':op,'old':host,'nodeUID':node['metadata']['uid'],'stage':'selected','machine':{},'startedAt':now}
                book['starts'].append(now);write_json(bp,book)
            j=book['operation'];op=j['id'];old=j['old']
            assert_identity(self.m,j)
            self.d.distributed_lock('repair-'+op,state['clusterUID'])
            def save():write_json(bp,book)
            nodepath='/api/v1/nodes/'+old['name']
            if j['stage']=='selected':
                current=self.d.request('GET',nodepath)
                if current['metadata']['uid']!=j['nodeUID']:raise Blocked('NODE_UID_CHANGED')
                if ready(current):
                    if j.get('cordonedByOperation') and not j.get('wasUnschedulable',False):
                        current.setdefault('spec',{})['unschedulable']=False
                        self.d.request('PUT',nodepath,current)
                    self.d.unlock('repair-'+op,state['clusterUID']);book.pop('operation');save();return {'state':'recovered-before-destruction'}
                if 'wasUnschedulable' not in j:
                    j['wasUnschedulable']=current.get('spec',{}).get('unschedulable',False)
                    j['cordonedByOperation']=True;save()
                current.setdefault('spec',{})['unschedulable']=True
                self.d.request('PUT',nodepath,current)
                query='/api/v1/pods?fieldSelector=spec.nodeName%3D'+old['name']
                safe_workloads(self.d.request('GET',query)['items'])
                attachments=self.d.request('GET','/apis/storage.k8s.io/v1/volumeattachments')['items']
                if any(v.get('spec',{}).get('nodeName')==old['name'] for v in attachments):
                    raise Blocked('VOLUME_ATTACHMENT_BLOCKS_AUTOREPAIR')
                volumes=self.d.request('GET','/api/v1/persistentvolumes')['items']
                if any(v.get('spec',{}).get('local') or v.get('spec',{}).get('hostPath') for v in volumes):
                    raise Blocked('LOCAL_PV_REQUIRES_OPERATOR_REVIEW')
                self.m.ownership(self.m.get(old['serverId']),p['name'],'worker',old.get('pool','default'),old['name'])
                self.m.preflight(policy['template'])
                j['stage']='delete-intent';save()
                # Timeout may mean success. A retry observes status and never repeats
                # a destructive request against a possibly repurposed identity.
                try:self.m.api.call('DELETE','/servers/'+str(old['serverId']))
                except Blocked:pass
            if j['stage']=='delete-intent':
                server=self.m.get(old['serverId'])
                if server is not None:
                    self.m.ownership(server,p['name'],'worker',old.get('pool','default'),old['name'])
                    return {'state':'waiting-for-permanent-provider-deletion','operation':op}
                j['stage']='fenced';j['providerAbsentAt']=now;save()
            if j['stage']=='fenced':
                current=self.d.request('GET',nodepath,notfound=True)
                if current:
                    if current['metadata']['uid']!=j['nodeUID']:raise Blocked('REFUSING_DELETE_OF_NEW_NODE_UID')
                    self.d.request('DELETE',nodepath,{'apiVersion':'v1','kind':'DeleteOptions','preconditions':{'uid':j['nodeUID']}})
                j['stage']='creating';save()
            if j['stage']=='creating':
                replacement=self.m.create(p['name'],'worker',old.get('pool','default'),op,policy['template'],root/'repair-machines'/op,j['machine'],save)
                j['new']=replacement;j['stage']='preparing';save()
            if j['stage']=='preparing':
                target=copy.deepcopy(p);target['hosts']=[h for h in target['hosts'] if h['name']!=old['name']]+[j['new']]
                self.d.fresh_hosts(target,[j['new']['name']])
                j['stage']='joining';save()
            if j['stage']=='joining':
                target=copy.deepcopy(p);target['hosts']=[h for h in target['hosts'] if h['name']!=old['name']]+[j['new']]
                validate(target);self.d.apply(target)
                result=self.d.verify(target,state['clusterUID'])
                if result['nodeUIDs'].get(j['new']['name'])==j['nodeUID']:raise Blocked('REPLACEMENT_NODE_UID_REUSED')
                j['target']=target;j['result']=result;j['stage']='commit';save()
            if j['stage']=='commit':
                write_json(root/'cluster.json',{'format':'werftkern-kube-state/v1','plan':j['target'],**j['result']})
                self.d.unlock('repair-'+op,state['clusterUID'])
                write_json(root/'repair-history'/(op+'.json'),j)
                book.pop('operation');book['observations']={};save()
            return {'state':'replacement-ready','operation':op,'productionQualified':False}
