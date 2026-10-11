"""Durable cloud-backed worker scaling for Hetzner-managed workers.

Scaling Kubernetes and deleting provider machines are separate irreversible
boundaries. Scale-down removes/drains Kubernetes nodes first, then issues at
most one provider DELETE per persisted intent and observes permanent absence.
"""
from __future__ import annotations
import copy, pathlib, time
from decimal import Decimal
from .common import Blocked, fingerprint, lock, read_json, write_json
from .kube_provider_identity import identity, assert_identity
from .kube_spec import fields, integer, validate

FORMAT='werftkern-kube-cloud-scale/v1'

def validate_request(req):
    fields(req,('format','desiredWorkers','template','acceptCreateCosts','acceptDelete','maxAddedMonthlyEUR'))
    if req['format']!=FORMAT: raise Blocked('CLOUD_SCALE_FORMAT_INVALID')
    integer(req['desiredWorkers'],1,20);integer(req['maxAddedMonthlyEUR'],0,20000)
    if type(req['acceptCreateCosts']) is not bool or type(req['acceptDelete']) is not bool:
        raise Blocked('CLOUD_SCALE_BOOLEAN_REQUIRED')
    t=req['template'];fields(t,('location','serverType','imageId','networkId','firewallId','sshKeyId','maxMonthlyEUR'))
    for k in ('imageId','networkId','firewallId','sshKeyId','maxMonthlyEUR'):integer(t[k],1,2**63-1 if k!='maxMonthlyEUR' else 1000)
    for k in ('location','serverType'):
        if not isinstance(t[k],str) or not t[k]:raise Blocked('CLOUD_SCALE_TEMPLATE_INVALID')
    return fingerprint(req)

