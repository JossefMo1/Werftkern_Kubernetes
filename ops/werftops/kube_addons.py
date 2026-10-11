"""Reviewed addon catalogue, immutable local charts, Keycloak and OIDC.

No unmaintained ingress-nginx default. Optional tools are not Kubernetes core.
No issuer, external DB, cloud LB, DNS ownership or conformance is fabricated.
"""
from __future__ import annotations
import base64, copy, json, pathlib, re, secrets, time, urllib.request, ssl
from .common import Blocked, atomic, canonical, fingerprint, lock, name, private_read, read_json, write_json
from .kube_spec import fields,domain,image,path
from .kube_driver import NoRedirect

CATALOG={
 'traefik':{'namespace':'ingress-system','requires':[], 'rollouts':['deployment/traefik']},
 'cert-manager':{'namespace':'cert-manager','requires':[], 'rollouts':['deployment/cert-manager','deployment/cert-manager-webhook','deployment/cert-manager-cainjector']},
 'keycloak-operator':{'namespace':'identity','requires':['cert-manager','traefik'],'manifest':True,'rollouts':['deployment/keycloak-operator']},
 'kube-prometheus-stack':{'namespace':'monitoring','requires':['traefik','cert-manager'],'rollouts':[]},
 'velero':{'namespace':'velero','requires':[],'rollouts':['deployment/velero']},
 'hcloud-csi':{'namespace':'storage-system','requires':[],'rollouts':[]},
 'argocd':{'namespace':'argocd','requires':['traefik','cert-manager'],'rollouts':[]},
}

def order(selected):
    result=[];visiting=set()
    def visit(k):
        if k not in CATALOG:raise Blocked('ADDON_NOT_IN_REVIEWED_CATALOG')
        if k in visiting:raise Blocked('ADDON_DEPENDENCY_CYCLE')
        if k in result:return
        visiting.add(k)
        for dep in CATALOG[k]['requires']:visit(dep)
        visiting.remove(k);result.append(k)
    for k in selected:visit(k)
    return result

def validate_rendered(raw):
    # PyYAML safe parser, bounded before parsing; no constructors or execution.
    import yaml
    if len(raw)>16*1024*1024:raise Blocked('RENDER_TOO_LARGE')
    try: docs=list(yaml.safe_load_all(raw))
    except (ValueError,yaml.YAMLError):raise Blocked('RENDER_YAML_INVALID') from None
    if len(docs)>3000:raise Blocked('RENDER_RESOURCE_LIMIT')
    visited=set();budget=[0]
    def walk(x,depth=0):
        budget[0]+=1
        if budget[0]>200000:raise Blocked('RENDER_OBJECT_LIMIT')
        if isinstance(x,(dict,list)):
            if id(x) in visited:raise Blocked('YAML_ALIASES_FORBIDDEN')
            visited.add(id(x))
        if depth>80:raise Blocked('RENDER_DEPTH_LIMIT')
        if isinstance(x,dict):
            if x.get('kind')=='Secret' and (x.get('data') or x.get('stringData')):raise Blocked('USE_EXISTING_SECRETS_NOT_INLINE_CHART_SECRETS')
            for k,v in x.items():
                if k=='image' and isinstance(v,str):image(v)
                walk(v,depth+1)
        elif isinstance(x,list):
            for a in x:walk(a,depth+1)
    for doc in docs:
        if doc:walk(doc)
    return len([d for d in docs if d])

def manifest(kind,name_,namespace=None,spec=None,api='v1'):
    m={'apiVersion':api,'kind':kind,'metadata':{'name':name_,'labels':{'app.kubernetes.io/managed-by':'werftkern'}}}
    if namespace:m['metadata']['namespace']=namespace
    if spec is not None:m['spec']=spec
    return m

