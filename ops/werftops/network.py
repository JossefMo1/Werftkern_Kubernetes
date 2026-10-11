"""Routed private WireGuard mesh + dedicated Docker bridges, not a CNI plugin."""
from __future__ import annotations
import base64, ipaddress, json, os, pathlib
from .common import Blocked, atomic, fingerprint, host_preflight, lock, name, private_read, read_json, run, write_json

def validate(topology):
    hosts = topology.get("hosts", [])
    name(topology.get("name"))
    if not 1 <= len(hosts) <= 20: raise Blocked("MESH_HOST_LIMIT")
    names, addrs, networks = set(), set(), []
    for h in hosts:
        n = name(h.get("name")); ip=ipaddress.IPv4Address(h["address"]); endpoint=ipaddress.IPv4Address(h["endpoint"])
        subnet=ipaddress.IPv4Network(h["podCidr"],strict=True)
        if n in names or str(ip) in addrs or not ip.is_private or ip.is_loopback or not endpoint.is_private or endpoint.is_loopback or not subnet.is_private or not 24<=subnet.prefixlen<=28:
            raise Blocked("MESH_HOST_INVALID")
        names.add(n);addrs.add(str(ip));networks.append(subnet)
    for i,sub in enumerate(networks):
        if any(sub.overlaps(other) for other in networks[i+1:]) or any(ipaddress.ip_address(h["address"]) in sub or ipaddress.ip_address(h["endpoint"]) in sub for h in hosts):
            raise Blocked("MESH_SUBNET_OVERLAP")
    return hosts

def prepare(topology, output, runner=run):
    hosts=validate(topology);path=pathlib.Path(output)
    if path.exists(): raise Blocked("NEW_OUTPUT_DIRECTORY_REQUIRED")
    keys={}
    for h in hosts:
        private=runner(["wg","genkey"]).strip();public=runner(["wg","pubkey"],data=private+b"\n").strip()
        if len(base64.b64decode(public,validate=True))!=32 or len(base64.b64decode(private,validate=True))!=32: raise Blocked("WG_KEY_INVALID")
        keys[h["name"]]=(private.decode(),public.decode())
    path.mkdir(mode=0o700)
    for h in hosts:
        kit={"format":"werftkern-mesh/v1","cluster":topology["name"],"host":h,"privateKey":keys[h["name"]][0],"peers":[dict(peer,publicKey=keys[peer["name"]][1]) for peer in hosts if peer!=h]}
        write_json(path/(h["name"]+".mesh.json"),kit,exclusive=True)

def render(kit):
    if kit.get("format")!="werftkern-mesh/v1": raise Blocked("MESH_FORMAT_INVALID")
    h=kit["host"];validate({"name":kit["cluster"],"hosts":[h]+kit["peers"]})
    key=kit["privateKey"]
    if len(base64.b64decode(key,validate=True))!=32: raise Blocked("WG_KEY_INVALID")
    lines=["[Interface]",f"Address = {h['address']}/32",f"PrivateKey = {key}","ListenPort = 51820","MTU = 1380"]
    for p in sorted(kit["peers"],key=lambda p:p["name"]):
        if len(base64.b64decode(p["publicKey"],validate=True))!=32: raise Blocked("WG_KEY_INVALID")
        lines += ["", "[Peer]",f"PublicKey = {p['publicKey']}",f"AllowedIPs = {p['address']}/32, {p['podCidr']}",f"Endpoint = {p['endpoint']}:51820","PersistentKeepalive = 25"]
    return ("\n".join(lines)+"\n").encode()

