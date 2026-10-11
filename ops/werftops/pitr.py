"""pgBackRest adapter: encrypted repository, explicit backup set, isolated PITR.

A successful file restore is NOT a successful WAL replay. Promotion is never
performed here. Run database actions as the postgres OS account. Configuration
and repository storage are trusted operator resources, outside source control.
"""
from __future__ import annotations
import configparser, datetime, hashlib, json, os, pathlib, pwd, re, stat, time
from .common import Blocked, atomic, canonical, digest_file, fingerprint, lock, name, private_read, read_json, run, write_json

UTC=datetime.timezone.utc
LABEL=re.compile(r'^\d{8}-\d{6}F(?:_\d{8}-\d{6}[DI])?$')

def owned_actor():
    if pwd.getpwuid(os.geteuid()).pw_name!='postgres':raise Blocked('RUN_AS_POSTGRES_OS_ACCOUNT')

def path_value(raw):
    if not isinstance(raw,str) or not re.fullmatch('/[A-Za-z0-9_./-]+',raw):raise Blocked('PITR_ABSOLUTE_PATH_REQUIRED')
    p=pathlib.Path(raw)
    if '..' in p.parts or str(p)!=raw or str(p)=='/':raise Blocked('PITR_PATH_INVALID')
    if any(x.is_symlink() for x in [p,*p.parents]):raise Blocked('PITR_SYMLINK_PATH_FORBIDDEN')
    return p

def independent(a,b):
    return a!=b and a not in b.parents and b not in a.parents

def target_time(value):
    try:
        t=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
        if t.tzinfo is None:raise ValueError()
        t=t.astimezone(UTC)
        if t>datetime.datetime.now(UTC)+datetime.timedelta(seconds=5):raise ValueError()
        return t
    except (ValueError,TypeError,AttributeError):raise Blocked('PITR_TARGET_REQUIRES_PAST_TIMESTAMP_WITH_TIMEZONE') from None

def prepare(plan,passfile,out):
    if not isinstance(plan,dict) or set(plan)!={'format','name','pgPath','socketDir','pgPort','repositoryPath'} or plan['format']!='werftkern-pitr/v1':raise Blocked('PITR_PLAN_INVALID')
    scope=name(plan['name']);pg=path_value(plan['pgPath']);repo=path_value(plan['repositoryPath']);sock=path_value(plan['socketDir'])
    if not independent(pg,repo) or type(plan['pgPort']) is not int or not 1024<=plan['pgPort']<=65535:raise Blocked('PITR_REPOSITORY_OR_PORT_INVALID')
    secret=private_read(passfile,256).decode().strip()
    if not re.fullmatch(r'[A-Za-z0-9_+/-]{32,128}={0,2}',secret):raise Blocked('PITR_RANDOM_CIPHER_SECRET_REQUIRED')
    raw=f'[{scope}]\npg1-path={pg}\npg1-port={plan["pgPort"]}\npg1-socket-path={sock}\n[global]\nrepo1-type=posix\nrepo1-path={repo}\nrepo1-cipher-type=aes-256-cbc\nrepo1-cipher-pass={secret}\nrepo1-retention-full=3\narchive-check=y\narchive-mode-check=y\nlog-level-console=error\nlog-level-file=off\n'.encode()
    include=path_value(str(pathlib.Path(out).absolute())+'.d')
    include.mkdir(mode=0o700,parents=True,exist_ok=False)
    atomic(out,raw,exclusive=True)
    return {'stanza':scope,'config':str(out),'status':'private-config-created-archive-setup-still-required','productionQualified':False}

def configuration(file,scope):
    name(scope);raw=private_read(file,65536)
    parser=configparser.ConfigParser(interpolation=None,strict=True)
    try: parser.read_string(raw.decode())
    except (configparser.Error, UnicodeError): raise Blocked('PITR_CONFIG_SYNTAX_INVALID') from None
    include=path_value(str(pathlib.Path(file).absolute())+'.d')
    try: st=include.stat()
    except OSError: raise Blocked('PITR_EMPTY_PRIVATE_INCLUDE_DIRECTORY_REQUIRED') from None
    if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode&0o077 or any(include.iterdir()):
        raise Blocked('PITR_EMPTY_PRIVATE_INCLUDE_DIRECTORY_REQUIRED')
    globalkeys={'repo1-type','repo1-path','repo1-cipher-type','repo1-cipher-pass','repo1-retention-full','archive-check','archive-mode-check','log-level-console','log-level-file'}
    if parser.defaults() or set(parser.sections())!={scope,'global'} or set(parser[scope])!={'pg1-path','pg1-port','pg1-socket-path'} or set(parser['global'])!=globalkeys:raise Blocked('PITR_CONFIG_CONTRACT_INVALID')
    g=parser['global'];local=parser[scope]
    if any(g[k]!=v for k,v in {'repo1-type':'posix','repo1-cipher-type':'aes-256-cbc','archive-check':'y','archive-mode-check':'y','log-level-console':'error','log-level-file':'off','repo1-retention-full':'3'}.items()):raise Blocked('PITR_UNSAFE_REPOSITORY_POLICY')
    if not re.fullmatch(r'[A-Za-z0-9_+/-]{32,128}={0,2}',g['repo1-cipher-pass']):raise Blocked('PITR_RANDOM_CIPHER_SECRET_REQUIRED')
    pg=path_value(local['pg1-path']);repo=path_value(g['repo1-path']);sock=path_value(local['pg1-socket-path'])
    if not independent(pg,repo):raise Blocked('PITR_REPO_OVERLAPS_DATA')
    port=int(local['pg1-port'])
    if not 1024<=port<=65535:raise Blocked('PITR_PORT_INVALID')
    return {'source':pg,'repository':repo,'socket':sock,'port':port,'sha256':hashlib.sha256(raw).hexdigest()}