def identity_resources(c,keycloak_image):
    fields(c,('domain','realm','databaseHost','databaseName','databaseSecret','databaseCASecret','acmeEmail','acmeProduction'))
    domain(c['domain']);domain(c['databaseHost']);name(c['realm']);name(c['databaseName']);name(c['databaseSecret']);name(c['databaseCASecret']);image(keycloak_image)
    if type(c['acmeProduction']) is not bool or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',c['acmeEmail']):raise Blocked('ACME_CONFIGURATION_INVALID')
    if not c['acmeProduction']: raise Blocked('PUBLIC_SSO_REQUIRES_TRUSTED_CERTIFICATES_NOT_ACME_STAGING')
    issuer=manifest('ClusterIssuer','werft-acme',spec={'acme':{'email':c['acmeEmail'],
       'server':'https://acme-v02.api.letsencrypt.org/directory','privateKeySecretRef':{'name':'werft-acme-account'},
       'solvers':[{'http01':{'ingress':{'ingressClassName':'traefik'}}}]}},api='cert-manager.io/v1')
    hostname='login.'+c['domain']
    cert=manifest('Certificate','keycloak-tls','identity',{'secretName':'keycloak-tls','dnsNames':[hostname],
       'issuerRef':{'name':'werft-acme','kind':'ClusterIssuer'},'privateKey':{'rotationPolicy':'Always'}},'cert-manager.io/v1')
    kc=manifest('Keycloak','werft-keycloak','identity',{
        'instances':2,'image':keycloak_image,'hostname':{'hostname':'https://'+hostname},
        'db':{'vendor':'postgres','host':c['databaseHost'],'database':c['databaseName'],
              'usernameSecret':{'name':c['databaseSecret'],'key':'username'},'passwordSecret':{'name':c['databaseSecret'],'key':'password'}},
        'truststores':{'database-ca':{'secret':{'name':c['databaseCASecret']}}},
        'additionalOptions':[{'name':'db-tls-mode','value':'verify-server'}],
        'http':{'httpEnabled':True},'proxy':{'headers':'xforwarded'},'ingress':{'enabled':False},
        'resources':{'requests':{'cpu':'500m','memory':'1Gi'},'limits':{'cpu':'2','memory':'2Gi'}}},'k8s.keycloak.org/v2beta1')
    ing=manifest('Ingress','keycloak','identity',{'ingressClassName':'traefik','tls':[{'hosts':[hostname],'secretName':'keycloak-tls'}],
       'rules':[{'host':hostname,'http':{'paths':[{'path':'/','pathType':'Prefix',
          'backend':{'service':{'name':'werft-keycloak-service','port':{'number':8080}}}}]}}]},'networking.k8s.io/v1')
    # Edge TLS: restrict HTTP ingress to the trusted ingress namespace. Never
    # assume forwarded headers are trustworthy just because they exist.
    np=manifest('NetworkPolicy','keycloak-ingress-boundary','identity',{'podSelector':{'matchLabels':{'app':'keycloak'}},
       'policyTypes':['Ingress'],'ingress':[
       {'from':[{'namespaceSelector':{'matchLabels':{'kubernetes.io/metadata.name':'ingress-system'}}}],'ports':[{'protocol':'TCP','port':8080}]},
       {'from':[{'podSelector':{}}],'ports':[{'protocol':'TCP','port':7800},{'protocol':'TCP','port':57800},{'protocol':'TCP','port':9000}]}]},'networking.k8s.io/v1')
    rbac=manifest('ClusterRoleBinding','werft-oidc-viewers',api='rbac.authorization.k8s.io/v1')
    rbac['roleRef']={'apiGroup':'rbac.authorization.k8s.io','kind':'ClusterRole','name':'view'}
    rbac['subjects']=[{'apiGroup':'rbac.authorization.k8s.io','kind':'Group','name':'oidc:viewers'}]
    mapper={'name':'groups','protocol':'openid-connect','protocolMapper':'oidc-group-membership-mapper',
            'config':{'claim.name':'groups','full.path':'false','id.token.claim':'true','access.token.claim':'true','userinfo.token.claim':'true'}}
    public={'clientId':'werft-kubectl','enabled':True,'publicClient':True,'protocol':'openid-connect','standardFlowEnabled':True,
       'directAccessGrantsEnabled':False,'redirectUris':['http://localhost:8000','http://localhost:8000/*','http://127.0.0.1:8000','http://127.0.0.1:8000/*'],
       'attributes':{'pkce.code.challenge.method':'S256'},'protocolMappers':[mapper]}
    confidential={'clientId':'werft-grafana','enabled':True,'publicClient':False,'secret':'${GRAFANA_CLIENT_SECRET}',
       'protocol':'openid-connect','standardFlowEnabled':True,'directAccessGrantsEnabled':False,
       'redirectUris':['https://grafana.'+c['domain']+'/login/generic_oauth'],
       'webOrigins':['https://grafana.'+c['domain']],'attributes':{'pkce.code.challenge.method':'S256'},'protocolMappers':[mapper]}
    realm=manifest('KeycloakRealmImport','werft-realm','identity',{'keycloakCRName':'werft-keycloak',
        'placeholders':{'GRAFANA_CLIENT_SECRET':{'secret':{'name':'grafana-oidc','key':'client-secret'}}},
        'realm':{'realm':c['realm'],'enabled':True,'sslRequired':'all','registrationAllowed':False,'resetPasswordAllowed':True,
                 'bruteForceProtected':True,'groups':[{'name':'viewers'},{'name':'operators'}],'clients':[public,confidential]}},'k8s.keycloak.org/v2beta1')
    return [issuer,cert,np,kc,ing,rbac,realm]

