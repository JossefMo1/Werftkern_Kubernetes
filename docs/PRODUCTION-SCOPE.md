# Candidate production scope

This document defines the **proposed first support boundary**, not a production
release. Werftkern remains an experimental alpha. The boundary becomes supported
only after one unchanged release candidate and its digest-bound artifacts pass
every applicable live, security, supply-chain and operational gate.

The machine-readable contract is `release/production-scope.json`; CI validates
that it classifies every item in the 52-item masterplan and keeps the Native and
Kubernetes paths separate. Scope validation cannot set `productionReady`.

## Native runtime candidate

| Area | Proposed supported boundary |
| --- | --- |
| Host | Fresh Ubuntu 24.04 LTS amd64, systemd and cgroup v2 |
| Runtime | Werftkern Native 0.2.0-dev.4, state schema 2, Docker Engine and etcd |
| Topology | Exactly three controllers and at least three workers; one site |
| Trust | One trusted administrator and trusted workloads; no hostile multi-tenancy |
| Capacity ceiling | 20 nodes, 50 workloads, 200 allocations and 900,000 state bytes; these are hard model bounds, not performance claims |
| Dependencies | systemd, cgroup v2, Docker Engine and etcd, using the exact versions selected for the candidate |
| Operations | Fresh-host installation; uninstall/reinstall; dev.3 workers to dev.4 only after every controller is on dev.4; backup/restore on a new host; candidate-specific rollback and recovery, all only after live qualification |

Direct containerd, CNI compatibility, per-workload network policy, air-gap,
native Jobs/CronJobs, autoscaling and GPU workloads are explicitly outside the
first boundary. Docker-socket access remains privileged host authority. Loss of
contact is not storage fencing and no automatic quorum-loss recovery is promised.

## Kubernetes manager candidate

| Area | Proposed supported boundary |
| --- | --- |
| Management host | Ubuntu 24.04 LTS amd64 with Python 3.10 or newer |
| Target hosts | Fresh dedicated Ubuntu 24.04 LTS amd64 hosts |
| Engine | Separately supplied and digest-pinned k0s/Kubernetes; not the Native scheduler |
| Topology | Exactly three controllers and at least three workers with an external highly available API endpoint |
| Trust | One trusted administrator and one cluster; no multi-writer manager HA |
| Storage and add-ons | Only the exact storage profile, charts and images pinned for the candidate and proven by the live matrix |
| Upgrade | One adjacent Kubernetes minor-version edge selected before RC; no skipped-minor, downgrade or simultaneous topology/authentication change |

The k0s, k0sctl, Kubernetes, storage and add-on version pins are deliberately
unresolved today. Until they are selected, reviewed and tested, there is no
supported Kubernetes combination. Control-plane backup does not include
application volumes; storage and database recovery need their own evidence.

## Release evidence for the exact candidate

Both paths require a reproducible clean build, commit/artifact identity, all
relevant unit/race/contract/integration/package/source/vulnerability checks,
SBOM and dependency evidence, signed artifacts and provenance, fresh install,
uninstall/reinstall, supported upgrade and rollback, backup/restore on a new
host, multi-host failure and partition tests, negative authorization, load/soak
limits, complete operator runbooks, an RC with real feedback, required independent
review and a final Go/No-Go decision.

The Native gate inventory remains in `release/qualification.json`; the Kubernetes
inventory remains in `release/kubernetes-readiness.json`. Neither a green fixture
nor this narrower scope removes the still-open full-masterplan work. The JSON
contract records every deferred K20 item and its reason so scope cannot shrink
silently. The current Native qualification contract still requires the full
52-item masterplan; this proposal does not weaken or replace that gate.
