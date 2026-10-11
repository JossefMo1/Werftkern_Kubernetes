# Werftkern Kubernetes 0.1.0-dev.3 — tatsächlicher Entwicklungs- und Teststand

Stand: 2026-09-26T10:13:15.791067+00:00. Basiscommit: `c51ff03af8cbbad5ce444fd82960ba9eecd45c50`.
**NOT_PRODUCTION_READY · fullMasterplanComplete=false · cncfCertified=false.**
Die separate Native-Runtime bleibt `0.2.0-dev.4`. Die neue Kubernetes-Komponente setzt
auf k0s/k0sctl; keine Behauptung eines Kubernetes-unabhängigen zertifizierten Ersatzes.

## Implementierte Änderungen

- Journalisierter Controller-Ersatz für drei reine Hetzner/k0s-Controller: zwei
  gesunde überlebende Controller mit übereinstimmender Mitgliedschaft, verschlüsseltes
  Backup, Eigentums-/Identitätsprüfung, permanente Providerlöschung mit zwei getrennten
  Abwesenheitsbeobachtungen, dann ControlNode-/etcd-Memberentfernung, neuer Host und Join.
- Stateful-Recovery nur für ausdrücklich registrierte einreplizierte StatefulSets mit
  erhaltenen Hetzner-CSI-Single-Writer-Dateisystemvolumes. Fencing vor Out-of-service;
  keine eigenmächtige Entfernung von CSI-Finalizern, keine leeren Ersatzdaten.
  Detach-on-timeout muss im Plan und im tatsächlich laufenden Controllerprozess
  deaktiviert sein. PVC-/PV-/Provider-/Pod-UIDs und fremde Attachments werden geprüft.
- Opt-in-Recovery-Watcher mit Beobachtungsfristen, Umfang-/Kosten-/Ersatzbudget und
  persistenter Auftragsauswahl. Sein systemd-Dienst wird nicht automatisch aktiviert.
- Quarantänisierter Velero-/CSI-Snapshot-Restore in ein anderes Cluster und neue
  Namespaces: nur Storageobjekte, keine gesicherten Workloads, Hooks oder RBAC-Ausführung.
  Neue Volumeidentität, eingeschränkter Read-only-Prüfjob und operatorfestgelegte
  Dateihashes. Keine automatische DB-Promotion, Verkehrsumschaltung oder fachliche
  Konsistenzfreigabe. **Hetzner-Volumes bieten keine Snapshots; dieser Restorepfad
  braucht ein anderes, zuvor qualifiziertes snapshotfähiges CSI-Backend.**
- Kandidatengebundene Ed25519-Prüfbelege: getrennt administriertes und hashgepinntes
  Vertrauen, autorisierte Aussteller, Zeit-/Dateihashes, Rohbelege, Rollen-/Schlüsseltrennung,
  nichtleere CycloneDX-SBOM, Trivy-Daten und passendes SLSA-Provenance-Dokument.
  Eigenes Belegformat, keine Behauptung einer Sigstore-/SLSA-Level-Zertifizierung.
  Selbst vollständig gültige Belege werden nicht automatisch zur Produktions- oder
  CNCF-Freigabe. Der bisherige mechanische Releasevalidator setzt ebenfalls nie
  `productionReady=true`.

## Tatsächlich ausgeführt

| Prüfung | Ergebnis | Grenze |
|---|---|---|
| Kubernetes-Python-Suite | **198 Tests bestanden** | Provider, Kubernetes, CSI, Velero, SSH, Helm und k0sctl werden durch gekennzeichnete Testadapter beantwortet. |
| Native Go-Suite mit Race Detector | **175 Haupttest- und 110 Untertestergebnisse, 22 Pakete bestanden** | Kein fehlgeschlagener/übersprungener Testfall; zusätzlich vier Pakete ohne Testdateien. Keine 285 unabhängigen E2E-Szenarien. |
| Go vet | Bestanden | Statische Prüfung, kein Security-Audit. |
| Native Python-Betriebsbefehle | **64 bestanden** | Host-/Provider-/DB-Testadapter. |
| Release-/Publikationsguards | **7 bestanden** | Mechanische Konsistenzprüfung. |
| Chromium-DOM | **11 bestanden** | Echte UI-Dateien, synthetische In-Memory-API; keine Live-Kubernetes-Weboberfläche. |
| OpenSSL-Prüfbelege | Echte Ed25519-Schlüssel/Signaturen und negative Signaturtests bestanden | Ausschließlich temporäre Testschlüssel und synthetische Belege; kein Produktionsrelease oder fremder Reviewer. |
| Restore-Prüfprogramm | Echte temporäre Dateien und SHA256 geprüft; veränderte Bytes/Symlinks abgewiesen | Lokales Pythonprogramm, kein echter PVC-/CSI-/PostgreSQL-Restore. |
| Historische Fehlerreproduktion | **6 Regressionstests scheitern erwartungsgemäß am unveränderten dev.2-Code** | Drei Failures und drei Errors sind der Reproduktionsnachweis, keine bestandene dev.2-Suite. Korrigierte Tests bestehen im neuen Stand. |
| Echte etcd-Suite | **Zwei Tests fehlgeschlagen/BLOCKED: Binary fehlt** | Kein echter Raft-/Quorumtest bestanden. |
| Echter PostgreSQL-/WAL-Restore | **BLOCKED/Exit 3: PostgreSQL17/pgBackRest fehlen** | Kein SQL-/WAL-Replay ausgeführt. |
| Echte Kubernetes-VM-Suite | **BLOCKED/Exit 3: kein freigegebener Wegwerf-Clusterplan/Assets/Managementroot** | Keine Kubernetes-/SSH-Testadapter in diesem Versuch; kein Live-Test bestanden. |