def grafana_values(c):
    root='https://grafana.'+c['domain'];issuer='https://login.'+c['domain']+'/realms/'+c['realm']
    return {'grafana':{'admin':{'existingSecret':'grafana-bootstrap-admin','userKey':'username','passwordKey':'password'},
       'envValueFrom':{'GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET':{'secretKeyRef':{'name':'grafana-oidc','key':'client-secret'}}},
       'grafana.ini':{'server':{'root_url':root},'auth.anonymous':{'enabled':False},
        'auth.generic_oauth':{'enabled':True,'name':'Keycloak','client_id':'werft-grafana','scopes':'openid profile email',
         'auth_url':issuer+'/protocol/openid-connect/auth','token_url':issuer+'/protocol/openid-connect/token',
         'api_url':issuer+'/protocol/openid-connect/userinfo','use_pkce':True,'allow_sign_up':True,
         'allow_assign_grafana_admin':False,'role_attribute_path':"contains(groups[*], 'operators') && 'Editor' || 'Viewer'"}},
       'ingress':{'enabled':True,'ingressClassName':'traefik','hosts':['grafana.'+c['domain']],
          'annotations':{'cert-manager.io/cluster-issuer':'werft-acme'},'tls':[{'secretName':'grafana-tls','hosts':['grafana.'+c['domain']]}]}}}

def merge(a,b):
    out=copy.deepcopy(a)
    for k,v in b.items():out[k]=merge(out.get(k,{}) if isinstance(out.get(k),dict) else {},v) if isinstance(v,dict) else copy.deepcopy(v)
    return out

