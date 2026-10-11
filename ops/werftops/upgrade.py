"""Signed same-schema host package updates, with persisted phases and recovery.

The lock in the control plane deliberately does not expire: the next operator
must inspect an interrupted update instead of allowing concurrent host updates.
"""
from __future__ import annotations
import json, os, pathlib, secrets, shutil, time
from . import readiness
from .common import Blocked, digest_file, host_preflight, lock, read_json, run, write_json

ROOT=pathlib.Path("/var/lib/werftkern")
CONFIG=pathlib.Path("/etc/werftkern")

def verify(package, manifest, signature, key, runner=run):
    return json.loads(runner(["werft","release","verify","--manifest",str(manifest),"--signature",str(signature),"--public-key",str(key),"--package",str(package)]))

def apply(package,manifest,signature,key,confirm,runner=run):
    host_preflight()
    m=verify(package,manifest,signature,key,runner)
    if confirm!=m["version"]:raise Blocked("EXACT_TARGET_VERSION_CONFIRMATION_REQUIRED")
    current=runner(["dpkg-query","-W","-f=${Version}","werftkern"]).decode().strip()
    if current not in m["sources"]:raise Blocked("UPGRADE_SOURCE_VERSION_NOT_ALLOWED")
    package_version=runner(["dpkg-deb","-f",str(package),"Version"]).decode().strip()
    package_name=runner(["dpkg-deb","-f",str(package),"Package"]).decode().strip()
    if package_name!="werftkern" or package_version!=m["packageVersion"]:raise Blocked("PACKAGE_MANIFEST_IDENTITY_MISMATCH")
    if not (CONFIG/"admin.json").exists():raise Blocked("CONTROLLER_HOST_REQUIRED_WORKER_UPGRADES_NOT_AUTOMATED")
    with lock(ROOT/"update.lock"):
        home=(ROOT/"updates")/m["packageSha256"]
        if home.exists():raise Blocked("UPDATE_JOURNAL_EXISTS_USE_RECOVERY_NOT_REAPPLY")
        home.mkdir(mode=0o700,parents=True)
        copied=home/"target.deb";shutil.copyfile(package,copied);os.chmod(copied,0o600)
        if digest_file(copied)!=m["packageSha256"]:raise Blocked("STAGED_PACKAGE_CHANGED")
        observed=json.loads(runner(["werft","status","--json"]))
        cluster=observed.get("clusterId", "")
        if not isinstance(cluster,str) or len(cluster)!=32 or any(c not in "0123456789abcdef" for c in cluster):raise Blocked("SOURCE_CLUSTER_ID_REQUIRED")
        operation=secrets.token_hex(16)
        state={"format":"werftkern-host-update/v1","id":operation,"clusterId":cluster,"from":current,"target":m,"phase":"prepared","package":str(copied)}
        journal=home/"journal.json";write_json(journal,state,exclusive=True)
        runner(["werft","maintenance","on","--id",operation,"--reason","signed-host-upgrade"])
        state["phase"]="frozen";write_json(journal,state)
        runner(["werft","backup","create","--out",str(home/"config.backup"),"--key-file",str(home/"backup.key")],timeout=120)
        # Backup is logical only. Existing process/data writes are not rolled back.
        state["phase"]="backed-up";write_json(journal,state)
        active=[]
        for service in ("werftkern-control","werftkern-agent"):
            try:runner(["systemctl","is-active","--quiet",service]);active.append(service)
            except Blocked:pass
        state["services"]=active;state["phase"]="stopping";write_json(journal,state)
        for service in active:runner(["systemctl","stop",service])
        state["phase"]="installing";write_json(journal,state)
        # dpkg does not fetch additional dependencies; change fails visibly if unmet.
        runner(["dpkg","--install",str(copied)],timeout=600)
        state["phase"]="installed";write_json(journal,state)
        for service in active:runner(["systemctl","start",service])
        # Recovery remains frozen if verification fails. No automatic state downgrade.
        runner(["werft","status","--json"],timeout=90)
        installed=runner(["dpkg-query","-W","-f=${Version}","werftkern"]).decode().strip()
        if installed!=m["packageVersion"]:raise Blocked("INSTALLED_VERSION_MISMATCH")
        state["phase"]="awaiting-runtime-qualification";write_json(journal,state)
        return state

