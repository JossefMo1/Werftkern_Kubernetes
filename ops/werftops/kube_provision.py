"""Create an explicit cost-approved fleet; never reset existing installations."""
from __future__ import annotations
import copy, pathlib
from .common import Blocked, fingerprint, lock, name, read_json, write_json
from .kube_spec import fields,integer,validate,validate_cluster_base

def validate_blueprint(b):
    fields(b,('format','cluster','controllers','workers','template','acceptCosts','maxFleetMonthlyEUR'))
    if b['format']!='werftkern-kube-fleet/v1' or b['acceptCosts'] is not True:raise Blocked('FLEET_EXPLICIT_COST_ACCEPTANCE_REQUIRED')
    if type(b['controllers']) is not int or b['controllers'] not in (1,3):raise Blocked('FLEET_CONTROLLER_COUNT_INVALID')
    integer(b['workers'],1,20);integer(b['maxFleetMonthlyEUR'],1,25000)
    fields(b['cluster'],('format','name','profile','version','apiEndpoint','podCIDR','serviceCIDR','sshKeyPath','backupRecipient','repair'))
    if b['controllers']!=(3 if b['cluster']['profile']=='ha' else 1):raise Blocked('FLEET_PROFILE_MISMATCH')
    validate_cluster_base(b['cluster'])
    t=b['template'];fields(t,('location','serverType','imageId','networkId','firewallId','sshKeyId','maxMonthlyEUR'))
    name(t['location']);name(t['serverType'])
    for k in ('imageId','networkId','firewallId','sshKeyId'):integer(t[k],1,2**63-1)
    integer(t['maxMonthlyEUR'],1,1000)
    # Host identities and address overlap are checked again after provider results.
    return fingerprint(b)

class Provision:
    def __init__(self,driver,machines):self.d=driver;self.m=machines
    def apply(self,b,confirm):
        from decimal import Decimal
        digest=validate_blueprint(b)
        if digest!=confirm:raise Blocked('EXACT_FLEET_PLAN_CONFIRMATION_REQUIRED')
        with lock(self.d.root/'manager.lock'):
            jp=self.d.root/'fleet.json';j=read_json(jp,private=True) if jp.exists() else {'blueprint':digest,'machines':{},'stage':'provisioning'}
            if j['blueprint']!=digest:raise Blocked('FLEET_JOURNAL_IDENTITY_CONFLICT')
            if (self.d.root/'cluster.json').exists():raise Blocked('FLEET_INITIAL_PROVISION_NOT_SCALE_OR_REPAIR')
            price=Decimal(self.m.preflight(b['template']))
            if price*(b['controllers']+b['workers'])>b['maxFleetMonthlyEUR']:raise Blocked('TOTAL_FLEET_PRICE_CAP_EXCEEDED')
            hosts=[]
            for role,count in [('controller',b['controllers']),('worker',b['workers'])]:
                for i in range(count):
                    key=role+'-'+str(i);record=j['machines'].setdefault(key,{})
                    op=fingerprint({'blueprint':digest,'machine':key})
                    def save():write_json(jp,j)
                    save()
                    hosts.append(self.m.create(b['cluster']['name'],role,'default',op,b['template'],self.d.root/'fleet-machines'/key,record,save))
            p=copy.deepcopy(b['cluster']);p['hosts']=hosts;validate(p)
            write_json(self.d.root/'fleet-plan.json',p)
            j['stage']='vms-created-api-endpoint-and-egress-required';write_json(jp,j)
            return {'plan':str(self.d.root/'fleet-plan.json'),'planHash':fingerprint(p),'stage':j['stage'],
                    'controllerAddresses':[h['address'] for h in hosts if h['role']=='controller'],
                    'warning':'Configure and verify API LB/DNS and private-network egress before applying the cluster plan.',
                    'productionQualified':False}
