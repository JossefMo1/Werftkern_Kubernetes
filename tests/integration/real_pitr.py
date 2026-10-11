#!/usr/bin/env python3
"""Opt-in integration with REAL PostgreSQL17 and pgBackRest2.59.1+ processes.

Run as postgres on an explicitly disposable host. No fixtures, mocks, Docker or
remote cloud actions. Missing prerequisites are BLOCKED (exit 3), not a skip/pass.
The isolated data directories are on ONE HOST: this does not qualify cross-host
DR, Patroni HA, storage fencing, watchdogs, production RPO/RTO or source isolation.
"""
from __future__ import annotations
import argparse, datetime, json, os, pathlib, pwd, re, secrets, shutil, signal, subprocess, sys, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ops'))
from werftops import pitr
from werftops.common import Blocked,atomic,run
BIN=pathlib.Path('/usr/lib/postgresql/17/bin')
ENV={'PATH':str(BIN)+':/usr/bin:/bin','LANG':'C','LC_ALL':'C'}

class Server:
 def __init__(self,data,socket,port,options):
  self.data,self.socket,self.port=data,socket,port
  socket.mkdir(mode=0o700)
  self.log=open(data.parent/(data.name+'.log'),'wb')
  self.process=subprocess.Popen([str(BIN/'postgres'),'-D',str(data),'-k',str(socket),'-p',str(port),'-c','listen_addresses=',*options],stdout=self.log,stderr=subprocess.STDOUT,env=ENV,start_new_session=True)
 def sql(self,statement):
  return run([str(BIN/'psql'),'-X','-w','-h',str(self.socket),'-p',str(self.port),'-U','postgres','-d','postgres','-t','-A','-v','ON_ERROR_STOP=1','-c',statement],env=ENV,timeout=10).decode().strip()
 def wait(self):
  end=time.monotonic()+45
  while time.monotonic()<end:
   if self.process.poll() is not None:raise Blocked('POSTGRES_START_FAILED')
   try:
    if self.sql('SELECT 1')=='1':return
   except Blocked:pass
   time.sleep(0.2)
  raise Blocked('POSTGRES_START_DEADLINE')
 def stop(self):
  if self.process.poll() is None:
   os.killpg(self.process.pid,signal.SIGINT) # PG fast shutdown, no active clients
   try:self.process.wait(timeout=20)
   except subprocess.TimeoutExpired:
    os.killpg(self.process.pid,signal.SIGKILL);self.process.wait();self.log.close()
    raise Blocked('POSTGRES_REQUIRED_UNCLEAN_SHUTDOWN')
  self.log.close()

