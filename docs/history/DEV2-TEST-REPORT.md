# Werftkern 0.2.0-dev.2 — tatsächlicher Entwicklungs- und Teststand

**NOT_PRODUCTION_READY · vollständiger Masterplan nicht umgesetzt.**
Stand: 2026-09-25T10:50:16.109587+00:00. Basis: `cbc01de44284274947f81c244b091af7c626363c`. Finale Git-Identität im separaten
Liefermanifest; dieser Bericht vermeidet einen selbstreferenziellen Commit-Hash.

## Identität

Version `0.2.0-dev.2`, State-Schema **2**. Quellinventar: **172 Dateien**.
SHA-256: `80b76d652aa91a501910200faf7deaf3ed5f507d64f4ebe7886c5879420a4547`.
Inventar umfasst sortiert Pfad, Datei-SHA256 und Bytezahl; Git, Build/Dist, Evidence,
Caches und `docs/validation` sind ausdrücklich ausgeschlossen.
Toolchain: **Go1.23.2** im Debian13-Authoringcontainer, nicht Go1.27.1/Ubuntu24.04.

## Tatsächlich ausgeführt

| Prüfung | Ergebnis | Aussagegrenze |
|---|---|---|
| Go-Suite `go test -race -count=1 -json ./...` | 151 Haupttest-, 84 Untertestergebnisse; 21 Pakete bestanden; keine fehlgeschlagenen Tests | Einschließlich Fuzzseeds/Prozesshelfer, nicht ebenso viele unabhängige E2E-Szenarien |
| Test-Skips | 0 Testfälle übersprungen; 4 Pakete ohne Testdateien | Pakete ohne Tests sind keine bestandenen Tests |
| `go vet` | bestanden | Statische Prüfung, kein Security-Audit |
| Python-Betriebsbefehle | 16 Tests bestanden | Provider-/Befehlsfixtures; keine Host-/Cloudmutation |
| Release-/Publikationsguards | 7 Tests bestanden | Konsistenz-/Sperrprüfung, keine unabhängige Evidenzauthentifizierung |
| Browser | 11 Chromium-DOM-Prüfungen bestanden | In-Memory-API, synthetische UI-Daten; kein Livecluster |
| Python/JavaScript/Shell/YAML | Prüfungen bestanden | Keine systemd-/Paketinstallation oder GitHub-CI-Ausführung |
| Physische Volumearchive | echte Mehr-Megabyte-Dateien verschlüsselt, wiederhergestellt und bytegleich verglichen | Offline Dateibaum, kein echter Container-/PostgreSQL-/Host-Restore |
| Root-CLI-Integration | tatsächlicher Backup-/Restorebefehl, verlorenes API-ACK, erneuter Aufruf ohne Überschreiben bestanden | Echt: Dateien, Kryptografie, TLS, Unix-HTTP. Testadapter: Docker und etcd |
| HTTPS-Ingress | echte lokale TLS-Anfragen und HTTP-Upstreams bestanden | Discovery-Testdaten, kein öffentlicher/mehrhostiger Anwendungspfad |
| Real-etcd-Suite Kompilierung | bestanden | `-run '^$'` führt keine Tests aus |
| Real-etcd-Ausführung | **2 Tests fehlgeschlagen / BLOCKED**: Binary fehlt | Weder ein realer etcd- noch ein HA-Test ist hier bestanden |

Ein erster kalter Go-Race-Lauf wurde vom Ausführungszeitlimit abgebrochen. Er steht separat
unter `go-test-interrupted.jsonl` und zählt nicht als Erfolg. Der folgende vollständige Lauf
hat Exit0. Das Releasegate bleibt trotz grüner lokaler Tests BLOCKED.

## Neue Korrektheitsnachweise

**Node-Sperre ≠ Fencing.** Mit dem unveränderten dev.1-Scheduler wurde ein unbestätigter
Doppelstart nach Revocation reproduziert. `reproduced-dev1-revocation-defect.log` enthält
den erwarteten Fehler. Mit korrigiertem Scheduler besteht derselbe Regressionstest.
Standard behält unsichere alte Ausführung/Reservierungen. Nur ausdrücklich duplikattolerante
zustandslose Anwendungen erlauben Ersatz. Stateful-/Volumeprofile lehnen die Policy ab.

