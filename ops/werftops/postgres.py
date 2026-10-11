"""Logical PostgreSQL backup and isolated restore. No PITR or database HA claim."""
from __future__ import annotations
import contextlib, datetime, ipaddress, json, os, pathlib, re, tempfile
from .common import Blocked, atomic, digest_file, fingerprint, lock, private_read, read_json, run, sha, write_json

@contextlib.contextmanager
def connection(config, passfile, runner=run):
    allowed={"host","port","user","database","transport","rootCA"}
    if not set(config)<=allowed or not {"host","port","user","database","transport"}<=set(config):raise Blocked("DATABASE_CONFIG_INVALID")
    host=ipaddress.IPv4Address(config["host"])
    if not host.is_private or type(config["port"]) is not int or not 1024<=config["port"]<=65535:raise Blocked("PRIVATE_DATABASE_ENDPOINT_REQUIRED")
    for k in ("user","database"):
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,39}",config[k]):raise Blocked("DATABASE_IDENTIFIER_INVALID")
    private_read(passfile,65536)
    transport=config["transport"]
    if transport=="loopback":
        if not host.is_loopback:raise Blocked("LOOPBACK_REQUIRED")
        sslmode="disable"
    elif transport=="wireguard":
        route=json.loads(runner(["ip","-j","route","get",str(host)]))
        if not route or route[0].get("dev")!="wgwerft":raise Blocked("WIREGUARD_ROUTE_REQUIRED")
        sslmode="disable"
    elif transport=="tls":
        ca=pathlib.Path(config.get("rootCA",""))
        if not ca.is_file() or "\n" in str(ca):raise Blocked("TRUSTED_DATABASE_CA_REQUIRED")
        sslmode="verify-full"
    else:raise Blocked("DATABASE_SECURE_TRANSPORT_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="werft-pg-") as d:
        service=pathlib.Path(d)/"service.conf"
        text=f"[werft]\nhost={host}\nport={config['port']}\nuser={config['user']}\ndbname={config['database']}\nsslmode={sslmode}\nconnect_timeout=10\n"
        if transport=="tls":text+="sslrootcert="+str(ca.resolve())+"\n"
        atomic(service,text.encode())
        env={"PATH":"/usr/bin:/bin","LANG":"C","PGSERVICEFILE":str(service),"PGPASSFILE":str(pathlib.Path(passfile).resolve()),"PGCONNECT_TIMEOUT":"10"}
        yield env

def major(runner,tool):
    value=runner([tool,"--version"]).decode()
    m=re.search(r"\(PostgreSQL\) (\d+)",value)
    if not m or int(m.group(1))<17:raise Blocked("POSTGRES_CLIENT_17_OR_NEWER_REQUIRED")
    return int(m.group(1))

def backup(config,passfile,out,runner=run):
    path=pathlib.Path(out)
    if path.exists() or pathlib.Path(str(path)+".json").exists():raise Blocked("BACKUP_DESTINATION_EXISTS")
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    version=major(runner,"pg_dump")
    with lock(str(path)+".lock"), connection(config,passfile,runner) as env:
        # Root-owned temporary file, not a shell pipeline; no password in argv.
        fd,tmp=tempfile.mkstemp(prefix=".pgdump-",dir=path.parent);os.close(fd)
        try:
            runner(["pg_dump","--dbname=service=werft","--format=custom","--no-owner","--no-acl","--file",tmp],timeout=3600,env=env)
            with open(tmp,"rb") as check: magic=check.read(5)
            if magic!=b"PGDMP":raise Blocked("INVALID_POSTGRES_ARCHIVE")
            runner(["pg_restore","--list",tmp],timeout=120)
            with open(tmp,"rb") as f:os.fsync(f.fileno())
            os.link(tmp,path)
            manifest={"format":"werftkern-pgdump/v1","sha256":digest_file(path),"source":{k:config[k] for k in ("host","port","database")},"clientMajor":version,"createdAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"kind":"logical-single-database","restoreTested":False}
            write_json(str(path)+".json",manifest,exclusive=True)
            return manifest
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

def restore(config,passfile,archive,confirm,runner=run):
    if confirm!=config.get("database"):raise Blocked("EXACT_TARGET_DATABASE_CONFIRMATION_REQUIRED")
    manifest=read_json(str(archive)+".json",private=True)
    if manifest.get("format")!="werftkern-pgdump/v1" or digest_file(archive)!=sha(manifest["sha256"]):raise Blocked("DATABASE_BACKUP_INTEGRITY_FAILED")
    source=manifest["source"]
    if all(config[k]==source[k] for k in ("host","port","database")):raise Blocked("RESTORE_OVER_SOURCE_FORBIDDEN")
    if major(runner,"pg_restore")<manifest["clientMajor"]:raise Blocked("RESTORE_CLIENT_TOO_OLD")
    # Database must already be created empty by an operator, isolated from apps.
    with lock(str(archive)+".restore.lock"),connection(config,passfile,runner) as env:
        probe="SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','m','v','S','f');"
        count=runner(["psql","--no-psqlrc","--dbname=service=werft","--tuples-only","--no-align","--set=ON_ERROR_STOP=1","--command",probe],env=env).decode().strip()
        if count!="0":raise Blocked("RESTORE_TARGET_MUST_BE_EMPTY_AND_QUIESCENT")
        runner(["pg_restore","--dbname=service=werft","--single-transaction","--exit-on-error","--no-owner","--no-acl",str(archive)],timeout=3600,env=env)
        runner(["psql","--no-psqlrc","--dbname=service=werft","--set=ON_ERROR_STOP=1","--command","SELECT 1;"],env=env)
        proof={"format":"werftkern-pgrestore/v1","sha256":manifest["sha256"],"target":{k:config[k] for k in ("host","port","database")},"completedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"applicationValidation":"required-not-performed"}
        write_json(str(archive)+".restore-"+fingerprint(proof)[:16]+".json",proof,exclusive=True)
        return proof
