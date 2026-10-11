"""Hetzner machine factory, no blind create retry and pinned SSH host identities.

Deleting a VM is irreversible. Only dedicated, explicitly tagged Kubernetes
workers with the persisted provider identity are eligible for replacement.
"""
from __future__ import annotations
import copy, decimal, pathlib, time, urllib.parse
from .cloud import Hetzner,Ambiguous
from .common import Blocked, atomic, canonical, fingerprint, private_read, read_json, write_json
from .kube_provider_identity import identity, assert_identity
from .kube_spec import fields,name,integer,private_ip,host_key

class Machines:
    def __init__(self,api,driver):self.api=api;self.d=driver
    def get(self,id_):
        integer(id_,1,2**63-1)
        try:return self.api.call('GET','/servers/'+str(id_))['server']
        except Ambiguous as e:
            if str(e)=='PROVIDER_HTTP_404':return None
            raise
    def ownership(self,server,cluster,role,pool=None,expected_name=None):
        if not server:raise Blocked('SOURCE_VM_MISSING_WITHOUT_FENCING_RECEIPT')
        labels=server.get('labels',{})
        if labels.get('werftkern-cluster')!=cluster or labels.get('werftkern-engine')!='kubernetes' or labels.get('werftkern-role')!=role:
            raise Blocked('PROVIDER_VM_OWNERSHIP_MISMATCH')
        if pool is not None and labels.get('werftkern-pool')!=pool:raise Blocked('PROVIDER_POOL_MISMATCH')
        if expected_name is not None and server.get('name')!=expected_name:raise Blocked('PROVIDER_VM_NAME_CHANGED')
    def preflight(self,t):
        fields(t,('location','serverType','imageId','networkId','firewallId','sshKeyId','maxMonthlyEUR'))
        name(t['location']);name(t['serverType'])
        for key in ('imageId','networkId','firewallId','sshKeyId'):integer(t[key],1,2**63-1)
        integer(t['maxMonthlyEUR'],1,1000)
        network=self.api.call('GET','/networks/'+str(t['networkId']))['network']
        if not network.get('subnets'):raise Blocked('CLOUD_NETWORK_SUBNET_REQUIRED')
        self.api.call('GET','/firewalls/'+str(t['firewallId']));self.api.call('GET','/ssh_keys/'+str(t['sshKeyId']))
        img=self.api.call('GET','/images/'+str(t['imageId']))['image']
        if img.get('os_flavor')!='ubuntu' or img.get('os_version')!='24.04':raise Blocked('UBUNTU_24_04_IMAGE_REQUIRED')
        types=self.api.call('GET','/server_types?'+urllib.parse.urlencode({'name':t['serverType']}))['server_types']
        prices=[p for st in types if st.get('name')==t['serverType'] for p in st.get('prices',[]) if p.get('location')==t['location']]
        if len(prices)!=1:raise Blocked('CLOUD_PRICE_UNAVAILABLE')
        price=decimal.Decimal(prices[0]['price_monthly']['gross'])
        if not price.is_finite() or price<0 or price>t['maxMonthlyEUR']:raise Blocked('SERVER_MONTHLY_COST_CAP_EXCEEDED')
        return str(price)
    def create(self,cluster,role,pool,operation,t,directory,j,save):
        if j:assert_identity(self,j)
        else:j['providerCredential']=identity(self);save()
        self.preflight(t)
        name(cluster);name(pool)
        if role not in ('controller','worker'):raise Blocked('MACHINE_ROLE_INVALID')
        target=(cluster[:16]+'-'+role[:1]+'-'+operation[:12]);name(target)
        labels={'werftkern-cluster':cluster,'werftkern-engine':'kubernetes','werftkern-role':role,
                'werftkern-pool':pool,'werftkern-operation':operation[:32]}
        directory=pathlib.Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        kp=directory/'ssh-host'
        if not j.get('hostKey'):
            if kp.exists():raise Blocked('PARTIAL_SSH_KEY_REQUIRES_REVIEW')
            self.d.command('ssh-keygen',['-q','-t','ed25519','-N','','-f',kp])
            key=' '.join((kp.with_suffix('.pub')).read_text().split()[:2]);host_key(key)
            j['hostKey']=key;save()
        matches=self.api.call('GET','/servers?'+urllib.parse.urlencode({'name':target,'per_page':50}))['servers']
        if len(matches)>1:raise Blocked('CLOUD_NAME_AMBIGUOUS')
        if matches:
            if not j.get('createIntent'):raise Blocked('PREEXISTING_VM_NOT_THIS_OPERATION')
            server=matches[0]
        else:
            if j.get('createIntent'):raise Blocked('CREATE_AMBIGUOUS_NO_BLIND_RETRY')
            j['createIntent']=time.time();save()
            userdata={'hostname':target,'manage_etc_hosts':True,'ssh_pwauth':False,'disable_root':False,'ssh_deletekeys':True,
               'ssh_keys':{'ed25519_private':private_read(kp,16384).decode(),'ed25519_public':j['hostKey']}}
            payload={'name':target,'server_type':t['serverType'],'image':t['imageId'],'location':t['location'],
              'networks':[t['networkId']],'firewalls':[{'firewall':t['firewallId']}],'ssh_keys':[t['sshKeyId']],
              'labels':labels,'public_net':{'enable_ipv4':False,'enable_ipv6':False},'start_after_create':True,
              'user_data':'#cloud-config\n'+canonical(userdata).decode()}
            server=self.api.call('POST','/servers',payload).get('server',{})
            if type(server.get('id')) is not int:raise Blocked('CREATE_RESPONSE_UNKNOWN')
            j['id']=server['id'];save()
            server=self.get(j['id'])
        self.ownership(server,cluster,role,pool,target)
        if server.get('labels',{}).get('werftkern-operation')!=operation[:32] or j.get('id',server['id'])!=server['id']:
            raise Blocked('REPLACEMENT_IDENTITY_CONFLICT')
        if server.get('server_type',{}).get('name')!=t['serverType'] or server.get('image',{}).get('id')!=t['imageId']:
            raise Blocked('REPLACEMENT_SPEC_CHANGED')
        if server.get('datacenter',{}).get('location',{}).get('name')!=t['location']:raise Blocked('REPLACEMENT_LOCATION_CHANGED')
        ips=[n['ip'] for n in server.get('private_net',[]) if n['network']==t['networkId']]
        if len(ips)!=1 or server.get('status')!='running':raise Blocked('NEW_VM_NOT_READY_YET')
        ip=private_ip(ips[0]);j['id']=server['id'];save()
        return {'name':target,'role':role,'pool':pool,'address':ip,'user':'root','port':22,'hostKey':j['hostKey'],'serverId':server['id']}
