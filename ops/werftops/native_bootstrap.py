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
import socket
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
MAX_DISCOVERY_CANDIDATES = 64
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


def _resolve_private_ipv4(host: str) -> set[str]:
    """Resolve a hostname without accepting public or ambiguous addresses."""
    try:
        answers = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        return set()
    addresses: set[str] = set()
    for answer in answers:
        try:
            address = ipaddress.IPv4Address(answer[4][0])
        except (IndexError, ValueError):
            continue
        if address.is_private and not address.is_loopback and not address.is_link_local and not address.is_unspecified:
            addresses.add(str(address))
    return addresses


def _known_host_token(value: str) -> tuple[str, int] | None:
    """Return the connect host and port for one non-pattern known_hosts token."""
    if not value or value.startswith("|") or value.startswith("!") or "*" in value or "?" in value:
        return None
    if value.startswith("["):
        close = value.find("]:")
        if close < 0:
            return None
        host, raw_port = value[1:close], value[close + 2:]
        try:
            port = int(raw_port)
        except ValueError:
            return None
        if not 1 <= port <= 65535:
            return None
        return host, port
    if ":" in value:
        # Unbracketed IPv6 and host:port forms are not accepted by this IPv4-only
        # discovery path. They remain valid inputs for other SSH tooling.
        return None
    return value, 22


def _known_hosts_candidates(path: pathlib.Path) -> list[dict]:
    """Extract private, host-key-trusted SSH endpoints from known_hosts.

    Hashed names, wildcards and certificate-authority-only lines cannot be used
    to derive a safe endpoint and are deliberately ignored. A hostname is only
    accepted when local name resolution produces a private IPv4 address.
    """
    raw = _regular(path, MAX_KNOWN_HOSTS_BYTES).decode("utf-8", "strict")
    candidates: dict[tuple[str, int], dict] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if not fields:
            continue
        host_field_index = 1 if fields[0].startswith("@") else 0
        if len(fields) <= host_field_index:
            continue
        if fields[0].startswith("@"):
            continue
        for raw_token in fields[host_field_index].split(","):
            parsed = _known_host_token(raw_token)
            if parsed is None:
                continue
            host, port = parsed
            try:
                literal = ipaddress.IPv4Address(host)
                addresses = {str(literal)} if literal.is_private and not literal.is_loopback and not literal.is_link_local else set()
            except ValueError:
                addresses = _resolve_private_ipv4(host)
            for address in addresses:
                key = (address, port)
                candidate = candidates.setdefault(key, {
                    "address": address,
                    "sshPort": port,
                    "sshHosts": [],
                    "aliases": [],
                })
                if host not in candidate["sshHosts"]:
                    candidate["sshHosts"].append(host)
                if host not in candidate["aliases"]:
                    candidate["aliases"].append(host)
    result = list(candidates.values())
    if len(result) > MAX_DISCOVERY_CANDIDATES:
        raise Blocked("AUTO_DISCOVERY_CANDIDATE_LIMIT_EXCEEDED")
    return result


