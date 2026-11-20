"""Fail-closed six-host native bootstrap coordinator.

The existing :mod:`bootstrap` module performs one verified SSH installation.
This module adds the missing coordinator around it: resolve an explicit
inventory against a trusted hosts file, preflight every host before mutation,
generate one shared HA topology, and persist enough intent to resume without
blindly repeating an uncertain remote operation.

This is deliberately an experimental lab operation.  It does not imply a
production-qualified release or replace signed-release verification.
"""
from __future__ import annotations

import ipaddress
import json
import os
import pathlib
import re
import shlex
import stat
from typing import Callable

from . import bootstrap
from .common import (
    Blocked,
    bounded_read,
    digest_file,
    fingerprint,
    lock,
    name,
    read_json,
    run,
    write_json,
)


FORMAT = "werftkern-native-inventory/v1"
JOURNAL_FORMAT = "werftkern-native-bootstrap-journal/v1"
MAX_INVENTORY_BYTES = 512 * 1024
MAX_HOSTS_FILE_BYTES = 1 * 1024 * 1024
MAX_KNOWN_HOSTS_BYTES = 1 * 1024 * 1024
MAX_REMOTE_JSON_BYTES = 256 * 1024
REMOTE_SENTINEL = "WERFTKERN_NATIVE_PREFLIGHT_V1"


def _regular(path: pathlib.Path, limit: int, *, private: bool = False) -> bytes:
    try:
        st = path.lstat()
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_mode & 0o022:
            raise Blocked("INPUT_FILE_UNSAFE")
        raw = bounded_read(path, limit)
    except (OSError, Blocked):
        raise Blocked("INPUT_FILE_UNREADABLE") from None
    if private:
        try:
            st = path.lstat()
        except OSError:
            raise Blocked("INPUT_FILE_UNREADABLE") from None
        if st.st_uid != os.geteuid() or stat.S_ISLNK(st.st_mode) or st.st_mode & 0o077:
            raise Blocked("PRIVATE_INPUT_REQUIRED")
    return raw


def _hosts_file(path: pathlib.Path) -> dict[str, str]:
    raw = _regular(path, MAX_HOSTS_FILE_BYTES).decode("utf-8", "strict")
    result: dict[str, str] = {}
    for line_no, line in enumerate(raw.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) < 2:
            raise Blocked(f"HOSTS_FILE_LINE_INVALID:{line_no}")
        try:
            addr = ipaddress.ip_address(fields[0])
        except ValueError:
            raise Blocked(f"HOSTS_FILE_ADDRESS_INVALID:{line_no}") from None
        if addr.version != 4:
            continue
        for alias in fields[1:]:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,252}", alias):
                continue
            old = result.get(alias)
            if old is not None and old != str(addr):
                raise Blocked("HOSTS_FILE_AMBIGUOUS")
            result[alias] = str(addr)
    return result


def _private_ipv4(value: object) -> str:
    if not isinstance(value, str):
        raise Blocked("HOST_ADDRESS_REQUIRED")
    try:
        addr = ipaddress.IPv4Address(value)
    except ValueError:
        raise Blocked("HOST_ADDRESS_INVALID") from None
    if not addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified:
        raise Blocked("PRIVATE_HOST_ADDRESS_REQUIRED")
    if str(addr) != value:
        raise Blocked("HOST_ADDRESS_CANONICAL_REQUIRED")
    return value


def _port(value: object) -> int:
    if value is None:
        return 22
    if type(value) is not int or not 1 <= value <= 65535:
        raise Blocked("SSH_PORT_INVALID")
    return value


