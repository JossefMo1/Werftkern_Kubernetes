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

Main contains [PR #122](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/122), merged at `c95511a5f1e1c8ca6aa909b3e69bb21558b00634`, [PR #140](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/140), [PR #143](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/143), [PR #148](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/148), [PR #152](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/152), [PR #154](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/154), [PR #156](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/156) and [PR #158](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/158). The code-bearing handoff commit remains `2ab2ebe5433b938925b4aebd57c84a7939d92a43`; the latest tracker-synchronized Main handoff is `9403d55e2deae30f4c99e889a56cfffbafb0390b`, with this status/roadmap/tracker synchronization following PR #158. Native auto-discovery binds both the explicit `--hosts-file` path and its exact bytes in the private resume journal; changed content is rejected with `AUTO_DISCOVERY_HOSTS_FILE_CONTENT_CHANGED`, and legacy journals without the byte binding fail closed. PR #140 adds fail-closed TCP port-range validation for Native control-plane endpoints. PR #143 makes the Native package `postinst` execute `/usr/bin/werft --help` and `/usr/bin/werft-ops --help` before declaring the package configured, with a release regression test protecting both checks. PR #148 adds a release-contract regression test that covers every service stop/disable action and prevents uninstall scripts from deleting persisted state, identities or workloads. PR #152 adds a release-contract regression test for both Kubernetes recovery/repair systemd templates, preserving their explicit root, token/assets and sandbox boundaries. PR #154 adds hermetic Kubernetes-manager wrapper tests for staged package-root execution and exit-78 fail-closed behavior when Python modules are missing. PR #156 requires the Kubernetes wrapper entrypoint to exist before selecting an installed, staged or source-tree module path and regression-tests incomplete package trees. PR #158 requires the Native `werft-ops` wrapper to find both `werftops/__init__.py` and `werftops/__main__.py` before selecting a module path and regression-tests incomplete package trees. Post-merge Native, Kubernetes-package, source-audit and Private-Alpha workflows passed; real-vm/real-pitr remain skipped. Test17 remains immutable at `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and does not contain PR #140, PR #143, PR #148, PR #152, PR #154, PR #156 or PR #158; a new candidate is required before live testing the updated package. The production decision remains no-go.

## Latest code handoff (2026-11-21)

PR #160 is merged at [a04b0b4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a04b0b4c9db7f4f0aa5e408446b45cb5fe25dd1a). The Kubernetes-manager `werft-kube plan` command now rejects valid non-object JSON before format dispatch and returns the stable `KUBE_PLAN_OBJECT_REQUIRED` block instead of an uncaught traceback; the regression test covers the JSON response and stderr. This is a CLI error-handling guard only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and does not contain PR #160. Post-merge source, contract, Real-etcd and publication-audit checks passed; `real-vm` and `real-pitr` remain skipped. Production remains no-go.


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



## Latest code handoff (2026-11-21, PR #162)

PR #162 merged at [2ad8daeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2ad8daebed99f8ea2b6735f9f626e500666cd694). The Kubernetes wrapper now requires both `werftops/__init__.py` and `werftops/kube_main.py` before selecting installed, staged or source modules; a missing package marker fails closed with exit 78 and is covered by a regression test. This is a packaging/error-boundary fix for the Kubernetes manager only. Post-merge test, contracts, real-etcd, publication-audit and private-alpha checks passed; real-vm and real-pitr remain skipped because no authorized disposable lab is configured. The immutable test17 candidate is unchanged, and `productionReady=false` remains the honest status.
## Latest code handoff (2026-11-21, PR #164)

PR [#164](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/164) merged at [552a9aeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/552a9aeb46097d703300475ff21c87ecbffa282c). The Kubernetes conformance evidence parser now validates archived `serverversion.json` and `gitVersion` before comparison, returning stable blocked reasons for malformed evidence. Post-merge automated checks passed; real-VM/PITR remain skipped because no authorized disposable lab is configured. Test17 is unchanged and `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #166)

[PR #166](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/166) merged as [e88b667](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e88b6679829be356710cc88a35e090093054ec8b). Kubernetes supply-chain evidence verification now validates top-level and nested SBOM, vulnerability-scan and provenance document shapes before access, returning stable blocked reasons for malformed evidence. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #168)

[PR #168](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/168) merged as [7b1408a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7b1408a38f830405af52da47143cffa6058068c9). The Kubernetes evidence verifier now validates the trust-policy `keys` inventory before iteration and returns stable `TRUST_KEYS_REQUIRED` for null, empty or non-list inventories. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #170)

[PR #170](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/170) merged as [289c0f2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/289c0f2c37e4ce011e2c1c4827a2646915c3b340). The Kubernetes evidence verifier now requires every signed environment identity to be a non-empty string and returns stable `EVIDENCE_IDENTITIES_INVALID` for malformed entries. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.


## Latest code handoff — PR #172 (2026-11-21)

[PR #172](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/172) merged at [77bdc1d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/77bdc1d1af128f5c98fefec3f6720d74df01b3d7). The Kubernetes evidence verifier now rejects trust-policy key roles and organization metadata unless they are non-empty strings, preserving stable `TRUST_KEY_INVALID` handling. Regression tests cover both malformed trust-key paths. Exact post-merge Kubernetes, Native, Source/Privacy and private-alpha audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520639),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520655),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520708),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959717872).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #174 (2026-11-22)

[PR #174](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/174) merged at [0245997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0245997861b9eb663f261cf0d7bcc5623c4627e1). The Kubernetes supply-chain evidence verifier now rejects CycloneDX SBOM component entries unless each is a JSON object, preserving stable `SBOM_COMPONENT_INVALID` handling. A regression test covers `components: [null]`. Exact post-merge audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222806),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222823),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222792),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964385448).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #176 (2026-11-22)

[PR #176](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/176) merged at [33d8780](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/33d87805b952fcfff1b98ff43e18a60cb041db32). The Kubernetes Trivy-v2 evidence verifier now rejects empty or whitespace-only result targets, preserving stable `VULNERABILITY_RESULT_INVALID` handling. Nullable `Vulnerabilities` fields remain supported; a regression test covers the malformed target. Exact post-merge audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159822),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159864),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159804),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969356902).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.