def _short_host(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.rstrip(".").lower().split(".", 1)[0]


def _host_key(value: object) -> str:
    """Normalize common lab naming separators for safe profile matching."""
    return re.sub(r"[-_]", "", _short_host(value))


def _role_hint(values: list[str]) -> str | None:
    text = "-".join(values).lower().replace("_", "-").replace(".", "-")
    # Accept both worker-1 and worker1, plus the corresponding controller
    # forms. Only a numeric suffix is accepted; arbitrary substrings such as
    # workermanager are not role evidence.
    controller = re.search(
        r"(^|-)master(?:-?\d+)?(?=-|$)|"
        r"(^|-)control(?:ler)?(?:-?\d+)?(?=-|$)|"
        r"(^|-)cp(?:-?\d+)?(?=-|$)",
        text,
    )
    worker = re.search(
        r"(^|-)worker(?:-?\d+)?(?=-|$)|"
        r"(^|-)compute(?:-?\d+)?(?=-|$)|"
        r"(^|-)node(?:-?\d+)?(?=-|$)",
        text,
    )
    if controller and not worker:
        return "controller"
    if worker and not controller:
        return "worker"
    return None


def _candidate_matches(candidate: dict, desired: str) -> bool:
    wanted = _host_key(desired)
    values = list(candidate.get("aliases", []))
    if candidate.get("observedHostname"):
        values.append(candidate["observedHostname"])
    return any(value == desired or _host_key(value) == wanted for value in values)


def _default_inventory(known_hosts: str, ssh_user: str, ssh_port: int) -> dict:
    return {
        "format": FORMAT,
        "name": "werft-lab-3m-3w",
        "hostsFile": "/etc/hosts",
        "knownHostsFile": known_hosts,
        "sshUser": ssh_user,
        "sshPort": ssh_port,
        "autoDiscover": True,
        "hosts": [
            {"name": "master-1", "role": "controller"},
            {"name": "master-2", "role": "controller"},
            {"name": "master-3", "role": "controller"},
            {"name": "worker-1", "role": "worker", "podCidr": "10.88.11.0/24"},
            {"name": "worker-2", "role": "worker", "podCidr": "10.88.12.0/24"},
            {"name": "worker-3", "role": "worker", "podCidr": "10.88.13.0/24"},
        ],
    }


def _port(value: object) -> int:
    if value is None:
        return 22
    if type(value) is not int or not 1 <= value <= 65535:
        raise Blocked("SSH_PORT_INVALID")
    return value


def _resolve_inventory(raw: dict, inventory_path: pathlib.Path, *, auto_discover: bool = False) -> tuple[dict, dict, dict[str, str]]:
    if not isinstance(raw, dict) or raw.get("format") != FORMAT:
        raise Blocked("NATIVE_INVENTORY_SCHEMA_INVALID")
    auto_discover = auto_discover or raw.get("autoDiscover") is True
    if "autoDiscover" in raw and type(raw["autoDiscover"]) is not bool:
        raise Blocked("NATIVE_INVENTORY_SCHEMA_INVALID")
    allowed = {"format", "name", "hostsFile", "knownHostsFile", "sshUser", "sshPort", "autoDiscover", "hosts"}
    if set(raw) - allowed or not isinstance(raw.get("name"), str):
        raise Blocked("NATIVE_INVENTORY_SCHEMA_INVALID")
    name(raw["name"])
    hosts_path = pathlib.Path(raw.get("hostsFile", "/etc/hosts"))
    if not hosts_path.is_absolute():
        hosts_path = inventory_path.parent / hosts_path
    if auto_discover:
        mapping = _hosts_file(hosts_path) if hosts_path.exists() else {}
    else:
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
        allowed_host = {"name", "address", "role", "sshUser", "sshPort", "sshHost", "podCidr", "expectedHostname"}
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
        if addr is None and auto_discover:
            resolved = _resolve_private_ipv4(host_name)
            if len(resolved) == 1:
                addr = next(iter(resolved))
        if addr is None:
            raise Blocked("HOST_ADDRESS_REQUIRED")
        addr = _private_ipv4(addr)
        mapped_address = mapping.get(host_name)
        if auto_discover:
            if mapped_address is not None and mapped_address != addr:
                raise Blocked("HOSTS_FILE_ADDRESS_MISMATCH")
        elif mapped_address != addr:
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
        ssh_host = item.get("sshHost")
        if ssh_host is not None:
            if not isinstance(ssh_host, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,252}", ssh_host):
                raise Blocked("SSH_HOST_INVALID")
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
            "sshHost": ssh_host or addr,
            **({"podCidr": pod} if pod is not None else {}),
            **({"expectedHostname": expected} if expected is not None else {}),
        })
    if controllers != 3:
        raise Blocked("EXACTLY_THREE_CONTROLLERS_REQUIRED")
    if workers < 1:
        raise Blocked("AT_LEAST_ONE_WORKER_REQUIRED")
    known_hosts = raw.get("knownHostsFile")
    if known_hosts is None and auto_discover:
        known_hosts = "/root/.ssh/known_hosts"
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
    return spec["sshUser"] + "@" + spec.get("sshHost", spec["address"])


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
if dpkg-query -W -f='${Status}' werftkern 2>/dev/null | grep -q '^install ok installed$'; then
  printf 'package=present\\n'
else
  printf 'package=absent\\n'