class CloudScale:
    def __init__(self,driver,machines,lifecycle):self.d=driver;self.m=machines;self.life=lifecycle;self.root=driver.root
    def plan(self,req):
        digest=validate_request(req);s=self.life.state()
        if not s:raise Blocked('CLUSTER_NOT_CREATED')
        validate(s['plan']);workers=[h for h in s['plan']['hosts'] if h['role']=='worker']
        desired=req['desiredWorkers'];delta=desired-len(workers)
        if delta>0 and not req['acceptCreateCosts']:raise Blocked('CLOUD_SCALE_CREATE_COST_ACCEPTANCE_REQUIRED')
        if delta<0 and not req['acceptDelete']:raise Blocked('CLOUD_SCALE_DELETE_ACCEPTANCE_REQUIRED')
        if delta<0:
            managed=[h for h in workers if 'serverId' in h]
            if len(managed)<-delta:raise Blocked('NOT_ENOUGH_PROVIDER_MANAGED_WORKERS_TO_REMOVE')
        op=fingerprint({'request':req,'clusterUID':s['clusterUID'],'sourcePlan':fingerprint(s['plan']),'assets':self.d.assets.fingerprint})
        return op,s,delta
    def apply(self,req,confirm):
        validate_request(req)
        jp=self.root/'cloud-scale.json'
        with lock(self.root/'cloud-scale.lock'):
            j=read_json(jp,private=True) if jp.exists() else None
            if j and j.get('operation')==confirm:
                if j.get('request')!=req:raise Blocked('CLOUD_SCALE_REQUEST_CHANGED')
                if j['stage']=='completed':
                    return {'operation':confirm,'stage':'completed','historicallyCompleted':True,'productionQualified':False}
                if j.get('assets')!=self.d.assets.fingerprint:raise Blocked('CLOUD_SCALE_ASSETS_CHANGED_OR_UNBOUND')
                assert_identity(self.m,j)
                current=self.life.state()
                allowed=[j['sourcePlan']]+([j['targetPlan']] if 'targetPlan' in j else [])
                if not current or current['clusterUID']!=j['clusterUID'] or current['plan'] not in allowed:
                    raise Blocked('CLUSTER_CHANGED_DURING_CLOUD_SCALE')
                op=confirm
            else:
                if j and j['stage']!='completed':raise Blocked('UNFINISHED_OTHER_CLOUD_SCALE')
                op,state,delta=self.plan(req)
                if confirm!=op:raise Blocked('EXACT_CLOUD_SCALE_CONFIRMATION_REQUIRED')
                if j:write_json(self.root/'cloud-scale-history'/(j['operation']+'.json'),j)
                j={'format':'werftkern-kube-cloud-scale-journal/v1','operation':op,'request':req,'clusterUID':state['clusterUID'],
                   'sourcePlan':state['plan'],'sourcePlanHash':fingerprint(state['plan']), 'providerCredential':identity(self.m),
                   'assets':self.d.assets.fingerprint,'machines':{},'deletions':{},'stage':'preparing','startedAt':time.time()}
                write_json(jp,j)
            source=j['sourcePlan'];workers=[h for h in source['hosts'] if h['role']=='worker'];desired=req['desiredWorkers']
            if j['stage']=='preparing':
                if desired>len(workers):
                    price=Decimal(self.m.preflight(req['template']));added=desired-len(workers)
                    if price*added>req['maxAddedMonthlyEUR']:raise Blocked('CLOUD_SCALE_ADDED_MONTHLY_CAP_EXCEEDED')
                    additions=[]
                    for i in range(added):
                        key='add-'+str(i);record=j['machines'].setdefault(key,{})
                        machine_op=fingerprint({'scaleOperation':op,'slot':key})
                        def save():write_json(jp,j)
                        additions.append(self.m.create(source['name'],'worker','default',machine_op,req['template'],self.root/'cloud-scale-machines'/op/key,record,save))
                    target=copy.deepcopy(source);target['hosts']=source['hosts']+additions
                elif desired<len(workers):
                    count=len(workers)-desired
                    managed=sorted([h for h in workers if 'serverId' in h],key=lambda h:h['name'],reverse=True)
                    remove=managed[:count]
                    for h in remove:self.m.ownership(self.m.get(h['serverId']),source['name'],'worker',h.get('pool','default'),h['name'])
                    target=copy.deepcopy(source);names={h['name'] for h in remove};target['hosts']=[h for h in source['hosts'] if h['name'] not in names]
                    j['remove']=remove
                else:
                    target=copy.deepcopy(source)
                validate(target);j['targetPlan']=target;j['targetPlanHash']=fingerprint(target);j['stage']='cluster-apply';write_json(jp,j)
            # Lifecycle owns manager.lock and has its own restart-safe journal.
            if j['stage']=='cluster-apply':
                self.life.apply(j['targetPlan'],j['targetPlanHash'])
                j['stage']='provider-cleanup';write_json(jp,j)
            if j['stage']=='provider-cleanup':
                # Only after Kubernetes has committed the reduced plan may provider
                # deletion begin. Additions require no provider cleanup.
                for h in j.get('remove',[]):
                    sid=h['serverId'];rec=j['deletions'].setdefault(h['name'],{})
                    server=self.m.get(sid)
                    if rec.get('absent'):
                        if server is not None:raise Blocked('DELETED_PROVIDER_ID_REAPPEARED')
                        continue
                    if server is None:
                        rec['absent']=True;rec['observedAbsentAt']=time.time();write_json(jp,j);continue
                    self.m.ownership(server,j['sourcePlan']['name'],'worker',h.get('pool','default'),h['name'])
                    if not rec.get('deleteIntent'):
                        rec['deleteIntent']=time.time();write_json(jp,j)
                        try:self.m.api.call('DELETE','/servers/'+str(sid))
                        except Blocked:pass
                    # Never repeat DELETE after intent. Observe until definitely absent.
                    server=self.m.get(sid)
                    if server is not None:
                        self.m.ownership(server,j['sourcePlan']['name'],'worker',h.get('pool','default'),h['name'])
                        write_json(jp,j);raise Blocked('PROVIDER_DELETE_PENDING_OR_AMBIGUOUS_NO_BLIND_RETRY')
                    rec['absent']=True;rec['observedAbsentAt']=time.time();write_json(jp,j)
                j['stage']='completed';j['completedAt']=time.time();write_json(jp,j)
        return {'operation':op,'stage':j['stage'],'desiredWorkers':req['desiredWorkers'],'productionQualified':False}
