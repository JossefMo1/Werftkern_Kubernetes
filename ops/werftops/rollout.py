"""One worker at a time, durable roll-forward coordinator.

Maintenance remains owned for the entire workflow. All uncertain remote
installations are OBSERVED, never blindly resubmitted. No forced drain, pinned
volume migration, package downgrade, arbitrary user command or SSH TOFU.
"""
from __future__ import annotations
import datetime
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import shlex
import stat
import time
from . import readiness, upgrade
from .common import Blocked, canonical, digest_file, fingerprint, lock, read_json, run, write_json

VERSION = '0.2.0-dev.4'
ROOT = pathlib.Path('/var/lib/werftkern')

def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {'format','clusterId','operationId','workers','drainTimeoutSeconds','observationSeconds'} or plan['format'] != 'werftkern-worker-rollout/v1':
        raise Blocked('ROLLOUT_SCHEMA_INVALID')
    for key in ('clusterId','operationId'):
        if not isinstance(plan[key],str) or not re.fullmatch('[a-f0-9]{32}',plan[key]):
            raise Blocked('ROLLOUT_ID_INVALID')
    for key, lo, hi in [('drainTimeoutSeconds',30,1800),('observationSeconds',12,600)]:
        if type(plan[key]) is not int or not lo <= plan[key] <= hi:
            raise Blocked('ROLLOUT_TIMEOUT_INVALID')
    if not isinstance(plan['workers'],list) or not 1 <= len(plan['workers']) <= 20:
        raise Blocked('ROLLOUT_WORKERS_REQUIRED')
    ids, addresses = set(), set()
    for worker in plan['workers']:
        if not isinstance(worker,dict) or set(worker) != {'nodeId','address','sshUser'}:
            raise Blocked('WORKER_PLAN_SCHEMA_INVALID')
        if not isinstance(worker['nodeId'],str) or not re.fullmatch('[a-f0-9]{32}', worker['nodeId']) or worker['nodeId'] in ids:
            raise Blocked('WORKER_NODE_ID_INVALID_OR_DUPLICATE')
        try: address=ipaddress.IPv4Address(worker['address'])
        except (ValueError,TypeError): raise Blocked('WORKER_ADDRESS_INVALID') from None
        if not address.is_private or address.is_loopback or address.is_link_local or address.is_unspecified or str(address) != worker['address'] or str(address) in addresses:
            raise Blocked('DISTINCT_PRIVATE_WORKER_ADDRESS_REQUIRED')
        if not isinstance(worker['sshUser'],str) or not re.fullmatch('[a-z_][a-z0-9_-]{0,30}',worker['sshUser']):
            raise Blocked('WORKER_SSH_USER_INVALID')
        ids.add(worker['nodeId']); addresses.add(str(address))
    return fingerprint(plan)

def _json(runner, args, **kwargs):
    # A process' stdout is a protocol message; reject duplicate keys/constants.
    raw=runner(args,**kwargs)
    if len(raw) > 2_000_000: raise Blocked('COMMAND_JSON_TOO_LARGE')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out: raise Blocked('COMMAND_JSON_DUPLICATE_KEY')
            out[k]=v
        return out
    def constant(_): raise Blocked('COMMAND_JSON_NONFINITE')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)

def _workloads(s):
    return fingerprint({k: {p:w.get(p) for p in ('uid','generation','spec','paused','deleting')}
                        for k,w in s['workloads'].items()})

def _snapshot(plan,j,runner):
    s=_json(runner,['werft','status','--json'])
    if s.get('clusterId')!=plan['clusterId'] or s.get('schema')!=2 or s.get('maintenanceId','')!=plan['operationId']:
        raise Blocked('ROLLOUT_LOCK_OR_CLUSTER_CHANGED')
    if _workloads(s)!=j['workloadHash']:
        raise Blocked('ROLLOUT_WORKLOAD_INTENT_CHANGED')
    _identities(s,j)
    return s

def _identities(s,j):
    for node_id, identity in j['nodeIdentities'].items():
        n=s['nodes'].get(node_id)
        if not n or {k:n.get(k) for k in ('id','instanceId','address')}!=identity or n.get('revoked'):
            raise Blocked('ROLLOUT_NODE_IDENTITY_CHANGED')
    if set(s['nodes'])!=set(j['nodeIdentities']): raise Blocked('ROLLOUT_NODE_INVENTORY_CHANGED')

