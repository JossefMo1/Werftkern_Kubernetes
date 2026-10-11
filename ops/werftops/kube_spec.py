"""Explicit Kubernetes backend contract. No native-runtime conformance claims.

All supplied files and artifact pins are an administrator trust boundary. A digest
is integrity, not provenance or a security certification. No latest resolution.
"""
from __future__ import annotations
import base64, copy, ipaddress, os, pathlib, re, stat, struct
from .common import Blocked, fingerprint, sha, digest_file, private_read, read_json, name

FORMAT = 'werftkern-kubernetes/v1'
RFC1918 = [ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]

def fields(d, required, optional=()):
    if not isinstance(d, dict) or not set(required) <= set(d) or set(d) - set(required) - set(optional):
        raise Blocked('KUBE_CONTRACT_FIELDS_INVALID')

def integer(v, lo, hi):
    if type(v) is not int or not lo <= v <= hi: raise Blocked('KUBE_INTEGER_RANGE')
    return v

def boolean(v):
    if type(v) is not bool: raise Blocked('KUBE_BOOLEAN_REQUIRED')
    return v

def private_ip(v):
    try: ip = ipaddress.IPv4Address(v)
    except (ValueError, TypeError): raise Blocked('PRIVATE_IPV4_REQUIRED') from None
    if not any(ip in n for n in RFC1918): raise Blocked('RFC1918_ADDRESS_REQUIRED')
    return str(ip)

def domain(v):
    if not isinstance(v, str) or len(v) > 253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',v):
        raise Blocked('DNS_NAME_INVALID')
    if '.' not in v or any(not x or len(x)>63 or x.startswith('-') or x.endswith('-') for x in v.split('.')):
        raise Blocked('DNS_NAME_INVALID')
    return v

def path(v):
    if not isinstance(v,str) or not v.startswith('/') or re.search(r'[\s$`\\"\x00-\x1f]',v) or '..' in pathlib.PurePath(v).parts:
        raise Blocked('ABSOLUTE_UNAMBIGUOUS_PATH_REQUIRED')
    return v

def host_key(v):
    # Accept only ed25519 host keys and check the SSH wire-format, not a dummy string.
    if not isinstance(v,str) or not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+',v): raise Blocked('ED25519_HOST_KEY_REQUIRED')
    try:
        b=base64.b64decode(v.split()[1],validate=True)
        if len(b)!=51 or b[:4]!=struct.pack('>I',11) or b[4:15]!=b'ssh-ed25519' or b[15:19]!=struct.pack('>I',32): raise ValueError()
    except ValueError: raise Blocked('SSH_HOST_KEY_MALFORMED') from None
    return v

def version(v):
    m=re.fullmatch(r'v1\.(\d+)\.(\d+)\+k0s\.(\d+)',v) if isinstance(v,str) else None
    if not m: raise Blocked('EXACT_STABLE_K0S_VERSION_REQUIRED')
    return tuple(int(x) for x in m.groups())

def image(v):
    if not isinstance(v,str) or not re.fullmatch(r'[a-zA-Z0-9./_:-]+@sha256:[a-f0-9]{64}',v): raise Blocked('IMAGE_DIGEST_REQUIRED')
    return v

