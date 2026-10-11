# Öffentliche Roadmap und Abgleich mit dem Masterplan

52 ursprüngliche Plan-IDs; **keine erfundenen GitHub-Issuenummern, keine als abgeschlossen behaupteten Tasks**.
Der private Masterplan mit Geschäftsplanung ist nicht Teil dieses öffentlichen Quellcodesnapshots.
Ein vollständiger Task braucht seine ursprünglichen Negativ-, Integrations- und Abnahmebedingungen.

| Plan-ID | Aufgabe | Ist-Stand dieser Lieferung |
|---|---|---|
| K20-001 | Review-Baseline und Ausführungspfade verifizieren | Separate Alpha neu gebaut/getestet; private C#-DI nicht erneut ausgeführt. |
| K20-002 | ADRs, Invarianten und Threat Model festlegen | Architektur-/Threat-Grenzen dokumentiert, kein unabhängiger Review. |
| K20-003 | Management auf .NET 10 LTS migrieren | Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen. |
| K20-004 | Native-Modul und versionierte Buildgrenzen anlegen | Eigenes Go-Modul und Paket/CI vorhanden, Managementintegration fehlt. |
| K20-005 | Versioniertes Runtime-Ressourcenmodell definieren | Begrenztes Workload/Node/Allocation/Secret-Modell vorhanden. |
| K20-006 | etcd-State-Adapter und revisionssicheren Watch implementieren | etcd-CAS über ein Stateobjekt; kein revisionssicherer Watch. |
| K20-007 | Admission, Autorisierung und Idempotenz sichern | Admin/Node-mTLS, Idempotenz, CAS; kein Tenant-/Workspace-IAM. |
| K20-008 | Native-CLI für Apply, Status und Delete liefern | CLI Apply/Status/Delete vorhanden; kein echtes Ubuntu-Gate. |
| K20-009 | Einmaliges Enrollment und mTLS-Nodeidentität umsetzen | Signierte Nodebeitrittsdatei; keine kurzlebige Enrollment-/Rotationsinfrastruktur. |
| K20-010 | Agentprotokoll mit Allocation- und Epoch-Verträgen umsetzen | HTTP-JSON und monotone Snapshots; kein gRPC-/vollständiger Epochvertrag. |
| K20-011 | Durables Agentjournal und Replay entwickeln | Journal, Eigentum, Replay und Widerspruchstests vorhanden. |
| K20-012 | Echten Container-Lifecycle über containerd integrieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-013 | Nodeinventar und Ressourcenreservierung modellieren | Nodekapazität und Reservierungen; keine umfassende Hostdruckmessung. |
| K20-014 | Deterministischen Scheduler mit atomarem Binding implementieren | Deterministische atomare Planung mit zentralem State-CAS; keine HA-Wahl. |
| K20-015 | Level-basierten Reconciler und Revisionsstatus implementieren | Periodischer Soll-/Ist-Abgleich; kein Watch-/vollständiger Controllervertrag. |
| K20-016 | Löschsemantik, Tombstones und Ressourcen-GC absichern | Stop/Deletion/Journal; historische State-/Tombstone-GC begrenzt. |
| K20-017 | Lokalen CNI-Vertrag und Attachment-Cleanup implementieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-018 | Nodeübergreifendes Netz, IPAM und WireGuard qualifizieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-019 | Default-deny-Policies und Quarantäne einführen | Nicht implementiert bzw. nicht durchgeführt. |
| K20-020 | CoreDNS-Service-Discovery ohne Kubernetes anbinden | Nicht implementiert bzw. nicht durchgeführt. |
| K20-021 | Envoy-Ingress, TLS und reale Verkehrsprüfung integrieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-022 | Versionierte Secretbereitstellung auf Allocations begrenzen | AES-GCM-Versionen, Allocation-ACL und tmpfs-Staging; echte Mountqualifikation fehlt. |
| K20-023 | Startup-, Readiness- und Liveness-Semantik testen | HTTP-Readiness und Beobachtungsalter; Startup/Liveness nicht vollständig. |
| K20-024 | Rolling Update, Drain und Image-Rollback liefern | Rolling Update, Drain/Rollback, Pause; reale VM-Gates fehlen. |
| K20-025 | Native-RuntimeTarget und Hetzner-Provisionierung integrieren | Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen. |
| K20-026 | Management-Outbox und Runtime-Statusprojektion implementieren | Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen. |
| K20-027 | Native-Workload- und Diagnoseansichten entwickeln | Eigenes minimales Dashboard, nicht vollständige Management-UI. |
| K20-028 | Management- und Runtime-Berechtigungen negativ prüfen | Negative Admin/Node- und Scope-Tests; keine Management-/Multi-Tenant-IAM. |
| K20-029 | Drei-Controller-HA und unabhängiges Bootstrap liefern | Nicht implementiert bzw. nicht durchgeführt. |
| K20-030 | Metriken, Korrelation und Supportbundle integrieren | Gebundene Metriken/Ereignisse, kein vollständiger Support-/Tracepfad. |
| K20-031 | Partition- und Quorumverlustverhalten qualifizieren | Konservativer Unknown-Zustand; kein echtes Quorum-/Partition-Gate. |
| K20-032 | Backup/Restore mit neuer Recovery-Epoch umsetzen | Verschlüsseltes logisches Backup/neue UID/pausierter Import; kein physisches DR. |
| K20-033 | Signierte Native-Releases und Lieferkettenevidenz aufbauen | Paket/Quellcodechecks/Releaseblockade; keine Signaturen/Provenancefreigabe. |
| K20-034 | Ubuntu-, RHEL- und root/sudo-Installationsprofile qualifizieren | Ubuntu-Setupcode, keine tatsächliche Ubuntu-/RHEL-Qualifikation. |
| K20-035 | N/N−1-Protokoll, Canary-Updates und sichere Migration testen | Nicht implementiert bzw. nicht durchgeführt. |
| K20-036 | Airgap-Bundle und Offline-Recovery qualifizieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-037 | Deterministischen Zustands- und Nachrichtensimulator erstellen | Reale Prozesstests mit Protokollfixtures; kein vollständiger Zustandsraum-Simulator. |
| K20-038 | Fault-Injection-Suite auf echten VMs ausführen | Nicht implementiert bzw. nicht durchgeführt. |
| K20-039 | Kapazitäts-, Latenz- und Betriebsvergleich messen | Nicht implementiert bzw. nicht durchgeführt. |
| K20-040 | Externen Sicherheitsreview mit Remediation abschließen | Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt. |
| K20-041 | Read-only Kubernetes-Migrationsassessor entwickeln | Offline-JSON-Assessor ohne Werte; kein automatischer Import. |
| K20-042 | Parallele Migration und Routing-Rollback proben | Nicht implementiert bzw. nicht durchgeführt. |
| K20-043 | Zehn Problemgespräche und zwei Designpartner validieren | Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt. |
| K20-044 | Begrenzten bezahlten Designpartner-Pilot durchführen | Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt. |
| K20-045 | Nodegebundene persistente Volumes als eigene Klasse ergänzen | Nicht implementiert bzw. nicht durchgeführt. |
| K20-046 | Unabhängige Writer-Fencing-Capability implementieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-047 | Einen CSI-Treiber vollständig qualifizieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-048 | Ein Stateful-Profil mit Replikation und Restore freigeben | Nicht implementiert bzw. nicht durchgeführt. |
| K20-049 | Jobs und CronJobs mit expliziter Retry-Semantik entwickeln | Nicht implementiert bzw. nicht durchgeführt. |
| K20-050 | Regelbasiertes App- und Node-Autoscaling ergänzen | Nicht implementiert bzw. nicht durchgeführt. |
| K20-051 | Ein GPU-Workloadprofil qualifizieren | Nicht implementiert bzw. nicht durchgeführt. |
| K20-052 | Enge GA anhand der Freigabegates entscheiden | Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt. |

Priorität: echte Single-Node-Qualifikation vor größerem Funktionsumfang; danach direktes Runtime-/Netzprofil, Multi-Node und Fehler-/Recoveryprüfung. Public Alpha ist keine GA.