def command(file,scope,*args):
    file=str(pathlib.Path(file).absolute())
    return ['pgbackrest','--config='+file,'--config-include-path='+file+'.d','--stanza='+scope,'--repo=1',*args]

def environment():
    # PGBACKREST_* and PG* override policy. No ambient overrides/passfiles/loaders.
    return {'PATH':'/usr/lib/postgresql/17/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C'}

def metadata_path(raw,c,other=()):
    p=path_value(str(pathlib.Path(raw).absolute()))
    if any(not independent(p,q) for q in (c['source'],c['repository'],*other)):
        raise Blocked('PITR_JOURNAL_MUST_BE_OUTSIDE_DATA_AND_REPOSITORY')
    return p

def catalog(file,scope,runner=run,allow_empty=False):
    raw=runner(command(file,scope,'--output=json','info'),timeout=60,env=environment())
    if len(raw)>4*1024*1024:raise Blocked('PITR_CATALOG_TOO_LARGE')
    values=json.loads(raw)
    if not isinstance(values,list) or len(values)!=1 or values[0].get('name')!=scope:raise Blocked('PITR_CATALOG_SCOPE_MISMATCH')
    s=values[0]
    code=s.get('status',{}).get('code')
    # pgBackRest release/2.59.1 src/command/info/info.c: status 2 = no valid backups.
    # Allowed only before the FIRST backup, never as restored/healthy evidence.
    empty=allow_empty and type(code) is int and code==2 and s.get('backup')==[]
    if (type(code) is not int or code!=0) and not empty or s.get('cipher')!='aes-256-cbc':
        raise Blocked('PITR_REPOSITORY_NOT_HEALTHY_OR_ENCRYPTED')
    dbs=s.get('db');backups=s.get('backup')
    if not isinstance(dbs,list) or not dbs or not isinstance(backups,list):raise Blocked('PITR_CATALOG_INCOMPLETE')
    return s

def backup_identity(s,label):
    if not isinstance(label,str) or not LABEL.fullmatch(label):raise Blocked('EXPLICIT_BACKUP_LABEL_REQUIRED')
    found=[b for b in s['backup'] if b.get('label')==label]
    if len(found)!=1:raise Blocked('BACKUP_LABEL_NOT_UNIQUE_OR_AVAILABLE')
    b=found[0]
    if b.get('error'):raise Blocked('BACKUP_CONTAINS_ERRORS')
    identity=b.get('database',{})
    found=[d for d in s['db'] if d.get('id')==identity.get('id') and d.get('repo-key')==identity.get('repo-key')==1]
    if len(found)!=1 or str(found[0].get('version'))!='17':raise Blocked('BACKUP_DATABASE_IDENTITY_UNSUPPORTED')
    sysid=str(found[0].get('system-id'))
    if not re.fullmatch(r'[0-9]{10,25}',sysid):raise Blocked('BACKUP_SYSTEM_ID_INVALID')
    stop=b.get('timestamp',{}).get('stop')
    if type(stop) is not int or stop<=0:raise Blocked('BACKUP_STOP_TIME_INVALID')
    return {'label':label,'systemId':sysid,'stop':stop,'catalogBackupSHA256':fingerprint(b)}

def initialize(file,scope,runner=run):
    owned_actor();configuration(file,scope)
    runner(command(file,scope,'stanza-create'),timeout=180,env=environment())
    runner(command(file,scope,'check'),timeout=180,env=environment())
    return {'status':'stanza-and-archive-check-completed','scope':scope,'restoreQualified':False}

def backup(file,scope,receipt,runner=run):
    owned_actor();c=configuration(file,scope);receipt=metadata_path(receipt,c)
    with lock(str(receipt)+'.lock'):
        if pathlib.Path(receipt).exists():raise Blocked('BACKUP_OPERATION_EXISTS_INSPECT_BEFORE_RETRY')
        before=catalog(file,scope,runner,allow_empty=True);labels={b.get('label') for b in before['backup']}
        intent={'format':'werftkern-pgbackrest-backup/v1','scope':scope,'configSHA256':c['sha256'],'phase':'backup-intent'}
        write_json(receipt,intent,exclusive=True)
        runner(command(file,scope,'check'),timeout=180,env=environment())
        runner(command(file,scope,'--type=full','backup'),timeout=7200,env=environment())
        after=catalog(file,scope,runner);new=[b['label'] for b in after['backup'] if b.get('label') not in labels]
        if len(new)!=1:raise Blocked('BACKUP_RESULT_AMBIGUOUS')
        ident=backup_identity(after,new[0]);intent.update(ident)
        intent['phase']='backup-observed-wal-replay-not-tested';write_json(receipt,intent)
        return intent

