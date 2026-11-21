# Release status — 0.2.0-dev.4

**NOT_PRODUCTION_READY. Full masterplan incomplete. State schema 2.**

The [candidate production scope](PRODUCTION-SCOPE.md) records a proposed,
bounded first support matrix for the Native and Kubernetes paths. It is a
planning and drift-detection contract, not qualification evidence. All listed
live, security, supply-chain and operational gates remain open until evidence
for one unchanged release candidate is verified.

The active [German E2E production plan](PRODUCTION-E2E-PLAN-DE.md) and the
machine-readable [`production-tracker.json`](../release/production-tracker.json)
make the next blocked and independent steps explicit between runs. They are
tracking aids only; their status never closes a qualification gate.

The Kubernetes matrix now selects hcloud-csi 2.24.2 as a candidate RWO storage
path with a digest-bound chart and `Retain` StorageClass. Its six upstream OCI
index digests are pinned after each registry digest header matched the SHA-256 of
the received manifest body, and the checker can repeat that online comparison.
The hash-checked chart was rendered with the conservative values and exact image
multiset; the generated manifest is committed and hash-bound. The chart, Helm and
images have not been signature- or vulnerability-verified, executed or independently
reviewed; real Volume lifecycle, failure, backup and restore evidence remains absent.
The exact render now also has a fail-closed static privilege audit: RBAC contains no
wildcards or Secret access, and the only accepted privileged container/host-path set
is the CSI node driver boundary. The exact render now selects a separately hash-bound
node ServiceAccount with automatic API-token mounts disabled. Both workloads set
`RuntimeDefault` at pod level, covering their non-privileged containers; Kubernetes
privileged-container semantics leave the CSI node driver as an explicit exception.
The linux/amd64 manifest and config blobs behind all six locked image indexes were
also hash-checked. Their image configs select root explicitly (`User: 0`) or implicitly
(empty `User`), while the upstream chart exposes no per-container security-context
values. Pod-level `runAsNonRoot` is therefore explicitly unsafe for this candidate,
not a completed control. An exact-input, fail-closed post-render step now makes every
root identity explicit. The seven non-privileged container instances disable privilege
escalation, drop every Linux capability and bind `RuntimeDefault` at container level;
the privileged node driver retains only its reviewed explicit root/privileged context.
Hardening remains blocked pending qualified non-root identities and disposable-cluster
runtime evidence. Every rendered CSI container has a hash-bound CPU/memory request and
limit; these conservative starting budgets have not been measured under load or soak
and are not production capacity claims.
These audits are not runtime security or live CSI compatibility evidence.

The authoring-environment observations below are historical, including the
compiler version and whether CI had run at that time. For subsequently verified
GitHub CI and public-source preparation, see
[the dated publication review](validation/PUBLICATION-REVIEW-2026-10-12.md).
That review does not qualify the production features listed here.
The later [production qualification review](validation/PRODUCTION-READINESS-2026-10-12.md)
records a successful exact-commit single-host Ubuntu test. Multi-host, Kubernetes,
database recovery and signed production acceptance remain unqualified.

## Current immutable lab candidate

The latest immutable experimental candidate is [`v0.2.0-dev.4-test.17`](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17), built from source commit `28efa7518e171a618d4dcf9ff3aba58cddaf3296`. Its Native, Kubernetes-package and source-audit workflows passed; the Native real-etcd job passed, while VM/PITR jobs were skipped. The release includes the auto-discovery known-hosts replay guard, is unsigned and remains a lab artifact only: it does not qualify installation, HA, recovery, Kubernetes lifecycle, supply-chain or production readiness. The machine-readable tracker records the exact asset digests and open gates.

