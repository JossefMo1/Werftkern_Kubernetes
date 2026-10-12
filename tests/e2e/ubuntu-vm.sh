#!/usr/bin/env bash
# DESTRUCTIVE ONLY WITH RESPECT TO THIS NEW TEST CLUSTER. Dedicated disposable VM.
# Not run in the authoring sandbox. A passing result requires real Docker + etcd.
set -euo pipefail
[[ "${WERFT_DISPOSABLE_VM:-}" == 1 && "$EUID" == 0 ]] || {
  echo 'Run as root on a disposable Ubuntu 24.04 VM with WERFT_DISPOSABLE_VM=1.' >&2; exit 64;
}
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]] || { echo 'Unsupported test host' >&2; exit 65; }
[[ -d /run/systemd/system && -e /sys/fs/cgroup/cgroup.controllers ]] || { echo 'systemd / cgroup v2 required' >&2; exit 65; }
[[ ! -e /etc/werftkern/setup.json ]] || { echo 'Existing cluster: refusing destructive reuse' >&2; exit 65; }
package="$(realpath "${1:?Path to .deb required}")"
out="${WERFT_EVIDENCE_DIR:-/var/tmp/werftkern-e2e}"
mkdir -p "$out"; chmod 0700 "$out"
start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export TEST_EVIDENCE_DIR="$out" TEST_START="$start"
stage=installation
result() {
  code=$?
  EXIT_CODE="$code" TEST_STAGE="$stage" python3 - <<'PY'
import datetime,json,os,pathlib
p=pathlib.Path(os.environ['TEST_EVIDENCE_DIR'])/'ubuntu-vm-result.json'
p.write_text(json.dumps({'suite':'real-ubuntu-docker-etcd-single-node-e2e','stage':os.environ['TEST_STAGE'],'startedAt':os.environ['TEST_START'],'finishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':int(os.environ['EXIT_CODE']),'status':'passed' if os.environ['EXIT_CODE']=='0' else 'failed','note':'This record is generated only on the machine actually executing the test. It does not certify HA or multi-node networking.'},indent=2)+'\n')
PY
  if [[ "$code" != 0 ]]; then
    printf 'FAILED at stage %s: leave the disposable VM for inspection. No automatic wipe of keys/data.\n' "$stage" >&2
  fi
  exit "$code"
}
trap result EXIT
apt-get update
# Ubuntu package sources must be configured by the operator. Do not add random repos.
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 curl "$package"
address="${WERFT_NODE_ADDRESS:-127.0.0.1}"
werft setup --name runtime-e2e --address "$address"
werft version > "$out/version.txt"
docker version > "$out/docker-version.txt"
etcd --version > "$out/etcd-version.txt"
stage=demo
werft demo --replicas 2 --wait
assert_state() {
 local expected="$1"
 werft status --json | python3 -c '
import json,sys
s=json.load(sys.stdin); n=int(sys.argv[1]);w=s["workloads"]["demo"]
a=[a for a in s["allocations"].values() if a["desired"]=="run"]
assert w["phase"]=="ready" and w["spec"]["replicas"]==n
assert len(a)==n and all(x["phase"]=="ready" for x in a)
assert len({x["id"] for x in a})==n
' "$expected"
}
assert_state 2
cluster="$(werft status --json | python3 -c 'import sys,json;print(json.load(sys.stdin)["clusterId"])')"
filter="org.werftkern.runtime.cluster=$cluster"
probe() {
 while IFS= read -r endpoint; do curl --fail --silent --show-error --noproxy '*' "$endpoint/healthz" >/dev/null; done < <(werft endpoints demo)
}
probe
# Containers are real, constrained and running, not mocked agents.
docker ps -q --filter "label=$filter" | sort > "$out/container-ids-before.txt"
[[ "$(wc -l < "$out/container-ids-before.txt")" == 2 ]]
mapfile -t ids < "$out/container-ids-before.txt"
docker inspect "${ids[@]}" | python3 -c '
import json,sys
for c in json.load(sys.stdin):
 h=c["HostConfig"]
 assert c["State"]["Running"] and c["Config"]["User"]=="65532:65532"
 assert h["ReadonlyRootfs"] and not h["Privileged"] and "ALL" in h["CapDrop"]
 assert not h.get("Binds") and h["Memory"]==32*1024*1024