def _health(plan,runner):
    h=_json(runner,['werft','health','--all','--json','--expected-version',VERSION],timeout=90)
    if h.get('clusterId')!=plan['clusterId'] or not h.get('controllers'):
        raise Blocked('CONTROLLER_TARGET_VERIFICATION_REQUIRED')
    endpoints=set()
    for c in h['controllers']:
        if c.get('status')!='ready' or c.get('version')!=VERSION or c.get('clusterId')!=plan['clusterId'] or c.get('stateSchema')!=2 or not c.get('endpoint') or c['endpoint'] in endpoints:
            raise Blocked('CONTROLLER_TARGET_VERIFICATION_REQUIRED')
        if set(c.get('supportedAgentVersions',[]))!={VERSION,'0.2.0-dev.3'}:
            raise Blocked('EXPLICIT_WORKER_COMPATIBILITY_REQUIRED')
        endpoints.add(c['endpoint'])

def _stable(s, plan, operation, mixed=True):
    # Strict original snapshots remain unchanged; normalize only the validated
    # compatibility edge for the reused readiness checker.
    cloned=json.loads(canonical(s))
    for n in cloned.get('nodes',{}).values():
        if n.get('version') not in ({VERSION,'0.2.0-dev.3'} if mixed else {VERSION}):
            raise Blocked('WORKER_VERSION_OUTSIDE_UPGRADE_EDGE')
        n['version']=VERSION
    return readiness.check(cloned,plan['clusterId'],operation,VERSION,2)

def _receipt_valid(r, worker, plan, manifest, instance):
    expected={'format':'werftkern-worker-update/v1','operationId':plan['operationId'],
              'clusterId':plan['clusterId'],'nodeId':worker['nodeId'],'instanceId':instance,
              'packageSha256':manifest['packageSha256'],'packageVersion':manifest['packageVersion'],
              'version':VERSION,'phase':'installed-awaiting-controller'}
    if not isinstance(r,dict) or any(r.get(k)!=v for k,v in expected.items()):
        raise Blocked('WORKER_INSTALLATION_NOT_CONFIRMED')

