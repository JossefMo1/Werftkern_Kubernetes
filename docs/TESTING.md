# Verification levels

The commands below cover the native runtime; the separate Kubernetes manager
also has `PYTHONPATH=ops python3 -m unittest discover -s tests/kubernetes -v`.
Use Linux for process, file-permission and symlink tests. Current GitHub run
evidence and publication checks are recorded in
[the 2026-10-12 review](validation/PUBLICATION-REVIEW-2026-10-12.md).
Historical observations below describe their authoring environment and do not
override successful or skipped checks on a later exact commit.

Exact counts, toolchain and source fingerprint: `validation/TEST-REPORT.md`.
Actual behavior and test doubles must remain separate in every claim.

## Executable local tests

```sh
go test -race -count=1 ./...
go vet ./...
go run golang.org/x/vuln/cmd/govulncheck@v1.9.0 ./...
python3 -m unittest discover -s tests/ops -v
python3 -m unittest discover -s tests/release -v
python3 tests/browser/test_ui.py
```

Archive tests use real files, AES-GCM and hashes. Ingress tests use real local HTTPS and
HTTP. `TestVolumeArchiveCLIPhysicalRestoreAfterLostAcknowledgment` is root-only and uses
real filesystem/CLI/mTLS/Unix HTTP with explicit Docker and etcd fixtures. It skips on
non-root runs. It is not a container, new-host or database restore test. The older process
E2E starts true Linux child processes, not Docker containers. Browser data is synthetic.

Native CI pins Go 1.27.2 and runs the pinned Go vulnerability scanner before package
construction. A nonzero scanner result fails the job; its text output is retained in
the existing evidence artifact. This check covers reachable Go vulnerabilities, not
Debian dependencies, Kubernetes assets/images or independent security qualification.
Manual native qualification and push/PR checks use separate concurrency groups, so
a delayed push run cannot cancel an explicitly requested disposable-VM test.

## Actual etcd, never a mock fallback

```sh
bash scripts/install-test-etcd.sh "$HOME/werft-test-etcd"
PATH="$HOME/werft-test-etcd:$PATH" go test -race -count=1 -timeout 4m \
  -tags real_etcd ./tests/integration
```

The installer uses the official fixed3.7.2 download and SHA-256 recorded in
`tests/runtime/etcd-tool.json`, not a mutable tag. CI runs it in an ephemeral Ubuntu runner.
The new test creates **three actual etcd processes on one host**, distinct data/ports and
mTLS, concurrent CAS, real leader termination, quorum loss, restart and persisted data.
It cannot substitute for separate hosts, asymmetric networks, partitions or power-loss.
Here it compiled, but the attempted run failed because etcd is missing. Never record this
as a pass, and never replace its daemon with a fixture while retaining the same gate name.
GitHub CI has been prepared, not executed.

## Disposable Ubuntu installation

```sh
sudo env WERFT_DISPOSABLE_VM=1 bash tests/e2e/ubuntu-vm.sh PATH_TO_DEB
```

Destructive to the disposable testhost; never use a customer or existing installation.
This inherited script covers only its explicitly implemented single-host behavior, not
all dev.2 functions. Docker/etcd installation itself has not passed here.

## Required qualification still open

Actual three-host controller loss/quorum/partition, persistent container/host reboot,
WireGuard/CoreDNS/MTU/firewall, copied volumes and SQL validation on another host, clean
shutdown consistency, abrupt backup/restore interruption and disk-full, migration of a
real schema1 cluster, current-agent-only upgrade windows, edge TLS/DNS/expiry/security,
cloud create/recovery/cleanup, signed exact release install/upgrade/rollback, sustained
load, independent security/crypto review and operator approval.

Record exact versions/topology/release digests, traffic results, integrity hashes and
bounded redacted logs. Fixture success does not satisfy real-world gates. A current
compiler or green linter does not certify security. The release validator remains BLOCKED.

## dev.3: real PITR and TLS

`tests/integration/real_pitr.py` never substitutes binaries or manufactures WAL results.
It requires PG17 and pgBackRest2.59.1+, OS user postgres and WERFT_DISPOSABLE_VM=1.
Here: missing dependencies, BLOCKED/Exit3. The manual CI job `real-pitr` needs a
separately approved disposable self-hosted runner label and protected environment.
No runner exists or workflow was triggered by authoring this code. Do not attach a
production DB host or run untrusted PR code on that runner. Hosted CI remains read-only
for source. The fixture-based operations tests are a distinct suite.

Leaf rotation tests use an actual local TLS server and client, replace both PEMs and
verify new handshakes, corruption rejection and identity consistency. CLI tests issue
real keys in temporary test directories, never source/evidence. This is not cross-host
PKI rollover, hardware identity, online issuance or immediate session revocation.

## Actual previous executable compatibility test

Requires the retained dev.3 commit in Git history or an explicitly supplied,
hash-verified historical bundle. See
[the local compatibility report](validation/LOCAL-DEV3-DEV4-COMPAT.md) and
`scripts/test-agent-compat.sh` for the bundle opt-in. Do not import private
historical Git refs into the public repository. Missing prerequisites FAIL the
opt-in test rather than passing or silently skipping. Docker and etcd remain test
adapters here; this suite qualifies the executable/protocol/journal edge only.

```bash
bash scripts/test-agent-compat.sh
```

The script builds the previous Git revision and current source, then runs a real
previous-agent process against the new TLS API and replaces it with the new binary.
Evidence records original Git SHA, binary hashes and the actual test log.


`tests/integration/verify_upgrade_package.py` prüft ein tatsächlich gebautes dev.4-.deb
mit dem echten dev.3-Releaseprüfer und einem ausschließlich temporären Ed25519-Testschlüssel.
Ein manipulierter Signaturbytewert muss scheitern. Der Test signiert keine freigegebene
Produktionsrelease und führt weder Paketinstallation noch root-Hoständerungen aus.