def _resolve_inventory(raw: dict, inventory_path: pathlib.Path) -> tuple[dict, dict, dict[str, str]]:
    if not isinstance(raw, dict) or raw.get("format") != FORMAT:
        raise Blocked("NATIVE_INVENTORY_SCHEMA_INVALID")
    allowed = {"format", "name", "hostsFile", "knownHostsFile", "sshUser", "sshPort", "hosts"}
    if set(raw) - allowed or not isinstance(raw.get("name"), str):
        raise Blocked("NATIVE_INVENTORY_SCHEMA_INVALID")
    name(raw["name"])
    hosts_path = pathlib.Path(raw.get("hostsFile", "/etc/hosts"))
    if not hosts_path.is_absolute():
        hosts_path = inventory_path.parent / hosts_path
    mapping = _hosts_file(hosts_path)
    global_user = raw.get("sshUser", "root")
    if not isinstance(global_user, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", global_user):
        raise Blocked("SSH_USER_INVALID")
    global_port = _port(raw.get("sshPort"))
    hosts = raw.get("hosts")
    if not isinstance(hosts, list) or not 1 <= len(hosts) <= 20:
        raise Blocked("NATIVE_INVENTORY_HOSTS_REQUIRED")
    seen_names: set[str] = set()
    seen_addresses: set[str] = set()
    controllers = 0
    workers = 0
    normalized_hosts = []
    for item in hosts:
        if not isinstance(item, dict):
            raise Blocked("NATIVE_INVENTORY_HOST_INVALID")
        allowed_host = {"name", "address", "role", "sshUser", "sshPort", "podCidr", "expectedHostname"}
        if set(item) - allowed_host:
            raise Blocked("NATIVE_INVENTORY_HOST_INVALID")
        host_name = item.get("name")
        name(host_name)
        if host_name in seen_names:
            raise Blocked("NATIVE_INVENTORY_DUPLICATE_HOST")
        seen_names.add(host_name)
        role = item.get("role")
        if role not in {"controller", "worker"}:
            raise Blocked("NATIVE_INVENTORY_ROLE_INVALID")
        addr = item.get("address")
        if addr is None:
            addr = mapping.get(host_name)
        addr = _private_ipv4(addr)
        if mapping.get(host_name) != addr:
            raise Blocked("HOSTS_FILE_ADDRESS_MISMATCH")
        if addr in seen_addresses:
            raise Blocked("NATIVE_INVENTORY_DUPLICATE_ADDRESS")
        seen_addresses.add(addr)
        user = item.get("sshUser", global_user)
        if not isinstance(user, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", user):
            raise Blocked("SSH_USER_INVALID")
        port = _port(item.get("sshPort", global_port))
        expected = item.get("expectedHostname")
        if expected is not None:
            name(expected)
        pod = item.get("podCidr")
        if role == "worker":
            workers += 1
            if not isinstance(pod, str) or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+/\d+", pod):
                raise Blocked("WORKER_POD_CIDR_REQUIRED")
        else:
            controllers += 1
            if pod is not None:
                raise Blocked("CONTROLLER_POD_CIDR_UNSUPPORTED")
        normalized_hosts.append({
            "name": host_name,
            "address": addr,
            "role": role,
            "sshUser": user,
            "sshPort": port,
            **({"podCidr": pod} if pod is not None else {}),
            **({"expectedHostname": expected} if expected is not None else {}),
        })
    if controllers != 3:
        raise Blocked("EXACTLY_THREE_CONTROLLERS_REQUIRED")
    if workers < 1:
        raise Blocked("AT_LEAST_ONE_WORKER_REQUIRED")
    known_hosts = raw.get("knownHostsFile")
    if not isinstance(known_hosts, str):
        raise Blocked("KNOWN_HOSTS_FILE_REQUIRED")
    known_path = pathlib.Path(known_hosts)
    if not known_path.is_absolute():
        known_path = inventory_path.parent / known_path
    _regular(known_path, MAX_KNOWN_HOSTS_BYTES)
    topology = {
        "name": raw["name"],
        "hosts": [
            {"name": h["name"], "address": h["address"],
             "controller": h["role"] == "controller", "worker": h["role"] == "worker",
             **({"podCidr": h["podCidr"]} if "podCidr" in h else {})}
            for h in normalized_hosts
        ],
    }
    return {
        "format": FORMAT,
        "name": raw["name"],
        "hostsFile": str(hosts_path.resolve()),
        "knownHostsFile": str(known_path.resolve()),
        "hosts": normalized_hosts,
    }, topology, mapping


def _ssh_options(spec: dict, known_hosts: pathlib.Path) -> list[str]:
    return [
        "-F", "/dev/null", "-p", str(spec["sshPort"]),
        "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=" + str(known_hosts.resolve()),
        "-o", "ConnectTimeout=10",
    ]


def _target(spec: dict) -> str:
    return spec["sshUser"] + "@" + spec["address"]


def _parse_probe(raw: bytes) -> dict:
    if len(raw) > MAX_REMOTE_JSON_BYTES:
        raise Blocked("REMOTE_PREFLIGHT_OUTPUT_TOO_LARGE")
    lines = raw.decode("utf-8", "strict").splitlines()
    if not lines or lines[0] != REMOTE_SENTINEL:
        raise Blocked("REMOTE_PREFLIGHT_SENTINEL_MISSING")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            if key in result:
                raise Blocked("REMOTE_PREFLIGHT_DUPLICATE_FIELD")
            result[key] = value
    for key in ("hostname", "os", "cgroup", "config", "incomplete", "data", "package", "docker", "etcd"):
        if not result.get(key):
            raise Blocked("REMOTE_PREFLIGHT_FIELD_MISSING")
    if result["os"] != "ubuntu:24.04" or result["cgroup"] != "v2":
        raise Blocked("REMOTE_UBUNTU_OR_CGROUP_REQUIREMENT_FAILED")
    return result


def probe(spec: dict, known_hosts: pathlib.Path, runner: Callable = run) -> dict:
    script = """set -eu
. /etc/os-release
test \"$ID\" = ubuntu
test \"$VERSION_ID\" = 24.04
test -e /run/systemd/system
test -e /sys/fs/cgroup/cgroup.controllers
printf '%s\\n' WERFTKERN_NATIVE_PREFLIGHT_V1
printf 'hostname=%s\\n' \"$(hostname -s)\"
printf 'os=%s:%s\\n' \"$ID\" \"$VERSION_ID\"
printf 'cgroup=v2\\n'
if test -f /etc/werftkern/ha-host.json; then printf 'config=present\\n'; else printf 'config=absent\\n'; fi
if test -f /etc/werftkern/ha-installing.json; then printf 'incomplete=present\\n'; else printf 'incomplete=absent\\n'; fi
if test -e /var/lib/werftkern/etcd/member || test -e /var/lib/werftkern/agent/journal.json; then printf 'data=present\\n'; else printf 'data=absent\\n'; fi
if dpkg-query -W -f='${Status}|${Version}' werftkern 2>/dev/null; then printf '\\n'; else printf 'package=absent\\n'; fi
if command -v docker >/dev/null 2>&1; then printf 'docker=present\\n'; else printf 'docker=missing\\n'; fi
if command -v etcd >/dev/null 2>&1; then printf 'etcd=present\\n'; else printf 'etcd=missing\\n'; fi
"""
    args = ["ssh", *_ssh_options(spec, known_hosts), _target(spec),
            "sudo", "-n", "sh", "-c", shlex.quote(script)]
    return _parse_probe(runner(args, timeout=60))


def _remote_json(spec: dict, known_hosts: pathlib.Path, path: str, runner: Callable = run) -> dict:
    raw = runner(["ssh", *_ssh_options(spec, known_hosts), _target(spec), "sudo", "-n", "cat", path], timeout=30)
    if len(raw) > MAX_REMOTE_JSON_BYTES:
        raise Blocked("REMOTE_STATE_TOO_LARGE")
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        raise Blocked("REMOTE_STATE_INVALID") from None
    if not isinstance(value, dict):
        raise Blocked("REMOTE_STATE_INVALID")
    return value


def _remote_command(spec: dict, known_hosts: pathlib.Path, command: list[str], runner: Callable = run) -> bytes:
    return runner(["ssh", *_ssh_options(spec, known_hosts), _target(spec), "sudo", "-n", *command], timeout=900)


def _probe_state(spec: dict, known_hosts: pathlib.Path, expected_cluster: str, runner: Callable,
                 observed: dict | None = None, require_tools: bool = False) -> tuple[str, dict]:
    p = observed if observed is not None else probe(spec, known_hosts, runner)
    if require_tools and (p["docker"] != "present" or p["etcd"] != "present"):
        raise Blocked("REMOTE_RUNTIME_TOOLS_MISSING")
    if p["incomplete"] == "present":
        raise Blocked("REMOTE_INSTALLATION_INCOMPLETE_REQUIRES_REVIEW")
    if p["config"] == "present":
        state = _remote_json(spec, known_hosts, "/etc/werftkern/ha-host.json", runner)
        if state.get("clusterId") != expected_cluster or state.get("host", {}).get("name") != spec["name"]:
            raise Blocked("REMOTE_CONFIGURATION_CONFLICT")
        return "configured", p
    if p["data"] == "present":
        raise Blocked("REMOTE_DATA_WITHOUT_CONFIGURATION_REQUIRES_REVIEW")
    return "clean", p


def _kits(topology: dict, directory: pathlib.Path, runner: Callable) -> dict[str, pathlib.Path]:
    expected = {h["name"] for h in topology["hosts"]}
    if directory.exists():
        paths = {p.stem.removesuffix(".kit"): p for p in directory.glob("*.kit.json")}
        if set(paths) != expected:
            raise Blocked("HA_KIT_INVENTORY_MISMATCH")
        return paths
    directory.parent.mkdir(parents=True, exist_ok=True)
    topology_path = directory.parent / (directory.name + ".topology.json")
    write_json(topology_path, topology, exclusive=True)
    runner(["werft", "ha", "prepare", "--topology", str(topology_path), "--out", str(directory)], timeout=120)
    paths = {p.stem.removesuffix(".kit"): p for p in directory.glob("*.kit.json")}
    if set(paths) != expected:
        raise Blocked("HA_KIT_INVENTORY_MISMATCH")
    return paths


def _host_spec(host: dict, package_sha: str) -> dict:
    return {
        "name": host["name"], "address": host["address"], "sshUser": host["sshUser"],
        "sshPort": host["sshPort"], "packageSha256": package_sha,
    }


def _binding(inventory: dict, topology: dict, package: pathlib.Path, known_hosts: pathlib.Path) -> dict:
    return {
        "inventory": fingerprint(inventory),
        "topology": fingerprint(topology),
        "packageSha256": digest_file(package),
        "knownHostsSha256": digest_file(known_hosts),
    }


def _validate_journal(journal: dict, binding: dict, hosts: list[dict]) -> None:
    if journal.get("format") != JOURNAL_FORMAT or journal.get("binding") != binding:
        raise Blocked("NATIVE_BOOTSTRAP_REPLAY_CONFLICT")
    if not isinstance(journal.get("hosts"), dict) or set(journal["hosts"]) != {h["name"] for h in hosts}:
        raise Blocked("NATIVE_BOOTSTRAP_JOURNAL_HOST_SET_INVALID")


def _seed_host(hosts: list[dict]) -> dict:
    controllers = sorted((h for h in hosts if h["role"] == "controller"), key=lambda h: h["name"])
    if len(controllers) != 3:
        raise Blocked("EXACTLY_THREE_CONTROLLERS_REQUIRED")
    return controllers[0]


def apply(inventory_path: str | os.PathLike[str], package_path: str | os.PathLike[str],
          journal_path: str | os.PathLike[str], *, check_only: bool = False,
          known_hosts_override: str | os.PathLike[str] | None = None,
          runner: Callable = run) -> dict:
    inventory_file = pathlib.Path(inventory_path).resolve(strict=True)
    package = pathlib.Path(package_path).resolve(strict=True)
    journal_file = pathlib.Path(journal_path).resolve()
    if not package.is_file() or package.is_symlink() or package.stat().st_size > bootstrap.MAX_PACKAGE_BYTES:
        raise Blocked("PACKAGE_PAYLOAD_UNREADABLE")
    raw = read_json(inventory_file)
    if known_hosts_override is not None:
        raw["knownHostsFile"] = str(pathlib.Path(known_hosts_override).resolve())
    inventory, topology, _ = _resolve_inventory(raw, inventory_file)
    known_hosts = pathlib.Path(inventory["knownHostsFile"])
    binding = _binding(inventory, topology, package, known_hosts)
    package_sha = binding["packageSha256"]
    kits_dir = journal_file.parent / ("." + journal_file.stem + ".ha-kits")
    with lock(pathlib.Path(str(journal_file) + ".lock")):
        if journal_file.exists():
            journal = read_json(journal_file, private=True)
            _validate_journal(journal, binding, inventory["hosts"])
        else:
            journal = {
                "format": JOURNAL_FORMAT, "binding": binding, "phase": "preflight",
                "clusterName": inventory["name"], "hosts": {
                    h["name"]: {"phase": "pending", "address": h["address"], "role": h["role"]}
                    for h in inventory["hosts"]
                }, "productionQualified": False,
            }
            write_json(journal_file, journal, exclusive=True)
        kits = _kits(topology, kits_dir, runner)
        expected_cluster = None
        if kits:
            first = read_json(next(iter(kits.values())), private=True)
            expected_cluster = first.get("clusterId")
        if not isinstance(expected_cluster, str) or not expected_cluster:
            raise Blocked("HA_KIT_CLUSTER_ID_MISSING")
        if journal.get("clusterId") not in (None, expected_cluster):
            raise Blocked("NATIVE_BOOTSTRAP_CLUSTER_ID_CHANGED")
        journal["clusterId"] = expected_cluster
        if journal["phase"] == "preflight":
            for host in inventory["hosts"]:
                n = journal["hosts"][host["name"]]
                if n.get("phase") == "preflight":
                    continue
                spec = _host_spec(host, package_sha)
                state, observed = _probe_state(spec, known_hosts, expected_cluster, runner)
                expected_hostname = host.get("expectedHostname")
                if expected_hostname is not None and observed.get("hostname") != expected_hostname:
                    raise Blocked("REMOTE_HOSTNAME_MISMATCH")
                n.update({"phase": "preflight", "hostname": observed["hostname"], "remoteState": state})
                write_json(journal_file, journal)
            journal["phase"] = "staging"
            write_json(journal_file, journal)
        if check_only:
            return {"operation": "preflight", "journal": str(journal_file), "hosts": journal["hosts"], "productionQualified": False}
        if journal["phase"] == "staging":
            for host in inventory["hosts"]:
                n = journal["hosts"][host["name"]]
                spec = _host_spec(host, package_sha)
                if n.get("phase") == "staged":
                    continue
                state, _ = _probe_state(spec, known_hosts, expected_cluster, runner)
                if state == "configured":
                    _probe_state(spec, known_hosts, expected_cluster, runner, require_tools=True)
                    n["phase"] = "staged"
                    n["remoteState"] = state
                    write_json(journal_file, journal)
                    continue
                n["phase"] = "install-intent"
                write_json(journal_file, journal)
                bootstrap.install(spec, str(package), str(kits[host["name"]]), str(known_hosts), host["name"], runner)
                verify, _ = _probe_state(spec, known_hosts, expected_cluster, runner, require_tools=True)
                if verify != "configured":
                    raise Blocked("REMOTE_INSTALLATION_NOT_CONFIRMED")
                n["phase"] = "staged"
                n["remoteState"] = verify
                write_json(journal_file, journal)
            journal["phase"] = "init-intent"
            write_json(journal_file, journal)
        if journal["phase"] == "init-intent":
            seed = _seed_host(inventory["hosts"])
            _remote_command(seed, known_hosts, ["werft", "ha", "init"], runner)
            journal["phase"] = "verify-intent"
            write_json(journal_file, journal)
        if journal["phase"] == "verify-intent":
            seed = _seed_host(inventory["hosts"])
            spec = _host_spec(seed, package_sha)
            health = json.loads(_remote_command(seed, known_hosts, ["werft", "health", "--all", "--json"], runner))
            status = json.loads(_remote_command(seed, known_hosts, ["werft", "status", "--json"], runner))
            if health.get("clusterId") != expected_cluster or len(health.get("controllers", [])) != 3 or status.get("clusterId") != expected_cluster:
                raise Blocked("NATIVE_BOOTSTRAP_VERIFICATION_FAILED")
            expected_workers = {h["name"]: h["address"] for h in inventory["hosts"] if h["role"] == "worker"}
            observed_workers = {}
            for node in (status.get("nodes") or {}).values():
                if not isinstance(node, dict) or node.get("name") in observed_workers:
                    raise Blocked("NATIVE_BOOTSTRAP_NODE_INVENTORY_INVALID")
                if node.get("name") in expected_workers:
                    if node.get("address") != expected_workers[node["name"]] or node.get("healthy") is not True or node.get("revoked") is True:
                        raise Blocked("NATIVE_BOOTSTRAP_WORKER_NOT_READY")
                    observed_workers[node["name"]] = node["address"]
            if observed_workers != expected_workers:
                raise Blocked("NATIVE_BOOTSTRAP_WORKER_INVENTORY_MISMATCH")
            journal["health"] = health
            journal["status"] = {"clusterId": status.get("clusterId"), "nodes": status.get("nodes", {})}
            journal["phase"] = "completed"
            write_json(journal_file, journal)
        return {"operation": "completed", "journal": str(journal_file), "clusterId": expected_cluster, "productionQualified": False}