def exercise():
 missing=[str(BIN/x) for x in ('postgres','initdb','psql') if not (BIN/x).is_file()]
 if not shutil.which('pgbackrest'):missing.append('pgbackrest')
 if missing:raise Blocked('MISSING_REAL_TEST_DEPENDENCIES:'+','.join(missing))
 if os.environ.get('WERFT_DISPOSABLE_VM')!='1':raise Blocked('EXPLICIT_DISPOSABLE_HOST_OPT_IN_REQUIRED')
 if pwd.getpwuid(os.geteuid()).pw_name!='postgres':raise Blocked('REAL_DATABASE_TEST_MUST_RUN_AS_POSTGRES')
 version=run(['pgbackrest','version'],env=ENV).decode().strip()
 match=re.search(r'\b(\d+)\.(\d+)(?:\.(\d+))?\b',version)
 if not match or tuple(int(v or 0) for v in match.groups())<(2,59,1):raise Blocked('PGBACKREST_2_59_1_OR_NEWER_REQUIRED')
 pgversion=run([str(BIN/'postgres'),'--version'],env=ENV).decode().strip()
 if not pgversion.startswith('postgres (PostgreSQL) 17.'):raise Blocked('POSTGRESQL_17_REQUIRED')
 source=restored=None
 with tempfile.TemporaryDirectory(prefix='werft-pitr-',dir='/var/tmp') as d:
  home=pathlib.Path(d);home.chmod(0o700)
  pg,repo,sock=home/'source',home/'repo',home/'source-socket'
  repo.mkdir(mode=0o700)
  run([str(BIN/'initdb'),'-D',str(pg),'--auth-local=peer','--auth-host=reject','--encoding=UTF8','--data-checksums'],env=ENV)
  cipher=home/'cipher.key';atomic(cipher,secrets.token_urlsafe(48).encode())
  config=home/'pgbackrest.conf'
  pitr.prepare({'format':'werftkern-pitr/v1','name':'proof','pgPath':str(pg),'socketDir':str(sock),'pgPort':55431,'repositoryPath':str(repo)},cipher,config)
  # Generated paths contain no shell metacharacters; archive_command is fixed.
  archive=' '.join(pitr.command(config,'proof','archive-push'))+' %p'
  try:
   source=Server(pg,sock,55431,['-c','wal_level=replica','-c','archive_mode=on','-c','archive_command='+archive])
   source.wait();pitr.initialize(config,'proof')
   source.sql("CREATE TABLE werft_pitr_proof(id integer PRIMARY KEY, value text); INSERT INTO werft_pitr_proof VALUES(1,'before');")
   backup=pitr.backup(config,'proof',home/'backup.json')
   point=source.sql('SELECT clock_timestamp()::text')
   time.sleep(1.1)
   source.sql("INSERT INTO werft_pitr_proof VALUES(2,'after-target');")
   source.sql('SELECT pg_switch_wal()')
   run(pitr.command(config,'proof','check'),env=ENV,timeout=180)
   if source.sql('SELECT count(*) FROM werft_pitr_proof')!='2':raise Blocked('SOURCE_PROOF_INCOMPLETE')
   source.stop();source=None
   # Separate-path lab only. No original tablespaces or customer data exist.
   pg.rename(home/'stopped-source-quarantine')
   target=home/'restored';journal=home/'restore.json'
   receipt=pitr.restore(config,'proof',backup['label'],point,target,backup['systemId'],journal,'proof:'+str(target))
   if receipt['phase']!='files-restored-wal-replay-required':raise Blocked('FILE_RESTORE_RECEIPT_INVALID')
   restored=Server(target,home/'restore-socket',55432,['-c','archive_mode=off','-c','hot_standby=on','-c','shared_preload_libraries=','-c','session_preload_libraries=','-c','local_preload_libraries='])
   restored.wait()
   end=time.monotonic()+60
   while True:
    try:replayed=pitr.verify_replay(journal,restored.socket,55432);break
    except Blocked:
     if time.monotonic()>=end:raise Blocked('WAL_REPLAY_DID_NOT_REACH_PAUSED_TARGET')
     time.sleep(0.25)
   if restored.sql('SELECT count(*) FROM werft_pitr_proof')!='1':raise Blocked('PITR_WRONG_TRANSACTION_SET')
   if restored.sql("SELECT value FROM werft_pitr_proof WHERE id=1")!='before':raise Blocked('PITR_PROOF_DATA_MISMATCH')
   try:restored.sql("INSERT INTO werft_pitr_proof VALUES(3,'must-fail')")
   except Blocked:pass
   else:raise Blocked('PAUSED_RESTORE_ACCEPTED_A_WRITE')
   return {'status':'passed','mode':'real-single-host-PG17-pgBackRest-PITR','postgres':pgversion,'pgbackrest':version,'backupLabel':backup['label'],'restorePhase':replayed['phase'],'sourceRows':2,'restoredRows':1,'writeRejected':True,'productionQualified':False,'crossHostRestoreTested':False,'patroniHAOrWatchdogTested':False}
  finally:
   # Do not remove a tree while one of these owned postmasters is still running.
   if restored is not None:restored.stop()
   if source is not None:source.stop()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True);args=parser.parse_args()
 try:result=exercise();code=0
 except (Blocked,OSError,ValueError) as e:
  result={'status':'BLOCKED','reason':str(e) if isinstance(e,Blocked) else type(e).__name__,'productionQualified':False};code=3
 result['at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 atomic(args.evidence,json.dumps(result,indent=2).encode()+b'\n')
 print(json.dumps(result));return code
if __name__=='__main__':sys.exit(main())
