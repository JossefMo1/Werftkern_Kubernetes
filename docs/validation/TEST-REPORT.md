# Werftkern 0.2.0-dev.4 — tatsächlicher Entwicklungs- und Teststand

**NOT_PRODUCTION_READY · fullMasterplanComplete=false · StateSchema 2.**
Stand: 2026-09-25T12:45:13.802232+00:00. Basis: `67f5617188a8536d0ce915267a27ed552e55687e`.
Der endgültige Commit und die letzten Paket-/Checkoutprüfungen stehen im separaten
Liefermanifest; keine selbstreferenzielle Git-ID in diesem Bericht.

## Identität und Änderungen

Quellinventar: **213 Dateien**, SHA256 `3e7d3c96121b9f62f25111b929e95564808e9d8800bd9de362d45abc58c986cd`.
Pfad, Bytezahl und Datei-SHA256 werden kanonisch inventarisiert; Git/Build/Dist/Evidence,
Caches und `docs/validation` sind ausgeschlossen. Compiler: **Go1.23.2**, Debian13,
eingeschränkter Linux-Authoringcontainer. Aktuelle vorbereitete CI nicht ausgeführt.

Neu implementiert: sequenzielle Worker-Updatewellen, eigener Node-Wartungszugriff,
operationsgebundener selektiver Drain, signierte Artefaktstaging-/Hostupdatepfade,
node-lokale Docker-Smoke-Befehle und ein expliziter dev.3→dev.4-Agentvertrag.
Veraltete Readiness wird nicht mehr durch frische Nodeheartbeats als gesund gewertet.
Ausgelassene leere Wartungs-IDs im echten Go-JSON-Vertrag werden korrekt verarbeitet.
Pausierte Anwendungen können eine Updateprüfung nur ohne aktive Ausführung bestehen.

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis | Aussagegrenze |
|---|---|---|
| Vollständige Go-Race-Suite ohne Cache | **175 Haupttest-, 110 Untertestergebnisse; 22 Pakete; 0 fehlgeschlagen/übersprungen** | Enthält Fuzzseeds und Prozesshelfer; nicht 285 unabhängige E2E-Szenarien. Vier weitere Pakete ohne Testdateien. |
| Go vet | bestanden | Statische Prüfung, kein unabhängiger Audit. |
| Python-Betriebsbefehle | **64 bestanden** | Worker/SSH/Cloud/Datenbank/Hostantworten in diesen Tests sind Fixtures. |
| Release-/Publikationsguards | **7 bestanden** | Mechanische Konsistenz, keine externe Evidenzauthentizität. |
| Chromium-DOM | **11 bestanden** | Echte UI-Dateien mit synthetischem In-Memory-Fetch, kein Livecluster. |
| Tatsächliche dev.3/dev.4-Agent-Binaries | **bestanden** | Beide Quellstände wirklich gebaut; echte Agentprozesse, Journal, TLS; Docker und etcd sind Testadapter. |
| Tatsächlicher Go→Python-JSON-Vertrag | **bestanden** | Realer Go-Encoder und echte Python-Readinessfunktion; kein Server/Hoststart. |
| Alter Releaseprüfer gegen neues .deb | **bestanden** | Echtes dev.3-Binary, OpenSSL, Paketbytes; temporärer Testschlüssel. Keine Produktionssignatur oder Installation. |
| Python/JavaScript/Shell/YAML/gofmt | bestanden | Syntax-/Import-/Formatprüfungen, keine GitHub-CI oder systemd-Installation. |
| Echte etcd-Suite | **2 Tests fehlgeschlagen / BLOCKED: Binary fehlt** | Kein realer Raft-/Quorumtest bestanden. |
| Echter PostgreSQL-/WAL-Restoretest | **BLOCKED/Exit3: Dependencies fehlen** | Kein SQL-/WAL-/Patroni-/Watchdog-Nachweis. |
| DigitalOcean-Zugang | **Droplet-Liste 403; Kontostatus warning** | Konto meldet erreichtes Maximum von 3 Droplets; kein erfolgreiches VM-Inventar und keine Hostbefehle. |

Die Rohlogs werden separat als Evidence-ZIP geliefert. Neue Fuzz-Kampagnen wurden in
diesem Inkrement nicht ausgeführt. Historische Fuzz-Zahlen sind keine neuen Resultate.

## Reproduzierte und behobene Fehler

`reproduced-dev3-stale-readiness.log` dokumentiert zwei scheiternde Regressionstests am
vorherigen Scheduler: abgelaufene Readiness blieb positiv und eine nur früher gesunde
Surge-Allocation konnte die noch gesunde alte Revision verdrängen. Der neue Scheduler,
Discovery und die Übernahme von Probezeitstempeln verwenden tatsächliche Frische.
Dies ist ein Verfügbarkeitsfehler im bisherigen Code, kein hier entdeckter externer CVE.

`reproduced-omitted-maintenance-wire.log` zeigt die fehlerhafte Annahme, freie Wartung
werde immer als leerer String serialisiert. Go verwendet `omitempty`. Fehlendes Feld
wird nun als frei verarbeitet, explizites `null` bleibt ungültig. Das beeinflusst den
neuen Rolloutstart und die bestehende Wiederaufnahme nach verlorenem Unlock-ACK.
Der neue Integrationstest serialisiert das echte Go-State-Modell und ruft den echten
Python-Verbraucher auf; keine separat erfundene JSON-Fixture für diesen Vertrag.

