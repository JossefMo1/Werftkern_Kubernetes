import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ops"))

from werftops import native_bootstrap
from werftops.common import Blocked, read_json, write_json


class NativeBootstrapTests(unittest.TestCase):
    def test_probe_parser_accepts_installed_package_marker(self):
        parsed = native_bootstrap._parse_probe(
            b"\n".join([
                native_bootstrap.REMOTE_SENTINEL.encode(),
                b"hostname=master-1",
                b"os=ubuntu:24.04",
                b"cgroup=v2",
                b"config=absent",
                b"incomplete=absent",
                b"data=absent",
                b"package=present",
                b"docker=present",
                b"etcd=present",
            ])
        )
        self.assertEqual(parsed["package"], "present")

    def inventory(self, root):
        hosts = root / "hosts"
        hosts.write_text(
            "10.87.0.1 master-1\n"
            "10.87.0.2 master-2\n"
            "10.87.0.3 master-3\n"
            "10.87.0.11 worker-1\n"
            "10.87.0.12 worker-2\n"
            "10.87.0.13 worker-3\n",
            encoding="utf-8",
        )
        known = root / "known_hosts"
        known.write_text("master-1 ssh-ed25519 AAAA\n", encoding="utf-8")
        inv = root / "inventory.json"
        write_json(inv, {
            "format": "werftkern-native-inventory/v1",
            "name": "lab",
            "hostsFile": str(hosts),
            "knownHostsFile": str(known),
            "sshUser": "ubuntu",
            "hosts": [
                {"name": "master-1", "role": "controller"},
                {"name": "master-2", "role": "controller"},
                {"name": "master-3", "role": "controller"},
                {"name": "worker-1", "role": "worker", "podCidr": "10.88.11.0/24"},
                {"name": "worker-2", "role": "worker", "podCidr": "10.88.12.0/24"},
                {"name": "worker-3", "role": "worker", "podCidr": "10.88.13.0/24"},
            ],
        })
        return inv, known

    def fake_runner(self, root):
        def run(args, **kwargs):
            if args[:3] == ["werft", "ha", "prepare"]:
                topology = json.loads(pathlib.Path(args[args.index("--topology") + 1]).read_text())
                out = pathlib.Path(args[args.index("--out") + 1])
                out.mkdir(mode=0o700)
                for host in topology["hosts"]:
                    kit = {
                        "format": "werftkern-ha-kit/v1",
                        "clusterId": "a" * 32,
                        "host": host,
                        "controllers": [h for h in topology["hosts"] if h["controller"]],
                        "files": {"control.json": "fixture"} if host["controller"] else {"agent.json": "fixture"},
                    }
                    path = out / (host["name"] + ".kit.json")
                    write_json(path, kit)
                return b""
            if args and args[0] == "ssh":
                return (
                    b"WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                    b"hostname=fixture\n"
                    b"os=ubuntu:24.04\n"
                    b"cgroup=v2\n"
                    b"config=absent\n"
                    b"incomplete=absent\n"
                    b"data=absent\n"
                    b"package=absent\n"
                    b"docker=missing\n"
                    b"etcd=missing\n"
                )
            raise AssertionError(args)
        return run

    def test_inventory_check_resolves_hosts_file_and_persists_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            inv, known = self.inventory(root)
            package = root / "runtime.deb"
            package.write_bytes(b"fixture-package")
            journal = root / "journal.json"
            result = native_bootstrap.apply(inv, package, journal, check_only=True, runner=self.fake_runner(root))
            self.assertEqual(result["operation"], "preflight")
            self.assertEqual(len(result["hosts"]), 6)
            self.assertEqual(read_json(journal, private=True)["phase"], "staging")

    def test_apply_stages_all_hosts_initializes_and_replays_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            inv, known = self.inventory(root)
            package = root / "runtime.deb"
            package.write_bytes(b"fixture-package")
            journal = root / "journal.json"
            installed = set()
            names = {
                "10.87.0.1": "master-1", "10.87.0.2": "master-2", "10.87.0.3": "master-3",
                "10.87.0.11": "worker-1", "10.87.0.12": "worker-2", "10.87.0.13": "worker-3",
            }
            cluster = "a" * 32

            def runner(args, **kwargs):
                if args[:3] == ["werft", "ha", "prepare"]:
                    topology = json.loads(pathlib.Path(args[args.index("--topology") + 1]).read_text())
                    out = pathlib.Path(args[args.index("--out") + 1])
                    out.mkdir(mode=0o700)
                    for host in topology["hosts"]:
                        write_json(out / (host["name"] + ".kit.json"), {
                            "format": "werftkern-ha-kit/v1", "clusterId": cluster,
                            "host": host, "controllers": [h for h in topology["hosts"] if h["controller"]],
                            "files": {"control.json": "fixture"} if host["controller"] else {"agent.json": "fixture"},
                        })
                    return b""
                if args and args[0] == "ssh":
                    target = next(x for x in args if "@10.87." in x)
                    address = target.rsplit("@", 1)[1]
                    host = names[address]
                    command = " ".join(str(x) for x in args)
                    if "apt-get install" in command and "werft ha install" in command:
                        installed.add(host)
                        return b""
                    if " cat /etc/werftkern/ha-host.json" in command:
                        return json.dumps({"clusterId": cluster, "host": {"name": host}}).encode()
                    if " health --all --json" in command:
                        return json.dumps({"clusterId": cluster, "controllers": [{"status": "ready"}] * 3}).encode()
                    if " status --json" in command:
                        return json.dumps({"clusterId": cluster, "nodes": {
                            ("b" * 32) + str(i): {"name": "worker-" + str(i), "address": "10.87.0.1" + str(i), "healthy": True, "revoked": False}
                            for i in range(1, 4)
                        }}).encode()
                    if "sh -c" in command:
                        configured = host in installed
                        config = "present" if configured else "absent"
                        address_value = address
                        return ("WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                                f"hostname={host}\n"
                                "os=ubuntu:24.04\n"
                                "cgroup=v2\n"
                                f"config={config}\n"
                                "incomplete=absent\n"
                                "data=absent\n"
                                f"package={'install ok installed|0.2.0~dev4' if configured else 'absent'}\n"
                                f"docker={'present' if configured else 'missing'}\n"
                                f"etcd={'present' if configured else 'missing'}\n").encode()
                    return b""
                raise AssertionError(args)

            result = native_bootstrap.apply(inv, package, journal, runner=runner)
            self.assertEqual(result["operation"], "completed")
            self.assertEqual(read_json(journal, private=True)["phase"], "completed")
            before = len(installed)
            replay = native_bootstrap.apply(inv, package, journal, runner=runner)
            self.assertEqual(replay["operation"], "completed")
            self.assertEqual(len(installed), before)

    def test_inventory_rejects_hosts_file_address_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            inv, _ = self.inventory(root)
            value = read_json(inv)
            value["hosts"][0]["address"] = "10.87.0.99"
            write_json(inv, value)
            with self.assertRaisesRegex(Blocked, "^HOSTS_FILE_ADDRESS_MISMATCH$"):
                native_bootstrap._resolve_inventory(value, inv)

    def test_probe_rejects_wrong_os(self):
        with self.assertRaisesRegex(Blocked, "^REMOTE_UBUNTU_OR_CGROUP_REQUIREMENT_FAILED$"):
            native_bootstrap._parse_probe(
                b"WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                b"hostname=fixture\nos=debian:12\ncgroup=v2\n"
                b"config=absent\nincomplete=absent\ndata=absent\n"
                b"package=absent\ndocker=missing\netcd=missing\n"
            )

    def auto_profile(self, root):
        known = root / "known_hosts"
        pairs = [
            ("master-1", "10.87.0.1"), ("master-2", "10.87.0.2"), ("master-3", "10.87.0.3"),
            ("worker-1", "10.87.0.11"), ("worker-2", "10.87.0.12"), ("worker-3", "10.87.0.13"),
        ]
        known.write_text(
            "".join(f"{name} ssh-ed25519 AAAA\n{address} ssh-ed25519 AAAA\n" for name, address in pairs),
            encoding="utf-8",
        )
        hosts = root / "hosts"
        hosts.write_text(
            "".join(f"{address} {name}\n" for name, address in pairs),
            encoding="utf-8",
        )
        raw = {
            "format": "werftkern-native-inventory/v1",
            "name": "lab",
            "hostsFile": str(hosts),
            "knownHostsFile": str(known),
            "sshUser": "ubuntu",
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
        return raw, known

    def discovery_runner(self, names):
        def run(args, **kwargs):
            if args and args[0] == "ssh":
                target = next(value for value in args if value.startswith("ubuntu@"))
                address = target.rsplit("@", 1)[1]
                return ("WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                        f"hostname={names[address]}\n"
                        "os=ubuntu:24.04\n"
                        "cgroup=v2\n"
                        "config=absent\n"
                        "incomplete=absent\n"
                        "data=absent\n"
                        "package=absent\n"
                        "docker=missing\n"
                        "etcd=missing\n").encode()
            raise AssertionError(args)
        return run

    def test_auto_discovery_maps_trusted_ip_endpoints_to_remote_hostnames(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            names = {
                "10.87.0.1": "master-1", "10.87.0.2": "master-2", "10.87.0.3": "master-3",
                "10.87.0.11": "worker-1", "10.87.0.12": "worker-2", "10.87.0.13": "worker-3",
            }
            discovered = native_bootstrap._auto_discover_inventory(
                raw, known, self.discovery_runner(names)
            )
            self.assertEqual(
                [host["address"] for host in discovered["hosts"]],
                list(names),
            )
            self.assertEqual(
                [host["sshHost"] for host in discovered["hosts"]],
                list(names),
            )
            resolved, _, _ = native_bootstrap._resolve_inventory(
                discovered, root / "profile.json", auto_discover=True
            )
            self.assertEqual(resolved["hosts"][0]["address"], "10.87.0.1")

    def test_auto_discovery_accepts_numeric_role_suffixes(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            hosts = root / "hosts"
            hosts.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            raw["hostsFile"] = str(hosts)
            addresses = [
                "10.87.0.1", "10.87.0.2", "10.87.0.3",
                "10.87.0.11", "10.87.0.12", "10.87.0.13",
            ]
            known.write_text(
                "".join(f"{address} ssh-ed25519 AAAA\n" for address in addresses),
                encoding="utf-8",
            )
            names = {
                "10.87.0.1": "master1", "10.87.0.2": "master2", "10.87.0.3": "master3",
                "10.87.0.11": "worker1", "10.87.0.12": "worker2", "10.87.0.13": "worker3",
            }
            discovered = native_bootstrap._auto_discover_inventory(
                raw, known, self.discovery_runner(names)
            )
            self.assertEqual(
                [host["sshHost"] for host in discovered["hosts"]],
                addresses,
            )

    def test_dual_endpoint_preflight_checks_alias_and_ip(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            names = {
                "10.87.0.1": "master-1", "10.87.0.2": "master-2", "10.87.0.3": "master-3",
                "10.87.0.11": "worker-1", "10.87.0.12": "worker-2", "10.87.0.13": "worker-3",
            }
            spec = {
                "name": "master-1", "address": "10.87.0.1", "sshHost": "master-1",
                "sshUser": "ubuntu", "sshPort": 22,
            }
            seen = []

            def runner(args, **kwargs):
                if args and args[0] == "ssh":
                    target = next(value for value in args if value.startswith("ubuntu@"))
                    endpoint = target.rsplit("@", 1)[1]
                    seen.append(endpoint)
                    hostname = names.get(endpoint, endpoint)
                    return (
                        "WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                        f"hostname={hostname}\n"
                        "os=ubuntu:24.04\n"
                        "cgroup=v2\n"
                        "config=absent\n"
                        "incomplete=absent\n"
                        "data=absent\n"
                        "package=absent\n"
                        "docker=missing\n"
                        "etcd=missing\n"
                    ).encode()
                raise AssertionError(args)

            observations, parsed = native_bootstrap._probe_endpoints(spec, known, runner)
            self.assertEqual(seen, ["master-1", "10.87.0.1"])
            self.assertEqual([item["endpoint"] for item in observations], seen)
            self.assertEqual(parsed["hostname"], "master-1")

    def test_dual_endpoint_preflight_rejects_profile_hostname_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            spec = {
                "name": "master-1",
                "address": "10.87.0.1",
                "sshHost": "master-1",
                "sshUser": "ubuntu",
                "sshPort": 22,
            }

            def runner(args, **kwargs):
                if args and args[0] == "ssh":
                    return (
                        "WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                        "hostname=master-2\n"
                        "os=ubuntu:24.04\n"
                        "cgroup=v2\n"
                        "config=absent\n"
                        "incomplete=absent\n"
                        "data=absent\n"
                        "package=absent\n"
                        "docker=missing\n"
                        "etcd=missing\n"
                    ).encode()
                raise AssertionError(args)

            with self.assertRaisesRegex(Blocked, "^REMOTE_HOSTNAME_PROFILE_MISMATCH$"):
                native_bootstrap._probe_endpoints(spec, known, runner)

    def test_auto_discovery_allows_missing_hosts_file_names(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            hosts = root / "hosts"
            hosts.write_text("127.0.0.1 localhost\n", encoding="utf-8")
            raw["hostsFile"] = str(hosts)
            addresses = [
                "10.87.0.1", "10.87.0.2", "10.87.0.3",
                "10.87.0.11", "10.87.0.12", "10.87.0.13",
            ]
            known.write_text(
                "".join(f"{address} ssh-ed25519 AAAA\n" for address in addresses),
                encoding="utf-8",
            )
            names = {
                "10.87.0.1": "master-1", "10.87.0.2": "master-2", "10.87.0.3": "master-3",
                "10.87.0.11": "worker-1", "10.87.0.12": "worker-2", "10.87.0.13": "worker-3",
            }
            discovered = native_bootstrap._auto_discover_inventory(
                raw, known, self.discovery_runner(names)
            )
            self.assertEqual(
                [host["address"] for host in discovered["hosts"]],
                addresses,
            )

    def test_auto_discovery_blocks_ambiguous_role_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            raw["hosts"] = [dict(host, name="node-" + str(index + 1)) for index, host in enumerate(raw["hosts"])]
            names = {address: "host" for address in (
                "10.87.0.1", "10.87.0.2", "10.87.0.3", "10.87.0.11", "10.87.0.12", "10.87.0.13"
            )}
            with self.assertRaisesRegex(Blocked, "^AUTO_DISCOVERY_ROLE_MAPPING_AMBIGUOUS:controller$"):
                native_bootstrap._auto_discover_inventory(raw, known, self.discovery_runner(names))


    def test_auto_discovery_cli_ssh_user_override_is_bound_and_used(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            profile = root / "profile.json"
            write_json(profile, raw)
            package = root / "runtime.deb"
            package.write_bytes(b"fixture-package")
            journal = root / "journal.json"
            names = {
                "10.87.0.1": "master-1", "10.87.0.2": "master-2", "10.87.0.3": "master-3",
                "10.87.0.11": "worker-1", "10.87.0.12": "worker-2", "10.87.0.13": "worker-3",
            }
            prepare_runner = self.fake_runner(root)
            seen = []

            def discovery_runner(args, **kwargs):
                if args and args[0] == "ssh":
                    target = next(value for value in args if value.startswith("root@"))
                    seen.append(target)
                    endpoint = target.rsplit("@", 1)[1]
                    hostname = names.get(endpoint, endpoint)
                    return (
                        "WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                        f"hostname={hostname}\n"
                        "os=ubuntu:24.04\n"
                        "cgroup=v2\n"
                        "config=absent\n"
                        "incomplete=absent\n"
                        "data=absent\n"
                        "package=absent\n"
                        "docker=missing\n"
                        "etcd=missing\n"
                    ).encode()
                raise AssertionError(args)

            def runner(args, **kwargs):
                if args[:3] == ["werft", "ha", "prepare"]:
                    return prepare_runner(args, **kwargs)
                return discovery_runner(args, **kwargs)

            with patch("werftops.native_bootstrap.shutil.which", return_value="/usr/bin/ssh"):
                native_bootstrap.apply(
                    profile,
                    package,
                    journal,
                    check_only=True,
                    known_hosts_override=known,
                    auto_discover=True,
                    auto_ssh_user="root",
                    runner=runner,
                )
                generated = read_json(
                    journal.with_name("journal.inventory.json"), private=True
                )
                self.assertEqual(generated["sshUser"], "root")
                self.assertTrue(seen)
                self.assertTrue(all(target.startswith("root@") for target in seen))
                with self.assertRaisesRegex(
                    Blocked, "^AUTO_DISCOVERY_SSH_USER_CHANGED$"
                ):
                    native_bootstrap.apply(
                        profile,
                        package,
                        journal,
                        check_only=True,
                        known_hosts_override=known,
                        auto_discover=True,
                        auto_ssh_user="ubuntu",
                        runner=runner,
                    )

    def test_auto_discovery_rejects_changed_known_hosts_on_resume(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw, known = self.auto_profile(root)
            profile = root / "profile.json"
            write_json(profile, raw)
            package = root / "runtime.deb"
            package.write_bytes(b"fixture-package")
            journal = root / "journal.json"
            names = {
                "10.87.0.1": "master-1", "10.87.0.2": "master-2", "10.87.0.3": "master-3",
                "10.87.0.11": "worker-1", "10.87.0.12": "worker-2", "10.87.0.13": "worker-3",
            }
            prepare_runner = self.fake_runner(root)
            discovery_runner = self.discovery_runner(names)

            def runner(args, **kwargs):
                if args[:3] == ["werft", "ha", "prepare"]:
                    return prepare_runner(args, **kwargs)
                return discovery_runner(args, **kwargs)

            with patch("werftops.native_bootstrap.shutil.which", return_value="/usr/bin/ssh"):
                native_bootstrap.apply(
                    profile,
                    package,
                    journal,
                    check_only=True,
                    known_hosts_override=known,
                    auto_discover=True,
                    runner=runner,
                )
                alternate = root / "alternate_known_hosts"
                alternate.write_text(known.read_text(encoding="utf-8"), encoding="utf-8")
                with self.assertRaisesRegex(
                    Blocked, "^AUTO_DISCOVERY_KNOWN_HOSTS_CHANGED$"
                ):
                    native_bootstrap.apply(
                        profile,
                        package,
                        journal,
                        check_only=True,
                        known_hosts_override=alternate,
                        auto_discover=True,
                        runner=runner,
                    )

    def test_apply_blocks_before_journal_when_local_ssh_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            inv, _ = self.inventory(root)
            package = root / "runtime.deb"
            package.write_bytes(b"fixture-package")
            journal = root / "journal.json"
            with patch("werftops.native_bootstrap.shutil.which", return_value=None):
                with self.assertRaisesRegex(Blocked, "^LOCAL_SSH_REQUIRED$"):
                    native_bootstrap.apply(
                        inv,
                        package,
                        journal,
                        check_only=True,
                        runner=self.fake_runner(root),
                    )
            self.assertFalse(journal.exists())
            self.assertFalse(journal.with_name("journal.inventory.json").exists())


if __name__ == "__main__":
    unittest.main()