fi
if command -v docker >/dev/null 2>&1; then printf 'docker=present\\n'; else printf 'docker=missing\\n'; fi
if command -v etcd >/dev/null 2>&1; then printf 'etcd=present\\n'; else printf 'etcd=missing\\n'; fi
"""
    args = ["ssh", *_ssh_options(spec, known_hosts), _target(spec),
            "sudo", "-n", "sh", "-c", shlex.quote(script)]
    return _parse_probe(runner(args, timeout=60))


def _probe_endpoints(spec: dict, known_hosts: pathlib.Path, runner: Callable = run) -> tuple[list[dict[str, str]], dict]:
    """Probe both the trusted hostname and its resolved IP endpoint."""
    endpoints = []
    for endpoint in (spec.get("sshHost", spec["address"]), spec["address"]):
        if endpoint not in endpoints:
            endpoints.append(endpoint)
    observations = []
    parsed = []
    for endpoint in endpoints:
        endpoint_spec = dict(spec)
        endpoint_spec["sshHost"] = endpoint
        observed = probe(endpoint_spec, known_hosts, runner)
        parsed.append(observed)
        observations.append({"endpoint": endpoint, "hostname": observed["hostname"]})
    if len({_short_host(item["hostname"]) for item in observations}) != 1:
        raise Blocked("REMOTE_HOSTNAME_ENDPOINT_MISMATCH")
    return observations, parsed[0]

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
        "sshPort": host["sshPort"], "sshHost": host.get("sshHost", host["address"]),
        "packageSha256": package_sha,
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


def _auto_discover_inventory(raw: dict, known_hosts: pathlib.Path, runner: Callable, hosts_file: pathlib.Path | None = None) -> dict:
    """Resolve a role profile from trusted SSH endpoints without manual edits."""
    if not isinstance(raw, dict) or not isinstance(raw.get("hosts"), list):
        raise Blocked("NATIVE_INVENTORY_HOSTS_REQUIRED")
    candidates = _known_hosts_candidates(known_hosts)
    if not candidates:
        raise Blocked("AUTO_DISCOVERY_NO_TRUSTED_HOSTS")
    global_user = raw.get("sshUser", "ubuntu")
    if not isinstance(global_user, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", global_user):
        raise Blocked("SSH_USER_INVALID")
    global_port = _port(raw.get("sshPort"))
    hosts_path = pathlib.Path(hosts_file or raw.get("hostsFile", "/etc/hosts")).resolve()
    mapping = _hosts_file(hosts_path) if hosts_path.exists() else {}

    assigned: dict[int, dict] = {}
    used: set[int] = set()

    # A matching hosts-file entry is useful evidence, but its absence is not
    # an operator task in auto mode. If present, it must point to a trusted
    # known_hosts endpoint.
    for index, item in enumerate(raw["hosts"]):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise Blocked("NATIVE_INVENTORY_HOST_INVALID")
        host_name = item["name"]
        name(host_name)
        address = mapping.get(host_name)
        if address is not None:
            address = _private_ipv4(address)
            wanted_port = _port(item.get("sshPort", global_port))
            matches = [
                candidate_index for candidate_index, candidate in enumerate(candidates)
                if candidate_index not in used
                and candidate["address"] == address
                and candidate["sshPort"] == wanted_port
            ]
            if not matches:
                raise Blocked("AUTO_DISCOVERY_HOSTS_ADDRESS_NOT_TRUSTED:" + host_name)
            if len(matches) > 1:
                raise Blocked("AUTO_DISCOVERY_HOSTS_ADDRESS_AMBIGUOUS:" + host_name)
            candidate_index = matches[0]
            assigned[index] = candidates[candidate_index]
            used.add(candidate_index)
            continue
        matches = [
            candidate_index for candidate_index, candidate in enumerate(candidates)
            if candidate_index not in used and _candidate_matches(candidate, host_name)
        ]
        if len(matches) > 1:
            raise Blocked("AUTO_DISCOVERY_NAME_AMBIGUOUS:" + host_name)
        if len(matches) == 1:
            candidate_index = matches[0]
            assigned[index] = candidates[candidate_index]
            used.add(candidate_index)

    # IP-only known_hosts entries are mapped through a read-only remote
    # hostname probe. No key scanning, TOFU, or network scan is performed.
    for candidate_index, candidate in enumerate(candidates):
        if candidate_index in used:
            continue
        probe_spec = {
            "name": "discovery",
            "address": candidate["address"],
            "sshHost": candidate["sshHosts"][0],
            "sshUser": global_user,
            "sshPort": candidate["sshPort"] or global_port,
        }
        try:
            observed = probe(probe_spec, known_hosts, runner)
        except Blocked:
            continue
        candidate["observedHostname"] = observed["hostname"]

    for index, item in enumerate(raw["hosts"]):
        if index in assigned:
            continue
        matches = [
            candidate_index for candidate_index, candidate in enumerate(candidates)
            if candidate_index not in used and _candidate_matches(candidate, item["name"])
        ]
        if len(matches) > 1:
            raise Blocked("AUTO_DISCOVERY_NAME_AMBIGUOUS:" + item["name"])
        if len(matches) == 1:
            candidate_index = matches[0]
            assigned[index] = candidates[candidate_index]
            used.add(candidate_index)

    remaining_by_role: dict[str, list[int]] = {"controller": [], "worker": []}
    for index, item in enumerate(raw["hosts"]):
        if index not in assigned:
            role = item.get("role") if isinstance(item, dict) else None
            if role not in remaining_by_role:
                raise Blocked("NATIVE_INVENTORY_ROLE_INVALID")
            remaining_by_role[role].append(index)

    candidates_by_role: dict[str, list[int]] = {"controller": [], "worker": []}
    for candidate_index, candidate in enumerate(candidates):
        if candidate_index in used:
            continue
        hint = _role_hint(
            list(candidate.get("aliases", []))
            + ([candidate["observedHostname"]] if candidate.get("observedHostname") else [])
        )
        if hint is not None:
            candidates_by_role[hint].append(candidate_index)

    for role in ("controller", "worker"):
        slots = remaining_by_role[role]
        available = candidates_by_role[role]
        if not slots:
            continue
        if len(available) != len(slots):
            raise Blocked("AUTO_DISCOVERY_ROLE_MAPPING_AMBIGUOUS:" + role)
        available.sort(key=lambda i: (candidates[i]["address"], candidates[i]["sshHosts"][0]))
        for index, candidate_index in zip(
            sorted(slots, key=lambda i: raw["hosts"][i]["name"]),
            available,
        ):
            assigned[index] = candidates[candidate_index]
            used.add(candidate_index)

    if len(assigned) != len(raw["hosts"]):
        raise Blocked("AUTO_DISCOVERY_HOST_MAPPING_AMBIGUOUS")

    discovered_hosts = []
    for index, item in enumerate(raw["hosts"]):
        candidate = assigned[index]
        updated = dict(item)
        updated["address"] = candidate["address"]
        if "sshPort" not in updated:
            updated["sshPort"] = candidate["sshPort"] or global_port
        updated["sshHost"] = next(
            (
                alias for alias in candidate["sshHosts"]
                if _host_key(alias) == _host_key(item["name"])
            ),
            candidate["sshHosts"][0],
        )
        discovered_hosts.append(updated)
    result = dict(raw)
    result["autoDiscover"] = True
    result["hosts"] = discovered_hosts
    result["hostsFile"] = str(hosts_path)
    return result

def apply(inventory_path: str | os.PathLike[str] | None, package_path: str | os.PathLike[str],
          journal_path: str | os.PathLike[str], *, check_only: bool = False,
          known_hosts_override: str | os.PathLike[str] | None = None,
          auto_discover: bool = False, auto_ssh_user: str = "ubuntu", auto_ssh_port: int = 22,
          runner: Callable = run) -> dict:
    package = pathlib.Path(package_path).resolve(strict=True)
    journal_file = pathlib.Path(journal_path).resolve()
    if not package.is_file() or package.is_symlink() or package.stat().st_size > bootstrap.MAX_PACKAGE_BYTES:
        raise Blocked("PACKAGE_PAYLOAD_UNREADABLE")
    generated_inventory = journal_file.with_name(journal_file.stem + ".inventory.json")
    if auto_discover and inventory_path is None:
        inventory_file = generated_inventory
        raw = _default_inventory(
            str(pathlib.Path(known_hosts_override or "/root/.ssh/known_hosts").resolve()),
            auto_ssh_user,
            _port(auto_ssh_port),
        )
    else:
        if inventory_path is None:
            raise Blocked("NATIVE_INVENTORY_REQUIRED")
        inventory_file = pathlib.Path(inventory_path).resolve(strict=True)
        raw = read_json(inventory_file)
    if known_hosts_override is not None:
        raw["knownHostsFile"] = str(pathlib.Path(known_hosts_override).resolve())
    auto_mode = auto_discover or (isinstance(raw, dict) and raw.get("autoDiscover") is True)
    known_path_value = raw.get("knownHostsFile", "/root/.ssh/known_hosts") if isinstance(raw, dict) else "/root/.ssh/known_hosts"
    hosts_path_value = raw.get("hostsFile", "/etc/hosts") if isinstance(raw, dict) else "/etc/hosts"
    known_path = pathlib.Path(known_path_value)
    hosts_path = pathlib.Path(hosts_path_value)
    if not known_path.is_absolute():
        known_path = inventory_file.parent / known_path
    if not hosts_path.is_absolute():
        hosts_path = inventory_file.parent / hosts_path
    known_path = known_path.resolve()
    hosts_path = hosts_path.resolve()
    if auto_mode:
        if generated_inventory.exists():
            raw = read_json(generated_inventory, private=True)
        else:
            raw = _auto_discover_inventory(raw, known_path, runner, hosts_path)
            write_json(generated_inventory, raw, exclusive=True)
        inventory_file = generated_inventory
    inventory, topology, _ = _resolve_inventory(raw, inventory_file, auto_discover=auto_mode)
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
                if auto_mode:
                    endpoint_observations, observed = _probe_endpoints(spec, known_hosts, runner)
                else:
                    endpoint = spec.get("sshHost", spec["address"])
                    observed = probe(spec, known_hosts, runner)
                    endpoint_observations = [{"endpoint": endpoint, "hostname": observed["hostname"]}]
                state, observed = _probe_state(spec, known_hosts, expected_cluster, runner, observed=observed)
                expected_hostname = host.get("expectedHostname")
                if expected_hostname is not None and observed.get("hostname") != expected_hostname:
                    raise Blocked("REMOTE_HOSTNAME_MISMATCH")
                n.update({"phase": "preflight", "hostname": observed["hostname"], "remoteState": state, "sshEndpoints": endpoint_observations})
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