def apply(plan, journal_path, package, manifest, signature, public_key, known_hosts, confirm,
          runner=run, remote=None, sleeper=time.sleep, monotonic=time.monotonic):
    plan_hash=validate(plan)
    if confirm!=plan_hash: raise Blocked('EXACT_ROLLOUT_PLAN_CONFIRMATION_REQUIRED')
    m=upgrade.verify(package,manifest,signature,public_key,runner)
    if m.get('version')!=VERSION or m.get('stateSchema')!=2:
        raise Blocked('COORDINATOR_TARGET_RELEASE_REQUIRED')
    # Bind all supplied files; do not allow changing host trust on resume.
    binding=fingerprint({'plan':plan,'release':m,'manifest':digest_file(manifest),
                         'signature':digest_file(signature),'key':digest_file(public_key),
                         'knownHosts':digest_file(known_hosts)})
    remote=remote or SSHWorkers(known_hosts,public_key,package,manifest,signature,runner)
    path=pathlib.Path(journal_path)
    with lock(ROOT/'update.lock'):
        if path.exists():
            j=read_json(path,private=True)
            if j.get('format')!='werftkern-rollout-journal/v1' or j.get('binding')!=binding:
                raise Blocked('ROLLOUT_REPLAY_CONFLICT')
            phases={'freeze-intent','workers','unlock-intent','completed'}
            worker_phases={'pending','draining','drained','install-intent','awaiting-agent','observing','uncordon-intent','done'}
            if j.get('phase') not in phases or not isinstance(j.get('workers'),dict) or set(j['workers'])!={w['nodeId'] for w in plan['workers']}:
                raise Blocked('ROLLOUT_JOURNAL_STATE_INVALID')
            if any(not isinstance(v,dict) or v.get('phase') not in worker_phases for v in j['workers'].values()):
                raise Blocked('WORKER_JOURNAL_STATE_INVALID')
            if j.get('phase')=='completed': return j  # receipt, not fresh health
        else:
            _health(plan,runner)
            state=_json(runner,['werft','status','--json'])
            if state.get('maintenanceId','')!='': raise Blocked('CLUSTER_ALREADY_IN_MAINTENANCE')
            _stable(state,plan,'')
            requested={w['nodeId'] for w in plan['workers']}
            for n in state['nodes'].values():
                if n.get('drain') or n.get('revoked'): raise Blocked('EXISTING_NODE_POLICY_REQUIRES_REVIEW')
                if not n.get('instanceId'): raise Blocked('CLAIMED_WORKER_IDENTITY_REQUIRED')
                if n.get('version')!=VERSION and n['id'] not in requested:
                    raise Blocked('PLAN_MUST_COVER_ALL_PREVIOUS_VERSION_WORKERS')
            for worker in plan['workers']:
                n=state['nodes'].get(worker['nodeId'])
                if not n or n.get('address')!=worker['address']:
                    raise Blocked('WORKER_PLAN_INVENTORY_MISMATCH')
                if n.get('version')==VERSION: raise Blocked('ALREADY_TARGET_WORKER_NOT_AN_UPGRADE')
                # Preflight trust/local role on every host before cluster mutation.
                remote.preflight(worker,plan,m)
            for w in state['workloads'].values():
                if w.get('spec',{}).get('node') in requested and not w.get('paused') and w['spec'].get('replicas',0)>0:
                    raise Blocked('PINNED_WORKLOAD_REQUIRES_OFFLINE_MAINTENANCE')
            j={'format':'werftkern-rollout-journal/v1','binding':binding,'phase':'freeze-intent',
               'operationId':plan['operationId'],'planHash':plan_hash,'target':m,
               'workloadHash':_workloads(state),
               'nodeIdentities':{k:{p:n.get(p) for p in ('id','instanceId','address')} for k,n in state['nodes'].items()},
               'workers':{w['nodeId']:{'phase':'pending'} for w in plan['workers']}}
            write_json(path,j,exclusive=True)
        if j['phase']=='freeze-intent':
            runner(['werft','maintenance','on','--id',plan['operationId'],'--reason','worker-rollout'])
            _snapshot(plan,j,runner)
            j['phase']='workers';write_json(path,j)
        if j['phase']=='workers':
            _health(plan,runner)
            for worker in plan['workers']:
                node=worker['nodeId'];step=j['workers'][node]
                if step['phase']=='done':continue
                _snapshot(plan,j,runner)
                if step['phase']=='pending':
                    step['phase']='draining';write_json(path,j)
                if step['phase']=='draining':
                    deadline=monotonic()+plan['drainTimeoutSeconds']
                    while True:
                        _snapshot(plan,j,runner)
                        x=_json(runner,['werft','maintenance-node','drain','--node',node,'--id',plan['operationId']])
                        if x.get('nodeId')!=node or x.get('clusterId')!=plan['clusterId'] or x.get('maintenanceId')!=plan['operationId'] or x.get('drain') is not True:
                            raise Blocked('DRAIN_ACK_IDENTITY_MISMATCH')
                        if type(x.get('unconfirmedAllocations')) is not int: raise Blocked('DRAIN_ACK_INVALID')
                        if x['unconfirmedAllocations']==0:
                            step['beforeSequence']=x['heartbeatSequence'];step['phase']='drained';write_json(path,j);break
                        if monotonic()>=deadline:raise Blocked('DRAIN_DEADLINE_NO_FORCE_EVICTION')
                        sleeper(3)
                if step['phase']=='drained':
                    _stable(_snapshot(plan,j,runner),plan,plan['operationId'])
                    # Persist BEFORE remote execution. Lost response -> observation
                    # only on next run, even if remote receipt is absent.
                    step['phase']='install-intent';write_json(path,j)
                    r=remote.install(worker,plan,m)
                    _receipt_valid(r,worker,plan,m,j['nodeIdentities'][node]['instanceId'])
                    step['receipt']=r;step['phase']='awaiting-agent';write_json(path,j)
                elif step['phase']=='install-intent':
                    r=remote.receipt(worker,plan)
                    _receipt_valid(r,worker,plan,m,j['nodeIdentities'][node]['instanceId'])
                    step['receipt']=r;step['phase']='awaiting-agent';write_json(path,j)
                if step['phase']=='awaiting-agent':
                    deadline=monotonic()+120
                    while True:
                        s=_snapshot(plan,j,runner);n=s['nodes'][node]
                        if n.get('version')==VERSION and n.get('heartbeatSequence',0)>step['beforeSequence'] and n.get('healthy') is True:
                            _stable(s,plan,plan['operationId']);break
                        if monotonic()>=deadline:raise Blocked('NEW_AGENT_NOT_OBSERVED')
                        sleeper(3)
                    # Actual local Docker/demo smoke, separately from business
                    # application checks. The coordinator never fabricates it.
                    smoke=remote.smoke(worker,plan)
                    required={'clusterId':plan['clusterId'],'nodeId':node,'operationId':plan['operationId'],
                              'version':VERSION,'httpReady':True,'cleanupConfirmed':True}
                    if not isinstance(smoke,dict) or any(smoke.get(k)!=v for k,v in required.items()):
                        raise Blocked('WORKER_SMOKE_NOT_VERIFIED')
                    step['smoke']=smoke;step['phase']='observing';write_json(path,j)
                if step['phase']=='observing':
                    # Restarting the coordinator restarts this window. A stored
                    # old green observation is never enough to uncordon a node.
                    previous=None;start=monotonic();samples=0
                    while True:
                        s=_snapshot(plan,j,runner)
                        sequences=_stable(s,plan,plan['operationId'])
                        n=s['nodes'][node]
                        if n.get('version')!=VERSION or n.get('drain') is not True:raise Blocked('TARGET_WORKER_STATE_CHANGED')
                        readiness.advanced(previous,sequences);previous=sequences;samples+=1
                        if samples>=3 and monotonic()-start>=plan['observationSeconds']:break
                        sleeper(6)
                    step['verifiedSequence']=s['nodes'][node]['heartbeatSequence'];step['observations']=samples
                    step['phase']='uncordon-intent';write_json(path,j)
                if step['phase']=='uncordon-intent':
                    _stable(_snapshot(plan,j,runner),plan,plan['operationId'])
                    runner(['werft','maintenance-node','uncordon','--node',node,'--id',plan['operationId'],
                            '--expected-version',VERSION,'--min-sequence',str(step['verifiedSequence'])])
                    step['phase']='done';write_json(path,j)
            # Non-target nodes must already run the target, otherwise finish
            # would grant a misleading partially upgraded cluster success.
            _stable(_snapshot(plan,j,runner),plan,plan['operationId'],mixed=False)
            _health(plan,runner)
            j['phase']='unlock-intent';write_json(path,j)
        if j['phase']=='unlock-intent':
            s=_json(runner,['werft','status','--json'])
            lockid=s.get('maintenanceId','')
            if lockid not in ('',plan['operationId']):raise Blocked('NEW_MAINTENANCE_OWNER_NOT_TOUCHED')
            if _workloads(s)!=j['workloadHash']:raise Blocked('ROLLOUT_WORKLOAD_INTENT_CHANGED')
            _identities(s,j)
            _stable(s,plan,lockid,mixed=False)
            _health(plan,runner)
            if lockid:runner(['werft','maintenance','off','--id',plan['operationId'],'--reason','worker-rollout-verified'])
            else:j['unlockAcknowledgementRecovered']=True
            j['phase']='completed';j['businessValidation']='not-performed';write_json(path,j)
        return j