def validate_cluster_base(p):
    """Validate all host-independent intent BEFORE any cloud mutation.

    This does not invent hosts or assert their existence/readiness. Host identities
    and address overlap are separately validated once the provider supplies them.
    """
    fields(p,('format','name','profile','version','apiEndpoint','podCIDR','serviceCIDR','sshKeyPath','backupRecipient','repair'),('oidc','hosts','haControlPlane','storageRecovery'))
    if p['format']!=FORMAT or p['profile'] not in ('lab','ha'): raise Blocked('KUBE_PROFILE_INVALID')
    if 'storageRecovery' in p and (p['storageRecovery']!={'disableForceDetachOnTimeout':True} or p['storageRecovery']['disableForceDetachOnTimeout'] is not True):
        raise Blocked('STORAGE_RECOVERY_REQUIRES_MANUAL_FENCING')
    ha=p.get('haControlPlane')
    if p['profile']=='ha':
        if not isinstance(ha,dict): raise Blocked('HA_CONTROL_PLANE_STRATEGY_REQUIRED')
        fields(ha,('mode',),('vipCIDR','authPassFile','virtualRouterID','interface'))
        if ha['mode']=='external':
            if set(ha)!={'mode'}: raise Blocked('EXTERNAL_HA_HAS_NO_EMBEDDED_VIP_FIELDS')
        elif ha['mode']=='k0s-vip':
            if set(ha)-{'mode','vipCIDR','authPassFile','virtualRouterID','interface'} or not {'vipCIDR','authPassFile','virtualRouterID'}<=set(ha): raise Blocked('K0S_VIP_FIELDS_REQUIRED')
            try:
                vip=ipaddress.ip_interface(ha['vipCIDR'])
                if vip.version!=4 or not any(vip.ip in n for n in RFC1918): raise ValueError()
            except (ValueError,TypeError): raise Blocked('K0S_VIP_RFC1918_CIDR_REQUIRED') from None
            path(ha['authPassFile']);integer(ha['virtualRouterID'],1,255)
            if 'interface' in ha:name(ha['interface'])
        else: raise Blocked('HA_CONTROL_PLANE_MODE_INVALID')
    elif ha is not None:
        raise Blocked('HA_CONTROL_PLANE_ONLY_VALID_FOR_HA_PROFILE')
    name(p['name']); version(p['version']); domain(p['apiEndpoint']); path(p['sshKeyPath'])
    if not isinstance(p['backupRecipient'],str) or not re.fullmatch(r'age1[a-z0-9]{58}',p['backupRecipient']): raise Blocked('AGE_RECIPIENT_REQUIRED')
    try:
        nets=[ipaddress.ip_network(p[k],strict=True) for k in ('podCIDR','serviceCIDR')]
        if any(n.version!=4 for n in nets) or nets[0].overlaps(nets[1]): raise ValueError()
    except (ValueError,TypeError): raise Blocked('POD_SERVICE_CIDRS_INVALID') from None
    r=p['repair'];fields(r,('enabled','unhealthySeconds','observations','minHealthyWorkers','maxUnhealthyPercent','maxPerDay','cooldownSeconds','acceptDeleteAndCosts'),('template',))
    boolean(r['enabled']); boolean(r['acceptDeleteAndCosts']);integer(r['unhealthySeconds'],300,86400);integer(r['observations'],3,100)
    integer(r['minHealthyWorkers'],1,100);integer(r['maxUnhealthyPercent'],1,49);integer(r['maxPerDay'],1,20);integer(r['cooldownSeconds'],300,86400)
    if r['enabled']:
        if not r['acceptDeleteAndCosts'] or 'template' not in r: raise Blocked('AUTOREPAIR_EXPLICIT_COST_AND_DELETE_POLICY_REQUIRED')
        t=r['template'];fields(t,('location','serverType','imageId','networkId','firewallId','sshKeyId','maxMonthlyEUR'))
        name(t['location']);name(t['serverType'])
        for k in ('imageId','networkId','firewallId','sshKeyId'):integer(t[k],1,2**63-1)
        integer(t['maxMonthlyEUR'],1,1000)
    if 'oidc' in p:
        o=p['oidc'];fields(o,('issuer','clientId'))
        if not isinstance(o['issuer'],str) or not re.fullmatch(r'https://[a-z0-9.-]+/realms/[a-z][a-z0-9-]{0,39}',o['issuer']):raise Blocked('OIDC_HTTPS_REALM_REQUIRED')
        name(o['clientId'])
    return nets

