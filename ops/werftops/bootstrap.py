"""Install a hash-pinned package and host kit over previously verified SSH."""
from __future__ import annotations
import ipaddress, os, pathlib, re, shlex, stat
from .common import Blocked, digest_file, name, private_read, read_json, run, sha

MAX_PACKAGE_BYTES = 128 * 1024 * 1024

def _read_payload(path, limit=MAX_PACKAGE_BYTES):
    """Read one regular, non-symlink payload without unbounded allocation."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise Blocked("PACKAGE_PAYLOAD_UNREADABLE") from None
    with os.fdopen(fd, "rb") as f:
        try:
            st = os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
                raise Blocked("PACKAGE_PAYLOAD_TOO_LARGE")
            raw = f.read(limit + 1)
        except OSError:
            raise Blocked("PACKAGE_PAYLOAD_UNREADABLE") from None
    if len(raw) > limit:
        raise Blocked("PACKAGE_PAYLOAD_TOO_LARGE")
    return raw

def commands(spec, package, kit, known_hosts):
    required={"name","address","sshUser","packageSha256"}
    if not isinstance(spec,dict) or not required.issubset(spec) or set(spec)-required-{"sshPort"}:
        raise Blocked("BOOTSTRAP_SCHEMA_INVALID")
    name(spec["name"]);ipaddress.IPv4Address(spec["address"])
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}",spec["sshUser"]): raise Blocked("SSH_USER_INVALID")
    port=spec.get("sshPort",22)
    if type(port) is not int or not 1 <= port <= 65535: raise Blocked("SSH_PORT_INVALID")
    try:
        if not pathlib.Path(package).is_file() or pathlib.Path(package).stat().st_size > MAX_PACKAGE_BYTES:
            raise Blocked("PACKAGE_PAYLOAD_TOO_LARGE")
    except OSError:
        raise Blocked("PACKAGE_PAYLOAD_UNREADABLE") from None
    if digest_file(package)!=sha(spec["packageSha256"]): raise Blocked("PACKAGE_CHECKSUM_MISMATCH")
    hk=read_json(kit,private=True)
    if hk.get("host",{}).get("name")!=spec["name"]: raise Blocked("HOST_KIT_MISMATCH")
    target=spec["sshUser"]+"@"+spec["address"]
    options=["-F","/dev/null","-p",str(port),"-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","UserKnownHostsFile="+str(pathlib.Path(known_hosts).resolve()),"-o","ConnectTimeout=10"]
    if not pathlib.Path(known_hosts).is_file(): raise Blocked("OUT_OF_BAND_VERIFIED_KNOWN_HOSTS_REQUIRED")
    # Root-owned staging directory created by sudo, not a predictable writable /tmp path.
    remote="/var/lib/werftkern/bootstrap-"+spec["packageSha256"][:16]
    remote_name="host.kit.json";kit_hash=digest_file(kit)
    return target,options,remote,kit_hash

def install(spec, package, kit, known_hosts, confirm, runner=run):
    if confirm!=spec.get("name"): raise Blocked("EXACT_HOST_CONFIRMATION_REQUIRED")
    target,opts,remote,khash=commands(spec,package,kit,known_hosts)
    # Sudo requires preconfigured noninteractive privilege. No passwords are copied.
    runner(["ssh",*opts,target,"sudo -n install -d -m 0700 "+shlex.quote(remote)])
    for source,dest in ((package,"runtime.deb"),(kit,"host.kit.json")):
        raw = _read_payload(source) if source == package else private_read(source)
        cmd="sudo -n sh -c "+shlex.quote("umask 077; cat > "+remote+"/"+dest)
        runner(["ssh",*opts,target,cmd],data=raw,timeout=600)
    script=f"set -eu; cd {shlex.quote(remote)}; printf '%s  %s\\n' {shlex.quote(spec['packageSha256'])} runtime.deb {shlex.quote(khash)} host.kit.json | sha256sum -c -; DEBIAN_FRONTEND=noninteractive apt-get install -y ./runtime.deb; werft ha install --kit host.kit.json --confirm-host {shlex.quote(spec['name'])}"
    runner(["ssh",*opts,target,"sudo -n sh -c "+shlex.quote(script)],timeout=900)
