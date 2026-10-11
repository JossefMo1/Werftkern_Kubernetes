"""Opt-in live data-plane smoke on a disposable Kubernetes cluster.

Uses real kubectl and real workloads. Not conformance, not an SLO/HA proof.
"""
from __future__ import annotations
import ipaddress,secrets,time
from .common import Blocked,atomic,canonical,digest_file,fingerprint,lock,read_json,write_json
from .kube_spec import image
from .kube_addons import manifest

class Acceptance:
    def __init__(self,driver,state):self.d=driver;self.s=state
    def run(self,confirm):
        if confirm!='DISPOSABLE:'+self.s['clusterUID']:raise Blocked('DISPOSABLE_CLUSTER_CONFIRMATION_REQUIRED')
        with lock(self.d.root/'manager.lock'):
            workers=[h['name'] for h in self.s['plan']['hosts'] if h['role']=='worker']
            if len(workers)<3:raise Blocked('THREE_WORKERS_REQUIRED_FOR_NETWORK_SMOKE')
            self.d.verify(self.s['plan'],self.s['clusterUID'])
            server=image(self.d.assets.data['images']['smoke-http']);client=image(self.d.assets.data['images']['smoke-client'])
            ns='werft-check-'+secrets.token_hex(6);op='acceptance-'+ns
            self.d.distributed_lock(op,self.s['clusterUID'])
            label={'werft-test':ns}
            deployment=manifest('Deployment','echo',ns,{'replicas':3,'selector':{'matchLabels':label},'template':{'metadata':{'labels':label},'spec':{
                'automountServiceAccountToken':False,'securityContext':{'runAsNonRoot':True,'runAsUser':65532,'seccompProfile':{'type':'RuntimeDefault'}},
                'affinity':{'podAntiAffinity':{'requiredDuringSchedulingIgnoredDuringExecution':[{'labelSelector':{'matchLabels':label},'topologyKey':'kubernetes.io/hostname'}]}},
                'containers':[{'name':'echo','image':server,'command':['/agnhost','netexec','--http-port=8080'],
                    'securityContext':{'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},
                    'readinessProbe':{'httpGet':{'path':'/hostname','port':8080}},'ports':[{'containerPort':8080}],
                    'resources':{'requests':{'cpu':'50m','memory':'64Mi'},'limits':{'cpu':'200m','memory':'128Mi'}}}]}}},'apps/v1')
            service=manifest('Service','echo',ns,{'selector':label,'ports':[{'port':8080,'targetPort':8080}]})
            def apply(objs):self.d.command('kubectl',['apply','-f','-'],data=canonical({'apiVersion':'v1','kind':'List','items':objs}),timeout=180)
            jp=self.d.root/'acceptance'/ns/'run.json';j={'namespace':ns,'operation':op,'clusterUID':self.s['clusterUID'],'stage':'intent'};write_json(jp,j,exclusive=True)
            apply([manifest('Namespace',ns),deployment,service])
            j['namespaceUID']=self.d.request('GET','/api/v1/namespaces/'+ns)['metadata']['uid'];write_json(jp,j)
            self.d.command('kubectl',['-n',ns,'rollout','status','deployment/echo','--timeout=5m'],timeout=330)
            pods=self.d.request('GET','/api/v1/namespaces/'+ns+'/pods?labelSelector=werft-test%3D'+ns)['items']
            if len(pods)!=3 or len({p['spec']['nodeName'] for p in pods})!=3:raise Blocked('THREE_DISTINCT_POD_NODES_NOT_OBSERVED')
            ips=[ipaddress.ip_address(p['status']['podIP']) for p in pods]
            if any(ip not in ipaddress.ip_network(self.s['plan']['podCIDR']) for ip in ips):raise Blocked('SMOKE_ENDPOINT_OUTSIDE_CLUSTER_POD_CIDR')
            fixed='nslookup echo.'+ns+'.svc.cluster.local; wget -T 10 -qO- http://echo.'+ns+'.svc.cluster.local:8080/hostname; '
            fixed+='; '.join('wget -T 10 -qO- http://'+str(ip)+':8080/hostname' for ip in ips)
            job=manifest('Job','probe',ns,{'backoffLimit':0,'activeDeadlineSeconds':180,'template':{'spec':{
                'restartPolicy':'Never','nodeSelector':{'kubernetes.io/hostname':workers[0]},'automountServiceAccountToken':False,
                'securityContext':{'runAsNonRoot':True,'runAsUser':65532,'seccompProfile':{'type':'RuntimeDefault'}},
                'containers':[{'name':'probe','image':client,'command':['/bin/sh','-ec',fixed],
                    'securityContext':{'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},
                    'resources':{'requests':{'cpu':'25m','memory':'32Mi'},'limits':{'cpu':'100m','memory':'64Mi'}}}]}}},'batch/v1')
            apply([job]);self.d.command('kubectl',['-n',ns,'wait','--for=condition=Complete','job/probe','--timeout=4m'],timeout=270)
            logs=self.d.command('kubectl',['-n',ns,'logs','job/probe'],timeout=30);atomic(jp.parent/'probe.log',logs)
            j.update(stage='passed',observedAt=time.time(),scope='three-node pod traffic + ClusterIP + Service-DNS; not HA, storage, SSO or conformance',productionReady=False)
            write_json(jp,j);self.d.unlock(op,self.s['clusterUID']);return j
    def cleanup(self,namespace,confirm):
        from .common import name
        name(namespace);jp=self.d.root/'acceptance'/namespace/'run.json';j=read_json(jp,private=True)
        if confirm!=j.get('namespaceUID') or j['clusterUID']!=self.d.uid():raise Blocked('CLEANUP_NAMESPACE_UID_CONFIRMATION_REQUIRED')
        x=self.d.request('GET','/api/v1/namespaces/'+namespace,notfound=True)
        if x:
            if x['metadata']['uid']!=j['namespaceUID']:raise Blocked('REFUSING_FOREIGN_NAMESPACE_DELETE')
            self.d.request('DELETE','/api/v1/namespaces/'+namespace,{'apiVersion':'v1','kind':'DeleteOptions','preconditions':{'uid':j['namespaceUID']}})
        # The lock is released only if still ours; a newer operator lock is protected.
        self.d.unlock(j['operation'],j['clusterUID'])
        return {'namespace':namespace,'deletionRequested':True,'note':'Namespace finalizers may still be pending.'}
