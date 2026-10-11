"""Native-host PostgreSQL/Patroni integration, outside the workload scheduler.

Three dedicated database hosts; independent etcd trust domain; mandatory
watchdog. No forced promotion, disabling TLS, deleting PGDATA or shell input.
Generated artifacts are private installation kits, NOT release artifacts.
"""
from __future__ import annotations
import datetime, ipaddress, json, os, pathlib, pwd, re, secrets, ssl, stat, time
import urllib.error, urllib.parse, urllib.request
from .common import Blocked, atomic, canonical, digest_file, fingerprint, host_preflight, lock, name, private_read, read_json, run, write_json

ETCD_PORT=23901
PEER_PORT=23902
PG_PORT=5432
REST_PORT=8008
FORMAT='werftkern-database-ha/v1'
RFC1918=[ipaddress.IPv4Network(v) for v in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]

def private_ip(v):
    try: ip=ipaddress.IPv4Address(v)
    except (ValueError,TypeError): raise Blocked('DATABASE_IPV4_REQUIRED') from None
    if not any(ip in net for net in RFC1918):raise Blocked('DATABASE_RFC1918_ADDRESS_REQUIRED')
    return str(ip)

def validate(p):
    if not isinstance(p,dict) or set(p)!={'format','name','hosts','clientCIDRs','postgresMajor'} or p['format']!=FORMAT or p['postgresMajor']!=17:
        raise Blocked('DATABASE_PLAN_INVALID')
    name(p['name'])
    if not isinstance(p['hosts'],list) or len(p['hosts'])!=3:raise Blocked('THREE_DATABASE_HOSTS_REQUIRED')
    ips=set();names=set()
    for h in p['hosts']:
        if not isinstance(h,dict) or set(h)!={'name','address'}:raise Blocked('DATABASE_HOST_INVALID')
        name(h['name']);private_ip(h['address'])
        if h['name'] in names or h['address'] in ips:raise Blocked('DATABASE_HOST_DUPLICATE')
        ips.add(h['address']);names.add(h['name'])
    if not isinstance(p['clientCIDRs'],list) or not 1<=len(p['clientCIDRs'])<=20:raise Blocked('CLIENT_CIDRS_REQUIRED')
    for raw in p['clientCIDRs']:
        try:n=ipaddress.IPv4Network(raw,strict=True)
        except (ValueError,TypeError):raise Blocked('CLIENT_CIDR_INVALID') from None
        if not any(n.subnet_of(r) for r in RFC1918):raise Blocked('CLIENT_CIDR_NOT_PRIVATE')
    return fingerprint(p)

def paths(scope):
    return pathlib.Path('/etc/werftkern-database')/scope, pathlib.Path('/var/lib/werftkern-database')/scope

def certificate(directory, basename, ca=None, ip=None, runner=run):
    """All names are fixed/generated. Passwords never enter command arguments."""
    directory=pathlib.Path(directory);directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    key=directory/(basename+'.key');crt=directory/(basename+'.crt')
    runner(['openssl','genpkey','-algorithm','EC','-pkeyopt','ec_paramgen_curve:P-256','-out',str(key)])
    key.chmod(0o600)
    if ca is None:
        runner(['openssl','req','-new','-x509','-sha256','-days','1095','-key',str(key),'-subj','/CN='+basename,'-addext','basicConstraints=critical,CA:TRUE,pathlen:0','-addext','keyUsage=critical,keyCertSign,cRLSign','-out',str(crt)])
    else:
        csr=directory/(basename+'.csr');ext=directory/(basename+'.ext')
        runner(['openssl','req','-new','-key',str(key),'-subj','/CN='+basename,'-out',str(csr)])
        text='basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth,clientAuth\n'
        if ip is not None:text+='subjectAltName=IP:'+private_ip(ip)+'\n'
        atomic(ext,text.encode())
        runner(['openssl','x509','-req','-in',str(csr),'-CA',str(ca[0]),'-CAkey',str(ca[1]),'-set_serial','0x'+secrets.token_hex(16),'-days','90','-sha256','-extfile',str(ext),'-out',str(crt)])
        csr.unlink();ext.unlink()
    crt.chmod(0o600)
    return crt,key