class Addons:
    def __init__(self,driver,state):self.d=driver;self.s=state
    def apply_objects(self,objects):
        self.d.command('kubectl',['apply','--server-side','--field-manager=werftkern','-f','-'],data=canonical({'apiVersion':'v1','kind':'List','items':objects}),timeout=180)
    def apply(self,spec,confirm):
        fields(spec,('format','addons','values'),('identity',))
        if spec['format']!='werftkern-addons/v1':raise Blocked('ADDON_SPEC_INVALID')
        digest=fingerprint(spec)
        if confirm!=digest:raise Blocked('EXACT_ADDON_PLAN_CONFIRMATION_REQUIRED')
        if not isinstance(spec['addons'],list) or not spec['addons'] or not isinstance(spec['values'],dict):raise Blocked('ADDON_SPEC_INVALID')
        if set(spec['values'])-set(order(spec['addons'])):raise Blocked('VALUES_FOR_UNSELECTED_ADDON')
        ordered=order(spec['addons'])
        if spec.get('identity') and 'keycloak-operator' not in ordered:raise Blocked('IDENTITY_REQUIRES_KEYCLOAK_OPERATOR')
        if spec.get('identity'):ordered=order(['keycloak-operator']+spec['addons'])
        op='addons-'+fingerprint({'spec':spec,'assets':self.d.assets.fingerprint})
        with lock(self.d.root/'manager.lock'):
            self.d.distributed_lock(op,self.s['clusterUID'])
            jp=self.d.root/(op+'.json');j=read_json(jp,private=True) if jp.exists() else {'operation':op,'done':[],'stage':'running'}
            write_json(jp,j)
            inventory_path=self.d.root/'addons-state.json'
            inventory=read_json(inventory_path,private=True) if inventory_path.exists() else {}
            # All value files and charts are approved deployment inputs, not arbitrary
            # web URLs. Rendered manifests must have pinned image digests.
            for item in ordered:
                meta=CATALOG[item];ns=meta['namespace']
                self.apply_objects([manifest('Namespace',ns)])
                if meta.get('manifest'):
                    raw=pathlib.Path(self.d.assets.get('manifests',item)).read_bytes();validate_rendered(raw)
                    self.d.command('kubectl',['apply','--server-side','--field-manager=werftkern','-f','-'],data=raw,timeout=300)
                    for crd in ('keycloaks.k8s.keycloak.org','keycloakrealmimports.k8s.keycloak.org'):
                        self.d.command('kubectl',['wait','--for=condition=Established','crd/'+crd,'--timeout=180s'],timeout=200)
                else:
                    values=copy.deepcopy(spec['values'].get(item,{}))
                    if item=='traefik':values=merge(values,{'deployment':{'replicas':2},'ingressRoute':{'dashboard':{'enabled':False}}})
                    if item=='cert-manager':values=merge(values,{'crds':{'enabled':True,'keep':True}})
                    if item=='kube-prometheus-stack' and spec.get('identity'):
                        self.identity(spec['identity'],j,jp)
                        values=merge(values,grafana_values(spec['identity']))
                    vf=self.d.root/(item+'-values.json');write_json(vf,values)
                    chart=self.d.assets.get('charts',item)
                    raw=self.d.command('helm',['template',item,chart,'--namespace',ns,'--include-crds','-f',vf],timeout=120)
                    validate_rendered(raw)
                    atomic(self.d.root/(item+'-rendered.yaml'),raw)
                    marker='werftkern:'+op+':'+item
                    if item not in j['done']:
                        if j.get('applying')==item:
                            status=json.loads(self.d.command('helm',['status',item,'-n',ns,'-o','json']))
                            if status.get('info',{}).get('status')!='deployed' or status.get('info',{}).get('description')!=marker:
                                raise Blocked('HELM_PREVIOUS_MUTATION_UNCERTAIN_REVIEW_RELEASE')
                        else:
                            releases=json.loads(self.d.command('helm',['list','-n',ns,'--all','--filter','^'+item+'$','-o','json']))
                            if releases:
                                status=json.loads(self.d.command('helm',['status',item,'-n',ns,'-o','json']))
                                prior=inventory.get(item,{})
                                if status.get('info',{}).get('description')!=prior.get('marker') or status.get('version')!=prior.get('revision'):
                                    raise Blocked('REFUSING_FOREIGN_OR_CHANGED_HELM_RELEASE')
                            j['applying']=item;write_json(jp,j)
                            self.d.command('helm',['upgrade','--install',item,chart,'--namespace',ns,'--create-namespace',
                               '--wait','--atomic','--timeout','15m','--history-max','10','--description',marker,'-f',vf],timeout=1020)
                for obj in meta['rollouts']:
                    self.d.command('kubectl',['-n',ns,'rollout','status',obj,'--timeout=300s'],timeout=330)
                if not meta.get('manifest'):
                    result=json.loads(self.d.command('helm',['status',item,'-n',ns,'-o','json']))
                    if result.get('info',{}).get('status')!='deployed' or result.get('info',{}).get('description')!=marker:raise Blocked('HELM_RELEASE_NOT_DEPLOYED_OR_WRONG_OPERATION')
                    inventory[item]={'marker':marker,'revision':result['version']}
                    write_json(inventory_path,inventory)
                if item not in j['done']:j['done'].append(item)
                j.pop('applying',None);write_json(jp,j)
            if spec.get('identity'):
                if 'keycloak-operator' not in ordered:raise Blocked('IDENTITY_REQUIRES_KEYCLOAK_OPERATOR')
                self.identity(spec['identity'],j,jp)
            self.d.unlock(op,self.s['clusterUID']);j['stage']='completed';write_json(jp,j)
            return {'operation':op,'deployed':j['done'],'productionQualified':False,'ssoLoginE2E':'not-proven-by-pod-readiness'}
    def identity(self,c,j,jp):
        identity_state=self.d.root/'identity-state.json'
        identity_hash=fingerprint(c)
        if identity_state.exists() and read_json(identity_state,private=True).get('configuration')!=identity_hash:
            raise Blocked('REALM_IMPORT_NOT_A_REALM_UPDATE_ENGINE')
        resources=identity_resources(c,self.d.assets.data['images']['keycloak'])
        for ns in ('identity','monitoring'):self.apply_objects([manifest('Namespace',ns)])
        # External PostgreSQL credentials and CA are mandatory; never synthesize
        # a disposable database or default password for production-looking SSO.
        for secret,key in [(c['databaseSecret'],'username'),(c['databaseSecret'],'password'),(c['databaseCASecret'],'ca.crt')]:
            value=self.d.request('GET','/api/v1/namespaces/identity/secrets/'+secret)
            if key not in value.get('data',{}):raise Blocked('KEYCLOAK_DATABASE_SECRET_OR_CA_MISSING')
        source=self.d.root/'sso-secrets.json'
        if source.exists():values=read_json(source,private=True)
        else:
            if self.d.request('GET','/api/v1/namespaces/identity/secrets/grafana-oidc',notfound=True) is not None:
                raise Blocked('SSO_SECRET_EXISTS_WITHOUT_LOCAL_RECOVERY_STATE')
            values={'client-secret':secrets.token_urlsafe(48),'password':secrets.token_urlsafe(48),'username':'break-glass-admin'}
            write_json(source,values,exclusive=True)
        for ns in ('identity','monitoring'):
            obj=manifest('Secret','grafana-oidc',ns);obj['stringData']={'client-secret':values['client-secret']};self.apply_objects([obj])
        obj=manifest('Secret','grafana-bootstrap-admin','monitoring');obj['stringData']={k:values[k] for k in ('username','password')};self.apply_objects([obj])
        self.apply_objects(resources[:-1])
        self.d.command('kubectl',['-n','identity','wait','--for=condition=Ready','certificate/keycloak-tls','--timeout=10m'],timeout=630)
        self.d.command('kubectl',['-n','identity','wait','--for=condition=Ready','keycloak/werft-keycloak','--timeout=15m'],timeout=930)
        self.apply_objects(resources[-1:])
        self.d.command('kubectl',['-n','identity','wait','--for=condition=Done','keycloakrealmimport/werft-realm','--timeout=10m'],timeout=630)
        # TLS validation and exact issuer matching are independent from Ready pods.
        issuer='https://login.'+c['domain']+'/realms/'+c['realm']
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        try:
            with opener.open(issuer+'/.well-known/openid-configuration',timeout=20) as r:d=json.loads(r.read(1024*1024))
            if d.get('issuer')!=issuer:raise Blocked('OIDC_DISCOVERY_ISSUER_MISMATCH')
        except (OSError,ValueError):raise Blocked('OIDC_DISCOVERY_NOT_TLS_READY') from None
        write_json(identity_state,{'configuration':identity_hash,'issuer':issuer})
        j['identity']='realm-import-and-TLS-discovery-ready-not-user-login-tested';write_json(jp,j)