def restore(file,scope,label,when,target,expected_system_id,journal,confirm,runner=run):
    owned_actor();c=configuration(file,scope);t=target_time(when);target=path_value(str(target));ts=path_value(str(target)+'.tablespaces')
    if confirm!=scope+':'+str(target):raise Blocked('PITR_EXACT_TARGET_CONFIRMATION_REQUIRED')
    if any(not independent(p,q) for p in (target,ts) for q in (c['source'],c['repository'])):raise Blocked('PITR_RESTORE_OVER_SOURCE_OR_REPOSITORY_FORBIDDEN')
    if target.exists() or ts.exists():raise Blocked('PITR_RESTORE_TARGET_MUST_BE_NEW')
    # Remapping cannot protect against tablespaces created after backup start.
    # Do not run recovery on the source host or a host with its original data tree.
    if c['source'].exists():raise Blocked('PITR_SEPARATE_QUARANTINE_HOST_REQUIRED_SOURCE_PATH_EXISTS')
    journal=metadata_path(journal,c,(target,ts))
    with lock(str(journal)+'.lock'):
        if pathlib.Path(journal).exists():raise Blocked('PITR_RESTORE_ATTEMPT_EXISTS_NO_BLIND_REPLAY')
        ident=backup_identity(catalog(file,scope,runner),label)
        if ident['systemId']!=expected_system_id:raise Blocked('PITR_SYSTEM_ID_MISMATCH')
        if t.timestamp()<ident['stop']:raise Blocked('PITR_TARGET_PRECEDES_BACKUP_COMPLETION')
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        record={'format':'werftkern-pitr-restore/v1','scope':scope,'target':str(target),'tablespaces':str(ts),'configSHA256':c['sha256'],'time':t.isoformat(),'phase':'restore-intent',**ident}
        write_json(journal,record,exclusive=True)
        target.mkdir(mode=0o700);ts.mkdir(mode=0o700)
        runner(command(file,scope,'--set='+label,'--type=time','--target='+t.isoformat(),'--target-action=pause','--target-timeline=latest','--archive-mode=off','--recovery-option=hot_standby=on','--recovery-option=primary_conninfo=','--recovery-option=primary_slot_name=','--pg1-path='+str(target),'--tablespace-map-all='+str(ts),'restore'),timeout=7200,env=environment())
        if not (target/'PG_VERSION').is_file() or (target/'PG_VERSION').read_text().strip()!='17' or not (target/'recovery.signal').is_file():raise Blocked('PITR_RECOVERY_FILES_MISSING')
        record['phase']='files-restored-wal-replay-required';write_json(journal,record)
        return record

def verify_replay(journal,socket,port,runner=run):
    owned_actor();socket=path_value(str(socket))
    if type(port) is not int or not 1024<=port<=65535:raise Blocked('PITR_PORT_INVALID')
    with lock(str(journal)+'.lock'):
        record=read_json(journal,private=True)
        if record.get('format')!='werftkern-pitr-restore/v1' or record.get('phase') not in ('files-restored-wal-replay-required','replay-paused-application-validation-required'):raise Blocked('PITR_RESTORE_NOT_READY_FOR_VERIFICATION')
        sql="SELECT json_build_object('data', current_setting('data_directory'), 'systemId', (pg_control_system()).system_identifier::text, 'recovering', pg_is_in_recovery(), 'paused', pg_get_wal_replay_pause_state() = 'paused', 'target', current_setting('recovery_target_time'), 'action', current_setting('recovery_target_action'), 'listen', current_setting('listen_addresses'), 'archive', current_setting('archive_mode'))::text;"
        env={'PATH':'/usr/lib/postgresql/17/bin:/usr/bin:/bin','LANG':'C','PGCONNECT_TIMEOUT':'5'}
        raw=runner(['psql','--no-psqlrc','--no-password','--host',str(socket),'--port',str(port),'--dbname','postgres','--username','postgres','--tuples-only','--no-align','--set=ON_ERROR_STOP=1','--command',sql],timeout=20,env=env)
        observed=json.loads(raw)
        if observed.get('data')!=record['target'] or observed.get('systemId')!=record['systemId']:raise Blocked('PITR_REPLAY_SERVER_IDENTITY_MISMATCH')
        if observed.get('recovering') is not True or observed.get('paused') is not True or observed.get('action')!='pause' or observed.get('archive')!='off' or observed.get('listen') not in ('','127.0.0.1'):
            raise Blocked('PITR_REPLAY_NOT_PAUSED_AND_ISOLATED')
        if target_time(observed.get('target'))!=target_time(record['time']):raise Blocked('PITR_REPLAY_TARGET_MISMATCH')
        record['phase']='replay-paused-application-validation-required'
        record['verificationAt']=datetime.datetime.now(UTC).isoformat();write_json(journal,record)
        return record