def config_for(plan, host, passwords):
    scope=plan['name'];ip=host['address'];cfg,data=paths(scope)
    pg=str(cfg/'patroni');etc=str(cfg/'etcd')
    peers=sorted(plan['hosts'],key=lambda h:h['name'])
    hba=['local all postgres peer','local all all reject',
         'hostnossl all all 0.0.0.0/0 reject','hostnossl replication all 0.0.0.0/0 reject']
    for h in peers:
        hba.extend([f"hostssl replication wk_replication {h['address']}/32 scram-sha-256",
                    f"hostssl all postgres,wk_rewind {h['address']}/32 scram-sha-256"])
    hba.extend(['hostssl all postgres,wk_replication,wk_rewind 0.0.0.0/0 reject'])
    hba.extend(f'hostssl all all {c} scram-sha-256' for c in sorted(set(plan['clientCIDRs'])))
    hba.extend(['host all all 0.0.0.0/0 reject','host replication all 0.0.0.0/0 reject','host all all ::/0 reject','host replication all ::/0 reject'])
    auth={role:{'username':user,'password':passwords[role],'sslmode':'verify-full','sslrootcert':pg+'/db-ca.crt'} for role,user in [('superuser','postgres'),('replication','wk_replication'),('rewind','wk_rewind')]}
    patroni={
      'scope':scope,'name':host['name'],'namespace':'/werft-databases/',
      'restapi':{'listen':f'{ip}:{REST_PORT}','connect_address':f'{ip}:{REST_PORT}',
                 'certfile':pg+'/node.crt','keyfile':pg+'/node.key','cafile':pg+'/db-ca.crt','verify_client':'required',
                 'allowlist':[h['address']+'/32' for h in peers]},
      'ctl':{'cacert':pg+'/db-ca.crt','certfile':pg+'/node.crt','keyfile':pg+'/node.key','insecure':False},
      'etcd3':{'hosts':[f"{h['address']}:{ETCD_PORT}" for h in peers],'protocol':'https',
               'cacert':pg+'/dcs-ca.crt','cert':pg+'/dcs-client.crt','key':pg+'/dcs-client.key'},
      'bootstrap':{'dcs':{'ttl':60,'loop_wait':5,'retry_timeout':5,'maximum_lag_on_failover':0,'check_timeline':True,
                         'synchronous_mode':True,'synchronous_mode_strict':True,'synchronous_node_count':1,'failsafe_mode':False,
                         'postgresql':{'use_pg_rewind':True,'use_slots':True,'parameters':{'wal_level':'replica','hot_standby':'on',
                           'wal_log_hints':'on','max_wal_senders':10,'max_replication_slots':10,'password_encryption':'scram-sha-256',
                           'synchronous_commit':'on','ssl':'on','ssl_min_protocol_version':'TLSv1.2'}}},
                   'initdb':[{'encoding':'UTF8'},'data-checksums'], 'pg_hba':hba},
      'postgresql':{'listen':f'{ip}:{PG_PORT}','connect_address':f'{ip}:{PG_PORT}',
                    'data_dir':str(data/'pgdata'),'bin_dir':'/usr/lib/postgresql/17/bin',
                    'pgpass':str(data/'patroni'/'pgpass'),'authentication':auth,
                    'remove_data_directory_on_rewind_failure':False,'remove_data_directory_on_diverged_timelines':False,
                    'parameters':{'ssl_cert_file':pg+'/node.crt','ssl_key_file':pg+'/node.key',
                                  'unix_socket_directories':'/run/werft-db-'+scope},'pg_hba':hba},
      'watchdog':{'mode':'required','device':'/dev/watchdog','safety_margin':-1},
      'tags':{'nofailover':False,'noloadbalance':False,'nosync':False}}
    transport={'cert-file':etc+'/server.crt','key-file':etc+'/server.key','trusted-ca-file':etc+'/dcs-ca.crt','client-cert-auth':True}
    etcd={'name':host['name'],'data-dir':str(data/'etcd'),'listen-client-urls':f'https://{ip}:{ETCD_PORT}',
      'advertise-client-urls':f'https://{ip}:{ETCD_PORT}','listen-peer-urls':f'https://{ip}:{PEER_PORT}',
      'initial-advertise-peer-urls':f'https://{ip}:{PEER_PORT}',
      'initial-cluster':','.join(f"{h['name']}=https://{h['address']}:{PEER_PORT}" for h in peers),
      'initial-cluster-state':'new','initial-cluster-token':'werft-db-'+fingerprint(plan)[:32],
      'client-transport-security':transport,'peer-transport-security':transport,
      'auto-compaction-mode':'periodic','auto-compaction-retention':'1h','quota-backend-bytes':268435456}
    return patroni,etcd

