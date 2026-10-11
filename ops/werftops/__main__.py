from __future__ import annotations
import argparse, json, sys
from . import bootstrap, cloud, network, postgres, upgrade, database_ha, pitr, rollout, worker_upgrade
from .common import Blocked, read_json

def main(argv=None):
    p=argparse.ArgumentParser(prog="werft-ops",description="Explicit Werftkern administrative operations. No production qualification implied.")
    sub=p.add_subparsers(dest="command",required=True)
    n=sub.add_parser("network");ns=n.add_subparsers(dest="action",required=True)
    a=ns.add_parser("prepare");a.add_argument("--topology",required=True);a.add_argument("--out",required=True)
    a=ns.add_parser("apply");a.add_argument("--kit",required=True);a.add_argument("--confirm-host",required=True)
    a=ns.add_parser("enable-dns");a.add_argument("--kit",required=True)
    c=sub.add_parser("cloud");cs=c.add_subparsers(dest="action",required=True)
    a=cs.add_parser("plan");a.add_argument("--file",required=True)
    a=cs.add_parser("apply");a.add_argument("--file",required=True);a.add_argument("--journal",required=True);a.add_argument("--token-file",required=True);a.add_argument("--confirm-plan",required=True);a.add_argument("--accept-costs",action="store_true",required=True)
    b=sub.add_parser("bootstrap");b.add_argument("--host",required=True);b.add_argument("--package",required=True);b.add_argument("--kit",required=True);b.add_argument("--known-hosts",required=True);b.add_argument("--confirm-host",required=True)
    g=sub.add_parser("postgres");gs=g.add_subparsers(dest="action",required=True)
    for action in ("backup","restore"):
        a=gs.add_parser(action);a.add_argument("--config",required=True);a.add_argument("--passfile",required=True);a.add_argument("--archive",required=True)
        if action=="restore":a.add_argument("--confirm-database",required=True)
    u=sub.add_parser("upgrade");us=u.add_subparsers(dest="action",required=True)
    for action in ("apply","recover"):
        a=us.add_parser(action)
        for arg in ("package","manifest","signature","public-key"):a.add_argument("--"+arg,required=True)
        if action=="apply":a.add_argument("--confirm-version",required=True)
        else:a.add_argument("--journal",required=True);a.add_argument("--confirm-operation",required=True)
    a=us.add_parser("finish");a.add_argument("--journal",required=True);a.add_argument("--confirm-operation",required=True)
    db=sub.add_parser("database-ha");ds=db.add_subparsers(dest="action",required=True)
    a=ds.add_parser("prepare");a.add_argument("--plan",required=True);a.add_argument("--out",required=True)
    a=ds.add_parser("install");a.add_argument("--kit",required=True);a.add_argument("--confirm-host",required=True);a.add_argument("--accept-watchdog-reset",action="store_true",required=True)
    for action in ("inspect","switchover"):
        a=ds.add_parser(action)
        for arg in ("plan","ca","cert","key"):a.add_argument("--"+arg,required=True)
        if action=="switchover":
            a.add_argument("--target",required=True);a.add_argument("--journal",required=True);a.add_argument("--confirm",required=True)
    pr=sub.add_parser("pitr");ps=pr.add_subparsers(dest="action",required=True)
    a=ps.add_parser("prepare");a.add_argument("--plan",required=True);a.add_argument("--cipher-file",required=True);a.add_argument("--out",required=True)
    for action in ("initialize","backup","restore"):
        a=ps.add_parser(action);a.add_argument("--config",required=True);a.add_argument("--stanza",required=True)
        if action in ("backup","restore"):a.add_argument("--journal",required=True)
        if action=="restore":
            for arg in ("label","time","target","system-id","confirm"):a.add_argument("--"+arg,required=True)
    a=ps.add_parser("verify-replay");a.add_argument("--journal",required=True);a.add_argument("--socket",required=True);a.add_argument("--port",required=True,type=int)
    ro=sub.add_parser("rollout");rs=ro.add_subparsers(dest="action",required=True)
    a=rs.add_parser("plan");a.add_argument("--file",required=True)
    a=rs.add_parser("apply")
    for arg in ("file","journal","package","manifest","signature","public-key","known-hosts","confirm-plan"):
        a.add_argument("--"+arg,required=True)
    wu=sub.add_parser("worker-upgrade");ws=wu.add_subparsers(dest="action",required=True)
    a=ws.add_parser("install")
    for arg in ("package","manifest","signature","operation","cluster","node","staged-binary"):
        a.add_argument("--"+arg,required=True)
    a=ws.add_parser("receipt");a.add_argument("--operation",required=True)
    args=p.parse_args(argv)
    result=None
    if args.command=="rollout":
        plan=read_json(args.file)
        if args.action=="plan":result={"planSha256":rollout.validate(plan),"workers":len(plan["workers"]),"mutations":False}
        else:result=rollout.apply(plan,args.journal,args.package,args.manifest,args.signature,args.public_key,args.known_hosts,args.confirm_plan)
    elif args.command=="worker-upgrade":
        if args.action=="install":result=worker_upgrade.install(args.package,args.manifest,args.signature,args.operation,args.cluster,args.node,args.staged_binary)
        else:result=worker_upgrade.receipt(args.operation)
    elif args.command=="network":
        if args.action=="prepare":network.prepare(read_json(args.topology),args.out)
        elif args.action=="apply":network.apply(args.kit,args.confirm_host)
        else:network.enable_dns(args.kit)
    elif args.command=="cloud":
        plan=read_json(args.file)
        if args.action=="plan":result={"planSHA256":cloud.validate(plan),"vmCount":len(plan["servers"]),"costs":"not quoted; owner approval required", "mutations":False}
        else:result=cloud.apply(plan,args.journal,args.confirm_plan,args.accept_costs,cloud.Hetzner(args.token_file))
    elif args.command=="bootstrap":bootstrap.install(read_json(args.host),args.package,args.kit,args.known_hosts,args.confirm_host)
    elif args.command=="postgres":
        config=read_json(args.config,private=True)
        if args.action=="backup":result=postgres.backup(config,args.passfile,args.archive)
        else:result=postgres.restore(config,args.passfile,args.archive,args.confirm_database)
    elif args.command=="pitr":
        if args.action=="prepare":result=pitr.prepare(read_json(args.plan),args.cipher_file,args.out)
        elif args.action=="initialize":result=pitr.initialize(args.config,args.stanza)
        elif args.action=="backup":result=pitr.backup(args.config,args.stanza,args.journal)
        elif args.action=="restore":result=pitr.restore(args.config,args.stanza,args.label,args.time,args.target,args.system_id,args.journal,args.confirm)
        else:result=pitr.verify_replay(args.journal,args.socket,args.port)
    elif args.command=="database-ha":
        if args.action=="install":result=database_ha.install(args.kit,args.confirm_host,args.accept_watchdog_reset)
        else:
            plan=read_json(args.plan)
            if args.action=="prepare":result=database_ha.prepare(plan,args.out)
            else:
                api=database_ha.REST(plan,args.ca,args.cert,args.key)
                if args.action=="inspect":result=database_ha.inspect(plan,api)
                else:result=database_ha.switchover(plan,api,args.target,args.journal,args.confirm)
    elif args.command=="upgrade":
        if args.action=="apply":result=upgrade.apply(args.package,args.manifest,args.signature,args.public_key,args.confirm_version)
        elif args.action=="recover":result=upgrade.recover(args.journal,args.package,args.manifest,args.signature,args.public_key,args.confirm_operation)
        else:result=upgrade.finish(args.journal,args.confirm_operation)
    print(json.dumps(result or {"operation":"completed","productionQualified":False},indent=2))
if __name__=="__main__":
    try:main()
    except (Blocked,OSError,ValueError,KeyError) as e:
        # Do not dump raw provider, PG, SSH or secret-bearing exception payloads.
        print("BLOCKED: "+(str(e) if isinstance(e,Blocked) else type(e).__name__),file=sys.stderr)
        sys.exit(1)