**Heartbeatreihenfolge.** Persistierte positive Sequenz, Inhaltsbindung, Versionskontrolle
und monotone Terminalzustände verhindern verspätete Liveness-/Status-Reaktivierung. Das
ersetzt kein physisches Fencing und bietet keinen gemischten Versionsbetrieb.

**Dateidaten.** Chunkauthentisierung prüft Header, Reihenfolge, Abschluss und Integrität.
Manipulation, falscher Schlüssel, abgeschnittene/verlängerte Archive, unzulässige Links,
FIFO, Traversal, widersprüchliche Einträge und Limits werden abgewiesen. Zielkopien werden
nur neu angelegt; Pending-Reservierung/Receipt schützen den Wiederanlauf und ACK-Replay.
IO-Lock und Docker-Mountvertrag verweigern aktive/restartbare fremde Mounts einschließlich
Root-Mount. Diese Dockerantworten sind Fixtures; tatsächliche Hostdurchsetzung ist offen.

**Ingress.** Eigene gateway-Identität, servicebeschränkte Discovery, TLS-SNI/Hostprüfung,
zulässige private Ziele, Frischefrist, Ablehnung veralteter Routen und Wiederherstellung
nach transientem Discoveryfehler geprüft. App-Authorization/Cookies bleiben erhalten,
Forwarding-Spoofing wird entfernt. Fehlgeschlagener POST wird nicht bewusst dupliziert.
TLS endet am Edge; private HTTP-Upstreams sind nicht automatisch verschlüsselt.

**Schemawechsel.** Exakte Quellebytes vor CAS gesichert; falscher Hash, fehlgeschlagenes
Backup, veränderte Revision, aktive Workloads und vorhandene Allocations verweigert.
Replay erkennt bereits migrierten Zustand. Dies wurde gegen Speicherfixtures geprüft,
nicht an einem laufenden Ubuntu-/etcd-Verbund. Dokumentierte Offline-Migration ist Pflicht.

## Kurzes Fuzzing

5s angefordert je Lauf; reale Laufzeit einschließlich Abschluss kann darüber liegen.
Volumearchiv **93**, Vault **27114**, logisches Backup
**57801** Ausführungen. Alle Läufe bestanden. Das ist weder ein vollständiger
Parserbeweis noch eine unabhängige kryptografische Prüfung. Raw Logs liegen in Evidence.

## Unveränderte Testadaptergrenzen

Der ältere Prozess-E2E startet echte Linux-Kindprozesse und TLS/HTTP, aber keine Container.
Die etcd-Fixture ist kein Raft-Cluster. Browser nutzt nur In-Memory-Fetch. Keine Cloud-
Credentials oder produktiven Systeme wurden benutzt. Der Source-/History-Lint prüft
begrenzte Muster und ersetzt keine vollständige Rechte-, Secret- oder Lizenzprüfung.

## Fehlende Implementierungen und Produktionsnachweise

Keine fertige Datenbankreplikation/HA/PITR oder unabhängiges Writer-Fencing; kein CSI oder
replizierter Storage; kein vollständiges standortweites DR; keine automatisierte PKI-Rotation,
Worker-Upgrade-Wellen oder gemischte Versionskompatibilität; keine produktive NetworkPolicy,
kein hochverfügbarer Edge-VIP, kein direkter containerd-Adapter oder fertiger ClusterPilot-
Connector. Die ausführbaren HA-/Cloud-/Mesh-Ansätze bleiben unqualifiziert.

Nicht erfolgreich ausgeführt: echte Ubuntu-/Docker-/etcd-/Mehrhostpfade, reale Cloud-
Provisionierung, WireGuard/CoreDNS, Datenbank-Persistenz und Cross-Host-Restore, tatsächlicher
Paketupdate-/Schemamigrations-/Rückweg, Last-/Dauertest und unabhängige Securityfreigabe.
Keine SLA-, RPO- oder RTO-Zusage. Vor Produktion aktuelle Toolchain/Dependencies prüfen,
exakte signierte Artefakte bauen und alle qualifizierten Pfade real testen.

## Paket und Auslieferung

Ein separat erzeugtes `.deb` ist ein unsignierter Go1.23.2-Laborbuild mit `qualified=false`.
Extraktion und Binary-Start sind keine Ubuntuinstallation. Ein finales Git-Bundle, ZIP,
Paketprüfung und frischer Checkout werden im Liefermanifest und gesonderten Logs festgehalten.
Die finale Prüfung kann fehlende reale Cluster- oder Sicherheitsnachweise nicht ersetzen.