def prepare(plan,out,runner=run):
    digest=validate(plan);out=pathlib.Path(out)
    # No idempotent re-keying of existing kits. Incomplete creation is explicit.
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    write_json(out/'PREPARING.json',{'planSHA256':digest},exclusive=True)
    authority=out/'authority';authority.mkdir(mode=0o700)
    dbca=certificate(authority,'database-root',runner=runner)
    dcsca=certificate(authority,'database-dcs-root',runner=runner)
    passwords={r:secrets.token_urlsafe(36) for r in ('superuser','replication','rewind')}
    for h in sorted(plan['hosts'],key=lambda v:v['name']):
        directory=out/h['name'];directory.mkdir(mode=0o700)
        patroni=directory/'patroni';etcd=directory/'etcd';patroni.mkdir(mode=0o700);etcd.mkdir(mode=0o700)
        certificate(patroni,'node',dbca,h['address'],runner)
        certificate(patroni,'dcs-client',dcsca,h['address'],runner)
        certificate(etcd,'server',dcsca,h['address'],runner)
        for dst,src in ((patroni/'db-ca.crt',dbca[0]),(patroni/'dcs-ca.crt',dcsca[0]),(etcd/'dcs-ca.crt',dcsca[0])):atomic(dst,src.read_bytes())
        pgconfig,etcdconfig=config_for(plan,h,passwords)
        write_json(patroni/'patroni.json',pgconfig,exclusive=True);write_json(etcd/'etcd.json',etcdconfig,exclusive=True)
        files={str(p.relative_to(directory)):digest_file(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        write_json(directory/'kit.json',{'format':'werftkern-database-kit/v1','plan':plan,'planSHA256':digest,'host':h,'files':files},exclusive=True)
    write_json(out/'plan.json',plan,exclusive=True)
    (out/'PREPARING.json').unlink()
    return {'planSHA256':digest,'hosts':[h['name'] for h in plan['hosts']],'status':'private-kits-prepared','productionQualified':False}

EXPECTED={'patroni/node.crt','patroni/node.key','patroni/dcs-client.crt','patroni/dcs-client.key',
          'patroni/db-ca.crt','patroni/dcs-ca.crt','patroni/patroni.json',
          'etcd/server.crt','etcd/server.key','etcd/dcs-ca.crt','etcd/etcd.json'}

def load_kit(directory):
    directory=pathlib.Path(directory)
    if directory.is_symlink():raise Blocked('DATABASE_KIT_SYMLINK')
    k=read_json(directory/'kit.json',private=True)
    if set(k)!= {'format','plan','planSHA256','host','files'} or k['format']!='werftkern-database-kit/v1':raise Blocked('DATABASE_KIT_FORMAT_INVALID')
    if validate(k['plan'])!=k['planSHA256'] or k['host'] not in k['plan']['hosts'] or set(k['files'])!=EXPECTED:raise Blocked('DATABASE_KIT_IDENTITY_INVALID')
    actual={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
    if actual!=EXPECTED|{'kit.json'} or any(p.is_symlink() for p in directory.rglob('*')):raise Blocked('DATABASE_KIT_UNEXPECTED_FILES')
    for path,digest in k['files'].items():
        raw=private_read(directory/path,65536)
        import hashlib
        if hashlib.sha256(raw).hexdigest()!=digest:raise Blocked('DATABASE_KIT_CONTENT_CHANGED')
    pg=read_json(directory/'patroni/patroni.json',private=True)
    # Recompute expected configuration, not just self-declared file hashes.
    try:pw={r:pg['postgresql']['authentication'][r]['password'] for r in ('superuser','replication','rewind')}
    except (KeyError,TypeError):raise Blocked('DATABASE_PASSWORD_CONTRACT_INVALID') from None
    if any(not isinstance(p,str) or not re.fullmatch('[A-Za-z0-9_-]{48}',p) for p in pw.values()):raise Blocked('DATABASE_PASSWORD_CONTRACT_INVALID')
    expected,expected_etcd=config_for(k['plan'],k['host'],pw)
    if pg!=expected or read_json(directory/'etcd/etcd.json',private=True)!=expected_etcd:raise Blocked('DATABASE_SECURITY_PROFILE_CHANGED')
    return k

def verify_certificates(directory,host,runner=run):
    root=pathlib.Path(directory)
    for stem,ca in [('patroni/node','patroni/db-ca.crt'),('patroni/dcs-client','patroni/dcs-ca.crt'),('etcd/server','etcd/dcs-ca.crt')]:
        crt=str(root/(stem+'.crt'));key=str(root/(stem+'.key'))
        runner(['openssl','verify','-CAfile',str(root/ca),crt])
        runner(['openssl','x509','-in',crt,'-checkend','86400','-noout'])
        runner(['openssl','x509','-in',crt,'-checkip',host['address'],'-noout'])
        pub=runner(['openssl','x509','-in',crt,'-pubkey','-noout'])
        if pub!=runner(['openssl','pkey','-in',key,'-pubout']):raise Blocked('DATABASE_KEY_CERTIFICATE_MISMATCH')
    if (root/'patroni/db-ca.crt').read_bytes()==(root/'etcd/dcs-ca.crt').read_bytes():raise Blocked('DATABASE_TRUST_DOMAINS_NOT_SEPARATE')

def units(scope):
    cfg,data=paths(scope)
    common='Restart=on-failure\nRestartSec=5\nNoNewPrivileges=true\nProtectSystem=strict\nProtectHome=true\nProtectKernelTunables=true\nProtectKernelModules=true\nProtectControlGroups=true\nUMask=0077\n'
    etcd=f'[Unit]\nDescription=Werftkern database DCS {scope}\nAfter=network-online.target\nWants=network-online.target\n[Service]\nUser=etcd\nExecStart=/usr/bin/etcd --config-file={cfg}/etcd/etcd.json\nReadWritePaths={data}/etcd\nPrivateDevices=true\n'+common+'[Install]\nWantedBy=multi-user.target\n'
    patroni=f'[Unit]\nDescription=Werftkern Patroni {scope}\nAfter=network-online.target werft-db-{scope}-etcd.service\nWants=werft-db-{scope}-etcd.service\n[Service]\nUser=postgres\nExecStart=/usr/bin/patroni {cfg}/patroni/patroni.json\nKillMode=process\nTimeoutStopSec=120\nRuntimeDirectory=werft-db-{scope}\nRuntimeDirectoryMode=0700\nReadWritePaths={data}/pgdata {data}/patroni /run/werft-db-{scope}\nDevicePolicy=closed\nDeviceAllow=/dev/watchdog rw\n'+common+'[Install]\nWantedBy=multi-user.target\n'
    return {f'werft-db-{scope}-etcd.service':etcd,f'werft-db-{scope}-patroni.service':patroni}

def install(directory,confirm_host,accept_watchdog_reset=False,runner=run):
    host_preflight();k=load_kit(directory);h=k['host'];scope=k['plan']['name']
    if confirm_host!=h['name'] or accept_watchdog_reset is not True:raise Blocked('EXACT_HOST_AND_WATCHDOG_RESET_CONFIRMATION_REQUIRED')
    ips=json.loads(runner(['ip','-j','address','show']))
    if h['address'] not in {a.get('local') for i in ips for a in i.get('addr_info',[])}:raise Blocked('DATABASE_HOST_ADDRESS_NOT_LOCAL')
    # This integration does not install arbitrary dependencies or change package sources.
    if not runner(['/usr/lib/postgresql/17/bin/postgres','--version']).decode().startswith('postgres (PostgreSQL) 17.'):raise Blocked('POSTGRESQL_17_REQUIRED')
    if not re.search(r'\b4\.\d+\.\d+\b',runner(['/usr/bin/patroni','--version']).decode()):raise Blocked('PATRONI_4_REQUIRED')
    v=runner(['/usr/bin/etcd','--version']).decode()
    if not re.search(r'etcd Version: 3\.(?:[6-9]|[1-9][0-9])\.',v):raise Blocked('ETCD_3_6_OR_NEWER_REQUIRED')
    pg=pwd.getpwnam('postgres');et=pwd.getpwnam('etcd')
    wd=os.stat('/dev/watchdog',follow_symlinks=False)
    if not stat.S_ISCHR(wd.st_mode) or wd.st_uid!=pg.pw_uid or not wd.st_mode&stat.S_IWUSR:raise Blocked('POSTGRES_OWNED_WATCHDOG_REQUIRED')
    verify_certificates(directory,h,runner)
    cfg,data=paths(scope)
    with lock('/var/lib/werftkern-database/install.lock'):
        if cfg.exists() or data.exists():raise Blocked('DATABASE_INSTALL_EXISTS_OR_INTERRUPTED_NO_AUTOMATIC_REBOOTSTRAP')
        # Write intent before any service starts. Never erase on failure.
        data.parent.mkdir(parents=True,exist_ok=True,mode=0o755);cfg.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
        for parent in (data.parent,cfg.parent):
            if parent.is_symlink() or parent.stat().st_uid!=0:raise Blocked('DATABASE_PARENT_NOT_TRUSTED')
            parent.chmod(0o755)
        data.mkdir(mode=0o755);cfg.mkdir(mode=0o755)
        write_json(data/'install-intent.json',{'scope':scope,'planSHA256':k['planSHA256'],'host':h,'phase':'preparing'},exclusive=True)
        for role,user in [('patroni',pg),('etcd',et)]:
            (cfg/role).mkdir(mode=0o700);os.chown(cfg/role,user.pw_uid,user.pw_gid)
            (data/role).mkdir(mode=0o700);os.chown(data/role,user.pw_uid,user.pw_gid)
        (data/'pgdata').mkdir(mode=0o700);os.chown(data/'pgdata',pg.pw_uid,pg.pw_gid)
        for relative in sorted(EXPECTED):
            dest=cfg/relative;atomic(dest,private_read(pathlib.Path(directory)/relative,65536))
            user=pg if relative.startswith('patroni/') else et
            os.chown(dest,user.pw_uid,user.pw_gid)
        runner(['/usr/bin/patroni','--validate-config',str(cfg/'patroni/patroni.json')])
        for service,body in units(scope).items():atomic(pathlib.Path('/etc/systemd/system')/service,body.encode(),mode=0o644,exclusive=True)
        write_json(data/'install-intent.json',{'scope':scope,'planSHA256':k['planSHA256'],'host':h,'phase':'start-attempted'})
        runner(['systemctl','daemon-reload'])
        for service in units(scope):runner(['systemctl','enable','--now',service],timeout=180)
        # Starting a daemon is NOT database readiness. Health qualification is separate.
        write_json(data/'install-intent.json',{'scope':scope,'planSHA256':k['planSHA256'],'host':h,'phase':'services-started-health-unverified'})
        return {'status':'services-started-health-unverified','scope':scope,'productionQualified':False}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None

class REST:
    def __init__(self,plan,ca,cert,key):
        validate(plan);self.hosts={h['name']:h['address'] for h in plan['hosts']}
        context=ssl.create_default_context(cafile=str(ca));context.minimum_version=ssl.TLSVersion.TLSv1_2
        private_read(key,65536);context.load_cert_chain(str(cert),str(key))
        self.client=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=context))
    def call(self,host,method,path,body=None):
        if host not in self.hosts or (method,path) not in {('GET','/patroni'),('GET','/config'),('GET','/primary'),('POST','/switchover')}:raise Blocked('PATRONI_REQUEST_NOT_ALLOWED')
        req=urllib.request.Request(f'https://{self.hosts[host]}:{REST_PORT}'+path,data=canonical(body) if body is not None else None,method=method,headers={'Content-Type':'application/json'})
        try:
            with self.client.open(req,timeout=10) as response:
                raw=response.read(65537)
                if len(raw)>65536:raise Blocked('PATRONI_RESPONSE_TOO_LARGE')
                return response.status,({} if path=='/switchover' else json.loads(raw) if raw else {})
        except (urllib.error.URLError,ValueError,TimeoutError,OSError):
            # Do not leak body, credentials, raw addresses or retry a mutation.
            raise Blocked('PATRONI_REQUEST_FAILED_OR_AMBIGUOUS') from None

def inspect(plan,api,now=None):
    validate(plan);now=now or time.time();states={};identifiers=set();primary=[]
    for h in plan['hosts']:
        code,s=api.call(h['name'],'GET','/patroni')
        if code!=200 or not isinstance(s,dict):raise Blocked('DATABASE_MEMBER_UNAVAILABLE')
        if s.get('patroni',{}).get('scope')!=plan['name'] or s['patroni'].get('name')!=h['name']:raise Blocked('DATABASE_MEMBER_IDENTITY_MISMATCH')
        if s.get('state')!='running' or s.get('pause') or s.get('cluster_unlocked') or s.get('failsafe_mode_is_active'):raise Blocked('DATABASE_MEMBER_NOT_READY')
        last=s.get('dcs_last_seen')
        if type(last) not in (int,float) or not -5<=now-last<=15:raise Blocked('DATABASE_DCS_OBSERVATION_STALE')
        dbid=s.get('database_system_identifier')
        if not isinstance(dbid,str) or not re.fullmatch(r'[0-9]{10,25}',dbid):raise Blocked('DATABASE_SYSTEM_ID_REQUIRED')
        identifiers.add(dbid)
        if s.get('role')=='primary':primary.append(h['name'])
        elif s.get('role')!='replica':raise Blocked('DATABASE_ROLE_UNEXPECTED')
        states[h['name']]=s
    if len(primary)!=1 or len(identifiers)!=1:raise Blocked('DATABASE_SPLIT_BRAIN_OR_IDENTITY_CONFLICT')
    leader=primary[0];code,_=api.call(leader,'GET','/primary')
    if code!=200:raise Blocked('DATABASE_PRIMARY_LOCK_UNCONFIRMED')
    config_code,config=api.call(leader,'GET','/config')
    if config_code!=200 or not isinstance(config,dict):raise Blocked('DATABASE_DYNAMIC_CONFIG_UNAVAILABLE')
    expected={'synchronous_mode':True,'synchronous_mode_strict':True,'synchronous_node_count':1,'check_timeline':True,'maximum_lag_on_failover':0,'failsafe_mode':False}
    if any(type(config.get(k)) is not type(v) or config.get(k)!=v for k,v in expected.items()):raise Blocked('DATABASE_DYNAMIC_POLICY_DRIFT')
    replicas=states[leader].get('replication',[])
    peers={h['name'] for h in plan['hosts']}-{leader}
    sync={r.get('application_name') for r in replicas if r.get('state')=='streaming' and r.get('sync_state')=='sync'}
    if not sync or not sync<=peers:raise Blocked('DATABASE_SYNCHRONOUS_REPLICA_REQUIRED')
    return {'scope':plan['name'],'systemId':next(iter(identifiers)),'primary':leader,'synchronousReplicas':sorted(sync),'members':sorted(states),'status':'observed-synchronous-cluster','watchdogHardwareQualified':False}

def switchover(plan,api,target,journal,confirmation):
    """Planned switchover only. Lost POST answer is never blindly replayed."""
    digest=validate(plan)
    if target not in {h['name'] for h in plan['hosts']} or confirmation!=plan['name']+':'+target:raise Blocked('DATABASE_SWITCHOVER_CONFIRMATION_REQUIRED')
    with lock(str(journal)+'.lock'):
        old=read_json(journal,private=True) if pathlib.Path(journal).exists() else None
        before=inspect(plan,api)
        if old:
            if old.get('planSHA256')!=digest or old.get('target')!=target or old.get('systemId')!=before['systemId']:raise Blocked('DATABASE_SWITCHOVER_JOURNAL_CONFLICT')
            if before['primary']==target:
                old['phase']='observed-new-primary';write_json(journal,old);return old
            raise Blocked('DATABASE_SWITCHOVER_UNCERTAIN_INSPECT_NO_REPOST')
        if target not in before['synchronousReplicas']:raise Blocked('SYNCHRONOUS_SWITCHOVER_TARGET_REQUIRED')
        record={'format':'werftkern-db-switchover/v1','planSHA256':digest,'source':before['primary'],'target':target,'systemId':before['systemId'],'phase':'request-intent'}
        write_json(journal,record,exclusive=True)
        code,_=api.call(before['primary'],'POST','/switchover',{'leader':before['primary'],'candidate':target})
        if code not in (200,202):raise Blocked('SWITCHOVER_NOT_ACCEPTED')
        record['phase']='accepted-observation-required';write_json(journal,record)
        return record
