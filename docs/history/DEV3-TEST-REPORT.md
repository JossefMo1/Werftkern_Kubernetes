# Werftkern 0.2.0-dev.3 — tatsächlicher Entwicklungs- und Teststand

**NOT_PRODUCTION_READY · fullMasterplanComplete=false.**
Stand: 2026-09-25T11:55:11.010162+00:00. Ausgangscommit: `e30985e1367a6ac4d692fa05b999f6fc80bddd4f`.
Finaler Git-Commit steht im separaten Liefermanifest (keine selbstreferenzielle ID).

## Identität

StateSchema **2**, Version `0.2.0-dev.3`. 195 Dateien im kanonischen Quellinventar;
SHA256 `afa67d384fd5cfbe6d49fa8746f9b524f6cfc4eefd1930158c7df964fe6e4c3a`. Inventar enthält Pfad, Bytezahl, SHA256; Git, Builds, Evidence, Caches und
docs/validation sind ausgeschlossen. Toolchain hier: Go1.23.2 auf Debian13, root im
beschränkten Authoringcontainer. Vorbereitete CI: Go1.27.1, NICHT hier ausgeführt.

## Tatsächliche Prüfungen

| Prüfung | Ergebnis | Aussagegrenze |
|---|---|---|
| Vollständige Go-Race-Suite ohne Testcache | 164 Haupttest-, 99 Untertestergebnisse, 22 Pakete; 0 fehlgeschlagen/übersprungen | Inklusive Prozesshelfer/Fuzzseeds; nicht so viele unabhängige E2E-Szenarien |
| Go vet | bestanden | Kein unabhängiger Sicherheitsreview |
| Python-Betriebsbefehle | 42 Tests bestanden | Datenbank/Provider/Hostantworten ausdrücklich Testadapter |
| Release-/Quellcodeguards | 7 bestanden | Mechanische Konsistenz, keine Authentifizierung externer Freigaben |
| Browser-DOM | 11 Chromium-Prüfungen bestanden | Synthetische In-Memory-API, keine Browser-Livecluster-Verbindung |
| PKI / OpenSSL | Tatsächliche Schlüssel, separate CAs, Signaturen und Konfigurationskits geprüft | Temporäre lokale Testdateien, keine Datenbank-/Hostinstallation |
| Live-Leafwechsel | Client- und Serverzertifikate unter echter lokaler TLS-Kommunikation gewechselt | Keine CA-/Mehrhostrotation oder sofortige Sessionrevokation |
| Certificate-CLI | Bundle, Renewal, Compare-and-Swap-Installation, Wiederholung und Rechte geprüft | Temporäre Test-PKI, keine produktiven Schlüssel |
| Physische Archive / Root-CLI | Übernommene Datei-/TLS-/lost-ACK-Szenarien erneut bestanden | Docker/etcd-Fixtures, keine echte Container-/Volumeisolierung |
| Timeout-Kindprozesse | Echte lokale Prozessgruppen beendet, keine verspäteten Testschreibvorgänge | Kein Beweis für komplette Service-/Hostrecovery |
| JSON-Fuzzing | 110123 Ausführungen, bestanden | Kurzkampagne, keine umfassende Parser-/Securityqualifikation |
| Syntax / Quell-Lint | Python, JavaScript, Shell, Workflow-YAML und begrenzter Publikationsscan bestanden | Keine Workflow-/Paketinstallation, kein vollständiger Lizenz-/Secretsaudit |
| Echte etcd-Tests | **2 Tests fehlgeschlagen/BLOCKED: Binary fehlt** | Nicht bestanden, keine stillen Skips |
| Echte PostgreSQL-/pgBackRest-PITR | **BLOCKED/Exit3: Binaries fehlen** | Keine tatsächliche SQL-/WAL-Recovery durchgeführt |

## Konkrete Änderungen und Nachweisgrenzen

**Updatefehler reproduziert:** Der unveränderte dev.2-Updater meldet im neuen Regressionstest
`completed-app-validation-required`, statt vor Entsperrung auf Runtimeprüfung zu warten.
`reproduced-dev2-update-unlock.log` enthält den erwarteten Fehler. Neuer apply/recover-Pfad
bleibt eingefroren. Finish prüft alle konfigurierten Controller DIREKT, Versions-/Schema-/
Clusteridentität, drei fortschreitende frische Heartbeats und passende ready Allocations.
Ein verlorenes Entsperr-ACK wird durch Beobachtung abgeglichen; neue fremde Locks werden
nicht gelöst. Ein Status-Read allein genügt nicht. Tatsächlicher dpkg-/systemd-Updatepfad
ist damit nicht real qualifiziert; Workerwellen fehlen.