def validate(p):
    fields(p,('format','name','profile','version','apiEndpoint','podCIDR','serviceCIDR','sshKeyPath','backupRecipient','hosts','repair'),('oidc','haControlPlane','storageRecovery'))
    nets=validate_cluster_base(p)
    if not isinstance(p['hosts'],list) or not 2<=len(p['hosts'])<=100: raise Blocked('HOST_COUNT_INVALID')
    names=set();addresses=set(); ids=set()
    for h in p['hosts']:
        fields(h,('name','role','address','user','port','hostKey'),('pool','serverId'))
        name(h['name']); private_ip(h['address']); name(h['user']); integer(h['port'],1,65535); host_key(h['hostKey'])
        if h['role'] not in ('controller','worker'): raise Blocked('NODE_ROLE_INVALID')
        if h['name'] in names or h['address'] in addresses: raise Blocked('DUPLICATE_HOST')
        if any(ipaddress.ip_address(h['address']) in n for n in nets): raise Blocked('NODE_POD_CIDR_OVERLAP')
        if h['role']=='worker': name(h.get('pool','default'))
        if 'serverId' in h:
            integer(h['serverId'],1,2**63-1)
            if h['serverId'] in ids: raise Blocked('DUPLICATE_SERVER_ID')
            ids.add(h['serverId'])
        names.add(h['name']);addresses.add(h['address'])
    if p.get('haControlPlane',{}).get('mode')=='k0s-vip':
        vip=str(ipaddress.ip_interface(p['haControlPlane']['vipCIDR']).ip)
        if vip in addresses or any(ipaddress.ip_address(vip) in n for n in nets): raise Blocked('K0S_VIP_COLLIDES_WITH_CLUSTER_ADDRESSING')
    controllers=sum(h['role']=='controller' for h in p['hosts'])
    if controllers!=(3 if p['profile']=='ha' else 1) or not any(h['role']=='worker' for h in p['hosts']):
        raise Blocked('EXACTLY_THREE_HA_CONTROLLERS_OR_ONE_LAB_CONTROLLER_REQUIRED')
    return fingerprint(p)

def validate_change(old,new,edges):
    validate(old);validate(new)
    base=lambda x:{k:v for k,v in x.items() if k not in ('hosts','version','oidc','repair','storageRecovery')}
    if base(old)!=base(new): raise Blocked('IMMUTABLE_CLUSTER_CONFIG_CHANGED')
    oc={h['name']:h for h in old['hosts']};nc={h['name']:h for h in new['hosts']}
    if {n:h for n,h in oc.items() if h['role']=='controller'}!={n:h for n,h in nc.items() if h['role']=='controller'}:
        raise Blocked('CONTROLLER_MEMBERSHIP_CHANGE_REQUIRES_SEPARATE_RECOVERY')
    for n in oc.keys()&nc.keys():
        if oc[n]!=nc[n]: raise Blocked('EXISTING_HOST_IDENTITY_CHANGED')
    if old.get('storageRecovery') and old.get('storageRecovery')!=new.get('storageRecovery'):
        raise Blocked('STORAGE_FENCING_POLICY_CANNOT_BE_DISABLED')
    if old.get('storageRecovery')!=new.get('storageRecovery') and (old['hosts']!=new['hosts'] or old['version']!=new['version']):
        raise Blocked('STORAGE_POLICY_CHANGE_MUST_BE_SEPARATE')
    before,after=version(old['version']),version(new['version'])
    if before!=after:
        if after<=before or after[0]-before[0]>1 or {'from':old['version'],'to':new['version']} not in edges:
            raise Blocked('UNREVIEWED_OR_SKIPPED_UPGRADE_EDGE')
        if old['hosts']!=new['hosts'] or old.get('oidc')!=new.get('oidc') or old['repair']!=new['repair']:
            raise Blocked('UPGRADE_MUST_NOT_CHANGE_TOPOLOGY_OR_AUTH')
    return sorted(oc.keys()-nc.keys()),sorted(nc.keys()-oc.keys())

