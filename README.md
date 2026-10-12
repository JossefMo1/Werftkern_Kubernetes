# Werftkern

**Self-hosted container orchestration and Kubernetes management for Ubuntu.**

[![Native checks](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/workflows/ci.yml)
[![Kubernetes checks](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/workflows/kubernetes-backend.yml/badge.svg?branch=main)](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/workflows/kubernetes-backend.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[Deutsch: hier beginnen](START-HERE-DE.md) · [Documentation](#documentation) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) ·
[Source releases](https://github.com/JossefMo1/Werftkern_Kubernetes/releases)

> **Experimental alpha — not production-ready.** Use disposable test infrastructure.
> No production support, SLA or CNCF certification is claimed. Passing CI checks
> do not establish live cloud, multi-host recovery or production upgrade safety.

## What is Werftkern?

Werftkern contains two separate operating paths:

| Path | Implementation | Component version | Where to start |
| --- | --- | --- | --- |
| Native runtime | Go controller and node agent, Docker Engine execution, etcd persistence, mTLS and a local dashboard | `0.2.0-dev.4`, state schema 2 | [Architecture](docs/ARCHITECTURE.md), [Ubuntu setup](docs/INSTALL-UBUNTU-DE.md) |
| Kubernetes manager | Python management tooling around separately supplied k0s/k0sctl, kubectl, Helm, age and Sonobuoy | `0.1.0-dev.3` | [Kubernetes guide](docs/kubernetes/README-DE.md) |

The paths use separate processes, state, credentials and workers. Kubernetes is
not a dependency of the native runtime. The Kubernetes manager operates actual
Kubernetes through k0s; it does not implement a replacement Kubernetes engine.
There is no automatic migration of native workloads into Kubernetes.

This project derives from ClusterPilot Runtime and works without the private
ClusterPilot backend, commercial portal or licence. The optional ClusterPilot
connector is unfinished. Source provenance and attribution are recorded in
[NOTICE.md](NOTICE.md).

## Capabilities and boundaries

| Area | Implemented code | Qualification boundary |
| --- | --- | --- |
| Native workloads | Scheduling, revisions, scaling, readiness, drain and worker update waves | Docker/etcd fixtures are used in several tests; real host upgrade qualification remains open |
| Native networking and storage | TLS ingress, discovery, mesh tooling, node-local volumes and encrypted archives | Multi-host networking, replicated storage and physical fencing remain unqualified |
| Operations | Hetzner provisioning tooling, PostgreSQL/Patroni HA profiles, pgBackRest/PITR integration and certificate renewal | Cloud, database HA, watchdog and real WAL recovery need separate live qualification |
| Kubernetes lifecycle | Plans, create, scale, upgrade, backups, restore, add-on and OIDC/SSO tooling | Requires reviewed local assets, trusted SSH hosts and explicit topology; contract tests are not live cluster evidence |
| Kubernetes recovery | Budgeted worker replacement, journalled controller replacement and constrained stateful/CSI recovery | Restricted experimental profiles; full disaster recovery and production safety are not established |

Consult [native status](docs/STATUS.md), [Kubernetes readiness](release/kubernetes-readiness.json)
and the [roadmap](docs/ROADMAP.md) before selecting a feature. Host root and
Docker-socket access are trusted administrator capabilities. Hostile multi-tenancy
is unsupported; mTLS is not customer tenant RBAC.

## Get started

### Explore the source

```sh
git clone https://github.com/JossefMo1/Werftkern_Kubernetes.git
cd Werftkern_Kubernetes
```

The repository currently provides experimental source prereleases. Source tags
such as `v0.1.0-alpha.2` identify the repository release, not the native or
Kubernetes component versions. Read the [release notes](releases/v0.1.0-alpha.2.md)
for their exact scope. Source archives are not verified binary distributions.

### Native runtime on a disposable Ubuntu VM

Target: **Ubuntu 24.04 LTS, amd64**. Build with Bash, Python 3, `dpkg-deb` and a
supported Go toolchain accepted by [the build script](scripts/build-deb.sh).
Review the [installation guide](docs/INSTALL-UBUNTU-DE.md) before running:

```sh
bash scripts/build-deb.sh
sudo apt update
sudo apt install ./dist/werftkern_0.2.0~dev4_amd64.deb
sudo werft setup
sudo werft demo --wait
sudo werft dashboard
```

The package is an unsigned development build. Keep the dashboard local; the
basic wizard does not configure complete HA, network trust or cloud operations.
Existing installations require the [schema migration](docs/SCHEMA-MIGRATION.md)
and [upgrade guidance](docs/UPGRADE.md); do not upgrade one controller in isolation.

### Kubernetes manager

```sh
bash scripts/werft-kube version
bash scripts/build-kubernetes-deb.sh
```

Read the [Kubernetes guide](docs/kubernetes/README-DE.md) and review the
[example inventories](examples/kubernetes/) before provisioning. The `.deb`
installs management code, not k0s/Helm/Sonobuoy binaries, charts or images. You
must supply reviewed assets, target hosts, SSH host trust and an API endpoint.
Package installation alone does not create a cluster; its installation does
not automatically start services or mutate cloud infrastructure.

## Documentation

| Topic | Guides |
| --- | --- |
| Architecture and API | [Architecture](docs/ARCHITECTURE.md), [API](docs/API.md), [status](docs/STATUS.md), [roadmap](docs/ROADMAP.md) |
| Native operations | [HA](docs/HA.md), [network/DNS](docs/NETWORK.md), [ingress](docs/INGRESS.md), [cloud](docs/CLOUD.md) |
| Data and recovery | [Storage](docs/STORAGE.md), [volume archives](docs/VOLUME-BACKUP.md), [database HA](docs/DATABASE-HA.md), [PITR](docs/POSTGRES-PITR.md), [recovery](docs/RECOVERY.md) |
| Security and maintenance | [Secrets](docs/SECRETS.md), [certificates](docs/CERTIFICATE-ROTATION.md), [worker rollout](docs/WORKER-ROLLOUT.md), [upgrades](docs/UPGRADE.md) |
| Kubernetes | [Setup](docs/kubernetes/README-DE.md), [add-ons/SSO](docs/kubernetes/ADDONS-SSO-DE.md), [repair](docs/kubernetes/REPAIR-DE.md), [recovery](docs/kubernetes/DEV3-RECOVERY-DE.md), [PV restore](docs/kubernetes/DEV3-DATA-RESTORE-DE.md) |
| Validation | [Testing](docs/TESTING.md), [native report](docs/validation/TEST-REPORT.md), [Kubernetes report](docs/kubernetes/DEV3-TEST-REPORT.md) |
| Open-source publication | [Launch checklist](docs/OPEN-SOURCE-LAUNCH-CHECKLIST.md), [GitHub settings](docs/GITHUB-SECURITY-SETTINGS.md), [publication review](docs/validation/PUBLICATION-REVIEW-2026-10-12.md) |

Some operational guides are in German. Historical test reports describe their
recorded source and environment; current CI results belong to their exact commit.

## Development and tests

Run the checks in a Linux development environment. Privileged integration tests
require separately approved disposable hosts, never a production workstation.

```sh
go test -race -count=1 ./...
go vet ./...
python3 -m unittest discover -s tests/ops -v
PYTHONPATH=ops python3 -m unittest discover -s tests/kubernetes -v
python3 -m unittest discover -s tests/release -v
python3 scripts/check-public-source.py
python3 scripts/audit-git-history.py
node --check internal/dashboard/assets/app.js
```

[Testing](docs/TESTING.md) explains additional browser, real-etcd, compatibility,
VM and database tests. Synthetic browser data and test adapters must remain
distinct from real runtime evidence. The [production qualification gate](release/qualification.json)
remains blocked.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md) and the
[code of conduct](CODE_OF_CONDUCT.md). Use [issues](https://github.com/JossefMo1/Werftkern_Kubernetes/issues)
for reproducible non-sensitive bugs and bounded feature proposals.

For vulnerabilities, follow [SECURITY.md](SECURITY.md). Do not put tokens, private
keys, join bundles, backups, private infrastructure details or exploit reports
in public issues, PRs or CI artifacts.

## License and provenance

Source is licensed under [Apache License 2.0](LICENSE). Preserve
[NOTICE.md](NOTICE.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
Separately installed tools retain their own licenses. Werftkern is a working
name; trademark clearance has not been established. Public source availability
does not imply production qualification.