def apply(path, confirm, runner=run):
    host_preflight();kit=read_json(path,private=True);raw=render(kit);h=kit["host"]
    if confirm!=h["name"]: raise Blocked("EXACT_HOST_CONFIRMATION_REQUIRED")
    ident=fingerprint(kit)
    # Mesh establishment precedes HA-kit install. Refuse to mutate active workloads.
    journal=pathlib.Path("/var/lib/werftkern/agent/journal.json")
    if journal.exists() and read_json(journal).get("allocations"): raise Blocked("STOP_AND_VERIFY_ALL_WORKLOADS_BEFORE_NETWORK_CHANGE")
    local=json.loads(runner(["ip","-j","address","show"]))
    if h["endpoint"] not in {a.get("local") for link in local for a in link.get("addr_info",[])}: raise Blocked("UNDERLAY_ADDRESS_NOT_LOCAL")
    with lock("/var/lib/werftkern/network.lock"):
        target=pathlib.Path("/etc/wireguard/wgwerft.conf")
        if target.exists() and private_read(target)!=raw: raise Blocked("EXISTING_WIREGUARD_CONFIG_DIFFERS")
        subnet=ipaddress.IPv4Network(h["podCidr"]);gateway=str(subnet.network_address+1)
        ids=runner(["docker","network","ls","--filter","name=^werft$","--format","{{.ID}}"] ).decode().strip()
        if ids:
            info=json.loads(runner(["docker","network","inspect","werft"]))[0]
            if info.get("Labels",{}).get("org.werftkern.mesh")!=ident or info.get("IPAM",{}).get("Config",[{}])[0].get("Subnet")!=str(subnet): raise Blocked("EXISTING_DOCKER_NETWORK_IS_NOT_THIS_MESH")
        # Durable intent precedes kernel/network mutations. Repeat only identical plan.
        ledger="/var/lib/werftkern/network.json"
        if pathlib.Path(ledger).exists() and read_json(ledger)["fingerprint"]!=ident: raise Blocked("NETWORK_PLAN_CONFLICT")
        write_json(ledger,{"fingerprint":ident,"stage":"applying","host":h})
        atomic(target,raw)
        atomic("/etc/sysctl.d/70-werftkern-routing.conf",b"net.ipv4.ip_forward=1\n",mode=0o644)
        runner(["sysctl","-p","/etc/sysctl.d/70-werftkern-routing.conf"])
        runner(["systemctl","enable","--now","wg-quick@wgwerft"])
        if not ids:
            runner(["docker","network","create","--driver","bridge","--subnet",str(subnet),"--gateway",gateway,"--opt","com.docker.network.bridge.name=wkbr0","--opt","com.docker.network.driver.mtu=1380","--label","org.werftkern.mesh="+ident,"werft"])
        # Add only explicit pod/mesh rules. Never flush a customer's firewall.
        rules=[]
        for p in kit["peers"]:
            rules.extend([["-i","wgwerft","-o","wkbr0","-s",p["podCidr"],"-d",str(subnet),"-j","ACCEPT"], ["-i","wgwerft","-o","wkbr0","-s",p["address"]+"/32","-d",str(subnet),"-j","ACCEPT"], ["-i","wkbr0","-o","wgwerft","-s",str(subnet),"-d",p["podCidr"],"-j","ACCEPT"]])
        # A dedicated service reapplies these rules after Docker/host restart.
        script="#!/bin/sh\nset -eu\n"
        import shlex
        for rule in rules:
            quoted=shlex.join(rule)
            script+=f"iptables -w -C DOCKER-USER {quoted} 2>/dev/null || iptables -w -I DOCKER-USER 1 {quoted}\n"
        atomic("/usr/local/libexec/werftkern-routing",script.encode(),mode=0o700)
        atomic("/etc/systemd/system/werftkern-routing.service",b"[Unit]\nAfter=docker.service wg-quick@wgwerft.service\nRequires=docker.service wg-quick@wgwerft.service\nPartOf=docker.service\n[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/local/libexec/werftkern-routing\n[Install]\nWantedBy=docker.service\n",mode=0o644)
        runner(["systemctl","daemon-reload"]);runner(["systemctl","enable","--now","werftkern-routing"])
        write_json(ledger,{"fingerprint":ident,"stage":"applied-not-qualified","host":h})

def enable_dns(kit_path, runner=run):
    host_preflight();kit=read_json(kit_path,private=True);render(kit);h=kit["host"]
    if not pathlib.Path("/usr/local/bin/coredns").is_file(): raise Blocked("SEPARATELY_VERIFIED_COREDNS_BINARY_REQUIRED")
    ledger=read_json("/var/lib/werftkern/network.json")
    if ledger["fingerprint"]!=fingerprint(kit) or ledger["stage"]!="applied-not-qualified": raise Blocked("MESH_NOT_APPLIED")
    path="/etc/werftkern/agent.json";config=read_json(path,private=True)
    if config["address"]!=h["address"]: raise Blocked("AGENT_ADDRESS_DIFFERS_FROM_MESH")
    journal=pathlib.Path(config["journal"])
    if journal.exists() and read_json(journal).get("allocations"):raise Blocked("STOP_WORKLOADS_BEFORE_CHANGING_CONTAINER_NETWORK")
    config["network"]="werft";config["dns"]=[h["address"]]
    # This is authoritative ONLY for svc.werft; there is no public recursive resolver.
    core=f"svc.werft:53 {{\n bind {h['address']}\n file /var/lib/werftkern/dns/zone svc.werft {{\n  reload 2s\n }}\n errors\n}}\n"
    pathlib.Path("/var/lib/werftkern/dns").mkdir(mode=0o700,exist_ok=True)
    atomic("/etc/werftkern/Corefile",core.encode(),mode=0o644)
    write_json(path,config)
    runner(["systemctl","enable","--now","werftkern-discovery"])
    runner(["systemctl","enable","--now","werftkern-dns"])
    runner(["systemctl","restart","werftkern-agent"])
