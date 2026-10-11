"""Pinned command runner and certificate-only Kubernetes JSON client.

Runtime credentials remain in a private directory. This is a single-management-
writer backend; a persistent Kubernetes ConfigMap lock excludes other operations.
"""
from __future__ import annotations
import base64, contextlib, copy, http.client, json, os, pathlib, re, shlex, ssl, tempfile, time, urllib.error, urllib.parse, urllib.request
from .common import Blocked, atomic, canonical, private_read, run, write_json, read_json
from .kube_spec import fields, private_ip, domain, version, render, known_hosts

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

class KubeHTTP:
    def __init__(self,filename):
        c=read_json(filename,private=True)
        fields(c,('apiVersion','kind','clusters','contexts','current-context','users'),('preferences',))
        if c['kind']!='Config' or len(c['clusters'])!=1 or len(c['contexts'])!=1 or len(c['users'])!=1: raise Blocked('SINGLE_CERTIFICATE_KUBECONFIG_REQUIRED')
        cluster=c['clusters'][0]['cluster'];user=c['users'][0]['user'];ctx=c['contexts'][0]
        if ctx['name']!=c['current-context'] or ctx['context'].get('cluster')!=c['clusters'][0]['name'] or ctx['context'].get('user')!=c['users'][0]['name']:
            raise Blocked('KUBECONFIG_CONTEXT_MISMATCH')
        fields(cluster,('server','certificate-authority-data'));fields(user,('client-certificate-data','client-key-data'))
        u=urllib.parse.urlsplit(cluster['server'])
        if u.scheme!='https' or u.username or u.password or u.query or u.fragment or u.path not in ('','/') or u.port!=6443:
            raise Blocked('KUBECONFIG_HTTPS_6443_REQUIRED')
        try: private_ip(u.hostname)
        except Blocked: domain(u.hostname)
        self.base=cluster['server'].rstrip('/');self.temp=tempfile.TemporaryDirectory(prefix='werft-kube-pki-')
        try:
            ca=base64.b64decode(cluster['certificate-authority-data'],validate=True).decode()
            self.context=ssl.create_default_context(cadata=ca);self.context.minimum_version=ssl.TLSVersion.TLSv1_2
            for key,leaf in [('client-certificate-data','cert'),('client-key-data','key')]:
                atomic(pathlib.Path(self.temp.name)/leaf,base64.b64decode(user[key],validate=True))
            self.context.load_cert_chain(self.temp.name+'/cert',self.temp.name+'/key')
            self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=self.context))
        except BaseException:
            self.close();raise
    def close(self):self.temp.cleanup()
    def direct(self,address,method,path):
        private_ip(address)
        client=copy.copy(self);client.base='https://'+address+':6443'
        # Reuse credentials/CA, not hostname validation exceptions or LB fallback.
        return client.call(method,path)
    def call(self,method,path,payload=None,notfound=False):
        if not path.startswith('/') or '..' in path or any(c in path for c in '\r\n#'):raise Blocked('KUBE_API_PATH_INVALID')
        req=urllib.request.Request(self.base+path,data=canonical(payload) if payload is not None else None,method=method,
                                  headers={'Content-Type':'application/json','Accept':'application/json'})
        try:
            with self.opener.open(req,timeout=15) as r:
                raw=r.read(16*1024*1024+1)
                if len(raw)>16*1024*1024:raise Blocked('KUBE_RESPONSE_TOO_LARGE')
                return json.loads(raw) if raw and raw[:1] in (b'{',b'[') else raw.decode()
        except urllib.error.HTTPError as e:
            if e.code==404 and notfound:return None
            raise Blocked('KUBE_HTTP_'+str(e.code)) from None
        except (ValueError,OSError,http.client.HTTPException):raise Blocked('KUBE_API_UNREACHABLE_OR_INVALID') from None