class Assets:
    def __init__(self,filename):
        self.data=read_json(filename)
        fields(self.data,('format','tools','k0s','upgradeEdges','charts','manifests','images'))
        if self.data['format']!='werftkern-kube-assets/v1': raise Blocked('ASSET_FORMAT_INVALID')
        self.fingerprint=fingerprint(self.data)
    def get(self,group,key,executable=False):
        try: e=self.data[group][key]
        except KeyError:raise Blocked('PINNED_ASSET_MISSING:'+group+':'+key) from None
        fields(e,('path','sha256','version'));path(e['path']);sha(e['sha256'])
        p=pathlib.Path(e['path'])
        for ancestor in [p,*p.parents]:
            if ancestor.is_symlink():raise Blocked('ASSET_SYMLINK_FORBIDDEN')
        st=p.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode&0o022: raise Blocked('ASSET_OWNER_OR_MODE_INVALID')
        if executable and not os.access(p,os.X_OK): raise Blocked('ASSET_NOT_EXECUTABLE')
        if digest_file(p)!=e['sha256']: raise Blocked('ASSET_HASH_MISMATCH:'+key)
        return str(p)
    def tool(self,key):return self.get('tools',key,True)

def render(p,k0s_binary,known_hosts,reset=()):
    validate(p)
    hosts=[]
    for h in p['hosts']:
        x={'role':h['role'],'hostname':h['name'],'privateAddress':h['address'],
           'k0sBinaryPath':k0s_binary,'uploadBinary':True,
           'openSSH':{'address':h['address'],'user':h['user'],'port':h['port'],'keyPath':p['sshKeyPath'],
             'configPath':'/dev/null','disableMultiplexing':True,'options':{
                'StrictHostKeyChecking':'yes','UserKnownHostsFile':known_hosts,'GlobalKnownHostsFile':'/dev/null',
                'IdentitiesOnly':'yes','BatchMode':'yes','ForwardAgent':'no','ConnectTimeout':'10'}}}
        if h['role']=='worker':
            x['installFlags']=['--labels=werftkern.io/cluster='+p['name']+',werftkern.io/pool='+h.get('pool','default'),
                               '--kubelet-extra-args=--node-ip='+h['address']+(' --provider-id=hcloud://'+str(h['serverId']) if 'serverId' in h else '')]
        if h['name'] in reset:x['reset']=True
        hosts.append(x)
    api={'externalAddress':p['apiEndpoint'],'sans':[p['apiEndpoint']]}
    if p.get('oidc'):
        api['extraArgs']={'oidc-issuer-url':p['oidc']['issuer'],'oidc-client-id':p['oidc']['clientId'],
           'oidc-username-claim':'sub','oidc-username-prefix':'oidc:','oidc-groups-claim':'groups','oidc-groups-prefix':'oidc:'}
    network={'provider':'kuberouter','podCIDR':p['podCIDR'],'serviceCIDR':p['serviceCIDR']}
    ha=p.get('haControlPlane')
    if ha and ha['mode']=='k0s-vip':
        raw=private_read(ha['authPassFile'],64).decode().strip()
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,8}',raw): raise Blocked('K0S_VRRP_AUTHPASS_INVALID')
        v={'virtualIPs':[ha['vipCIDR']],'authPass':raw,'virtualRouterID':ha['virtualRouterID']}
        if ha.get('interface'):v['interface']=ha['interface']
        network['controlPlaneLoadBalancing']={'enabled':True,'type':'Keepalived','keepalived':{'vrrpInstances':[v]}}
        network['nodeLocalLoadBalancing']={'enabled':True,'type':'EnvoyProxy'}
    return {'apiVersion':'k0sctl.k0sproject.io/v1beta1','kind':'Cluster','metadata':{'name':p['name']},'spec':{
        'hosts':hosts,'k0s':{'version':p['version'],'dynamicConfig':False,'config':{
            'apiVersion':'k0s.k0sproject.io/v1beta1','kind':'ClusterConfig','metadata':{'name':p['name']},'spec':{
                'api':api,'telemetry':{'enabled':False},'storage':{'type':'etcd'},'network':network,
                **({'controllerManager':{'extraArgs':{'disable-force-detach-on-timeout':'true'}}} if p.get('storageRecovery') else {})}}},
        'options':{'wait':{'enabled':True},'drain':{'enabled':True,'timeout':'15m'},
                   'concurrency':{'limit':1,'workerDisruptionPercent':10,'uploads':1}}}}

def known_hosts(p):
    return ''.join(f"[{h['address']}]:{h['port']} {h['hostKey']}\n{h['address']} {h['hostKey']}\n" for h in p['hosts'])
