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

Die bestehende ci.yml besitzt den manuellen Parameter run_real_vm_e2e. Für den exakten Kandidaten kann der Lauf weiterhin mit run_real_vm_e2e=true gestartet werden. Zusätzlich startet ein autorisierter Push eines unveränderten Release-Candidate-Tags im Format `v0.2.0-rc.*` automatisch denselben privilegierten `real-vm`-Job; damit bleibt die Qualifikation ausführbar, wenn der GitHub-Connector keinen Workflow-Dispatch anbietet. Der Tag ist nur ein Trigger und schließt kein Gate: Commit-, Paket-Digest-, Evidence-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- und Signaturprüfung bleiben verpflichtend. Zusätzlich läuft der reale etcd-Test auf einem ephemeren Ubuntu-Runner.

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

## Verbindlicher Countdown 1–100

Der Countdown gilt ausschließlich für den ersten **Native Single-Host Production Release** auf Ubuntu 24.04 amd64. Ein Punkt darf nur mit kandidatengebundener Evidenz als erledigt markiert werden. Der Countdown wird nicht künstlich weitergezählt, wenn ein Gate fehlschlägt.

**Zeitfenster (Europe/Berlin):**
- 25.11.: Punkte 1–30, RC und automatisierte Qualität
- 26.11.: Punkte 31–60, Ubuntu-E2E, Docker/etcd und Lifecycle
- 27.11.: Punkte 61–70, Backup/Restore
- 28.11.: Punkte 71–80, Upgrade/Rollback
- 29.–30.11.: Punkte 81–90, Load/Soak, Security, SBOM, Signierung
- 01.12.: Punkte 91–95, RC-Konsolidierung und Dokumentation
- 02.–04.12.: Punkte 96–100, Maintainer-Freigabe und Production-Veröffentlichung
- Best case: 01.12.; realistisches Fenster: 02.–04.12.; jeder fehlgeschlagene Live-Gate-Lauf verschiebt den Termin.

1. **Release-Grundlage** – Punkte 1–10
2. **Kandidat und Build** – Punkte 11–20
3. **Automatisierte Qualität** – Punkte 21–30
4. **Ubuntu-24.04-Installations-E2E** – Punkte 31–40
5. **Workload-Lifecycle** – Punkte 41–50
6. **etcd und Wiederanlauf** – Punkte 51–60
7. **Backup und Restore** – Punkte 61–70
8. **Upgrade und Rollback** – Punkte 71–80
9. **Last, Sicherheit und Supply Chain** – Punkte 81–90
10. **RC, Maintainer und Release** – Punkte 91–100

1. Production-Scope festschreiben
2. Single-Host-Topologie bestätigen
3. 7-VM-Anforderung aus dem ersten Scope entfernen
4. HA/Kubernetes als Erweiterungspfad dokumentieren
5. Main-Commit einfrieren
6. Production-Tracker prüfen
7. Issues und PRs prüfen
8. Release-Risiken erfassen
9. Go-/No-Go-Regeln bestätigen
10. Maintainer-Prüfung definieren
11. RC-Versionsnummer festlegen
12. RC-Tag erstellen
13. Candidate-Commit dokumentieren
14. sauberen Build starten
15. Debian-Paket bauen
16. CLI-Paket bauen
17. Runtime-/Dashboard-Artefakte bauen
18. Artefakt-Digests erzeugen
19. Release-Manifest erzeugen
20. Build-Wiederholbarkeit prüfen
21. Unit-Tests ausführen
22. Race-Tests ausführen
23. Static-Checks ausführen
24. Go-Vulnerability-Checks ausführen
25. Source-/Privacy-Checks ausführen
26. Package-Layout prüfen
27. Installationsskripte prüfen
28. CLI-Smoke-Test ausführen
29. API-/Contract-Tests ausführen
30. Ergebnisse dem RC zuordnen
31. frischen Ubuntu-24.04-Runner starten
32. Systemvoraussetzungen prüfen
33. Paket installieren
34. Docker Engine prüfen
35. etcd installieren und konfigurieren
36. mTLS-Zertifikate prüfen
37. Controller starten
38. lokalen Worker starten
39. Dashboard starten
40. CLI-Verbindung prüfen
41. Test-Workload erstellen
42. Workload über CLI starten
43. Workload im Dashboard prüfen
44. Container-Zustand prüfen
45. Workload stoppen
46. Workload erneut starten
47. Prozessfehler simulieren
48. automatische Wiederherstellung prüfen
49. Docker-Neustart durchführen
50. Workload danach prüfen
51. etcd-Daten schreiben
52. etcd-Zustand prüfen
53. etcd-Dienst neustarten
54. Controller nach etcd-Neustart prüfen
55. Worker nach etcd-Neustart prüfen
56. Workload-Zustand prüfen
57. ungültige Zustände prüfen
58. Fehlerjournal prüfen
59. Cleanup ausführen
60. Lifecycle-Evidenz speichern
61. lokales Backup ausführen
62. Backup-Inhalt validieren
63. Backup-Digest erzeugen
64. Datenverlust simulieren
65. Restore auf demselben Host ausführen
66. etcd-Zustand wiederherstellen
67. Controller-Zustand wiederherstellen
68. Workload-Zustand wiederherstellen
69. Dashboard und CLI prüfen
70. Restore-Runbook dokumentieren
71. Upgrade vorbereiten
72. Upgrade durchführen
73. Datenmigration prüfen
74. API-Kompatibilität prüfen
75. Workload nach Upgrade prüfen
76. Dienste nach Upgrade prüfen
77. Rollback ausführen
78. Zustand nach Rollback prüfen
79. Downgrade-Grenzen dokumentieren
80. Upgrade-Runbook abschließen
81. Testlast festlegen
82. kontrollierten Load-Test starten
83. CPU-/RAM-Grenzen messen
84. Controller-Stabilität messen
85. etcd-Stabilität messen
86. begrenzten Soak-Test ausführen
87. Fehlerlogs und Leaks prüfen
88. Security-/Dependency-Checks abschließen
89. SBOM erzeugen
90. signierte Artefakte und Provenienz erzeugen
91. Evidenz auf denselben Commit prüfen
92. Paket-Digests abgleichen
93. Testberichte zusammenführen
94. Einschränkungen veröffentlichen
95. Installations-/Troubleshooting-Doku prüfen
96. RC zur Maintainer-Prüfung vorlegen
97. Maintainer-Feedback einarbeiten
98. Go-/No-Go-Entscheidung dokumentieren
99. Production-Release veröffentlichen
100. productionReady=true nur für geprüften Kandidaten setzen

### Produktionsentscheidung

Der Release bleibt `no-go`, bis alle 100 Punkte für denselben unveränderten RC nachgewiesen sind. Die sieben VMs sind kein Blocker, weil HA/Multi-Host außerhalb des ersten Scopes liegen. `productionReady=true` darf ausschließlich nach Maintainer-Prüfung und finaler Go-/No-Go-Entscheidung gesetzt werden.