class Driver:
    def __init__(self,root,assets,executor=run,api_factory=KubeHTTP):
        self.root=pathlib.Path(root).absolute();self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.root.is_symlink() or self.root.stat().st_uid!=os.geteuid() or self.root.stat().st_mode&0o077:
            raise Blocked('PRIVATE_MANAGER_DIRECTORY_REQUIRED')
        self.assets=assets;self.executor=executor;self.api_factory=api_factory;self.api=None
        self.env={'PATH':'/usr/bin:/bin','HOME':str(self.root/'home'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
                  'KUBECONFIG':str(self.root/'kubeconfig.json'),'HELM_CACHE_HOME':str(self.root/'helm/cache'),
                  'HELM_CONFIG_HOME':str(self.root/'helm/config'),'HELM_DATA_HOME':str(self.root/'helm/data')}
        pathlib.Path(self.env['HOME']).mkdir(mode=0o700,exist_ok=True)
    def command(self,tool,args,data=None,timeout=120,cwd=None):
        return self.executor([self.assets.tool(tool),*map(str,args)],data=data,timeout=timeout,env=self.env,cwd=cwd)
    def configuration(self,p,reset=(), selected_hosts=None):
        private_read(p['sshKeyPath'],65536)
        kh=self.root/'known_hosts';atomic(kh,known_hosts(p).encode())
        cfg=self.root/'k0sctl.json'
        binary=self.assets.get('k0s',p['version'],True)
        config=render(p,binary,str(kh),reset)
        if selected_hosts is not None:
            config['spec']['hosts']=[h for h in config['spec']['hosts'] if h['hostname'] in selected_hosts]
            if len(config['spec']['hosts']) != len(selected_hosts):raise Blocked('SELECTED_HOST_NOT_IN_PLAN')
        write_json(cfg,config)
        return str(cfg)
    def fresh_hosts(self,p,selected=None):
        cfg=self.configuration(p)
        # Read-only preflight. Never install over an existing Kubernetes/native host.
        for h in p['hosts']:
            if selected is not None and h['name'] not in selected:continue
            script="""set -eu
. /etc/os-release
test "${ID:-}" = ubuntu
test "${VERSION_ID:-}" = 24.04
test "$(uname -m)" = x86_64
test -d /run/systemd/system
test ! -e /var/lib/k0s
test ! -e /etc/kubernetes
test ! -e /etc/werftkern/agent.json
! systemctl is-active --quiet kubelet
! systemctl is-active --quiet werftkern-agent
printf WERFT_FRESH_UBUNTU_24_04
"""
            remote=('' if h['user']=='root' else 'sudo -n ')+'sh -c '+shlex.quote(script)
            args=['-F','/dev/null','-p',str(h['port']),'-i',p['sshKeyPath'],
                '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(self.root/'known_hosts'),
                '-o','GlobalKnownHostsFile=/dev/null','-o','IdentitiesOnly=yes','-o','BatchMode=yes',
                '-o','ForwardAgent=no','-o','ConnectTimeout=10',h['user']+'@'+h['address'],remote]
            if self.command('ssh',args,timeout=60).strip()!=b'WERFT_FRESH_UBUNTU_24_04':raise Blocked('FRESH_UBUNTU_HOST_PREFLIGHT_FAILED')
    def apply(self,p,reset=(),restore=None):
        cfg=self.configuration(p,reset)
        args=['apply','--config',cfg]
        if restore:args+=['--restore-from',restore]
        self.command('k0sctl',args,timeout=7200)
    def load_api(self):
        if self.api is None:self.api=self.api_factory(self.root/'kubeconfig.json')
        return self.api
    def capture_kubeconfig(self,p):
        raw=self.command('k0sctl',['kubeconfig','--config',self.configuration(p)],timeout=120)
        untrusted=self.root/'kubeconfig.generated';atomic(untrusted,raw)
        try:
            # config view does not contact the server; generated kubeconfig is still
            # restricted below before any authenticated server request or plugin use.
            canonical_config=self.command('kubectl',['--kubeconfig',untrusted,'config','view','--raw','-o','json'])
            atomic(self.root/'kubeconfig.json',canonical_config)
            if self.api:self.close();self.api=None
            api=self.load_api()
            if api.base!='https://'+p['apiEndpoint']+':6443':raise Blocked('KUBECONFIG_EXTERNAL_ENDPOINT_MISMATCH')
        finally:untrusted.unlink(missing_ok=True)
    def request(self,*args,**kwargs):return self.load_api().call(*args,**kwargs)
    def uid(self):
        x=self.request('GET','/api/v1/namespaces/kube-system')
        uid=x.get('metadata',{}).get('uid')
        if not isinstance(uid,str) or not uid:raise Blocked('KUBE_CLUSTER_UID_MISSING')
        return uid
    def snapshot(self):
        if str(self.request('GET','/readyz')).strip()!='ok':raise Blocked('KUBE_API_NOT_READY')
        return {'uid':self.uid(),'version':self.request('GET','/version').get('gitVersion'),
                'nodes':self.request('GET','/api/v1/nodes')['items']}
    def verify(self,p,expected_uid=None):
        s=self.snapshot()
        if expected_uid and s['uid']!=expected_uid:raise Blocked('KUBE_CLUSTER_IDENTITY_CHANGED')
        target=version(p['version']);prefix='v1.%d.%d'%target[:2]
        def exact(v):return isinstance(v,str) and re.fullmatch(re.escape(prefix)+r'(?:\+[A-Za-z0-9.-]+)?',v)
        if not exact(s['version']):raise Blocked('API_VERSION_NOT_TARGET')
        for controller in [h for h in p['hosts'] if h['role']=='controller']:
            api=self.load_api()
            if str(api.direct(controller['address'],'GET','/readyz')).strip()!='ok':raise Blocked('CONTROLLER_NOT_READY')
            observed=api.direct(controller['address'],'GET','/version').get('gitVersion','')
            if not exact(observed):raise Blocked('CONTROLLER_VERSION_NOT_TARGET')
            if api.direct(controller['address'],'GET','/api/v1/namespaces/kube-system')['metadata']['uid']!=s['uid']:
                raise Blocked('CONTROLLER_CLUSTER_UID_MISMATCH')
        workers={h['name']:h for h in p['hosts'] if h['role']=='worker'}
        seen={}
        for n in s['nodes']:
            nm=n['metadata']['name']
            if nm not in workers:continue
            h=workers[nm];st=n.get('status',{})
            if h['address'] not in [a.get('address') for a in st.get('addresses',[]) if a.get('type')=='InternalIP']:
                raise Blocked('WORKER_ADDRESS_MISMATCH')
            if not any(c.get('type')=='Ready' and c.get('status')=='True' for c in st.get('conditions',[])):raise Blocked('WORKER_NOT_READY')
            if not exact(st.get('nodeInfo',{}).get('kubeletVersion','')):raise Blocked('KUBELET_VERSION_NOT_TARGET')
            labels=n['metadata'].get('labels',{})
            if labels.get('werftkern.io/cluster')!=p['name'] or labels.get('werftkern.io/pool')!=h.get('pool','default'):raise Blocked('WORKER_LABEL_BINDING_MISMATCH')
            seen[nm]=n['metadata']['uid']
        if set(seen)!=set(workers):raise Blocked('EXPECTED_WORKERS_MISSING')
        # Do not equate successful apply or Ready nodes with functional DNS/CNI.
        self.command('kubectl',['--request-timeout=20s','-n','kube-system','rollout','status','deployment/coredns','--timeout=180s'],timeout=200)
        return {'clusterUID':s['uid'],'nodeUIDs':seen,'version':s['version'],'verifiedAt':time.time(),
                'scope':'Direct TLS API/version/UID on every controller, worker identity/version/Ready, CoreDNS rollout; not Sonobuoy or data-plane proof'}
    def distributed_lock(self,operation,expected_uid):
        if self.uid()!=expected_uid:raise Blocked('KUBE_CLUSTER_IDENTITY_CHANGED')
        path='/api/v1/namespaces/kube-system/configmaps/werftkern-operation'
        current=self.request('GET',path,notfound=True)
        if current is None:
            try:self.request('POST','/api/v1/namespaces/kube-system/configmaps',{
                'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'werftkern-operation','namespace':'kube-system'},
                'data':{'operation':operation,'clusterUID':expected_uid}})
            except Blocked:pass # Verify ambiguous create; never assume the write failed.
            current=self.request('GET',path)
        if current.get('data')!={'operation':operation,'clusterUID':expected_uid}:raise Blocked('OTHER_CLUSTER_OPERATION_HOLDS_LOCK')
        return current['metadata']['uid']
    def unlock(self,operation,expected_uid):
        if self.uid()!=expected_uid:raise Blocked('KUBE_CLUSTER_IDENTITY_CHANGED')
        path='/api/v1/namespaces/kube-system/configmaps/werftkern-operation';x=self.request('GET',path,notfound=True)
        if x is None:return
        if x.get('data')!={'operation':operation,'clusterUID':expected_uid}:raise Blocked('REFUSING_FOREIGN_OPERATION_UNLOCK')
        self.request('DELETE',path,{'apiVersion':'v1','kind':'DeleteOptions','preconditions':{'uid':x['metadata']['uid'],'resourceVersion':x['metadata']['resourceVersion']}})
    def backup(self,p,out,selected_hosts=None):
        out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True,mode=0o700)
        with tempfile.TemporaryDirectory(dir=self.root,prefix='backup-') as td:
            self.command('k0sctl',['backup','--config',self.configuration(p,selected_hosts=selected_hosts)],timeout=1800,cwd=td)
            files=list(pathlib.Path(td).glob('k0s_backup_*.tar.gz'))
            if len(files)!=1 or files[0].is_symlink():raise Blocked('EXACTLY_ONE_CONTROL_PLANE_BACKUP_REQUIRED')
            target=out/'control-plane.tar.gz.age'
            if target.exists():raise Blocked('BACKUP_TARGET_EXISTS')
            self.command('age',['--encrypt','--recipient',p['backupRecipient'],'--output',target,files[0]],timeout=1800)
            os.chmod(target,0o600)
        from .common import digest_file
        receipt={'format':'werftkern-kube-backup/v2','clusterUID':self.uid(),'version':p['version'],
                 'apiEndpoint':p['apiEndpoint'],'sha256':digest_file(target),'createdAt':time.time(),
                 'sourcePlanHash':__import__('hashlib').sha256(canonical(p)).hexdigest(),
                 'sourceControllerAddresses':sorted(h['address'] for h in p['hosts'] if h['role']=='controller'),
                 'contains':'control-plane state and PKI; NO application volume data'}
        write_json(out/'receipt.json',receipt,exclusive=True)
        return receipt
    def controller_observe(self, host, cluster_uid, release):
        api=self.load_api()
        if str(api.direct(host['address'],'GET','/readyz')).strip()!='ok':
            raise Blocked('CONTROLLER_NOT_READY')
        observed=api.direct(host['address'],'GET','/version').get('gitVersion','')
        prefix='v1.%d.%d'%version(release)[:2]
        if not re.fullmatch(re.escape(prefix)+r'(?:\+[A-Za-z0-9.-]+)?',observed):
            raise Blocked('CONTROLLER_VERSION_NOT_TARGET')
        if api.direct(host['address'],'GET','/api/v1/namespaces/kube-system')['metadata']['uid']!=cluster_uid:
            raise Blocked('CONTROLLER_CLUSTER_UID_MISMATCH')
        return True

    def controller_reachable(self, host, cluster_uid, release):
        try:return self.controller_observe(host,cluster_uid,release)
        except Blocked as error:
            if str(error) in ('CONTROLLER_NOT_READY','KUBE_API_UNREACHABLE_OR_INVALID','KUBE_HTTP_500','KUBE_HTTP_503'):
                return False
            raise  # Changed identity, authorization and version are not failure evidence.

    def remote(self, plan, host, argv, data=None, timeout=120):
        # Only fixed internal operations call this method. No CLI arbitrary-command surface.
        if host not in plan['hosts']:raise Blocked('REMOTE_HOST_NOT_IN_PLAN')
        self.configuration(plan)
        if any(not isinstance(a,str) or any(c in a for c in '\x00\r\n') for a in argv):
            raise Blocked('REMOTE_ARGUMENT_INVALID')
        remote=('' if host['user']=='root' else 'sudo -n ')+shlex.join(argv)
        args=['-F','/dev/null','-p',str(host['port']),'-i',plan['sshKeyPath'],
              '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(self.root/'known_hosts'),
              '-o','GlobalKnownHostsFile=/dev/null','-o','IdentitiesOnly=yes','-o','BatchMode=yes',
              '-o','ForwardAgent=no','-o','ConnectTimeout=10',host['user']+'@'+host['address'],remote]
        return self.command('ssh',args,data=data,timeout=timeout)

    def etcd_members(self, plan, host):
        raw=self.remote(plan,host,['/usr/local/bin/k0s','etcd','member-list'])
        try:value=json.loads(raw)
        except ValueError:raise Blocked('ETCD_MEMBERS_JSON_INVALID') from None
        fields(value,('members',))
        members=value['members']
        if not isinstance(members,dict) or not 1<=len(members)<=5:raise Blocked('ETCD_MEMBER_COUNT_INVALID')
        for name_,peer in members.items():
            if not isinstance(name_,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,62}',name_):raise Blocked('ETCD_MEMBER_NAME_INVALID')
            u=urllib.parse.urlsplit(peer)
            if u.scheme!='https' or u.port!=2380 or u.path or u.username or u.query or u.fragment:
                raise Blocked('ETCD_PEER_URL_INVALID')
            private_ip(u.hostname)
        return members

    def etcd_leave(self, plan, survivor, peer):
        u=urllib.parse.urlsplit(peer)
        if u.scheme!='https' or u.port!=2380 or u.path or u.query or u.fragment or u.username:
            raise Blocked('ETCD_PEER_URL_INVALID')
        private_ip(u.hostname)
        return self.remote(plan,survivor,['/usr/local/bin/k0s','etcd','leave','--peer-address',peer],timeout=180)

    def control_node(self, name_):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',name_):raise Blocked('CONTROL_NODE_NAME_INVALID')
        raw=self.command('kubectl',['get','controlnodes.autopilot.k0sproject.io',name_,'-o','json'])
        try:obj=json.loads(raw)
        except ValueError:raise Blocked('CONTROL_NODE_JSON_INVALID') from None
        if obj.get('kind')!='ControlNode' or obj.get('metadata',{}).get('name')!=name_:
            raise Blocked('CONTROL_NODE_IDENTITY_INVALID')
        if not re.fullmatch(r'autopilot.k0sproject.io/v[0-9]+(?:(?:alpha|beta)[0-9]+)?',obj.get('apiVersion','')):
            raise Blocked('CONTROL_NODE_API_VERSION_INVALID')
        meta=obj['metadata']
        if not meta.get('uid') or not meta.get('resourceVersion'):raise Blocked('CONTROL_NODE_UID_REQUIRED')
        return {'apiVersion':obj['apiVersion'],'metadata':{k:meta[k] for k in ('name','uid','resourceVersion')}}

    def delete_control_node(self, receipt):
        meta=receipt['metadata'];path='/apis/'+receipt['apiVersion']+'/controlnodes/'+meta['name']
        current=self.request('GET',path,notfound=True)
        if current is None:return
        if current['metadata']['uid']!=meta['uid']:raise Blocked('CONTROL_NODE_REPLACED_EXTERNALLY')
        return self.request('DELETE',path,{'apiVersion':'v1','kind':'DeleteOptions','preconditions':{
            'uid':meta['uid'],'resourceVersion':current['metadata']['resourceVersion']}})

    def backup_survivor(self, plan, survivor, out):
        receipt=pathlib.Path(out)/'receipt.json'
        if receipt.exists():
            from .common import digest_file
            existing=read_json(receipt,private=True)
            if existing.get('sourcePlanHash')!=__import__('hashlib').sha256(canonical(plan)).hexdigest() or \
               existing.get('clusterUID')!=self.uid() or existing.get('sha256')!=digest_file(pathlib.Path(out)/'control-plane.tar.gz.age'):
                raise Blocked('CONTROLLER_BACKUP_RECEIPT_CHANGED')
            return existing
        return self.backup(plan,out,selected_hosts=[survivor['name']])

    def verify_detach_policy(self, plan):
        if plan.get('storageRecovery')!={'disableForceDetachOnTimeout':True}:
            raise Blocked('EXPLICIT_MANUAL_FENCING_PROFILE_REQUIRED')
        script=("import pathlib,sys; rows=[]\n"
                "for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):\n"
                " try:\n"
                "  a=p.read_bytes().split(bytes([0])); exe=pathlib.Path(a[0].decode()).name if a[0] else ''\n"
                "  if exe=='kube-controller-manager': rows.append(a)\n"
                " except (OSError,UnicodeError): pass\n"
                "ok=len(rows)==1 and b'--disable-force-detach-on-timeout=true' in rows[0] and b'--disable-force-detach-on-timeout=false' not in rows[0]\n"
                "print('WERFT_MANUAL_FENCING' if ok else 'BLOCKED');sys.exit(0 if ok else 2)")
        # Script is static, sent via stdin; the remote command contains no user shell text.
        for h in (h for h in plan['hosts'] if h['role']=='controller'):
            if self.remote(plan,h,['/usr/bin/python3','-'],data=script.encode()).strip()!=b'WERFT_MANUAL_FENCING':
                raise Blocked('LIVE_FORCE_DETACH_POLICY_NOT_VERIFIED')

    def drain(self,node,uid):
        x=self.request('GET','/api/v1/nodes/'+node)
        if x['metadata']['uid']!=uid:raise Blocked('NODE_UID_CHANGED')
        self.command('kubectl',['drain',node,'--ignore-daemonsets','--timeout=15m'],timeout=960)
    def close(self):
        if self.api and hasattr(self.api,'close'):self.api.close()
