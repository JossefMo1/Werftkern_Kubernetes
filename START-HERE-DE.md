# Werftkern — hier beginnen

**Kubernetes-Pfad: `werft-kube 0.1.0-dev.3`.** Er verwendet k0s/Kubernetes und ist nicht
die separate Native-Runtime. Start: `docs/kubernetes/README-DE.md`, aktueller
Testbericht: `docs/kubernetes/DEV3-TEST-REPORT.md`, Status: `release/kubernetes-readiness.json`.
Beide Pfade sind **NOT_PRODUCTION_READY**. Nur isolierte Testumgebungen; kein automatischer Dienststart.

## Separate Native-Runtime (unverändert)

Eigenständig installierbares Open-Source-Projekt, abgeleitet aus ClusterPilot Runtime.
Das private ClusterPilot-Produkt wird weder benötigt noch veröffentlicht.

**0.2.0-dev.4 · Schema 2 · NOT_PRODUCTION_READY.**
Der vollständige Masterplan ist nicht umgesetzt. Bestehende HA-, Cloud-, Datenbank-,
Netzwerk- und Recoveryintegrationen sind noch nicht auf echten Mehrhostsystemen qualifiziert.

Neu: abgesicherte Worker-Updatewellen, nodebezogener Wartungszugriff, expliziter
Agentübergang dev.3→dev.4 und Korrektur eines reproduzierten Readiness-/Rolloutfehlers.
Der Kompatibilitätstest startet beide echten Agent-Binaries mit demselben Journal;
Docker und etcd sind dort ausdrücklich Testadapter.

Zuerst `docs/STATUS.md` und `docs/validation/TEST-REPORT.md` lesen.
Für eine frische Ubuntu-Test-VM: `docs/INSTALL-UBUNTU-DE.md`.
Für Bestandscluster: `docs/WORKER-ROLLOUT.md` und `docs/UPGRADE.md`.
Für dev.1 vor jedem Versionswechsel: `docs/SCHEMA-MIGRATION.md`.

Eine einzelne dev.4-Controllerinstanz neben alten Controllern ist keine abgeschlossene
Migration. Workerwellen beginnen erst nach direkter Prüfung sämtlicher konfigurierter
Controller auf dev.4. Die Orchestrierung dieser gesamten Controllerumstellung bleibt
separat und nicht qualifiziert. Gebundene aktive lokale Volumes blockieren den Workerdrain.

Ein mitgeliefertes `.deb` ist unsigniert, Go1.23.2-Laborbuild und nur für eine wegwerfbare
Test-VM. Nicht auf Kundensystemen einsetzen; aktuelle Toolchain, Signaturen und echte
Ubuntu-/Cluster-/Securitytests fehlen. Keine öffentliche Produktionsfreigabe.

Alle Ausgaben einschließlich früherer Historie sind vor GitHub-Veröffentlichung auf
Rechte und vertrauliche Daten zu prüfen (`docs/PUBLISHING.md`). Das Bundle enthält nur
die eigene Projektgeschichte, kein privates ClusterPilot-Repository.
