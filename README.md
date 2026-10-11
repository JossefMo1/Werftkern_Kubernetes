# Werftkern

## Neu: eigenständiger Kubernetes-Betriebsmodus

**Kubernetes-Backend `0.1.0-dev.3` · NOT_PRODUCTION_READY · keine CNCF-Zertifizierung.**

Der neue Befehl `werft-kube` ergänzt einen **separaten echten Kubernetes-Pfad auf
k0s/k0sctl**: Create, Upgrade, Scale, geprüfte lokale Helm-/Operatorkataloge,
Keycloak/Grafana/Kubernetes-OIDC, Sonobuoy-Auswertung und budgetierter automatischer
Ersatz zustandsloser Hetzner-Worker. **Es ist keine Neuimplementierung von Kubernetes.**

[Deutsche Anleitung und genaue Grenzen](docs/kubernetes/README-DE.md) ·
[Add-ons und SSO](docs/kubernetes/ADDONS-SSO-DE.md) ·
[Automatischer Node-Ersatz](docs/kubernetes/REPAIR-DE.md) ·
[Neue Testergebnisse](docs/kubernetes/TEST-REPORT.md)

Neu in dev.3: journallierter Controllerersatz im Drei-Controller-Profil, eng
begrenzte Single-Writer-/Hetzner-CSI-Reparatur, deaktivierter Policy-Watcher,
quarantinierter CSI-Snapshot-PV-Restore mit Dateihash-Jobs und ein Prüfer für extern
signierte Freigabenachweise. Nur Vertragstests; keine reale Produktionsqualifikation.

[Recovery-Vertrag](docs/kubernetes/DEV3-RECOVERY-DE.md) ·
[PV-Restore und Backendgrenzen](docs/kubernetes/DEV3-DATA-RESTORE-DE.md) ·
[Signierte Nachweise](docs/kubernetes/DEV3-RELEASE-EVIDENCE-DE.md) ·
[Dev.3 Testergebnisse](docs/kubernetes/DEV3-TEST-REPORT.md)

Das neue `.deb` installiert den Managementcode, **nicht** geprüfte k0s-/Helm-/
Sonobuoy-Binaries, Charts oder Images. Ein vorbereitetes Artefaktinventar, Zielhosts,
SSH-Hosttrust und API-Einstieg sind notwendig. Paketinstallation allein erzeugt
keinen Cluster. Keine Dienste oder Cloudmutationen im Paket-postinst.

Native-Runtime und Kubernetes verwenden getrennte Prozesse, Zustandsspeicher,
Credentials und Worker. Kein direktes Umstellen bestehender Native-Workloads auf
Kubernetes. Der nachfolgende Abschnitt dokumentiert den unveränderten Native-Kern.

---


**Independent, self-hosted container orchestration for Ubuntu.**

**0.2.0-dev.4 · State schema 2 · NOT_PRODUCTION_READY.** This is an implemented,
tested development increment, **not** the complete Kubernetes 2.0 masterplan and
not an official Kubernetes release. Kubernetes is not an execution dependency.

Werftkern derives from the independent ClusterPilot Runtime project. It requires no
ClusterPilot backend, licence or commercial portal. Its optional ClusterPilot connector
remains unfinished. Apache-2.0; see [NOTICE](NOTICE.md). The working name has not received
trademark clearance. No remote repository or cloud resource was created by this delivery.

## New in dev.4

| Area | Implemented change | Evidence boundary |
|---|---|---|
| Rollout safety | Readiness expires even while a node sends fresh heartbeats; stale surge replicas cannot retire healthy old instances | Both defects reproduced against the previous scheduler; regression tests pass after correction. |
| Worker update waves | Sequential owned drain, signed package staging, durable remote receipt, local engine smoke, advancing observations and uncordon | SSH, package and engine behavior in ordinary tests use explicit fixtures; no Ubuntu/SSH multi-host release qualification. |
| Node-scoped maintenance | Node credentials read only their own maintenance projection; no controller-admin credential travels to a worker | Real local TLS/API permission and negative tests. |
| Compatibility | Bounded same-schema **dev.3 agent → dev.4 controller** edge; all controllers must be upgraded first | Actual binaries built from both commits, real agent processes/TLS/journal. Docker and etcd remain fixtures. |

See [worker rollout contract](docs/WORKER-ROLLOUT.md), [change scope](docs/DEV4-CHANGES.md)
and the [actual test report](docs/validation/TEST-REPORT.md). Paused workloads may be
preserved during update verification, but any remaining live allocation still blocks.

## Inherited from dev.3 (still subject to qualification)