**Datenbank-HA:** Native drei-Host-Profile mit PostgreSQL17, Patroni4, eigenem etcd-DCS,
getrennten CAs, strikter synchroner Replikation, verpflichtendem Watchdog, Datenidentitäts-
prüfung und geplanten Switchover-Journalen. Tatsächlich getestet: OpenSSL-Kits und
Konfigurationsinvarianten, Split-Brain-/Stale-/Policy-/lost-ACK-Antworten als Fixtures.
Kein Patroni-/PostgreSQL-/Watchdogprozess gestartet. Keine generische Writer-Fencer-
Implementierung im Scheduler. Datenbank ist separat nativ, nicht im Workload-Wizard.

**PITR:** Ausführbarer pgBackRest-Adapter mit privater verschlüsselter POSIX-Repository-
konfiguration, gesperrten ENV-/Include-Overrides, exakten Backupset-/System-IDs, sicheren
Zielpfaden und persistenten Intents. Restore überschreibt kein vorhandenes Ziel und
startet/promotet keinen Server. SQL-Prüfung verlangt tatsächlich pausiertes WAL-Replay;
hier ausschließlich Befehlsfixtures. No-mock-Realtest geschrieben und gestartet, aber
an fehlenden Dependencies gescheitert. Tablespaces nach Backupbeginn und alte PG-
Konfiguration erfordern echte isolierte Recoveryumgebung; Pfadprüfungen beweisen diese
Isolation nicht. WAL-Archiv-/systemd-/Repositoryanbindung für Patroni bleibt Betreiber-
konfiguration, nicht automatisierter sicherheitsqualifizierter Ein-Klick-Betrieb.

**Leaf-Rotation:** Atomarer gemeinsamer PEM-Wechsel, aktueller Vertrauens-/Profilvergleich,
kein gecachter unsicherer Fallback. Reale TLS-Tests zeigen neue Zertifikate nach Wechsel.
Erfordert einmalige Konfigurationsumstellung; alter Zweidateipfad bleibt statisch. Kein
Online-CA-Dienst, keine vollständige CA-Rotation; Anti-Rollback nur pro Prozess und
bestehende TLS-Verbindungen behalten ihre alte Identität. Keine universelle Revokation.

**Parser/Prozesse:** Doppelte und Unicode-casefold-kollidierende JSON-Member, zu tiefe
Dokumente, unbekannte typisierte Felder und Nicht-JSON-Konstanten werden abgewiesen.
Die engere Membernamensregel gilt auch für dynamische Maps. Timeouts beenden ausschließlich
die für den jeweiligen Aufruf neu erzeugte lokale Prozessgruppe, nicht fremde PIDs.

## Noch offen

Reales Drei-Host-Raft-/Patroni-/Split-Brain-/Watchdog-/Netzwerkverhalten; aktuelle signierte
Abhängigkeiten/Pakete; Ubuntu-/systemd-/Docker-Installation; WireGuard/CoreDNS/Cloudpfade;
replizierter allgemeiner Storage/CSI; voll integrierte DB-Services; PKI-CA-Lifecycle;
Worker-Canarywellen/N-N1; standortweite DR; NetworkPolicies und HA-Edge; direkter
containerd-Adapter; IONOS/ClusterPilot-Connector; Last-/Dauertests und unabhängige Security.
Keine SLA/RPO/RTO-Freigabe. Der gesamte Masterplan ist weiterhin NICHT abgeschlossen.

## Auslieferung

Quellcode wird als eigener Git-Snapshot geliefert. Vor Veröffentlichung ist der
Produktionsreleasevalidator BLOCKED. Ein separat gebautes .deb ist unsigned/qualified=false
mit Go1.23.2, nur für eine frische wegwerfbare Test-VM. Paketextraktion/CLI-Start sind keine
Ubuntuinstallation. Aktuelle Git-Bundle-/Paket-/Fresh-Checkout-Resultate und finale
Identitäten werden im Liefermanifest zusätzlich dokumentiert.

Keine GitHub-Pushes oder Actions, keine produktiven Hosts/Cloudkosten, keine Änderung des
privaten ClusterPilot-Repositories. Eine VM-Verbindung wurde vorgeschlagen, aber nicht
verbunden oder benutzt. Externe Integrationsverfügbarkeit ist kein Testnachweis.
