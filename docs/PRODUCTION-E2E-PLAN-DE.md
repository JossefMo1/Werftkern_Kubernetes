# Produktions-E2E-Plan und Arbeitsrhythmus

**Status: aktiv, nicht qualifiziert.** Dieser Plan ist eine Ausführungs- und
Nachweisreihenfolge. Er ersetzt weder die Gate-Verträge in
`release/qualification.json` und `release/kubernetes-readiness.json` noch macht
eine vorbereitete Prüfung zu einem bestandenen Live-Gate.

Der aktuelle, maschinenlesbare Handoff steht in
[`release/production-tracker.json`](../release/production-tracker.json). Jeder
Arbeitslauf beginnt mit diesem Tracker, den Release- und Kubernetes-Gates, offenen
Issues/PRs und fehlgeschlagenen CI-Läufen. Nach einem Lauf wird der Tracker nur
bei einem echten, belegten Zustandswechsel aktualisiert.

## Sicherheits- und Nachweisregeln

- Nur frische, ausdrücklich entbehrliche Ubuntu-24.04-amd64-VMs oder Cluster;
  niemals Kunden-, bestehende Entwicklungs- oder Produktivsysteme.
- Keine Cloud-Erstellung, Kosten, öffentlichen Dienste oder Secrets ohne konkrete
  Konfiguration und ausdrückliche Autorisierung.
- Jeder Live-Nachweis bindet Kandidat-Commit, Paket-/Chart-/Image-Digests,
  Topologie, Start/Ende, Befehle, anonymisierte Logs, Exit-Status und Aufräumergebnis.
- Ein fehlender Zugang, abgebrochener Lauf, rotes Ergebnis oder nicht reproduzierter
  Kandidat bleibt `blocked` bzw. `failed`; keine Ersatznachweise aus Fixtures.
- Vor einem zerstörerischen Schritt: eindeutige Besitzmarkierung, Wiederanlauf- und
  sichere Aufräumprozedur. Nach einem Fehler bleiben Beweise und Sperren erhalten.

## Reihenfolge der End-to-End-Qualifikation

| Priorität | E2E-ID | Pfad | Mindestnachweis vor „passed“ | Aktueller Zustand |
| --- | --- | --- | --- | --- |
| P0 | E2E-00 | Gemeinsamer Release Candidate | sauberer Build, eindeutiger Commit und Artefakt-Digests, SBOM/Scanner-/Provenienzstatus für denselben Kandidaten | vorbereitet, noch kein RC |
| P0 | E2E-K01 | Kubernetes CSI Lab | frischer k0s-Cluster; admission, Pod-Start, Token-Abwesenheit am Node, Provision/Attach/Mount/Write/Read, Expansion und Aufräumen; unveränderte SecurityContexts belegen | externe Lab-Infrastruktur fehlt |
| P0 | E2E-N01 | Native Ubuntu | frische VM, echte Paketinstallation, Neustart, Deinstallation/Wiederinstallation und der bestehende Ubuntu-E2E-Skript-Nachweis | externe VM und Kandidat-Paket fehlen |
| P1 | E2E-K02 | Kubernetes Lifecycle | Controller/Worker-Lifecycle, Scale, Add-ons, Storage, Backup/Restore und negative Zugriffsprüfung im dokumentierten Scope | abhängig von E2E-K01 |
| P1 | E2E-N02 | Native Upgrade/Recovery | unterstützter dev.3→dev.4-Upgradepfad, Rollback, Backup/Restore auf neuem Host und Datenintegrität | abhängig von E2E-N01 und einem fixierten Kandidaten |
| P1 | E2E-H01 | Mehrhost/Fehlerfälle | Controller-Ausfall, Quorum, Netzpartition, Wiederanlauf und dokumentierte Grenzen | entbehrliche Mehrhost-Topologie fehlt |
| P2 | E2E-P01 | Last/Soak | gemessene Last-, Soak- und Fehlergrenzen für denselben Kandidaten | abhängig von stabilen Live-Pfaden |
| P2 | E2E-R01 | RC/Review | veröffentlichter RC, nachvollziehbares Nutzerfeedback, erforderliche unabhängige Prüfung und Go/No-Go | abhängig von allen technischen Gates |

## E2E-K01: vorbereiteter CSI-Lab-Lauf

**Vorbedingungen:** Ein ausdrücklich freigegebener entbehrlicher k0s-Cluster mit
einem Management-Host, drei Controllern, mindestens einem Worker, privaten
Zugängen, passenden Hetzner-Cloud-Volumes und einem bereits vorhandenen
`kube-system/hcloud`-Secret. Der Tokenwert wird niemals ausgegeben oder committed.

1. Kandidat und Assets hashen; der hcloud-CSI-Render muss exakt
   `1a439e5735f2635904acc8379a55185e010abfe8e3466b1ff8ae75433da6e438`
   entsprechen oder der Lauf wird abgebrochen.
2. Den Render anwenden und alle CSI-Pods direkt beobachten. Dokumentieren: Images,
   Workload-UIDs, gestartete Container, SecurityContexts und dass der Node-Pod keinen
   Service-Account-Token erhält. Keine Secrets auslesen.
3. Eine isolierte Test-Namespace/PVC/Pod-Kette mit `werftkern-hcloud-retain` erstellen;
   Daten schreiben, Hash erfassen und denselben Inhalt nach Attach/Mount lesen.
4. Eine erlaubte Expansion durchführen und den erweiterten Zustand direkt prüfen.
5. Testobjekte in umgekehrter Reihenfolge entfernen; `Retain`-Verhalten getrennt
   dokumentieren. Nie ein fremdes Volume löschen.
6. Logs und Checks an den exakten Kandidaten binden. Ein erfolgreicher E2E-K01 schließt
   nur die dokumentierten Storage-Teilaspekte, nicht HA, Backup/Restore oder Production.

**Sichere Rückabwicklung:** Test-Workloads und Namespace entfernen; nur eindeutig
Werftkern-eigene Testvolumes nach manueller Prüfung löschen. Bei Unsicherheit nicht
löschen, Kennung dokumentieren und den Lauf blockiert lassen.

## Kontinuierliches Tracking

Der Tracker darf nur diese Zustände verwenden: `not-started`, `prepared`,
`in-progress`, `blocked-external`, `failed` und `passed`. `passed` ist nur mit
unveränderlichem Kandidaten, überprüfbaren Evidence-Referenzen und passendem
Release-Gate zulässig. `productionReady` bleibt bis zum finalen Go/No-Go immer
`false`.

Bei jedem Lauf:

1. offene Issues, PRs, Checks, Feedback und Tracker lesen;
2. die höchste nicht blockierte Priorität bearbeiten;
3. Testergebnis, Commit/PR und Blocker knapp im Tracker sowie im Issue-Handoff
   festhalten;
4. den nächsten konkreten Schritt nennen, ohne fehlende Infrastruktur zu simulieren.

Damit bleibt die Arbeit auf dem Pfad zu einer Production-Version sichtbar, ohne
einen Release vorzeitig zu behaupten.