class SSHWorkers:
    """Fixed remote commands; host trust must be independently pre-established."""
    def __init__(self,known_hosts,public_key,package,manifest,signature,runner=run):
        self.runner=runner;self.key=pathlib.Path(public_key);self.package=pathlib.Path(package)
        self.manifest=pathlib.Path(manifest);self.signature=pathlib.Path(signature)
        self.hosts=pathlib.Path(known_hosts).resolve(strict=True)
        for p in (pathlib.Path(known_hosts),self.key):
            s=p.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_mode&0o022 or s.st_uid!=os.geteuid():
                raise Blocked('OWNED_UNMODIFIABLE_TRUST_FILE_REQUIRED')
        self.opts=['-F','/dev/null','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
                   '-o','UserKnownHostsFile='+str(self.hosts),'-o','GlobalKnownHostsFile=/dev/null',
                   '-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','PermitLocalCommand=no',
                   '-o','ControlMaster=no','-o','ControlPath=none','-o','ConnectTimeout=10']
    def _ssh(self,w,argv,**kwargs):
        return self.runner(['ssh',*self.opts,w['sshUser']+'@'+w['address'],shlex.join(argv)],**kwargs)
    def preflight(self,w,p,m):
        code="""import json,pathlib,hashlib,os
b=pathlib.Path('/etc/werftkern');a=json.loads((b/'agent.json').read_text())
if (b/'control.json').exists():raise SystemExit(2)
k=b/'trust/releases.pem';s=k.lstat()
if not k.is_file() or k.is_symlink() or s.st_uid!=0 or s.st_mode&0o022:raise SystemExit(3)
print(json.dumps({'nodeId':a['nodeId'],'instanceId':a['instanceId'],'clusterId':a['client']['clusterId'],'address':a['address'],'keySha':hashlib.sha256(k.read_bytes()).hexdigest()}))"""
        o=json.loads(self._ssh(w,['sudo','-n','python3','-I','-c',code]))
        if o.get('nodeId')!=w['nodeId'] or o.get('address')!=w['address'] or o.get('clusterId')!=p['clusterId'] or o.get('keySha')!=digest_file(self.key):
            raise Blocked('REMOTE_IDENTITY_OR_TRUST_MISMATCH')
    def _home(self,p):return '/var/lib/werftkern/worker-updates/'+p['operationId']+'/stage'
    def install(self,w,p,m):
        home=self._home(p)
        # A root-owned staging helper, no /tmp race and no overwrite of divergent
        # payloads. Temporary files can remain after crash, never authorize install.
        upload="""import sys,pathlib,os,stat,hashlib,tempfile
p=pathlib.Path(sys.argv[1]);expected=sys.argv[2]
for d in reversed(p.parent.parents):
 if d.exists() and (d.is_symlink() or not d.is_dir() or d.stat().st_mode&0o022 or d.stat().st_uid!=0):raise SystemExit(2)
p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
if p.parent.is_symlink() or p.parent.stat().st_uid!=0 or p.parent.stat().st_mode&0o077:raise SystemExit(3)
b=sys.stdin.buffer.read(128*1024*1024+1)
if len(b)>128*1024*1024 or hashlib.sha256(b).hexdigest()!=expected:raise SystemExit(4)
if p.exists():
 if p.is_symlink() or p.stat().st_uid!=0 or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise SystemExit(5)
else:
 fd,n=tempfile.mkstemp(dir=p.parent)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.link(n,p);os.unlink(n)
 fd=os.open(p.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
"""
        for src,dest in ((self.package,'runtime.deb'),(self.manifest,'release.json'),(self.signature,'release.sig')):
            if src.stat().st_size>128*1024*1024:raise Blocked('PACKAGE_PAYLOAD_TOO_LARGE')
            self._ssh(w,['sudo','-n','python3','-I','-c',upload,home+'/'+dest,digest_file(src)],data=src.read_bytes(),timeout=600)
        # Existing installed verifier authenticates the full target before ANY
        # helper from the package executes. Trust key is never uploaded here.
        self._ssh(w,['sudo','-n','/usr/bin/werft','release','verify','--package',home+'/runtime.deb',
                     '--manifest',home+'/release.json','--signature',home+'/release.sig',
                     '--public-key','/etc/werftkern/trust/releases.pem'])
        # Unique immutable staging and initial verifier make the target's helper
        # trustworthy. No privileged mutation was authorized by package filename.
        helper=home+'/helper'
        self._ssh(w,['sudo','-n','install','-d','-m','0700',helper])
        self._ssh(w,['sudo','-n','dpkg-deb','-x',home+'/runtime.deb',helper],timeout=120)
        code="import sys;sys.path.insert(0,sys.argv.pop(1));from werftops.__main__ import main;main()"
        args=['sudo','-n','env','-i','PATH=/usr/sbin:/usr/bin:/sbin:/bin','python3','-I','-c',code,
              helper+'/usr/lib/werftkern/ops','worker-upgrade','install','--package',home+'/runtime.deb',
              '--manifest',home+'/release.json','--signature',home+'/release.sig','--operation',p['operationId'],
              '--cluster',p['clusterId'],'--node',w['nodeId'],'--staged-binary',helper+'/usr/bin/werft']
        return json.loads(self._ssh(w,args,timeout=900))
    def receipt(self,w,p):
        return json.loads(self._ssh(w,['sudo','-n','/usr/bin/werft-ops','worker-upgrade','receipt','--operation',p['operationId']]))
    def smoke(self,w,p):
        return json.loads(self._ssh(w,['sudo','-n','/usr/bin/werft','worker-check','--operation',p['operationId'],'--json'],timeout=150))
