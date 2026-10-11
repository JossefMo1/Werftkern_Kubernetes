# Produktstatus — 0.2.0-dev.1

**Status: EXPERIMENTELL / NOT_PRODUCTION_READY.** Eigenständige Quellcodeweiterentwicklung,
keine vollständige Umsetzung des ursprünglichen Masterplans und keine Remote-Veröffentlichung.

## Implementierter und lokal getesteter Mechanismus

Scheduler/Reconciler mit zentralem atomarem etcd-State-Update; mTLS-API; eigenes Nodejournal;
Docker-HTTP-Adapter; Digest-/Resource-/Ownership-Guards; Ubuntu-Paket und Setup;
Deployment, Skalierung, Rollout, Rollback, Pause/Resume, Drain/Delete und Readiness;
versionierte verschlüsselte Secrets und autorisierte tmpfs-Materialisierung;
verschlüsselte logische Backups und pausierter Import in neues Cluster;
gebundene Metriken, lesender JSON-Migrationsassessor und lokales Dashboard.

Code vorhanden bedeutet nicht auf Ubuntu freigegeben. Ausgeführte Tests stehen im
aktuellen `docs/validation/TEST-REPORT.md`, nicht in alten Alpha1-Berichten.

## Offene implementierungsseitige Lücken

- Direkter containerd-Adapter, CNI/IPAM/WireGuard, Default-deny-Netzwerk, CoreDNS und Envoy.
- Mehrere Controller/etcd-Mitglieder, Leader-/Quorumqualifikation, echte HA und Remote-Recovery.
- Gültigkeits-/Rotationsautomatik für Zertifikate und Vault-Masterkey, kurzlebiges echtes Enrollment.
- Vollständige Startup-/Liveness-/Backoff-Semantik, private Registryauth, Hostdruckmessung.
- Cloud-VM-Provisionierung, ClusterPilot-Management-Outbox, Organisations-/Workspace-IAM.
- Physische Backups, Volumes/CSI, unabhängiges Writer-Fencing und Datenbankprofile.
- Jobs/CronJobs, Autoscaling/GPU, vollständiges Airgap, kontrollierte Produkt-Upgrades.
- Signierte Veröffentlichungen mit verifizierter Build-/Test-/Review-Provenance.

## Nicht nachgewiesen

Reale Ubuntu24.04-Paketinstallation, echte Docker-/etcd-Integration und systemd/tmpfs-Reboot;
Multi-VM-Netzwerk; HA-/Partitionstests; Host-zu-Host-Restore; Release-Upgrades; Langzeit-/Lasttests;
abhängigkeitsbezogene Schwachstellenfreigabe; unabhängiger Securityreview; Kundensupport-GA.

Der Autorentestsandbox ist Debian, enthält Go1.23.2, aber keine verwendbaren Docker-/etcd-/
Ubuntu-VM-Umgebungen. Die vorbereitete CI verwendet Go1.27.1. Ein lokaler Build mit älterem
Compiler wird explizit als unsigniertes, unqualifiziertes Laborartefakt ausgewiesen.

## Feste Grenzen

Ein Controller, ein etcd-Mitglied. Ein aggregierter Statewert mit 900.000 Bytes Limit,
maximal20 Nodes,50 Workloads,200 Allocations; Replikate maximal20 pro Workload.
Diese Grenzen sind Schutzgrenzen, **keine vermessene Kapazitätszusage**.
Bekannte zustandslose Anwendungen in einem Vertrauensbereich. Kein hostile Multi-Tenancy.
Private Hostports statt virtueller Service-IP. Unbekannte Nodes werden nicht automatisch ersetzt.

## Veröffentlichung versus Produktion

Die Apache-2.0-Quellen können nach Eigentümerprüfung als experimentelles Projekt veröffentlicht
werden. Das private ClusterPilot wird dadurch weder automatisch geöffnet noch verändert.
Die vollständige Produktion bleibt durch `release/qualification.json` blockiert.