## Workerablauf und Fehlernachweise

Alle Controller müssen bereits dev.4 melden; der Koordinator aktualisiert sie nicht.
Drei-Controller-Upgrades, Downgrades und allgemeine N/N−1-Kompatibilität sind nicht
implementiert. Nur der konkrete dev.3-Agent/dev.4-Controllervertrag ist freigegeben
für weitere Laborprüfung. Aktive gebundene/Stateful-Workloads blockieren den Drain.

Der Workflow hält die globale Wartungssperre mit eigener Operation. Nur betroffene
Workloads dürfen auf anderen Nodes ersetzt werden; Readiness und Stopbestätigung sind
Voraussetzungen. Keine Force-Eviction, keine Aufhebung unbekannter Reservierungen.
Journale binden Plan, Node-/Instance-/Cluster-Identität, Artefakte und Hosttrust.
Fehlende Kapazität, fremde Locks, Identitätswechsel, alter Controller, fehlender
Remote-Beleg, fehlgeschlagene Probe und nicht fortschreitende Heartbeats sperren.

Nach verlorenem Installations-ACK liest eine Wiederholung ausschließlich den Remote-
Beleg, statt dpkg blind erneut auszuführen. Ein unterbrochener oder unklarer Hostupdate
bleibt zur Operatorprüfung gesperrt. Beobachtungsfenster starten nach Neustart neu.
Verlorene Freeze-/Uncordon-/Unlock-Antworten sind getestet; fremde spätere Locks bleiben.
Einem historischen Abschlussbeleg wird keine neue Gesundheitszusage zugeschrieben.

Der Worker nutzt eigene mTLS-Rechte, keinen Controller-Adminschlüssel. Der vertrauenswürdig
vorinstallierte Release-Public-Key und SSH-Hostkeys werden geprüft, nicht ungeprüft
ersetzt. Das alte installierte Binary verifiziert das Paket vor Ausführung des neuen
Helpers. Der neue `worker-check` verwendet den echten Docker-Adapter; **hier wurde
seine Host-/Dockerdurchsetzung nicht ausgeführt**, sondern mit Enginefixtures geprüft.
HTTP-Smoke/Versionsprüfung ist kein Anwendungs- oder Datenintegritätsbeweis.

## Tatsächlicher Binärwechsel

`scripts/test-agent-compat.sh` baut das echte dev.3-Binary aus dem festgeschriebenen
Basiscommit und das neue Binary. Ein Agentprozess wird beendet und mit der neuen
Binärdatei über demselben lokalen Journal gestartet. Allocation-ID und Sequenz bleiben
konsistent; die Engine-Fixture sieht genau einen Create/Start und späteres Delete.
Das beweist keine Containerisolierung, Paketinstallation oder Mehrhost-Recovery.

Der Paketprüfertest erzeugt und entfernt private Testschlüssel in einem temporären
Verzeichnis. Das bedeutet keine physisch garantierte Schlüsselvernichtung auf dem
Datenträger. Keine privaten Schlüssel oder aus diesem Test gültige Release-Signaturen
werden ausgeliefert. Manipulierte Signatur wird vom tatsächlichen Vorgänger abgewiesen.

## Offene Implementierungen und reale Produktionsgates

Replizierter allgemeiner Storage/CSI, vollständig integrierte DB-Services, qualifiziertes
physisches Writer-Fencing, standortweite DR, vollständiger CA-Lifecycle, NetworkPolicies,
HA-Edge, automatische Controller-Updatewellen, direkter containerd-Adapter, IONOS und
ClusterPilot-Connector sowie weitere Masterplanpunkte bleiben offen.

Nicht erfolgreich durchgeführt: Ubuntu-/systemd-/Docker-/SSH-Installation und Updates,
realer etcd-Verbund, mehrere Worker/Controller mit Partitionen/Reboots, WireGuard/CoreDNS,
Cloudbootstrap, PostgreSQL-/Patroni-/Watchdog-Ausfälle, tatsächlicher WAL-Restore,
Last-/Dauertest, aktuelle signierte Lieferkette und unabhängige Securityqualifikation.
Keine SLA/RPO/RTO-Freigabe. Der Releasevalidator bleibt ausdrücklich **BLOCKED**.

## Umgebung, Veröffentlichung und Pakete

DigitalOcean ist verbunden. Die API verweigerte das Auflisten mit 403. Die getrennte
Kontoinformation meldete `warning` und das erreichte Droplet-Limit von drei. Aus dieser
Meldung wurde kein erfolgreiches VM-Inventar abgeleitet. Bestehende Ressourcen wurden
nicht verändert, angelegt oder gelöscht; keine Cloudkosten durch diesen Arbeitslauf.
Kein GitHub-Push, keine GitHub-Aktion und keine Änderung des privaten ClusterPilot.

Ein separat erzeugtes `.deb` ist ein **unsignierter Go1.23.2-Laborbuild**, nicht für
Kundensysteme. Bauen, Auspacken, Binary-Start und temporäre Testsignatur sind keine
Ubuntu-Paketinstallation oder Produktionsfreigabe. Finaler sauberer Commit, Bundle,
frischer Checkout, Paketidentität und SHA256 stehen im separaten Liefermanifest.
