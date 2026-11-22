# Masterplan traceability

**Dev.4: full scope remains incomplete.** Partial means code exists, not production qualification.

The [candidate production scope](PRODUCTION-SCOPE.md) classifies every K20 item
as in the proposed first support boundary or explicitly deferred. A deferral is
not completion and does not remove the item from this masterplan; the current
Native qualification contract still treats all 52 entries as blocking.
`release/production-scope.json` is checked against the complete inventory.

The Native Single-Host scope is defined by [PR #203](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/203), merged at `f75845424286c1c8bed6c9ef17d2b172066e6309`. The tagged lab candidate below predates that scope decision and remains non-qualifying; GitHub release metadata reports immutable=false and its assets are unsigned.

The release-tracker handoff contract is enforced by [PR #204](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/204), merged at `83c06425600749418994d34a1f197d4ad64f6d50`; PR #205 synchronizes this roadmap with that code-bearing handoff. No qualification gate is closed by these bookkeeping changes.

The next exact-candidate build is pinned to package-bearing Main code handoff `ec868d03299307b178e68fbbffabd8c211bda814`; documentation-only Main commits may have newer SHAs. No qualification gate is closed until the runner binds and verifies its own `GITHUB_SHA` and artifact digest. The current connector cannot dispatch `ci.yml`, so the live run remains blocked rather than implied.

The current tagged lab candidate is [`v0.2.0-dev.4-test.17`](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17), sourced from `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; GitHub release metadata reports `immutable=false` and its assets are unsigned. This candidate includes the auto-discovery known-hosts replay guard; it does not remove any K20 requirement or change the no-go production decision.

Main contains [PR #122](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/122), merged at `c95511a5f1e1c8ca6aa909b3e69bb21558b00634`, [PR #140](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/140), [PR #143](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/143), [PR #148](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/148), [PR #152](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/152), [PR #154](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/154), [PR #156](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/156) and [PR #158](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/158). The code-bearing handoff commit remains `2ab2ebe5433b938925b4aebd57c84a7939d92a43`; the latest tracker-synchronized Main handoff is `9403d55e2deae30f4c99e889a56cfffbafb0390b`, with this status/roadmap/tracker synchronization following PR #158. PR #148 adds a Native release-contract regression test covering every service stop/disable action and preventing uninstall scripts from deleting persisted state, identities or workloads. PR #152 adds a Kubernetes release-contract regression test covering both recovery/repair systemd templates and preserving their explicit root, token/assets and sandbox boundaries. PR #154 adds hermetic Kubernetes-manager wrapper tests for staged package-root execution and exit-78 fail-closed behavior when Python modules are missing. PR #156 requires the Kubernetes wrapper entrypoint to exist before selecting an installed, staged or source-tree module path and regression-tests incomplete package trees. PR #158 requires the Native `werft-ops` wrapper to find both `werftops/__init__.py` and `werftops/__main__.py` before selecting a module path and regression-tests incomplete package trees. Test17 remains immutable and does not contain PR #140, PR #143, PR #148, PR #152, PR #154, PR #156 or PR #158; publish a new candidate before live testing the updated package. No K20 requirement is removed and the production decision remains no-go.


## Latest code handoff (2026-11-22)

[PR #217](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/217) merged as [ec868d0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ec868d03299307b178e68fbbffabd8c211bda814). Native control startup, resume and local backup now validate both the control and etcd HTTPS endpoints, require matching cluster identities, and reject non-private or malformed listener addresses. Regression tests cover HTTP etcd, cluster-ID mismatch, public listeners and missing listener ports.

Exact PR checks passed: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45063829562), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45063829580) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45063829544). Real-VM and real-PITR jobs remained skipped. This is a native security-boundary handoff only: the tagged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; GitHub release metadata reports `immutable=false` and its assets are unsigned. `productionReady=false` and no qualification gate was closed. The next candidate must be built from `ec868d03299307b178e68fbbffabd8c211bda814` before live evidence can cover this fix.

## K20-001 — Review-Baseline und Ausführungspfade verifizieren

**partial**. Separate Alpha neu gebaut/getestet; private C#-DI nicht erneut ausgeführt.

## K20-002 — ADRs, Invarianten und Threat Model festlegen

**partial**. Architektur-/Threat-Grenzen dokumentiert, kein unabhängiger Review.

## K20-003 — Management auf .NET 10 LTS migrieren

**not-implemented-or-not-executed**. Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen.

## K20-004 — Native-Modul und versionierte Buildgrenzen anlegen

**partial**. Eigenes Go-Modul und Paket/CI vorhanden, Managementintegration fehlt.

## K20-005 — Versioniertes Runtime-Ressourcenmodell definieren

**partial**. Schema2 adds gateway ACLs, ordered heartbeats and restore receipts; explicit offline migration. Bounded model, no full ecosystem parity.

## K20-006 — etcd-State-Adapter und revisionssicheren Watch implementieren

**partial**. etcd-CAS über ein Stateobjekt; kein revisionssicherer Watch.

## K20-007 — Admission, Autorisierung und Idempotenz sichern

**partial**. Admin/Node/Gateway mTLS ACL and negative tests; still no tenant/workspace IAM or independent security review.

## K20-008 — Native-CLI für Apply, Status und Delete liefern

**partial**. CLI Apply/Status/Delete vorhanden; kein echtes Ubuntu-Gate.

## K20-009 — Einmaliges Enrollment und mTLS-Nodeidentität umsetzen

**partial**. Node join credentials plus offline-CA leaf renewal, atomic combined PEM install and real local TLS reload tests. No online enrollment service, full CA or multi-host rotation qualification.

## K20-010 — Agentprotokoll mit Allocation- und Epoch-Verträgen umsetzen

**partial**. Explicit state-schema2 dev.3/dev.4 protocol edge, tested with actual old/new agent executables and real mTLS; Docker/etcd fixtures. No general version guarantee.

## K20-011 — Durables Agentjournal und Replay entwickeln

**partial**. Journal/sequence durable replay and terminal-report rejection; real Docker/host recovery not qualified.

## K20-012 — Echten Container-Lifecycle über containerd integrieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-013 — Nodeinventar und Ressourcenreservierung modellieren

**partial**. Nodekapazität und Reservierungen; keine umfassende Hostdruckmessung.

## K20-014 — Deterministischen Scheduler mit atomarem Binding implementieren

**partial**. Reproduced/fixed stale-readiness retirement defect; lock-owned selective drain and CAS/scope tests. Real Raft/VM qualification remains absent.

## K20-015 — Level-basierten Reconciler und Revisionsstatus implementieren

**partial**. Periodischer Soll-/Ist-Abgleich; kein Watch-/vollständiger Controllervertrag.

## K20-016 — Löschsemantik, Tombstones und Ressourcen-GC absichern

**partial**. Stop/Deletion/Journal; historische State-/Tombstone-GC begrenzt.

## K20-017 — Lokalen CNI-Vertrag und Attachment-Cleanup implementieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-018 — Nodeübergreifendes Netz, IPAM und WireGuard qualifizieren

**partial**. WireGuard/routed Docker bridge preparation/apply code; no live mesh/MTU/firewall tests.

## K20-019 — Default-deny-Policies und Quarantäne einführen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-020 — CoreDNS-Service-Discovery ohne Kubernetes anbinden

**partial**. CoreDNS zone generator and authenticated discovery API; no live CoreDNS/multi-node proof.

## K20-021 — Envoy-Ingress, TLS und reale Verkehrsprüfung integrieren

**partial**. Scoped Go HTTPS ingress with actual local TLS/HTTP route tests. Deliberate alternative to Envoy; no public DNS/VM, ACME, HA edge or traffic qualification.

## K20-022 — Versionierte Secretbereitstellung auf Allocations begrenzen

**partial**. AES-GCM-Versionen, Allocation-ACL und tmpfs-Staging; echte Mountqualifikation fehlt.

## K20-023 — Startup-, Readiness- und Liveness-Semantik testen

**partial**. Readiness freshness unified, repeated observations keep original timestamp; full startup/liveness policy remains incomplete.

## K20-024 — Rolling Update, Drain und Image-Rollback liefern

**partial**. Rolling Update, Drain/Rollback, Pause; reale VM-Gates fehlen.

## K20-025 — Native-RuntimeTarget und Hetzner-Provisionierung integrieren

**partial**. Standalone Hetzner HTTP adapter and intent journal; no live calls or ClusterPilot connector.

## K20-026 — Management-Outbox und Runtime-Statusprojektion implementieren

**not-implemented-or-not-executed**. Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen.

## K20-027 — Native-Workload- und Diagnoseansichten entwickeln

**partial**. Eigenes minimales Dashboard, nicht vollständige Management-UI.

## K20-028 — Management- und Runtime-Berechtigungen negativ prüfen

**partial**. Negative Admin/Node- und Scope-Tests; keine Management-/Multi-Tenant-IAM.

## K20-029 — Drei-Controller-HA und unabhängiges Bootstrap liefern

**partial**. Three-controller kits and install path with TLS etcd peers; no actual quorum tests.

## K20-030 — Metriken, Korrelation und Supportbundle integrieren

**partial**. Gebundene Metriken/Ereignisse, kein vollständiger Support-/Tracepfad.

## K20-031 — Partition- und Quorumverlustverhalten qualifizieren

**partial**. Konservativer Unknown-Zustand; kein echtes Quorum-/Partition-Gate.

## K20-032 — Backup/Restore mit neuer Recovery-Epoch umsetzen

**partial**. Encrypted config/file backups and pgBackRest isolated PITR adapter; real WAL replay test blocked by absent binaries. No full-site DR.

## K20-033 — Signierte Native-Releases und Lieferkettenevidenz aufbauen

**partial**. Paket/Quellcodechecks/Releaseblockade; keine Signaturen/Provenancefreigabe.

## K20-034 — Ubuntu-, RHEL- und root/sudo-Installationsprofile qualifizieren

**partial**. Ubuntu-Setupcode, keine tatsächliche Ubuntu-/RHEL-Qualifikation.

## K20-035 — N/N−1-Protokoll, Canary-Updates und sichere Migration testen

**partial**. Sequential signed worker updater, owned drain, scoped host verification, local Docker/HTTP smoke code, persisted observation/recovery. Command fixtures pass; actual Ubuntu/SSH/Docker and controller-wave qualification NOT done.

## K20-036 — Airgap-Bundle und Offline-Recovery qualifizieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-037 — Deterministischen Zustands- und Nachrichtensimulator erstellen

**partial**. Reale Prozesstests mit Protokollfixtures; kein vollständiger Zustandsraum-Simulator.

## K20-038 — Fault-Injection-Suite auf echten VMs ausführen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-039 — Kapazitäts-, Latenz- und Betriebsvergleich messen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-040 — Externen Sicherheitsreview mit Remediation abschließen

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.

## K20-041 — Read-only Kubernetes-Migrationsassessor entwickeln

**partial**. Offline-JSON-Assessor ohne Werte; kein automatischer Import.

## K20-042 — Parallele Migration und Routing-Rollback proben

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-043 — Zehn Problemgespräche und zwei Designpartner validieren

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.

## K20-044 — Begrenzten bezahlten Designpartner-Pilot durchführen

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.

## K20-045 — Nodegebundene persistente Volumes als eigene Klasse ergänzen

**partial**. Node-bound persistent directories plus encrypted physical file archive/restore, IO locks and lost-ACK receipts. Real container/host/data-loss qualification absent.

## K20-046 — Unabhängige Writer-Fencing-Capability implementieren

**partial**. Native Patroni profile requires a watchdog; no real watchdog/fencing validation and no general orchestrator fencer.

## K20-047 — Einen CSI-Treiber vollständig qualifizieren

**partial**. Hetzner hcloud-csi 2.24.2 ist als enger Kandidat mit festem Chart-Digest,
k0s-Kubelet-Pfad und konservativer `Retain`-StorageClass ausgewählt. Sechs OCI-Index-
Digests und ein reproduzierbarer, hashgebundener Helm-Render sind geprüft. Signaturen,
Vulnerability-Clearance sowie reale Provision/Attach/Mount/Expansion/Failure/Backup/
Restore-Qualifikation fehlen. Ein statischer Fail-closed-Audit bindet RBAC, einen dedizierten
Node-ServiceAccount ohne automatischen Token-Mount, privilegierten Node-Treiber, HostPaths
und MountPropagation. `RuntimeDefault` ist auf Pod-Ebene für die nicht privilegierten
Container gebunden; der privilegierte Node-Treiber bleibt eine explizite Ausnahme.
Die immutable linux/amd64 Manifest-/Config-Kette ist zusätzlich geprüft: Alle sechs
Images verwenden explizit oder implizit root, und das Upstream-Chart bietet keine
SecurityContext-Werte je Container. Pod-weites `runAsNonRoot` bleibt deshalb bewusst
blockiert. Ein Post-Renderer akzeptiert nur den exakten geprüften Eingangs-Hash, macht
alle Root-Identitäten explizit und erzwingt für die sieben nicht privilegierten
Containerinstanzen `allowPrivilegeEscalation: false`, den Drop aller Capabilities und
`RuntimeDefault` auf Container-Ebene. Der privilegierte Node-Treiber bleibt die eng
gebundene Ausnahme. Alle acht gerenderten Container-Instanzen besitzen fail-closed
geprüfte CPU-/Memory-Requests und -Limits als konservative Startbudgets. Deren Eignung
ist nicht gemessen; echte Last-, Soak- und Laufzeittests sowie non-root-fähige
Container-Identitäten bleiben offen. Keine Produktionsfreigabe.

## K20-048 — Ein Stateful-Profil mit Replikation und Restore freigeben

**partial**. Native PostgreSQL17/Patroni4 synchronous HA profile and pgBackRest PITR adapter implemented; no actual database/HA/replay qualification.

## K20-049 — Jobs und CronJobs mit expliziter Retry-Semantik entwickeln

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-050 — Regelbasiertes App- und Node-Autoscaling ergänzen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-051 — Ein GPU-Workloadprofil qualifizieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-052 — Enge GA anhand der Freigabegates entscheiden

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.



## Latest code handoff (2026-11-21)

PR #160 is merged at [a04b0b4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a04b0b4c9db7f4f0aa5e408446b45cb5fe25dd1a). It hardens the Kubernetes-manager plan parser against valid non-object JSON and adds a regression test for the stable fail-closed response. This does not alter either component version, the immutable test17 candidate, or any production gate. Post-merge required checks passed; the privileged live jobs remain skipped. The next evidence-bearing step is an expressly authorized disposable Ubuntu/k0s run, not another readiness claim.


## Latest code handoff (2026-11-21, PR #162)

PR #162 merged at [2ad8daeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2ad8daebed99f8ea2b6735f9f626e500666cd694). It hardens Kubernetes-manager wrapper resolution against incomplete Python package trees and adds a regression test for a missing package marker. Required automated checks passed; privileged real-VM/PITR jobs remain skipped. This does not alter component versions, the immutable test17 candidate, or any production qualification gate. The next evidence-bearing step remains an expressly authorized disposable Ubuntu/k0s run.
## Latest code handoff (2026-11-21, PR #164)

PR #164 merged at [552a9aeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/552a9aeb46097d703300475ff21c87ecbffa282c). The Kubernetes conformance evidence parser now validates archived `serverversion.json` and `gitVersion` before comparison, returning stable blocked reasons for malformed evidence. Post-merge automated checks passed; real-VM/PITR remain skipped because no authorized disposable lab is configured. Test17 is unchanged and `productionReady=false` remains the honest status. The next evidence-bearing step is a new immutable candidate from this package-bearing main commit, followed by an expressly authorized disposable Ubuntu/k0s run.

## Code handoff — PR #166 (2026-11-21)

PR [#166](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/166) merged at [e88b667](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e88b6679829be356710cc88a35e090093054ec8b). The Kubernetes evidence verifier now fails closed for malformed top-level and nested SBOM, vulnerability-scan and provenance documents, with regression tests and green post-merge checks.

The next evidence step is a new immutable candidate built from `e88b667`. The existing `v0.2.0-dev.4-test.17` candidate remains unchanged and unqualified. Live Ubuntu/k0s, recovery, HA, load/soak, supply-chain signing/provenance and independent-review gates remain open until reproduced on authorized disposable infrastructure.

## Code handoff — PR #168 (2026-11-21)

PR [#168](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/168) merged at [7b1408a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7b1408a38f830405af52da47143cffa6058068c9). The Kubernetes evidence verifier now fails closed when the trust-policy `keys` inventory is null, empty or not a list, with regression coverage for the stable `TRUST_KEYS_REQUIRED` result.

The next evidence step is a new immutable candidate built from `7b1408a`. The existing `v0.2.0-dev.4-test.17` candidate remains unchanged and unqualified. Live Ubuntu/k0s, recovery, HA, load/soak, signed supply-chain provenance and independent-review gates remain open until reproduced on authorized disposable infrastructure.

## Code handoff — PR #170 (2026-11-21)

PR [#170](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/170) merged at [289c0f2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/289c0f2c37e4ce011e2c1c4827a2646915c3b340). The Kubernetes evidence verifier now fails closed when signed environment identities are not non-empty strings, with regression coverage for `EVIDENCE_IDENTITIES_INVALID`.

The next evidence step is a new immutable candidate built from `289c0f2`. The existing `v0.2.0-dev.4-test.17` candidate remains unchanged and unqualified. Live Ubuntu/k0s, recovery, HA, load/soak, signed supply-chain provenance and independent-review gates remain open until reproduced on authorized disposable infrastructure.


## Code handoff — PR #172 (2026-11-21)

[PR #172](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/172) merged as [77bdc1d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/77bdc1d1af128f5c98fefec3f6720d74df01b3d7). The Kubernetes evidence verifier now fails closed when trust-policy key roles or organization metadata are not non-empty strings, preserving the stable `TRUST_KEY_INVALID` reason. Two regression tests cover malformed roles and organization values before gate authorization and trust-separation checks.

Exact post-merge checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520639), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520655), [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520708) and [private alpha audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959717872). This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.


## Code handoff — PR #174 (2026-11-22)

[PR #174](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/174) merged as [0245997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0245997861b9eb663f261cf0d7bcc5623c4627e1). The Kubernetes supply-chain evidence verifier now rejects non-object entries in CycloneDX SBOM component arrays with stable `SBOM_COMPONENT_INVALID` handling and regression coverage.

Exact post-merge checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222806), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222823), [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222792) and [private alpha audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964385448). This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.


## Code handoff — PR #176 (2026-11-22)

[PR #176](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/176) merged as [33d8780](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/33d87805b952fcfff1b98ff43e18a60cb041db32). The Kubernetes Trivy-v2 evidence verifier now fails closed for empty or whitespace-only result targets with stable `VULNERABILITY_RESULT_INVALID` handling and regression coverage. Nullable `Vulnerabilities` fields remain supported.

Exact post-merge checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159822), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159864), [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159804) and [private alpha audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969356902). This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.

## Code handoff — PR #179 (2026-11-22)

[PR #179](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/179) merged as [6b44496](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6b44496ed69a0feb25e11e2ba0ea358802dc8945). The Kubernetes Trivy-v2 evidence verifier now accepts only a list or explicit null for each `Vulnerabilities` inventory; boolean, numeric and other scalar values fail closed with stable `VULNERABILITY_RESULT_INVALID` handling. Regression coverage protects the boolean case while preserving nullable Trivy output.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221312), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221342) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221313); real-VM and real-PITR remained skipped. This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.



## Code handoff — PR #181 (2026-11-22)

[PR #181](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/181) merged at [f38d33c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f38d33c77394d321ec8229033dda5e48299d16cf). The Kubernetes CycloneDX evidence verifier now requires every component entry to contain a non-empty string `name`; empty or malformed entries fail closed with stable `SBOM_COMPONENT_INVALID` handling. A regression test protects the empty-object path.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393959), [Native runtime/package, including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393878) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393890). Real-VM and real-PITR jobs were skipped because no authorized disposable lab is configured.

This is a code-quality/security-boundary handoff only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false`, the decision remains `no-go`, and no live qualification gate was closed. A new immutable candidate is required before any live evidence can cover this merge.

## Code handoff — PR #183 (2026-11-22)

[PR #183](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/183) merged as [8c0bc4a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8c0bc4aa21575891eb782ad6943bfe42c24cb4d6). The Kubernetes Trivy-v2 evidence verifier now requires each LOW/MEDIUM finding to carry a non-empty string `VulnerabilityID`; malformed findings fail closed with stable `VULNERABILITY_FINDING_INVALID` handling. A regression test protects a nameless LOW finding.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729213), [Native runtime/package, including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729235) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729267). Real-VM and real-PITR jobs were skipped because no authorized disposable lab is configured.

This is a code-quality/security-boundary handoff only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false`, the decision remains `no-go`, and no live qualification gate was closed. A new immutable candidate is required before live evidence can cover this merge.

## Code handoff — PR #185 (2026-11-22)

[PR #185](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/185) merged as [3cfe2e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3cfe2e9f25b68cce70a8e9684d8dd4dd957c8fa8). The Kubernetes release-candidate verifier now requires `sourceRepository` to be a canonical public GitHub repository URL, with an optional `.git` suffix; truncated identities fail closed with stable `SOURCE_REPOSITORY_INVALID` handling. A regression test protects the malformed URL path.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036663), [Native runtime/package, including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036674) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036662). Real-VM and real-PITR jobs were skipped because no authorized disposable lab is configured.

This is a code-quality/security-boundary handoff only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false`, the decision remains `no-go`, and no live qualification gate was closed. A new immutable candidate is required before live evidence can cover this merge.

## Code handoff — PR #187 (2026-11-22)

[PR #187](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/187) merged at [1954916](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/19549167b5a18c1e741d1603aaa990a67e5bbb11). The Kubernetes SLSA-provenance parser now validates every `resolvedDependencies` material: URI must be a non-empty string, the digest object must be non-empty, and every digest value must be a non-empty string. Malformed materials fail closed with `PROVENANCE_DEPENDENCIES_INVALID`; a regression test covers empty URI/digest data.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447134) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447123). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a fail-closed evidence-shape hardening only. It does not establish signed provenance, vulnerability clearance or production qualification. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #189 (2026-11-22)

[PR #189](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/189) merged at [93b0cb3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/93b0cb3672cd6889114e2e6f7b5e358057979fdf). The Kubernetes evidence verifier now rejects whitespace-only `builderId` values with stable `BUILD_IDENTITY_REQUIRED` handling; a regression test protects the fail-closed identity boundary.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512976), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512956) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512896). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow evidence-shape hardening only. It does not establish provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #191 (2026-11-22)

[PR #191](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/191) merged at [94b5110](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/94b51103edeaf16e1e381e5acac4232bf2ac58cc). The Kubernetes SLSA-provenance parser now rejects empty or whitespace-only digest keys in `resolvedDependencies` entries with stable `PROVENANCE_DEPENDENCIES_INVALID` handling; a regression test covers the malformed digest-key shape.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517149) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517249). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow evidence-shape hardening only. It does not establish signed provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #193 (2026-11-22)

[PR #193](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/193) merged at [e660826](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e66082608f67f4f51d996f86afc1ce94652b455d). The Kubernetes evidence verifier now rejects candidate `builderId` values with leading or trailing whitespace using the stable `BUILD_IDENTITY_REQUIRED` contract; a regression test covers the non-canonical identity shape.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520825), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520832) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520854). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow evidence-identity hardening only. It does not establish signed provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #195 (2026-11-22)

[PR #195](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/195) merged at [c587354](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c58735426626ee71dc9755fc3a38a6c7edb6c740). The Kubernetes evidence verifier now requires trust-policy `organization` identifiers to be non-empty and canonically free of leading or trailing whitespace; malformed identities fail closed with `TRUST_KEY_INVALID`. A regression test covers the boundary.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532273), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532243) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532236). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow trust-identity hardening only. It does not establish signed provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #197 (2026-11-22)

[PR #197](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/197) merged at [71f1dfd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/71f1dfddc2be51ad6a1c54371cac4339c9910167). The production-tracker validator now requires non-empty string lists for `nextAction.blockers`, `nextAction.successCriteria` and every workstream's `requiredGateFamilies`; the previous empty-list `all([])` acceptance is closed with regression tests.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865245), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865193) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865239). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow release-tracker validation hardening only. It does not establish live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Code handoff — PR #199 (2026-11-22)

[PR #199](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/199) merged at [f532b26](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f532b264a9f8bcc20ce26bfe2da6e4ab4debcc9d). The production-tracker validator now rejects empty or whitespace-only decision evidence lists, rollback contracts, next-action evidence strings and gate-family strings. Blocked workstreams also reject scalar, object or blank-entry blocker fields with stable `TRACKER_BLOCKERS_INVALID` handling; regression tests cover the malformed shapes.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092826), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092830) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092833). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is a narrow release-tracker validation hardening only. It does not establish live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Code handoff — PR #201 (2026-11-22)

[PR #201](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/201) merged at [a768d0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a768d0e304bc7c28ca8f3da7732a179e504001e6). The production-tracker validator now requires non-empty `nextAction.summary` and `nextAction.nextStep` strings, with regression coverage for missing actionable text. This closes a fail-open shape where a blocked release handoff could omit the operator-facing next step.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736383), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736359) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736350). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is a narrow release-tracker validation hardening only. It does not establish live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Code handoff — PR #209 (2026-11-22)

[PR #209](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/209) merged at [fe052af](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fe052af52ab80509f325b9ebee8338649f49ecdd). The Native API mTLS identity boundary now uses the injected UTC clock for certificate validity, with regression coverage for an out-of-window certificate. Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904516), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904485) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904486); real-VM and real-PITR remain skipped. This is a code-quality/security-boundary handoff only; the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed. The next evidence step is a new immutable candidate from `fe052af52ab80509f325b9ebee8338649f49ecdd`, followed by the scoped Ubuntu single-host run and remaining backup/restore, upgrade/rollback, bounded soak and signing gates.


## Code handoff — PR #211 (2026-11-22)

[PR #211](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/211) merged as [0a785a8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0a785a85435c6796a34cadd24d66e7c1256f553c). The ingress Gateway now evaluates edge TLS leaf validity through its injected clock, with regression coverage for an out-of-window certificate. Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437255), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437247) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437285); real-VM and real-PITR were skipped. This is a code-quality/security-boundary handoff only; the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed. The next evidence step is a new immutable candidate from `0a785a85435c6796a34cadd24d66e7c1256f553c`, followed by the scoped Ubuntu single-host run and remaining backup/restore, upgrade/rollback, bounded soak and signing gates.


## Code handoff — PR #213 (2026-11-22)

[PR #213](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/213) merged as [ea83bb6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea83bb618edd82586a269930f388a66e04ade566). The Native agent now restores the allocation ID when an engine returns a zero report on failure, with regression coverage for the strict heartbeat identity contract. Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874344), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874104) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874099); real-VM and real-PITR were skipped. This is a code-quality/reliability handoff only; the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed. The next evidence step is a new immutable candidate from `ea83bb618edd82586a269930f388a66e04ade566`, followed by the scoped Ubuntu single-host run and remaining backup/restore, upgrade/rollback, bounded soak and signing gates.