# Produktions-E2E-Plan und Arbeitsrhythmus

**Aktueller Zielumfang: Native Single-Host Production. Status: noch nicht qualifiziert.**

Der erste Production-Release benötigt keine sieben VMs. Er wird auf einem frischen, entbehrlichen Ubuntu-24.04-amd64-Runner als Single-Host-Produkt qualifiziert. HA, Multi-Host und Kubernetes werden separat weitergeführt und blockieren diesen ersten Scope nicht.

Der maschinenlesbare Handoff steht in release/production-tracker.json. Jeder Lauf beginnt mit dem Tracker, dem Native-Scope, offenen Issues/PRs und den exakten CI-Ergebnissen.

## Regeln

- Nur frische, ausdrücklich entbehrliche Linux-Runner oder Testhosts verwenden.
- Keine Kunden-, Entwicklungs- oder Produktivsysteme für destruktive Tests verwenden.
- Jeder Live-Nachweis bindet Kandidaten-Commit, Paket-Digest, Start/Ende, Exit-Status und bereinigtes Evidence.
- Ein fehlender oder abweichender Kandidat bleibt blockiert; Fixtures ersetzen keinen Live-Nachweis.
- productionReady=true ist nur für den unveränderten Kandidaten zulässig, nachdem alle anwendbaren Single-Host-Gates bestanden sind.

## Reihenfolge

| Priorität | E2E-ID | Nachweis | Status |
| --- | --- | --- | --- |
| P0 | E2E-00 | sauberer Build, SBOM, Digest-Identität und signierbares Release-Artefakt | vorbereitet |
| P0 | E2E-N01 | frische Ubuntu-Installation, Setup, echte Docker-/etcd-Workloads, Dienst-/etcd-Neustart, Cleanup | bereit zur Ausführung |
| P1 | E2E-N02 | lokales Backup/Restore und Datenintegrität | offen |
| P1 | E2E-N03 | unterstütztes Paket-Upgrade und Rollback auf demselben Host | offen |
| P1 | E2E-P01 | begrenzter Single-Host-Load-/Soak-Test | offen |
| P1 | E2E-R01 | Release Candidate, Nutzerfeedback, Runbooks und Go/No-Go | offen |
| — | E2E-H01 | Multi-Host-HA, Quorum und Netzwerkpartition | zurückgestellt, nicht Bestandteil des ersten Scopes |
| — | E2E-K01 | produktiver k0s/Kubernetes-Lifecycle | zurückgestellt, nicht Bestandteil des ersten Scopes |

## Native-Single-Host-Lauf

Die bestehende ci.yml besitzt den manuellen Parameter run_real_vm_e2e. Der Lauf muss für den exakten Kandidaten mit run_real_vm_e2e=true gestartet werden. Zusätzlich läuft der reale etcd-Test auf einem ephemeren Ubuntu-Runner.

Der E2E-N01-Nachweis muss mindestens enthalten:

- Paket- und BUILD-INFO-Commit stimmen mit dem Kandidaten überein;
- Ubuntu 24.04, amd64, systemd und cgroup v2;
- frische Paketinstallation und werft setup;
- reale Demo-Workloads in Docker;
- Workload-Neustart nach Controller-/Agent-Neustart;
- etcd-Neustart und erneute Status-/Health-Prüfung;
- Skalierung, Rollback, Secret-Mount- und Cleanup-Prüfung;
- nicht-sensitive, kandidatengebundene Evidence.

Danach werden Backup/Restore, Upgrade/Rollback und der begrenzte Soak-Lauf als eigene Nachweise gegen denselben Kandidaten ergänzt. Keine HA- oder Kubernetes-Evidence wird als Ersatz dafür akzeptiert.

## Abschluss

Erst wenn der Native-Single-Host-Vertrag, die Artefaktsignierung, die Runbooks und die Go/No-Go-Prüfung erfolgreich sind, darf die Version als Production Release veröffentlicht werden. Die Release Notes müssen die zurückgestellten HA-, Kubernetes- und Site-Recovery-Funktionen sichtbar nennen.