Main contains [PR #122](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/122), merged at `c95511a5f1e1c8ca6aa909b3e69bb21558b00634`, [PR #140](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/140), [PR #143](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/143), [PR #148](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/148), [PR #152](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/152), [PR #154](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/154) and [PR #156](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/156). The code-bearing handoff commit remains `2ab2ebe5433b938925b4aebd57c84a7939d92a43`; the latest tracker-synchronized Main handoff is `a1e0413233fa1b18f4281445e7cd96f4245f02d9`, with this status/roadmap/tracker synchronization following PR #156. Native auto-discovery binds both the explicit `--hosts-file` path and its exact bytes in the private resume journal; changed content is rejected with `AUTO_DISCOVERY_HOSTS_FILE_CONTENT_CHANGED`, and legacy journals without the byte binding fail closed. PR #140 adds fail-closed TCP port-range validation for Native control-plane endpoints. PR #143 makes the Native package `postinst` execute `/usr/bin/werft --help` and `/usr/bin/werft-ops --help` before declaring the package configured, with a release regression test protecting both checks. PR #148 adds a release-contract regression test that covers every service stop/disable action and prevents uninstall scripts from deleting persisted state, identities or workloads. PR #152 adds a release-contract regression test for both Kubernetes recovery/repair systemd templates, preserving their explicit root, token/assets and sandbox boundaries. PR #154 adds hermetic Kubernetes-manager wrapper tests for staged package-root execution and exit-78 fail-closed behavior when Python modules are missing. PR #156 requires the Kubernetes wrapper entrypoint to exist before selecting an installed, staged or source-tree module path and regression-tests incomplete package trees. Post-merge Native (including real-etcd), Kubernetes-package and source-audit workflows passed; real-vm/real-pitr remain skipped. Test17 remains immutable at `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and does not contain PR #140, PR #143, PR #148, PR #152, PR #154 or PR #156; a new candidate is required before live testing the updated package. The production decision remains no-go.

## Implemented in this increment

Owned sequential worker rollout, separately authorized node maintenance reads and drain,
signed remote staging, conservative uncertain-install recovery, local Docker-smoke command,
restarted observation windows, identity-bound final unlock and a narrowly supported
dev.3-agent/dev.4-controller compatibility edge. Stale probe observations no longer
count as ready in scheduling or discovery. Paused applications require zero live executions.

Both previous and new agent executables were actually built and started using a real
persistent local journal, real TLS and OS processes. The Docker endpoint and etcd store
were fixtures. This is stronger than changing a version string, but NOT real container,
Ubuntu, SSH, hardware, quorum or production upgrade evidence.

The new `werft-ops native-bootstrap` coordinator now covers the intended
three-controller/worker bootstrap flow in code: it resolves an explicit
inventory against a trusted hosts file, performs fail-closed SSH/Ubuntu/systemd/
cgroup-v2 preflight on every target, generates one bound HA kit set, installs
the unchanged package through the existing SSH bootstrap primitive, and resumes
from a private journal without overwriting foreign or incomplete state. The
coordinator has fixture tests only; no real six-host run was executed in this
authoring environment, so this does not close any live qualification gate.

All controllers must already be dev.4 before a dev.3 worker wave starts. General mixed
versions, old controllers accepting new agents, automated controller waves and the
historical dev.2→dev.3 edge are not supported by this compatibility test. Active pinned
or local-volume workloads require separately planned offline maintenance, not forced drain.

## Inherited integrations and boundaries

Native three-host PostgreSQL17/Patroni4 with mandatory watchdog and independent etcd DCS;
pgBackRest/POSIX encrypted backup and PITR adapter; offline CA leaf renewal and combined-PEM
live reload; physical encrypted local-volume archives; own Go TLS ingress; HA/mesh/DNS/
Hetzner tooling. These are not independently qualified multi-host production services.
Database HA runs on dedicated native hosts, not in the ordinary Docker scheduler.
File restore, actual WAL replay and business validation remain separate gates.

## Still missing or unqualified

Replicated generic storage/CSI; qualified physical fencing; complete site-wide DR;
integrated database service lifecycle; production NetworkPolicy and HA ingress endpoint;
full CA rotation/online issuer; automated controller upgrade orchestration; direct
containerd; IONOS/ClusterPilot connector and broader roadmap features. No model size
limit is a measured scalability claim. No SLA/RPO/RTO commitment.

Real Ubuntu/systemd/Docker/SSH/cloud/WireGuard/CoreDNS/PostgreSQL/Patroni/watchdog tests,
three-host failures, actual signed package upgrades, soak/load and independent security
assessment have not passed here. Opt-in etcd/PITR attempts fail explicitly if dependencies
are absent. All production qualification gates remain BLOCKED.

Local compiler: Go1.23.2 on Debian13. Prepared CI: Go1.27.1, not executed here. A separately
supplied `.deb` is unsigned, unqualified and for fresh disposable lab VMs only. Actual
counts and evidence scopes: `validation/TEST-REPORT.md`.