'
stage=service-restart
systemctl restart werftkern-control.service werftkern-agent.service
sleep 8
werft wait demo --timeout 120s
assert_state 2
probe
docker ps -q --filter "label=$filter" | sort > "$out/container-ids-after.txt"
cmp "$out/container-ids-before.txt" "$out/container-ids-after.txt"
stage=scale
werft scale demo 3
werft wait demo --timeout 120s
assert_state 3
probe
stage=rollback
werft rollback demo
werft wait demo --timeout 120s
assert_state 2
# The actual store must remain authoritative across its own restart.
stage=etcd-restart
systemctl restart werftkern-etcd.service
sleep 6
werft wait demo --timeout 120s
probe
# Test-only secret file and backup material stay OUTSIDE the uploaded evidence directory.
private="$(mktemp -d /root/clusterpilot-e2e-private.XXXXXX)"
chmod 0700 "$private"
printf 'disposable-runtime-test-value' > "$private/fixture.secret"
chmod 0600 "$private/fixture.secret"
werft secret put e2e --file "$private/fixture.secret"
werft status --json | python3 -c '
import json,sys
w=json.load(sys.stdin)["workloads"]["demo"];w["spec"]["secrets"]=[{"name":"e2e","version":1}]
print(json.dumps({"apiVersion":"werftkern/v1alpha1","name":"demo","expectedGeneration":w["generation"],"spec":w["spec"]}))
' > "$private/deploy.json"
stage=secret-rollout
werft apply "$private/deploy.json"
werft wait demo --timeout 120s
stage=secret-container-count
mapfile -t secret_ids < <(docker ps -q --filter "label=$filter")
[[ "${#secret_ids[@]}" == 2 ]]
stage=secret-mount-verification
for id in "${secret_ids[@]}"; do
 docker inspect "$id" | python3 -c '
import json,sys
h=json.load(sys.stdin)[0]["HostConfig"]
assert h["RestartPolicy"]["Name"]=="no"
assert len(h["Binds"])==1 and h["Binds"][0].endswith(":/run/secrets:ro,rprivate")
'
 docker cp "$id:/run/secrets/e2e" "$private/copied.secret" >/dev/null
 cmp "$private/fixture.secret" "$private/copied.secret"
 rm "$private/copied.secret"
done
stage=encrypted-backup
werft backup create --out "$private/config.backup" --key-file "$private/backup.key"
werft backup inspect --file "$private/config.backup" --key-file "$private/backup.key" > /dev/null
stage=pause
werft pause demo
for _ in $(seq 1 120); do
 if [[ -z "$(docker ps -q --filter "label=$filter")" ]]; then break; fi
 sleep 1
done
[[ -z "$(docker ps -q --filter "label=$filter")" ]]
stage=resume
werft resume demo
werft wait demo --timeout 120s
probe

stage=delete
werft delete demo
for _ in $(seq 1 120); do
 if werft status --json | python3 -c 'import json,sys;s=json.load(sys.stdin);sys.exit(0 if "demo" not in s["workloads"] and not s["allocations"] else 1)'; then break; fi
 sleep 1
done
werft status --json | python3 -c 'import json,sys;s=json.load(sys.stdin);assert "demo" not in s["workloads"] and not s["allocations"]'
[[ -z "$(docker ps -aq --filter "label=$filter")" ]]
stage=doctor
werft doctor > "$out/doctor.txt"
rm -rf -- "$private"
stage=complete
printf 'REAL UBUNTU E2E PASSED. Evidence: %s\n' "$out"