| Area | Implemented change | Evidence boundary |
|---|---|---|
| Database HA integration | Three dedicated PostgreSQL17/Patroni4 hosts; independent etcd DCS, TLS, strict synchronous policy, mandatory watchdog; planned switchover journal | Real OpenSSL kits; provider/process responses in tests are fixtures. No live Patroni/HA/watchdog qualification. |
| PostgreSQL PITR | Encrypted pgBackRest repository profile, explicit backup set/system identity, isolated restore, SQL replay-pause verification | Adapter tests use explicit command fixtures. The no-mock PostgreSQL/WAL realtest exists but is BLOCKED by missing dependencies here. |
| Update correctness | No automatic unfreeze after mere status-read; direct all-controller health checks, advancing node heartbeat and allocation checks; safe lost-unlock-ACK recovery | Runtime/API contracts tested; no real host package update. Worker-wave implementation is new in dev.4. |
| Leaf credentials | Offline-CA renewal, new private key, fingerprint-bound atomic install; combined PEM live reload for runtime clients/controllers | Actual local TLS tests, no CA rollover or autonomous signer. One-time manual combined-file adoption required. |
| Input/process safety | Duplicate JSON fields and invalid constants rejected; timed-out commands terminate their owned child process groups | Actual parser and local-process tests, not an independent security review. |

State remains schema2. Exact agent-version matching still requires coordinated offline
maintenance for dev.2→dev.3; This historical edge remains offline-only. Dev.4 adds only the explicit dev.3→dev.4 worker edge above, not general N/N−1 compatibility. The existing
native scheduler, Docker Engine adapter, local volume archives, Go ingress, mesh/DNS,
Hetzner and runtime HA tooling remain. Native database-host integration is a separate
operational profile, not a completed database service controller in the basic wizard.

## Fresh isolated Ubuntu 24.04 LTS amd64 VM

```sh
bash scripts/build-deb.sh
sudo apt update
sudo apt install ./dist/werftkern_0.2.0~dev4_amd64.deb
sudo werft setup
sudo werft demo --wait
sudo werft dashboard
```

Use a supported, current Go compiler for builds. A separately supplied Go1.23.2 binary
is an **unsigned lab artifact**, not a release. Do not install on customer infrastructure.
The basic wizard asks for role and private IPv4. HA/network/cloud/ingress need additional
explicit topology, certificates, network trust and cost decisions.

**Existing dev.1:** read [SCHEMA-MIGRATION](docs/SCHEMA-MIGRATION.md) first. Do not just
replace packages and restart one controller. Older ClusterPilot alpha installations
need separate new-cluster migration; package paths/identities changed previously.

## Documentation

[Ubuntu setup](docs/INSTALL-UBUNTU-DE.md) · [HA](docs/HA.md) · [Network/DNS](docs/NETWORK.md) ·
[HTTPS ingress](docs/INGRESS.md) · [Storage/PostgreSQL](docs/STORAGE.md) ·
[Volume archive/restore](docs/VOLUME-BACKUP.md) · [Cloud](docs/CLOUD.md) ·
[Recovery](docs/RECOVERY.md) · [Update completion](docs/UPGRADE.md) ·
[Database HA](docs/DATABASE-HA.md) · [PITR](docs/POSTGRES-PITR.md) ·
[Certificates](docs/CERTIFICATE-ROTATION.md) · [Previous changes](docs/DEV2-CHANGES.md).

## Tests

```sh
go test -race -count=1 ./...
go vet ./...
python3 -m unittest discover -s tests/ops -v
python3 -m unittest discover -s tests/release -v
python3 scripts/check-public-source.py
python3 tests/browser/test_ui.py
```

The root-only physical CLI test runs in the isolated authoring container; on non-root
systems it explicitly skips. Archive tests use actual files and encryption. Ingress
integration uses actual local TLS/HTTP. The process E2E still substitutes Docker/etcd.
Browser checks use in-memory fixtures. Those scopes must not be relabelled VM qualification.
See [TESTING](docs/TESTING.md) and [actual report](docs/validation/TEST-REPORT.md).

## Production and publication

[STATUS](docs/STATUS.md) and [52-task traceability](docs/ROADMAP.md) retain the missing work.
`release/qualification.json` is blocked. Live qualification of database HA/PITR/watchdog fencing, replicated storage/CSI,
full disaster recovery, a current signed build, separate-host failure tests, soak testing
and independent security review remain outstanding. Existing feature counts are not GA.

Open-source publication guidance: [PUBLISHING](docs/PUBLISHING.md),
[CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md). Review IP, secrets and history before
public upload. The Git bundle is a local repository, not evidence of GitHub publication.
