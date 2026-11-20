import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ops"))

from werftops import native_bootstrap
from werftops.common import Blocked, read_json, write_json


class NativeBootstrapTests(unittest.TestCase):
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
                        config = "present" if host in installed else "absent"
                        address_value = address
                        return ("WERFTKERN_NATIVE_PREFLIGHT_V1\n"
                                f"hostname={host}\n"
                                "os=ubuntu:24.04\n"
                                "cgroup=v2\n"
                                f"config={config}\n"
                                "incomplete=absent\n"
                                "data=absent\n"
                                "package=absent\n").encode()
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
            )


if __name__ == "__main__":
    unittest.main()
