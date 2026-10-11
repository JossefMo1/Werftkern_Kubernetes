# Masterplan traceability

**Dev.4: full scope remains incomplete.** Partial means code exists, not production qualification.

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

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

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