def recover(journal_path,package,manifest,signature,key,confirm,runner=run):
    """Explicit same-schema forward repair or rollback with another signed package."""
    host_preflight();old=read_json(journal_path,private=True);m=verify(package,manifest,signature,key,runner)
    if old.get("format")!="werftkern-host-update/v1" or confirm!=old.get("id"):raise Blocked("RECOVERY_OPERATION_CONFIRMATION_REQUIRED")
    if m["stateSchema"]!=old["target"]["stateSchema"]:raise Blocked("STATE_SCHEMA_DOWNGRADE_FORBIDDEN")
    actual=runner(["dpkg-query","-W","-f=${Version}","werftkern"]).decode().strip()
    if actual not in m["sources"]:raise Blocked("RECOVERY_SOURCE_VERSION_NOT_ALLOWED")
    if not pathlib.Path(journal_path).parent.joinpath("config.backup").is_file():raise Blocked("PREUPDATE_BACKUP_MISSING")
    with lock(ROOT/"update.lock"):
        runner(["werft","maintenance","on","--id",old["id"],"--reason","signed-host-recovery"])
        old["phase"]="explicit-recovery";write_json(journal_path,old)
        for service in old.get("services",[]):
            if service not in ("werftkern-control","werftkern-agent"):raise Blocked("RECOVERY_SERVICE_NOT_ALLOWED")
        staged=pathlib.Path(journal_path).parent/("repair-"+m["packageSha256"]+".deb")
        if not staged.exists():shutil.copyfile(package,staged);os.chmod(staged,0o600)
        if digest_file(staged)!=m["packageSha256"]:raise Blocked("RECOVERY_PACKAGE_CHANGED")
        pv=runner(["dpkg-deb","-f",str(staged),"Version"]).decode().strip()
        pn=runner(["dpkg-deb","-f",str(staged),"Package"]).decode().strip()
        if pv!=m["packageVersion"] or pn!="werftkern":raise Blocked("RECOVERY_PACKAGE_IDENTITY_MISMATCH")
        for service in old.get("services",[]):runner(["systemctl","stop",service])
        runner(["dpkg","--install",str(staged)],timeout=600)
        for service in old.get("services",[]):runner(["systemctl","start",service])
        runner(["werft","status","--json"],timeout=90)
        old["phase"]="awaiting-runtime-qualification";old["recoveryTarget"]=m;write_json(journal_path,old)
        return old


def finish(journal_path, confirm, runner=run, sleeper=time.sleep):
    """Explicit completion; three independent fresh heartbeat observations.

    Installation/recovery NEVER releases the cluster freeze itself. A failed
    sample leaves the durable journal and lock untouched. Application-specific
    business validation remains an independent acceptance gate.
    """
    host_preflight()
    with lock(ROOT/"update.lock"):
        j=read_json(journal_path,private=True)
        if j.get("format")!="werftkern-host-update/v1" or j.get("id")!=confirm or j.get("phase") not in ("awaiting-runtime-qualification", "runtime-verified-unlock-pending", "completed-runtime-verified"):
            raise Blocked("UPDATE_NOT_AWAITING_QUALIFICATION")
        if j["phase"] == "completed-runtime-verified":
            return j  # historical receipt; no fresh health claim or mutation
        pending = j["phase"] == "runtime-verified-unlock-pending"
        target=j.get("recoveryTarget",j["target"])
        installed=runner(["dpkg-query","-W","-f=${Version}","werftkern"]).decode().strip()
        if installed!=target["packageVersion"]:raise Blocked("INSTALLED_VERSION_MISMATCH")
        version=runner(["werft","version"]).decode().splitlines()
        if not version or version[0]!="Werftkern "+target["version"]:raise Blocked("BINARY_VERSION_MISMATCH")
        for service in j.get("services",[]):
            if service not in ("werftkern-control","werftkern-agent"):raise Blocked("SERVICE_NOT_ALLOWED")
            runner(["systemctl","is-active","--quiet",service])
        # Require every configured control endpoint to serve the exact target;
        # an API client's normal failover cannot substitute for peer verification.
        health=json.loads(runner(["werft","health","--all","--json","--expected-version",target["version"]],timeout=90))
        controllers=health.get("controllers")
        if health.get("clusterId")!=j.get("clusterId") or not isinstance(controllers,list) or not controllers:
            raise Blocked("ALL_CONTROLLER_HEALTH_EVIDENCE_REQUIRED")
        for c in controllers:
            if not isinstance(c,dict) or c.get("status")!="ready" or c.get("version")!=target["version"] or c.get("stateSchema")!=target["stateSchema"] or c.get("clusterId")!=j["clusterId"]:
                raise Blocked("CONTROLLER_TARGET_NOT_VERIFIED")
        previous=None
        lock_seen = None
        for sample in range(3):
            state=json.loads(runner(["werft","status","--json"],timeout=30))
            observed_lock = state.get("maintenanceId", "")
            # Only a persisted unlock intent authorizes empty-lock ACK recovery.
            if observed_lock != j["id"] and not (pending and observed_lock == ""):
                raise Blocked("UPDATE_MAINTENANCE_OWNER_CHANGED")
            if lock_seen is not None and observed_lock != lock_seen:
                raise Blocked("UPDATE_MAINTENANCE_CHANGED_DURING_OBSERVATION")
            lock_seen = observed_lock
            current=readiness.check(state,j.get("clusterId"),observed_lock,target["version"],target["stateSchema"])
            readiness.advanced(previous,current)
            previous=current
            if sample<2:sleeper(6)
        # Persist intent before unlocking; retry reconciles an empty/owned lock.
        # A different owner is never overridden or released.
        j["runtimeObservations"]=3
        j["controllersVerified"]=len(controllers)
        j["phase"]="runtime-verified-unlock-pending";write_json(journal_path,j)
        if lock_seen == j["id"]:
            runner(["werft","maintenance","off","--id",j["id"],"--reason","verified-host-upgrade"])
        else:
            j["unlockAcknowledgementRecovered"] = True
        j["phase"]="completed-runtime-verified"
        j["businessValidation"]="not-performed"
        write_json(journal_path,j)
        return j