Neue Fuzz-Kampagnen wurden in diesem Inkrement nicht ausgeführt. Historische Fuzz-Zahlen
sind keine neuen Nachweise. Rohlogs liegen im separaten Evidence-Archiv. Die Tests benutzen
kurzlebige lokale Schlüssel; Produktionsschlüssel werden weder angelegt noch ausgeliefert.

## Reproduzierte Fehler und Korrekturen

1. Cloud-Scaling konnte nach gespeichertem Kubernetes-Zielzustand den ursprünglichen
   Auftrag nicht korrekt wiederaufnehmen, insbesondere nach verlorenem DELETE-ACK.
2. Ein abgeschlossener Auftrag und ein neuer unterschiedlicher Scaling-Auftrag wurden
   nicht zuverlässig getrennt; Wiederholungen dürfen keine neue Gesundheitszusage erzeugen.
3. Der Cloud-Cleanup war nicht über die gesamte Providerphase lokal serialisiert.
   Jetzt umfasst die Sperre auch Bestätigung und Löschung, um paralleles DELETE zu verhindern.
4. Der Control-Plane-Restore blockierte den eigenen Abschluss-Replay durch eine zu frühe
   generische Prüfung auf vorhandenen Clusterzustand. Nur genau der eigene Zustand darf
   nun abgeglichen werden; ein fremder Zielcluster bleibt gesperrt.
5. Ein Projekt-/Credentialwechsel durfte einen 404 nicht zum Beweis für die Löschung
   einer VM aus dem ursprünglichen Projekt machen. Alle neuen Mutationsjournale binden
   einen separierten Fingerprint des verwendeten Provider-Tokens. Kein Tokenwert im Journal.

Ein laufender dev.2-Cloud-/Repair-Intent ohne diese Bindung wird nicht still übernommen.
Vor dem Upgrade alle alten Operationen abschließen oder unabhängig rekonstruieren.
Ein absichtlicher Tokenwechsel verlangt eine geprüfte Übernahme; automatische Rotation
laufender Provider-Intents wird nicht behauptet.

## Reale Grenzen und die 14 Anforderungen

`release/kubernetes-readiness.json` ordnet jeden verlangten Punkt zu. Controller- und
Stateful-Recovery sind jetzt eingeschränkt implementiert, aber nicht live qualifiziert.
Vollständiges PV-/DB-/Standort-DR, SSO für den ganzen Add-on-Katalog, universelles
Storage-Fencing, getestete Backupherkunft und ein Ein-Befehl-Produktionssetup fehlen.
Ein Dateihash ist kein SQL-Konsistenz- oder vollständiger Datenbank-HA-Nachweis.

Keine echten Ubuntu-/systemd-/Container-/Cluster-/Provider-/CSI-Mutationen; keine
HA-Partition/VIP-Umschaltung, Hostupgrades, Last-/Dauertests oder unabhängige Prüfung.
Kein tatsächlicher Keycloak-Login, ACME- oder Sonobuoy-Lauf, keine CNCF-Einreichung/-Annahme.
Keine aktuelle vollständige SBOM-/CVE-/Provenance-Erzeugung oder signierte Produktlieferkette.
Die Signaturtests authentifizieren synthetische Testdaten, nicht reale fremde Nachweise.

DigitalOcean ist verbunden; die aktuelle erfolgreiche Droplet-Liste war leer. Es wurden
keine Droplets erstellt, verändert oder gelöscht und keine Cloudkosten ausgelöst.
Hier fehlen die echten Cluster-/DB-Binaries; der versuchte externe Downloadzugang
funktionierte nicht. Das private ClusterPilot und GitHub wurden nicht verändert.

## Paket und Export

Das separat erzeugte Paket ist Python-Quellcode für den Kubernetes-Manager, Architektur
`all`, **unsigniert und unqualifiziert**. Es enthält keine k0s-/kubectl-/Helm-/Sonobuoy-
Binaries, Charts oder Images. Packaging/extrahierter CLI-Start sind keine Ubuntuinstallation.
Die tatsächliche lokale Native-Testtoolchain ist Go1.23.2; kein neues Native-Paket behauptet.

Endgültige Commit-/Dateiidentitäten, Paket-/Fresh-Checkout-Ergebnisse und Prüfsummen werden
im separaten Liefermanifest dokumentiert. Dieser Bericht vermeidet selbstreferenzielle IDs.
