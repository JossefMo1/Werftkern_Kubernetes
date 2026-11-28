Warning: truncated output (original token count: 63404)
Total output lines: 1390

## 2026-11-28 — Persistierte Events gegen Unicode-Steuerzeichen härten (PR #518)

- **Security/Runtime:** `Event.Validate` verwendet jetzt die zentrale `model.ValidReason`-Regel. Persistierte Event-Aktionen und -Ziele werden damit nicht nur auf NUL, CR, LF und TAB, sondern auf sämtliche Unicode-Control-Characters geprüft; ANSI-ESC- und U+0085-Injection werden vor Status-, Dashboard- und Log-Ausgabe fail-closed abgewiesen.
- **QA/SDET:** Neue Modell-Regressionen decken ANSI-ESC und U+0085 ab. GitHub Actions Native/runtime [Run 46142366611](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366611) bestand mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366611/job/140970916553) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366611/job/140970916301); Kubernetes-Verträge [Run 46142366641](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366641) und Source/Privacy [Run 46142366642](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366642) bestanden. Die Schritte für historische dev.3-Kompatibilität und ephemere Signaturprüfung waren erwartungsgemäß übersprungen.
- **Release:** `real-vm` ([Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366611/job/140971457727)) und `real-PITR` ([Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46142366611/job/140971457014)) wurden übersprungen. Diese automatisierte Evidenz schließt kein Live-Single-Host-Production-Gate; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.
- **Nächster Handoff:** Einen unveränderlichen RC aus Main [96e0a901c4eab232bc15ba97278e8800f6af7ab9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/96e0a901c4eab232bc15ba97278e8800f6af7ab9) bauen und Installation, Docker-/etcd-Lifecycle, Backup/Restore, Upgrade/Rollback, Load/Soak sowie signierte Provenienz auf demselben Kandidaten nachweisen. Der veraltete `v0.2.0-dev.4-test.17`-Kandidat bleibt unqualifiziert.

## 2026-11-28 — Heartbeat-/Persistenzgründe gegen Steuerzeichen härten (PR #515)

[PR #515](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/515) wurde als [ca2c8ca8230826708f76de4e0b6f634b2ed81f7a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ca2c8ca8230826708f76de4e0b6f634b2ed81f7a) gemergt. Der autorisierte Heartbeat- und Persistenzpfad verwendet jetzt eine gemeinsame `model.ValidReason`-Prüfung mit 100-Zeichen-Grenze und Ablehnung von Unicode-Steuerzeichen. NUL, ESC, TAB und Newline werden vor Persistenz oder Dashboard-/CLI-Ausgabe fail-closed abgewiesen; Workload- und Allocation-Inventur validiert gespeicherte Gründe erneut. Modell-, Persistenz- und Endpoint-Regressionstests prüfen zusätzlich, dass ein abgelehnter Heartbeat den Allocation-Zustand nicht verändert.

Die finalen GitHub-Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137477003) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137477003/job/140955904209) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137477003/job/140955904014), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137476952) sowie [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137476959). [Real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137477003/job/140956341132) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46137477003/job/140956340877) wurden übersprungen. Das ist automatisierte Evidenz; kein Live-Single-Host-Production-Gate ist geschlossen. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` ist weiterhin veraltet, unsigniert und nicht unveränderlich. Offen bleiben ein neuer unveränderlicher Kandidaten-Build mit Paket-/Artefakt-Digests, frische Ubuntu-Installation, Docker-/etcd-Lifecycle mit Neustarts, positiver Backup/Restore-Nachweis, Upgrade/Rollback, Load/Soak, SBOM/Vulnerability-Abschluss, Signierung/Provenienz und Maintainer-Freigabe.

Nächster Schritt: einen unveränderlichen Kandidaten exakt aus Main **ca2c8ca8230826708f76de4e0b6f634b2ed81f7a** bauen und erst danach den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` auf genau diesem Kandidaten ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 — Persistierte Node-Kapazitäten fail-closed begrenzen (PR #513)

[PR #513](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/513) wurde als [f1d8bb41e4cc389b2e3fef9d194685b359fa7a95](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f1d8bb41e4cc389b2e3fef9d194685b359fa7a95) gemergt. Das Modell verwendet jetzt gemeinsame CPU-/RAM-Obergrenzen für Heartbeat-Admission und die Validierung persistierter Node-Inventur. Negative oder unrealistisch große Kapazitäten werden vor Scheduler-Entscheidungen mit `NODE_CAPACITY_INVALID` zurückgewiesen; uninitialisierte Registrierungs-Nodes mit 0/0 und die dokumentierten Maximalgrenzen bleiben gültig. Der Regressionstest deckt beide ungültigen Richtungen und die gültigen Grenzen ab.

Die finalen GitHub-Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790805) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790805/job/140941440782) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790805/job/140941440689), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790971) sowie [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790827). [Real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790805/job/140941924545) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46132790805/job/140941924730) wurden übersprungen. Das ist automatisierte Evidenz; kein Live-Single-Host-Production-Gate ist geschlossen. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` ist weiterhin veraltet, unsigniert und nicht unveränderlich. Offen bleiben ein neuer unveränderlicher Kandidaten-Build mit Paket-/Artefakt-Digests, frische Ubuntu-Installation, Docker-/etcd-Lifecycle mit Neustarts, positiver Backup/Restore-Nachweis, Upgrade/Rollback, Load/Soak, SBOM/Vulnerability-Abschluss, Signierung/Provenienz und Maintainer-Freigabe.

Nächster Schritt: einen unveränderlichen Kandidaten exakt aus Main **f1d8bb41e4cc389b2e3fef9d194685b359fa7a95** bauen und erst danach den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` auf genau diesem Kandidaten ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 — Strict-JSON-Migration gegen doppelte Mitglieder (PR #511)

[PR #511](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/511) wurde als [268dee48c1d02f6a9481194ae91ba18a81438a1e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/268dee48c1d02f6a9481194ae91ba18a81438a1e) gemergt. Der Offline-Schema-Migrationspfad validiert die vollständigen Quellbytes jetzt vor der typisierten Dekodierung mit dem bestehenden Strict-JSON-Vertrag. Doppelte oder case-foldierte JSON-Mitglieder werden fail-closed abgewiesen; dadurch kann kein mehrdeutiger last-member-wins-Inhalt mit einem Quellhash migriert werden. Der neue Regressionstest deckt ein doppeltes `clusterId`-Mitglied ab.

Die finalen Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348680) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348680/job/140927874322) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348680/job/140927874140), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348659) sowie [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348685). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348680/job/140928337734) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46128348680/job/140928338032) wurden übersprungen. Damit ist kein Live-Single-Host-Production-Gate geschlossen; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. Offen bleiben unveränderlicher Kandidaten-Build/Digest, frische Ubuntu-Installation, Docker-/etcd-Lifecycle mit Neustarts, positiver Backup/Restore-Nachweis, Upgrade/Rollback, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Freigabe.

Nächster Schritt: einen unveränderlichen Kandidaten aus Main **268dee48c1d02f6a9481194ae91ba18a81438a1e** bauen und erst danach den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` auf genau diesem Kandidaten ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 – Strictes Schema-Migrations-Replay fail-closed (PR #509)

[PR #509](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/509) wurde als [a92ad2141b36c7699a49d37ebb8e358599e6c165](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a92ad2141b36c7699a49d37ebb8e358599e6c165) gemergt. Der Offline-Schema-Migrations-Replay verwendet für bereits migrierte Zustände jetzt denselben Strict-JSON-Vertrag wie der Etcd-Read-Pfad. Unbekannte oder eingeschleuste Persistenzfelder werden dadurch im Idempotenzpfad fail-closed zurückgewiesen, statt eine nicht mehr lesbare Persistenz als bereits erledigt zu bestätigen. Der Regressionstest injiziert ein unbekanntes Feld per Compare-and-Swap in das reale Etcd-Test-Setup und prüft zusätzlich, dass kein Migrations-Callback läuft.

Die finalen GitHub-Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251718) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251718/job/140918313165) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251718/job/140918313281), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251703) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251681). [Real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251718/job/140918837810) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46125251718/job/140918837993) wurden übersprungen; dafür wird kein Live-Nachweis behauptet. Diese automatisierte Evidenz schließt kein Live-Single-Host-Production-Gate; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. Der aktuelle Main-Code-Stand ist [a92ad2141b36c7699a49d37ebb8e358599e6c165](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a92ad2141b36c7699a49d37ebb8e358599e6c165); die neuen automatisierten Nachweise dürfen nicht rückwirkend auf test.17 übertragen werden. Offen bleiben unveränderlicher RC und Paket-/Artefakt-Digests, frische Ubuntu-Installation, Docker-/etcd-Lifecycle mit Neustarts, positiver Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM-/Vulnerability-Abschluss, Signierung/Provenienz sowie Maintainer-Go/No-Go.

Nächster Schritt: einen unveränderlichen Kandidaten aus diesem Main-Commit bauen und den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` auf genau diesem Kandidaten ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 – Volume-Restore-Maintenance-Bindung fail-closed (PR #507)

[PR #507](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/507) wurde als [3e5c2e45ec2400f6e49005e69560c108e407862e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3e5c2e45ec2400f6e49005e69560c108e407862e) gemergt. Eine reservierte Volume-Wiederherstellung speichert jetzt dauerhaft die Maintenance-ID, die das Volume quiesziert hat. Replay oder administrative Bestätigung unter einer späteren Maintenance-Übergabe wird fail-closed mit `VOLUME_RESTORE_MAINTENANCE_MISMATCH` abgewiesen. Legacy-Snapshots bleiben lesbar; ungebundene alte Restore-Reservierungen dürfen jedoch nicht erneut bestätigt werden. Der Regressionstest deckt genau diese Übergabegrenze ab.

Die finalen GitHub-Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46123654516) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46123654516/job/140913373907) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46123654516/job/140913374156), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46123654515) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46123654506). Real-vm und real-PITR wurden übersprungen; dafür wird kein Live-Nachweis behauptet. Diese automatisierte Evidenz schließt kein Live-Single-Host-Production-Gate; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. Der nächste Kandidatenstand ist der unveränderte Main-Commit [3e5c2e45ec2400f6e49005e69560c108e407862e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3e5c2e45ec2400f6e49005e69560c108e407862e). Offen bleiben frische Ubuntu-Installation, Docker-/etcd-Lifecycle, positiver Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM-/Vulnerability-Abschluss, Signierung/Provenienz und Maintainer-Go/No-Go.

Nächster Schritt: einen unveränderlichen Kandidaten aus diesem Main-Commit bauen und den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` auf genau diesem Kandidaten ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 – SBOM-Quellidentität fail-closed (PR #498)

[PR #498](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/498) wurde als [8f2f8dfed8073e449b7c9076f9a7d5e7a0e8d2fd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8f2f8dfed8073e449b7c9076f9a7d5e7a0e8d2fd) gemergt. Die Native-SBOM-Erzeugung verlangt jetzt einen vollständigen 40-stelligen kleingeschriebenen Source-Commit-SHA und weist Symlink-Pfade für Debian-Pakete zurück. Damit kann ein SBOM-Nachweis nicht mehr mit einer mehrdeutigen verkürzten Git-Identität oder einem indirekt aufgelösten Paketpfad erzeugt werden. Der Vertrag entspricht nun dem bereits strengeren Native-Release-Manifest.

Die finalen GitHub-Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178573) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178573/job/140840598387) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178573/job/140840598258), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178592) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178605). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178573/job/140841101550) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46100178573/job/140841101422) wurden übersprungen. Die Evidenz ist automatisiert und schließt kein Live-Single-Host-Production-Gate; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der Kandidatenstand bleibt unverändert: `v0.2.0-dev.4-test.17` ist veraltet, unsigniert und nicht unveränderlich; der einzufrierende candidate-bearing Quellstand bleibt `e6602a54f1f0efdc8a6b6a6840d92904f2078601`. Offen bleiben immutable RC-Digest, frische Ubuntu-Installation, Docker-/etcd-Lifecycle, positiver Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM-/Vulnerability-Abschluss, Signierung/Provenienz und Maintainer-Go/No-Go.

Nächster Schritt: einen unveränderlichen Kandidaten aus dem eingefrorenen candidate-bearing Quellstand bauen und den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 – Upgrade-Abschluss-Failure-Boundary (PR #496)

[PR #496](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/496) wurde als [90d60ffb13e20c8e283fc13c601006291ecf981b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/90d60ffb13e20c8e283fc13c601006291ecf981b) gemergt. Die QA-Regressionsabdeckung prüft zwei bereits implementierte Fail-Closed-Grenzen des nativen Upgrade-Abschlusses: Eine gemischte Controller-Gesundheitsantwort mit einem Peer auf falscher Zielversion darf keine Runtime-Qualifikation oder Entsperrung auslösen; ein Wechsel der Maintenance-Identität zwischen frischen Beobachtungen muss den Abschluss abbrechen und das Journal gesperrt lassen.

Die finalen GitHub-Prüfungen bestanden: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881606) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881606/job/140826988568) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881606/job/140826988925), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881508) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881484). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881606/job/140827757486) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46095881606/job/140827756580) wurden übersprungen. Das ist automatisierte Regressionsevidenz und schließt kein Live-Single-Host-Production-Gate; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Der Kandidatenstand bleibt unverändert: Der alte `v0.2.0-dev.4-test.17` ist veraltet, unsigniert und nicht unveränderlich; der eingefrorene candidate-bearing Quellstand bleibt `e6602a54f1f0efdc8a6b6a6840d92904f2078601`. Offen bleiben unveränderlicher RC-Digest, frische Ubuntu-Installation, Docker-/etcd-Lifecycle, positiver Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Go/No-Go.

Nächster Schritt: einen unveränderlichen Kandidaten aus dem eingefrorenen candidate-bearing Quellstand bauen und den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-28 – PITR-Backup-Zeitfenster fail-closed (PR #494)

[PR #494](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/494) wurde als [1e3c51352db7a753e3d6fbdc05bedb1993df35d0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1e3c51352db7a753e3d6fbdc05bedb1993df35d0) gemergt. `backup_identity` akzeptiert jetzt nur Katalogeinträge mit positivem Startzeitpunkt und einem strikt späteren Stopzeitpunkt. Regressionen in `tests/ops/test_pitr.py` weisen fehlende/ungültige Startzeiten sowie ein leeres Zeitfenster zurück. Dadurch kann eine manipulierte pgBackRest-Katalogantwort keine intern widersprüchliche PITR-Identität erzeugen.

Die automatisierten PR-Prüfungen bestanden: [Native/runtime + Package-Smoke](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637138) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637138/job/140810469597) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637138/job/140810469383), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637151) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637159). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637138/job/140811096036) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46090637138/job/140811095923) wurden übersprungen. Diese Evidenz ist automatisiert und schließt kein Live-Single-Host-Production-Gate; `productionReady=false`, Go/No-Go bleibt `no-go`.

Der Kandidaten-Quellstand bleibt `e6602a54f1f0efdc8a6b6a6840d92904f2078601`; `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. Offen bleiben gleichkandidater RC-Digest, frische Ubuntu-Installation, Docker-/etcd-Lifecycle, positiver Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Go/No-Go.

## 2026-11-28 – Worker-Upgrade-Scope-Fail-Closed (PR #492)

[PR #492](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/492) wurde als [21550cc71af767b0ea0090ca2c9e809efd8797bc](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/21550cc71af767b0ea0090ca2c9e809efd8797bc) gemergt. Die neuen Regressionen in `tests/ops/test_worker_upgrade.py` schützen zwei Single-Host-Betriebsinvarianten: Nach dem Stop eines Workers blockiert eine geänderte Maintenance-Identität die Installation und den Neustart mit `OWNED_DRAINED_EMPTY_NODE_REQUIRED`; ein bereits persistiertes, passendes Installations-Replay-Receipt führt weder erneut `dpkg` noch einen Dienststart aus. Die Tests prüfen damit den fail-closed Upgrade-/Rollback-Rand und vermeiden doppelte Paket- oder Dienstmutationen.

Die automatisierten PR-Prüfungen bestanden: [Native/runtime + Package-Smoke](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794744) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794744/job/140791735638) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794744/job/140791735953), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794743) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794740). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794744/job/140792330276) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46084794744/job/140792330039) wurden übersprungen. Das ist belastbare automatisierte Regressionsevidenz, aber kein Live-Single-Host-Production-Gate; `productionReady=false` und Go/No-Go bleibt `no-go`.

Der eingefrorene Kandidaten-Quellstand bleibt `e6602a54f1f0efdc8a6b6a6840d92904f2078601`; der veröffentlichte `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. Offen bleiben unveränderlicher Build/Digest, Ubuntu-Installation, Docker-/etcd-Lifecycle mit Neustarts, positiver Backup/Restore, Upgrade/Rollback auf demselben Kandidaten, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Go/No-Go.

Nächster Schritt: aus dem eingefrorenen Quellstand einen unveränderlichen Kandidaten bauen und den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` ausführen. HA/Multi-Host, Quorum/Partition, Kubernetes-Production, Cloud-/Site-Recovery, DB-HA, GPU, Air-Gap und hostile Multi-Tenancy bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-27 – Upgrade-/Rollback-Fail-Closed-Regression (PR #488)

- PR #488 merged as `b81c30530662d8190d0ebe78018c32cf9d2dee74`.
- `tests/ops/test_upgrade.py::test_recover_package_identity_mismatch_keeps_explicit_recovery_locked` proves that a signed repair package with a mismatching Debian identity fails after the durable maintenance lock, leaves the journal at `explicit-recovery`, and performs no service stop/start or `dpkg` mutation.
- Native/runtime, Kubernetes and Source/Privacy checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46079217499), [test job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46079217499/job/140774018307), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46079217499/job/140774017972), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46079217544), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46079217501).
- The real-vm and real-PITR jobs were skipped. This is automated regression evidence only and closes no live Single-Host production gate.
- Countdown remains **9/100**; `productionReady=false`, decision `no-go`.

## 2026-11-27 — Negativer Same-Cluster-Restore im Native-E2E (PR #486)

[PR #486](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/486) wurde als [8b57afb5fb113a713ec2cd25ec088218971765a9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8b57afb5fb113a713ec2cd25ec088218971765a9) gemergt. Der echte Ubuntu-E2E-Harness erstellt und inspiziert nun ein verschlüsseltes logisches Backup und versucht anschließend bewusst eine Wiederherstellung in dieselbe Cluster-Identität. Der Versuch muss mit `RESTORE_REQUIRES_A_NEW_CLUSTER_IDENTITY` fail-closed scheitern; Generation, Phase und Pausenstatus des laufenden Workloads werden vor und nach dem Fehlversuch verglichen. Dadurch wird kein Restore in den Quellzustand als scheinbar sichere Aktion akzeptiert.

Die finalen PR-Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46073921187) mit [Test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46073921187/job/140757086611) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46073921187/job/140757086160), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46073921697) sowie [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46073921258). Real-VM und real-PITR wurden übersprungen; dadurch ist kein Live-Single-Host-Production-Gate geschlossen.

`productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der alte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. Offen bleiben unveränderlicher Kandidaten-Build/Digest-Abgleich, frische Ubuntu-Installation, positiver Backup/Restore-Nachweis, Upgrade/Rollback, Load/Soak, Signierung/Provenienz, Maintainer-Feedback und finale Entscheidung.

Nächster Schritt: einen unveränderlichen Kandidaten aus Main **8b57afb5fb113a713ec2cd25ec088218971765a9** bauen und den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` ausführen. Der dokumentierte Tag-/`workflow_dispatch`-Berechtigungsblocker wird nicht wiederholt; HA/Multi-Host, Quorum und Kubernetes-Production bleiben Erweiterungspfade außerhalb des ersten Releases.

## 2026-11-27 — Digest-gebundenes Native-Kandidatenmanifest (PR #482)

[PR #482](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/482) wurde als [56fdfe6130f7e04a41b9589cf0636aa93a5204d0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/56fdfe6130f7e04a41b9589cf0636aa93a5204d0) gemergt. Der CI-Pfad erzeugt jetzt aus dem exakten Debian-Paket und dem SPDX-SBOM ein deterministisches Native-Release-Manifest und eine eigene Manifest-Checksumme. Das Manifest bindet Source-Commit, SOURCE_DATE_EPOCH, Paket-Digest, SBOM-Digest, Namespace und Paketmetadaten; es kennzeichnet ausdrücklich `qualified=false` und `signed=false`. Dadurch wird Supply-Chain-Evidenz reproduzierbar vorbereitet, aber kein Live-Single-Host-Production-Gate geschlossen.

Die finalen Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335149) mit [Test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335149/job/140735833371) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335149/job/140735833571), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335178) sowie [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335203). [Real-VM](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335149/job/140736700528) und [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46067335149/job/140736699949) wurden übersprungen; kein Live-Gate ist geschlossen.

[PR #483](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/483) synchronisierte den Production-Tracker auf den aktuellen Main [497dcb89633b6cf3797ee443d56d8e4a7a811ac2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/497dcb89633b6cf3797ee443d56d8e4a7a811ac2). `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der runtime-relevante Kandidatenpfad umfasst PR #479 und PR #482; der alte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich.

Nächster Schritt: unveränderlichen Kandidaten aus dem aktuellen Main [497dcb89633b6cf3797ee443d56d8e4a7a811ac2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/497dcb89633b6cf3797ee443d56d8e4a7a811ac2) bauen und den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` ausführen. Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM-/Vulnerability-Abschluss, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen. Der dokumentierte Tag-/`workflow_dispatch`-Berechtigungsblocker wird nicht wiederholt.

## 2026-11-27 — Docker-Engine-Neustart im Native-E2E (PR #479)

[PR #479](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/479) wurde als [ba2b820d735c71a2681fc7b0636fecac5800890e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ba2b820d735c71a2681fc7b0636fecac5800890e) gemergt. Der Ubuntu-24.04-E2E-Harness führt nach dem erfolgreichen Workload-Lifecycle jetzt einen echten `systemctl restart docker.service` aus und prüft anschließend erneut den Zustand, die Endpunkte und die Container-Identitäten. Damit ist der Docker-Neustart als reproduzierbarer Testschritt im Kandidatenpfad verankert; ein Live-Gate ist dadurch noch nicht geschlossen.

Die automatisierten Prüfungen bestanden in [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591366) mit [Test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591366/job/140713614867) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591366/job/140713615283), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591343) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591347). Der [real-vm-Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591366/job/140714463881) und der [real-PITR-Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46060591366/job/140714463938) wurden übersprungen; Fixture-/CI-Erfolg ersetzt keinen echten Ubuntu-Lauf.

[PR #480](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/480) synchronisierte anschließend den Production-Tracker und wurde als [05365d711f1e7a0b3a09ed8407aa0749b78e7488](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/05365d711f1e7a0b3a09ed8407aa0749b78e7488) gemergt. Der unveränderte runtime- und E2E-relevante Kandidatenstand bleibt [ba2b820d735c71a2681fc7b0636fecac5800890e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ba2b820d735c71a2681fc7b0636fecac5800890e); der aktuelle Main enthält zusätzlich nur die Tracker-Synchronisation.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Offen bleiben: unveränderlicher Build und Digest-Abgleich, Ubuntu-Installation, Docker-/etcd-Lifecycle auf einem frischen Host, Backup/Restore, Upgrade/Rollback, begrenzter Load-/Soak-Test, SBOM, Signierung/Provenienz, Maintainer-Prüfung, Feedback und finale Go-/No-Go-Entscheidung. HA/Multi-Host, Quorum und Kubernetes-Production bleiben Erweiterungspfade außerhalb des ersten Releases.

Nächster Schritt: einen unveränderlichen Kandidaten aus dem runtime-relevanten Stand [ba2b820d735c71a2681fc7b0636fecac5800890e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ba2b820d735c71a2681fc7b0636fecac5800890e) bauen und den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` ausführen. Tag- und `workflow_dispatch`-Berechtigungsblocker werden nicht wiederholt.

## 2026-11-27 — Native-Inventur und redigierte State-Antworten fail-closed (PR #474)

[PR #474](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/474) wurde als [d6d730d6f9e4825023a5bbf47cc9ffde62911340](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d6d730d6f9e4825023a5bbf47cc9ffde62911340) gemergt. `ValidateNativeSingleHost()` prüft nun auch die vollständige persistierte Inventur; dadurch werden manipulierte Workload-, Node- und Allocation-Records außerhalb des etcd-CAS-Pfads abgewiesen. Der Go-Client validiert redigierte `GET /v1/state`-Projektionen mit demselben Inventurvertrag, ohne bewusst entfernten Secret-Ciphertext fälschlich als Fehler zu behandeln. Regressionen decken mutable Images, nicht-private Node-Adressen und redigierte/exponierte Secret-Felder ab.

Der finale PR-Lauf bestand mit [Native/runtime + Package-Smoke](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876961) ([test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876961/job/140688356091), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876961/job/140688356485)), [Kubernetes-Verträgen](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876993) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876906). Real-VM ([Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876961/job/140689199482)) und real-PITR ([Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876961/job/140689198472)) wurden übersprungen; kein Live-Single-Host-Production-Gate ist geschlossen. Ein früherer PR-Stand scheiterte am Secret-Projection-Regressionstest und wurde vor dem Merge korrigiert.

Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der Tag-/`workflow_dispatch`-Berechtigungsblocker bleibt einmalig dokumentiert und wird nicht wiederholt.

Nächster Release-Schritt: unveränderlichen Kandidaten aus dem aktuellen Main-Commit [d6d730d6f9e4825023a5bbf47cc9ffde62911340](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d6d730d6f9e4825023a5bbf47cc9ffde62911340) erstellen und den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` ausführen. Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen.

## 2026-11-27 — Persistierte Event-Records fail-closed (PR #471)

[PR #471](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/471) wurde als [bea5189499275880d66c3c486d1ebc0f98232945](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bea5189499275880d66c3c486d1ebc0f98232945) gemergt. Das State-Modell validiert persistierte Event-IDs, Zeitstempel sowie begrenzte control-freie Action-/Target-Texte jetzt vor Status-Ausgabe, Reconciliation und Backup. Manipulierte Log-/Terminal-Injection-Daten werden mit `EVENT_RECORD_INVALID` abgewiesen; Regressionen liegen in [internal/model/model_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/bea5189499275880d66c3c486d1ebc0f98232945/internal/model/model_test.go).

Die exakten Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46046079313), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46046079314) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46046079372). Real-VM und real-PITR wurden übersprungen; diese State-Härtung schließt kein Live-Single-Host-Production-Gate. Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich; `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**.

Nächster Release-Schritt: unveränderlichen Kandidaten aus dem aktuellen Runtime-Commit `bea5189499275880d66c3c486d1ebc0f98232945` erstellen und den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` ausführen. Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen.

## 2026-11-27 — Überlappende persistierte Node-PodCIDRs fail-closed (PR #468)

[PR #468](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/468) wurde als [f2c13bd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f2c13bd3360308ab516b553ae46f0f8a4ac5e857) gemergt. Die persistierte Inventur weist jetzt überlappende gültige PodCIDRs zwischen Nodes mit `NODE_POD_CIDR_CONFLICT` zurück; leere PodCIDRs bleiben für zurückgestellte Profile zulässig. Die Registrierung hatte diese Überschneidung bereits abgewiesen, nun gilt dieselbe Invariante auch für Import, Backup und Commit-Validierung. Regressionen für disjunkte und überlappende Netze liegen in [internal/model/model_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/f2c13bd3360308ab516b553ae46f0f8a4ac5e857/internal/model/model_test.go).

Die exakten Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810984) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810984/job/140637570939) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810984/job/140637571296), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810956) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810943). Real-VM ([Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810984/job/140638597428)) und real-PITR ([Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810984/job/140638595211)) wurden übersprungen; kein Live-Single-Host-Production-Gate ist geschlossen. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich.

Nächster Schritt: einen unveränderlichen Kandidaten aus dem aktuellen Main-/Runtime-Stand `f2c13bd3360308ab516b553ae46f0f8a4ac5e857` bauen und den autorisierten Ubuntu-24.04-Pfad mit `run_real_vm_e2e=true` ausführen. HA, Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

## 2026-11-27 — Persistierte Allocation-Kollisionen fail-closed (PR #465)

[PR #465](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/465) wurde als [e49ffb3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e49ffb3910f2359c81fc0e4aef24165d6d061d88) gemergt. Die persistierte Inventur weist jetzt doppelte nicht-null HostPorts auf demselben Node sowie doppelte Container-IPs fail-closed zurück. HostPort 0 bleibt ein expliziter, nicht veröffentlichter Legacy-Zustand; HostPorts werden pro Node bewertet. Regressionen liegen in [internal/model/model_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/e49ffb3910f2359c81fc0e4aef24165d6d061d88/internal/model/model_test.go). Damit sind Architektur, Backend/Runtime, Security und QA gegen persistierte Endpoint-Kollisionen abgesichert.

Die exakten Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46029185204) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46029185204/job/140608304585) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46029185204/job/140608305158), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46029185179) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46029185171). Real-VM und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist geschlossen. productionReady=false, Go/No-Go bleibt no-go, Countdown **9/100**. Der veröffentlichte Kandidat v0.2.0-dev.4-test.17 bleibt veraltet, unsigniert und nicht unveränderlich.

Nächster Schritt: einen unveränderlichen Kandidaten aus Main e49ffb3910f2359c81fc0e4aef24165d6d061d88 bauen und den autorisierten Ubuntu-24.04-Pfad mit run_real_vm_e2e=true ausführen; danach Installation, Docker/etcd-Lifecycle, Backup/Restore, Upgrade/Rollback, Load/Soak sowie SBOM, Signatur und Provenienz auf demselben Kandidaten belegen. Der Tag-/workflow_dispatch-Berechtigungsblocker bleibt dokumentiert und wird nicht wiederholt. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

## 2026-11-27 — Persistierte Allocation-Endpunkte fail-closed (PR #462)

[PR #462](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/462) wurde als [72d4006](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/72d40068e212bc16097e1e01c238bed35fb95173) gemergt. Die persistierte Inventur weist nicht aufgelöste, aber nicht veröffentlichte HostPort-Werte (0) weiterhin als Legacy-Zustand aus und lehnt jeden nicht-null HostPort außerhalb des Scheduler-Bereichs **22000–22999** sowie jede Container-IP außerhalb des PodCIDR des eingeschriebenen Nodes fail-closed ab. Der Regressionstest liegt in [internal/model/model_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/72d40068e212bc16097e1e01c238bed35fb95173/internal/model/model_test.go). Damit sind Architecture, Backend/Runtime, Security und QA für diesen Persistenzrand synchronisiert.

Die exakten Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46020683219) mit [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46020683219/job/140579238073) und [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46020683219/job/140579238447), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46020683085) sowie [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46020683070). Real-VM und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist geschlossen. productionReady=false, Go/No-Go bleibt no-go, Countdown **9/100**. Der veröffentlichte Kandidat v0.2.0-dev.4-test.17 bleibt veraltet, unsigniert und nicht unveränderlich.

Nächster Schritt: einen unveränderlichen Kandidaten aus Main 72d40068e212bc16097e1e01c238bed35fb95173 bauen und den autorisierten Ubuntu-24.04-Pfad mit run_real_vm_e2e=true ausführen; anschließend Installation, Docker/etcd-Lifecycle, Backup/Restore, Upgrade/Rollback, begrenzten Load/Soak und Signatur/Provenienz auf demselben Kandidaten belegen. Der Tag-/workflow_dispatch-Berechtigungsblocker bleibt dokumentiert und wird nicht wiederholt. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

## 2026-11-27 — Discovery-Endpoints fail-closed (PR #458)

[PR #458](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/458) wurde als [8e44af0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8e44af05417c39a73610890f474180b040b3d980) gemergt. Host-geroutete Discovery-Endpunkte werden jetzt nur im Scheduler-Portbereich **22000–22999** veröffentlicht; Port 0, privilegierte Ports und Bereichsüberschreitungen werden vor CLI-/Dashboard-Ausgabe verworfen. Die Regressionen liegen in `internal/discovery/zone_test.go`.

Die finalen PR-Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46011079766), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46011079783) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46011079925). Real-VM und real-PITR wurden übersprungen; damit ist **kein** Live-Single-Host-Production-Gate geschlossen. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der alte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich.

Nächster Schritt: unveränderlichen Kandidaten aus Native Main `8e44af05417c39a73610890f474180b040b3d980` bauen und den autorisierten Ubuntu-24.04-`run_real_vm_e2e=true`-Pfad ausführen. Der Tag-/`workflow_dispatch`-Berechtigungsblocker bleibt dokumentiert und wird nicht wiederholt; HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfad.

## 2026-11-27 — Discovery-CLI-Eingaben fail-closed (PR #455)

- [PR #455](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/455) wurde als [9411d9a421b7161348338e7a773e3e564d772cb5](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/9411d9a421b7161348338e7a773e3e564d772cb5) gemergt. Der Native-CLI-Befehl `discovery` weist unerwartete Positionsargumente jetzt vor dem Laden der Agent-Konfiguration mit `DISCOVERY_ARGUMENTS_INVALID` zurück. Der Regressionstest liegt in `internal/cli/cli_test.go`.
- Der finale PR-Stand [2d285db9d1144d2a4a7cd067d923e9a03820fb08](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2d285db9d1144d2a4a7cd067d923e9a03820fb08) bestand [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46001736642) mit [real-etcd-Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46001736642/job/140514823272), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46001736915) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46001736530). real-vm und real-PITR wurden übersprungen.
- Kein Live-Single-Host-Production-Gate wurde geschlossen. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt veraltet, unsigniert und nicht unveränderlich; HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfad.
- Nächster Schritt: unveränderlichen Kandidaten aus Native-Main [9411d9a421b7161348338e7a773e3e564d772cb5](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/9411d9a421b7161348338e7a773e3e564d772cb5) bauen und den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` ausführen. Der Tag-/`workflow_dispatch`-Berechtigungsblocker bleibt dokumentiert und wird nicht wiederholt.

## 2026-11-27 — Volume-CLI-Eingaben fail-closed (PR #452)

- [PR #452](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/452) wurde als [89cd8c352d1d9d72bc3201462ac9e5a868c487fb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/89cd8c352d1d9d72bc3201462ac9e5a868c487fb) gemergt. Der Native-CLI-Pfad `volume list/create/release` weist unerwartete Positionsargumente ab und validiert Volume-Namen, Node-/Identitäts-IDs sowie UID/GID-Grenzen, bevor Konfiguration geladen oder das Netzwerk angesprochen wird. Regressionen stehen in `internal/cli/cli_test.go`.
- Der finale PR-Stand [96b3c1f2eb96b8f48e65cb138152e570a0dd5798](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/96b3c1f2eb96b8f48e65cb138152e570a0dd5798) bestand [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45994517282; real-etcd-Job https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45994517282/job/140490427375), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45994517512) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45994517362); real-vm und real-PITR wurden übersprungen. Ein früherer PR-Stand scheiterte am Compile-Check und wurde vor dem erfolgreichen finalen Lauf korrigiert.
- Dies schließt kein Live-Single-Host-Production-Gate. `productionReady=false`, Go/No-Go bleibt `no-go`, Countdown **9/100**. Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt für diesen Code veraltet, unsigniert und nicht unveränderlich; HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfad.
- Nächster Schritt: unveränderlichen Kandidaten aus Main `89cd8c352d1d9d72bc3201462ac9e5a868c487fb` bauen und anschließend den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` ausführen. Der Tag/\`workflow_dispatch\`-Berechtigungsblocker bleibt dokumentiert und wird nicht wiederholt.

## 2026-11-27 — Maintenance-CLI-Argumente fail-closed (PR #449)

- [PR #449](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/449) wurde als [5e5f1fd93d4618bd9e187615fffdb08fbee0a9e1](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5e5f1fd93d4618bd9e187615fffdb08fbee0a9e1) gemergt. Der Native-Befehl `maintenance` lehnt unerwartete Positionsargumente sowie ungültige/fehlende Operation-ID und Reason lokal ab, bevor Admin-Konfiguration oder Netzwerkzugriff erfolgt; die bisherige Prüfung ungültiger Aktionen bleibt erhalten. Regressionen sind in `internal/cli/cli_test.go` dokumentiert.
- Exakte PR-Prüfungen: [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242284), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242341) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242331) erfolgreich; der [real-etcd-Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242284/job/140462483976) war erfolgreich. real-vm und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist dadurch geschlossen.
- Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt auf `28efa7518e171a618d4dcf9ff3aba58cddaf3296` gebunden, veraltet, unsigniert und nicht unveränderlich. `productionReady=false`, Go/No-Go bleibt No-Go; Countdown **9/100**. Sieben-VM-HA, Quorum und Kubernetes-Production bleiben außerhalb des ersten Scopes.
- Nächster Schritt: unveränderlichen Kandidaten aus Main `5e5f1fd93d4618bd9e187615fffdb08fbee0a9e1` bauen und anschließend den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` starten. Der Tag/`workflow_dispatch`-Berechtigungsblocker bleibt dokumentiert und wird nicht wiederholt.

## 2026-11-27 — Recovery-Seal nil-State fail-closed (PR #446)

- [PR #446](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/446) wurde als [cdfc82d970eef770157ae9c41d9bafa142d90707](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cdfc82d970eef770157ae9c41d9bafa142d90707) gemergt. `internal/recovery.Seal` weist einen nil-`State` jetzt deterministisch mit `BACKUP_STATE_INVALID` zurück, bevor `ValidateInventory()` aufgerufen wird; damit bleibt die Backup-Grenze auch bei fehlerhaften Aufrufern panic-frei. Ein Regressionstest deckt den Fehlercode ab.
- Exakte PR-Prüfungen: [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295315), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295203) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295206) erfolgreich; der [real-etcd-Job](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295315/job/140432117768) war erfolgreich. real-vm und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist dadurch geschlossen.
- Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt auf `28efa7518e171a618d4dcf9ff3aba58cddaf3296` gebunden, veraltet, unsigniert und nicht unveränderlich. `productionReady=false`, Go/No-Go bleibt No-Go; Countdown **9/100**. Sieben-VM-HA, Quorum und Kubernetes-Production bleiben außerhalb des ersten Scopes.
- Nächster Schritt: unveränderlichen Kandidaten aus Main `cdfc82d970eef770157ae9c41d9bafa142d90707` bauen und anschließend den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` starten. Der Connector kann den autorisierten Tag bzw. `workflow_dispatch` nicht ausführen; dieser Blocker wird nicht wiederholt.

## 2026-11-27 — Native-Backup-Profil fail-closed (PR #443)

- [PR #443](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/443) wurde als [551162dd598d1860ec9537a8cdb3bca365b56bb4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/551162dd598d1860ec9537a8cdb3bca365b56bb4) gemergt. Der Native-CLI-Pfad validiert Backup-Erstellung und Restore jetzt mit `ValidateNativeSingleHost`: Quelle, bestehender Zielzustand und der vorbereitete Folgezustand werden vor der Verarbeitung bzw. CAS-Übernahme geprüft. Ungültige oder mehrknotige Zustände werden mit `NATIVE_STATE_PROFILE_INVALID` abgewiesen; die generische Recovery-Bibliothek bleibt für spätere Profile wiederverwendbar.
- Exakte PR-Prüfungen: [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45969482513), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45969482599) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45969482748) erfolgreich. real-vm und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist dadurch geschlossen.
- Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt auf `28efa7518e171a618d4dcf9ff3aba58cddaf3296` gebunden, veraltet, unsigniert und nicht unveränderlich. `productionReady=false`, Go/No-Go bleibt No-Go; Countdown **9/100**. Sieben-VM-HA, Quorum und Kubernetes-Production bleiben außerhalb des ersten Scopes.
- Nächster Schritt: unveränderlichen Kandidaten aus Main `551162dd598d1860ec9537a8cdb3bca365b56bb4` bauen und anschließend den autorisierten Ubuntu-24.04-Lauf mit `run_real_vm_e2e=true` starten.

## 2026-11-27 — Native-Startup-State fail-closed (PR #441)

- [PR #441](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/441) wurde als [52dff842451a1bf3c4709acf1c1651c02cd9c2d7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/52dff842451a1bf3c4709acf1c1651c02cd9c2d7) gemergt. Der Control-Daemon validiert den persistierten Zustand jetzt vor dem TLS-Listener gegen das Native-Single-Host-Profil; auch ein Setup-Resume stoppt bei ungültiger Inventur oder Profilüberschreitung. Die Native-Grenzen bleiben 1 Node, 20 Workloads und 50 Allocations; generische Mehrhost-Grenzen bleiben für den späteren Erweiterungspfad erhalten.
- Exakte PR-Prüfungen: [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45961609946), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45961610067) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45961610025) erfolgreich. real-vm und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist dadurch geschlossen.
- Der veröffentlichte Kandidat v0.2.0-dev.4-test.17 bleibt auf 28efa7518e171a618d4dcf9ff3aba58cddaf3296 gebunden, veraltet, unsigniert und nicht unveränderlich. productionReady=false, Go/No-Go bleibt No-Go; Countdown **9/100**. Sieben-VM-HA, Quorum und Kubernetes-Production bleiben außerhalb des ersten Scopes.
- Nächster Schritt: unveränderlichen Kandidaten aus dem aktuellen Main bauen und anschließend den autorisierten Ubuntu-24.04-Lauf mit run_real_vm_e2e=true starten.

## 2026-11-27 — Native Single-Host admission profile wired to the control process (PR #439)

- [PR #439](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/439) wurde als [5d848c585aa24b065bd1807aeab550482dd6ff6c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5d848c585aa24b065bd1807aeab550482dd6ff6c) gemergt. Der echte Native-Control-Prozess setzt jetzt NativeSingleHost=true; damit gelten NativeMaxNodes=1, NativeMaxWorkloads=20 und NativeMaxAllocations=50 nur für den verbindlichen Single-Host-Pfad. Die generischen Modellgrenzen bleiben für den ausdrücklich deferred Mehrhost-Erweiterungspfad erhalten.
- Exakte Prüfungen: [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45955910147), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45955915226) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45955915225) erfolgreich. real-vm und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist dadurch geschlossen.
- Der veröffentlichte Kandidat v0.2.0-dev.4-test.17 bleibt auf 28efa7518e171a618d4dcf9ff3aba58cddaf3296 und ist für diese Änderung veraltet. productionReady=false, Go/No-Go bleibt No-Go; sieben-VM-HA und Kubernetes-Production bleiben außerhalb des ersten Scopes.
- Nächster Schritt: neuer unveränderlicher Kandidat aus dem aktuellen Main und anschließend autorisierter Ubuntu-24.04-run_real_vm_e2e=true-Lauf.

## 2026-11-27 — Native allocation boundary aligned (PR #437)

- [PR #437](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/437) wurde als [0ce8e8254a073464081211ad4920262d47b68cf0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0ce8e8254a073464081211ad4920262d47b68cf0) gemergt. Die Native-Runtime begrenzt die persistierte Allocation-Inventur jetzt auf 50 Einträge und stimmt damit mit dem verbindlichen Single-Host-Scope überein; ein Regressionstest weist den 51. Eintrag mit `STATE_CAPACITY_REACHED` zurück.
- Exakte PR-Prüfungen: [Native/runtime einschließlich real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45949044127), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45949044133) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45949044189) erfolgreich. real-vm und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist dadurch geschlossen.
- Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt stale, unsigniert und nicht unveränderlich. Ubuntu-Installation, Backup/Restore, Upgrade/Rollback, Load/Soak, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen; `productionReady=false`, Entscheidung `no-go`, Countdown **9/100**.
- Nächster Handoff: unveränderlichen Kandidaten aus Main [0ce8e8254a073464081211ad4920262d47b68cf0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0ce8e8254a073464081211ad4920262d47b68cf0) bauen und mit `run_real_vm_e2e=true` auf Ubuntu 24.04 qualifizieren. Tag/Workflow-Dispatch bleiben ein einmalig dokumentierter Connector-Blocker; keine sieben-VM-HA- oder Kubernetes-Production-Qualifikation starten.

## 2026-11-27 — Restore-tree verification bounded (PR #426)

- [PR #426](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/426) wurde als [124a176fd9a6897ae9931c32070e1b7a74fdfb43](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/124a176fd9a6897ae9931c32070e1b7a74fdfb43) gemergt. Die Native-Volume-Restore-Integritätsprüfung begrenzt jetzt Bytes, Einträge und Tiefe auf dieselben Archivgrenzen wie Export/Extract. Ein lokal vergrößertes oder manipuliertes Restore-Ziel kann bei ACK-Replays nicht mehr ungebunden gelesen werden; ein neuer Regressionstest deckt die Byte-Grenze ab.
- Exakter PR-Head [8dd7bfd74d3b455c7a5a2adf6da9eb9bb5ff7687](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8dd7bfd74d3b455c7a5a2adf6da9eb9bb5ff7687): [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45919510060), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45919510070) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45919510172) erfolgreich; real-vm und real-PITR wurden übersprungen.
- Diese Recovery-/Runtime-Härtung schließt kein Single-Host-Production-Gate. Der Countdown bleibt bei **9/100**; `productionReady=false`, Entscheidung `no-go`.
- Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` bleibt an `28efa7518e171a618d4dcf9ff3aba58cddaf3296` gebunden, unsigniert und nicht unveränderlich. Ubuntu-Installation, Backup/Restore, Upgrade/Rollback, Load/Soak, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen.

## 2026-11-27 — Docker response-boundary hardening (PR #424)

- [PR #424](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/424) wurde als [7e07433ca88a8c00dba699260a2f97f2394deb4a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7e07433ca88a8c00dba699260a2f97f2394deb4a) gemergt. Der Native-Docker-Adapter begrenzt jetzt Image-Pull-, Image-Load- und Container-Log-Antworten; jeder JSON-Stream wird strict validiert. Überlange, abgeschnittene, doppelte/case-ambige, nachgestellte oder fehlerhafte Ereignisse werden fail-closed behandelt; explizite Docker-Pullfehler behalten den stabilen Fehlercode `IMAGE_PULL_FAILED`.
- Exakter PR-Head [ee2f90a166760369a89d64cb8ce46850bc7f6963](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ee2f90a166760369a89d64cb8ce46850bc7f6963): [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45913630095) erfolgreich (Test und real-etcd erfolgreich; real-vm und real-PITR übersprungen), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45913630058) erfolgreich, [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45913630098) erfolgreich.
- Die Regression deckt Response-Limits, strict JSON, Mehrdeutigkeit, Fehlerereignisse und gültige Docker-Ereignis-Streams ab. Diese Evidenz ist Runtime-/Security-Härtung; sie schließt kein Single-Host-Production-Gate. Der Countdown bleibt bei **9/100**; `productionReady=false`.
- Der veröffentlichte Kandidat `v0.2.0-dev.4-test.17` ist weiterhin an einen älteren Commit gebunden, unsigniert und nicht unveränderlich. Ubuntu-Installation, Backup/Restore, Upgrade/Rollback, Load/Soak, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen.

## 2026-11-26 — PostgreSQL-Operationspfade fail-closed (PR #422)

- [PR #422](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/422) wurde als [796f26e2ddcf754b02c007af4ce0f025d4a87da9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/796f26e2ddcf754b02c007af4ce0f025d4a87da9) gemergt. Ungültige Datenbank-Endpunkte werden mit `PRIVATE_DATABASE_ENDPOINT_REQUIRED`, fehlerhafte WireGuard-Routen mit `WIREGUARD_ROUTE_INVALID` und ungültige UTF-8-Ausgaben der PostgreSQL-Clients mit `POSTGRES_CLIENT_VERSION_INVALID` fail-closed abgewiesen; negative Regressionstests decken alle drei Pfade ab.
- Exakter PR-Head [318f46820542aa05c0f91b199e2ec3ceae1052c7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/318f46820542aa05c0f91b199e2ec3ceae1052c7): [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45907729007) erfolgreich (Test und real-etcd erfolgreich; real-vm und real-PITR übersprungen), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45907728933) erfolgreich und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45907729047) erfolgreich.
- Diese Operations-/Security-Härtung schließt kein Live-Production-Gate. `v0.2.0-dev.4-test.17` bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.
- Der nächste Kandidat muss aus Main [796f26e2ddcf754b02c007af4ce0f025d4a87da9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/796f26e2ddcf754b02c007af4ce0f025d4a87da9) gebaut und anschließend mit `run_real_vm_e2e=true` auf Ubuntu 24.04 qualifiziert werden. Der Connector kann Tag/`workflow_dispatch` nicht ausführen; der Blocker wird nicht wiederholt.
- HA/Multi-Host/Quorum und Kubernetes-Production bleiben Erweiterungspfade außerhalb des ersten Native-Single-Host-Scopes.

## 2026-11-26 — PITR-Konfiguration fail-closed (PR #420)

- [PR #420](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/420) wurde als [15ceb4ec891387268e816a79366dec1768917c0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/15ceb4ec891387268e816a79366dec1768917c0e) gemergt. PITR weist ungültiges UTF-8 im privaten Cipher-Secret mit `PITR_CIPHER_SECRET_ENCODING_INVALID` zurück und normalisiert nicht numerische `pg1-port`-Werte auf `PITR_PORT_INVALID`; beide Pfade haben Regressionstests.
- Exakte CI-Nachweise für den PR-Head [f5f5f3dfaff0d444bd316ab9fd7b4cf75cb77d0b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f5f5f3dfaff0d444bd316ab9fd7b4cf75cb77d0b): [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45900689098) erfolgreich (real-vm und real-PITR übersprungen), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45900689080) erfolgreich und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45900689051) erfolgreich.
- Diese Operations-/Recovery-Input-Validation schließt kein Live-Production-Gate. `v0.2.0-dev.4-test.17` bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.
- HA/Multi-Host/Quorum und Kubernetes-Production bleiben außerhalb des ersten Native-Single-Host-Scope.
- Nächster Handoff: unveränderlichen Kandidaten aus Main [15ceb4ec891387268e816a79366dec1768917c0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/15ceb4ec891387268e816a79366dec1768917c0e) bauen und darauf Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- sowie Signatur-/Provenance-Gates ausführen.

## 2026-11-26 — Native-Bootstrap-Eingaben fail-closed (PR #418)

- [PR #418](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/418) wurde als [4224039d0addb0a541785a94b3dd3e3983a4b61e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/4224039d0addb0a541785a94b3dd3e3983a4b61e) gemergt. Native Bootstrap weist ungültiges UTF-8 in `/etc/hosts`, `known_hosts` und Remote-Preflight-Ausgaben mit stabilen Fehlercodes zurück.
- Regressionen verwenden echte ungültige Bytes und prüfen alle drei Eingabepfade.
- Exakte CI-Prüfung: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45893968020), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45893968015) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45893968183) erfolgreich; `real-vm` und `real-PITR` übersprungen.
- Diese Operations-/Input-Validation-Härtung schließt kein Live-Production-Gate. `v0.2.0-dev.4-test.17` bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.
- HA/Multi-Host/Quorum und Kubernetes-Production bleiben außerhalb des ersten Native-Single-Host-Scope.
- Nächster Handoff: unveränderlichen Kandidaten aus Main 4224039d0addb0a541785a94b3dd3e3983a4b61e bauen und darauf Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- sowie Signatur-/Provenance-Gates ausführen.

## 2026-11-26 — Persistierte Allocation-Phasen fail-closed (PR #416)

- [PR #416](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/416) wurde als [2627e37201db7ebfdbc31b0a05c9f331d9eef6df](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2627e37201db7ebfdbc31b0a05c9f331d9eef6df) gemergt. Persistierte Allocation-Phasen werden vor Inventory-Validierung und Reconciliation gegen die explizite Native-State-Machine geprüft; leere oder unbekannte Werte werden fail-closed abgewiesen.
- Regressionen decken leere, unbekannte und nicht unterstützte Phasen ab; die betroffenen State-Fixtures tragen jetzt die gültige Phase `assigned`.
- Exakte CI-Prüfung des Heads: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45887037586) erfolgreich, [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45887037581) erfolgreich und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45887037638) erfolgreich. `real-vm` und `real-PITR` waren übersprungen.
- Diese Runtime-/State-Härtung schließt kein Live-Production-Gate. Der veröffentlichte `v0.2.0-dev.4-test.17`-Kandidat bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.
- HA/Multi-Host/Quorum und Kubernetes-Production bleiben außerhalb des ersten Native-Single-Host-Scope.
- Nächster Handoff: neuen unveränderlichen Kandidaten aus Main 2627e37201db7ebfdbc31b0a05c9f331d9eef6df bauen und darauf die Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- sowie Signatur-/Provenance-Gates mit `run_real_vm_e2e=true` ausführen; der Tag-/Dispatch-Blocker ist dokumentiert und wird nicht wiederholt.

## 2026-11-26 — Dashboard-Login strikt validiert

- PR #401 wurde aus Main `029b2d4ff29e590f2621adb574c14381dcf254f9` rebasiert und als `07c5d127687fdd9948919cacde6e9ad6f404a349` gemergt: https://github.com/JossefMo1/Werftkern_Kubernetes/pull/401
- Der lokale Dashboard-Login akzeptiert jetzt nur noch einen vollständigen, strikt validierten JSON-Wert. Nachlaufende JSON-Werte und case-fold doppelte Felder werden vor dem Vergleich des Einmalcodes abgewiesen; die 2-KiB-Eingangsgrenze bleibt aktiv.
- Exakte Verifikation des Heads `dad2580ec927dd7389673fed54c47ead76eda6c2`: Native (inkl. real-etcd) https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45832879069, Kubernetes-Contracts https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45832878958 und Source-/Publication-Audit https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45832878968 erfolgreich. `real-vm` und `real-PITR` waren übersprungen.
- Diese Security-/UX-Härtung schließt kein Live-Production-Gate. Der alte `v0.2.0-dev.4-test.17`-Kandidat bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.
- Aktueller Handoff: Main `07c5d127687fdd9948919cacde6e9ad6f404a349`; ein neuer unveränderlicher RC muss daraus für Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- und Signaturprüfungen gebaut werden.
## 2026-11-26 — Dashboard-Proxy-Grenze und CI-Runner-Evidenz

- PR #399 wurde aus dem aktuellen Main b13a51f3b0e75901cd4f654def766254293ce56e rebasiert und als 3f3301ecd5d20d8dcf176aba63d5c3e6d05b8076 gemergt: https://github.com/JossefMo1/Werftkern_Kubernetes/pull/399
- Der Dashboard-Control-Plane-Proxy liest Antworten nur noch bis zur dokumentierten Zustandsgrenze; nicht lesbare oder zu große Antworten werden mit 502 und stabilen Fehlercodes abgewiesen, statt abgeschnitten weitergereicht zu werden.
- Der erste Native-Lauf für #399 scheiterte ausschließlich am nicht benötigten packages.microsoft.com-APT-Repository des gehosteten Ubuntu-Runners (403, Paket nicht gefunden). Die CI isoliert solche optionalen Quellen jetzt nur für den Smoke-Test und stellt sie im Cleanup wieder her.
- Verifikation des korrigierten Heads 5c6b6833ccdaf5d8b754841531932c9d1c9ebeb9: Native (inkl. real-etcd) https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45824933962, Kubernetes-Contracts https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45824933974 und Source-/Publication-Audit https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45824933967 erfolgreich. real-vm und real-PITR waren übersprungen.
- Dies ist Runtime-/CI-Härtung, kein Live-Production-Gate. Der alte v0.2.0-dev.4-test.17-Kandidat bleibt stale, unsigniert und nicht unveränderlich; productionReady=false, Entscheidung no-go.
- Aktueller Handoff: Main 3f3301ecd5d20d8dcf176aba63d5c3e6d05b8076; als Nächstes muss ein unveränderlicher RC aus diesem Main für kandidatengebundene Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- und Signaturprüfungen bereitgestellt werden.
# Docker Engine response boundary handoff — PR #397 (2026-11-26)

- Code: [PR #397](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/397), merged commit [fd58520](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fd585204c834bcd3f80c53aad61bac831ba39a13).
- Runtime change: Docker Engine version responses are bounded to 64 KiB and API JSON responses to 4 MiB; strict validation rejects trailing JSON and case-fold duplicate members before decoding.
- Regression coverage: [Native runtime / Real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45823173437), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45823173749) and [Source/Publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45823173424) passed. Real-vm and real-PITR were skipped because candidate-input execution was not enabled.
- No Single-Host production gate closed. productionReady=false, decision no-go; test.17 remains stale, unsigned and mutable.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from current Main fd585204c834bcd3f80c53aad61bac831ba39a13 and run candidate-bound Ubuntu installation, Docker/etcd lifecycle, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks.
# Control-plane error boundary handoff — PR #395 (2026-11-26)

- Code: [PR #395](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/395), merged commit [98cc94b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/98cc94be7b7b6866c49a544b6a484af5dbea6879).
- Runtime/security change: non-2xx control-plane responses are bounded to 8 KiB and validated with the strict JSON contract before an API error code is exposed. Trailing JSON, case-fold duplicate members and oversized responses fail closed with CONTROL_PLANE_ERROR_RESPONSE_INVALID.
- Regression coverage: [Native runtime tests](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45814527042) and the exact PR head's Real-etcd job passed; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45814527078) and [Source/Publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45814527001) passed. Real-vm and real-PITR were skipped because candidate-input execution was not enabled.
- No Single-Host production gate closed. productionReady=false, decision no-go; test.17 remains stale, unsigned and mutable.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from current Main 98cc94be7b7b6866c49a544b6a484af5dbea6879 and run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The connector cannot create the authorized tag or dispatch workflow_dispatch; the blocker remains recorded and is not repeated.
# Recovery and archive integrity handoff — PRs #392/#393 (2026-11-26)

- Code: [PR #392](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/392) merged as [0723e98](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0723e9863db9fdd25f9b3463e4efee1d7421a7cd); [PR #393](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/393) merged as [b5da254](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b5da254fcd4aea95d504dc578a45ab6187d480a2).
- Operations/recovery boundary: #392 validates the journal-controlled service list before signature verification, maintenance-lock acquisition or phase writes, so malformed recovery state cannot strand a host in explicit recovery.
- Backup/restore boundary: #393 validates authenticated volume-archive headers with strict JSON decoding before deriving archive keys; duplicate/case-folded members and trailing JSON are rejected.
- CI evidence: #392 Native/runtime + real-etcd [workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45787124269), Kubernetes contracts [workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45787124345), source/publication [workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45787124208); #393 Native/runtime + real-etcd [workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45806589464), Kubernetes contracts [workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45806589543), source/publication [workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45806589398) — all successful. Real-vm and real-PITR jobs were skipped for #393 because candidate-input execution was not enabled.
- No Single-Host production gate closed. The published test.17 candidate remains stale, unsigned and mutable; productionReady=false and the decision remains no-go.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from current Main b5da254fcd4aea95d504dc578a45ab6187d480a2 and run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The connector cannot create the authorized tag or dispatch workflow_dispatch; that blocker is recorded once and is not repeated.

# Upgrade recovery phase guard handoff — PR #368 (2026-11-25)

- Code: [PR #368](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/368), merged commit [79c8688](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/79c8688286aacd916156dfb638e86c5372812976).
- Runtime/operations change: `werft-ops upgrade recover` now accepts only explicitly interrupted journal phases. Completed or unknown phases fail closed with `RECOVERY_PHASE_NOT_INTERRUPTED` before signature verification or any host mutation.
- Regression coverage: `test_recover_rejects_completed_journal_before_external_commands` writes a completed private journal, asserts the phase error and proves the command runner was never called.
- PR checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45640555952), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45640555833) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45640555904) — all successful. [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45640555952/job/139299258427) and [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45640555952/job/139299257747) were skipped because the candidate-input flag was not enabled.
- No Single-Host production gate closed. `productionReady=false`, decision `no-go`; published test.17 remains stale, mutable and unsigned. The tracker records the exact current Main commit and the connector's tag/dispatch blocker.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from the current Main ref at execution time (the merged runtime hardening from [79c8688](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/79c8688286aacd916156dfb638e86c5372812976) is already in history), then run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The current connector cannot create the authorized tag or dispatch `workflow_dispatch`; that blocker is recorded and not repeated.

# Secret staging content-integrity handoff — PR #365 (2026-11-25)

- Code: [PR #365](https://github.com/JossefMo1/Werftkern_Kube…23404 tokens truncated…efMo1/Werftkern_Kubernetes/pull/230) merged as [397e0ff](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/397e0ff6de39404f631aab92c12ed9719108c617). Native release verification now opens the candidate package through `safefile.OpenRead`, which validates non-symlink parent components, refuses final symlinks and rejects non-regular files before hashing. Regression coverage protects both final-package and parent-symlink paths.

Exact PR checks passed: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446362), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446302) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446373). Real-etcd passed; real-VM and real-PITR were skipped. The first PR attempt failed only because of a self-introduced Go formatting mistake, which was corrected before these final checks. This is release-artifact path hardening only: `v0.2.0-dev.4-test.17` remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, release metadata reports `immutable=false` and unsigned assets, `productionReady=false`, and no qualification gate was closed. Build the next candidate from `397e0ff6de39404f631aab92c12ed9719108c617` before live evidence can cover this fix.

# Release status — 0.2.0-dev.4

**NOT_PRODUCTION_READY. Full masterplan incomplete. State schema 2.**

The [candidate production scope](PRODUCTION-SCOPE.md) records a proposed,
bounded first support matrix for the Native and Kubernetes paths. It is a
planning and drift-detection contract, not qualification evidence. All listed
live, security, supply-chain and operational gates remain open until evidence
for one unchanged release candidate is verified.

The active [German E2E production plan](PRODUCTION-E2E-PLAN-DE.md) and the
machine-readable [`production-tracker.json`](../release/production-tracker.json)
make the next blocked and independent steps explicit between runs. They are
tracking aids only; their status never closes a qualification gate.

The Kubernetes matrix now selects hcloud-csi 2.24.2 as a candidate RWO storage
path with a digest-bound chart and `Retain` StorageClass. Its six upstream OCI
index digests are pinned after each registry digest header matched the SHA-256 of
the received manifest body, and the checker can repeat that online comparison.
The hash-checked chart was rendered with the conservative values and exact image
multiset; the generated manifest is committed and hash-bound. The chart, Helm and
images have not been signature- or vulnerability-verified, executed or independently
reviewed; real Volume lifecycle, failure, backup and restore evidence remains absent.
The exact render now also has a fail-closed static privilege audit: RBAC contains no
wildcards or Secret access, and the only accepted privileged container/host-path set
is the CSI node driver boundary. The exact render now selects a separately hash-bound
node ServiceAccount with automatic API-token mounts disabled. Both workloads set
`RuntimeDefault` at pod level, covering their non-privileged containers; Kubernetes
privileged-container semantics leave the CSI node driver as an explicit exception.
The linux/amd64 manifest and config blobs behind all six locked image indexes were
also hash-checked. Their image configs select root explicitly (`User: 0`) or implicitly
(empty `User`), while the upstream chart exposes no per-container security-context
values. Pod-level `runAsNonRoot` is therefore explicitly unsafe for this candidate,
not a completed control. An exact-input, fail-closed post-render step now makes every
root identity explicit. The seven non-privileged container instances disable privilege
escalation, drop every Linux capability and bind `RuntimeDefault` at container level;
the privileged node driver retains only its reviewed explicit root/privileged context.
Hardening remains blocked pending qualified non-root identities and disposable-cluster
runtime evidence. Every rendered CSI container has a hash-bound CPU/memory request and
limit; these conservative starting budgets have not been measured under load or soak
and are not production capacity claims.
These audits are not runtime security or live CSI compatibility evidence.

The authoring-environment observations below are historical, including the
compiler version and whether CI had run at that time. For subsequently verified
GitHub CI and public-source preparation, see
[the dated publication review](validation/PUBLICATION-REVIEW-2026-10-12.md).
That review does not qualify the production features listed here.
The later [production qualification review](validation/PRODUCTION-READINESS-2026-10-12.md)
records a successful exact-commit single-host Ubuntu test. Multi-host, Kubernetes,
database recovery and signed production acceptance remain unqualified.

## Current tagged lab candidate

The latest tagged experimental candidate is [`v0.2.0-dev.4-test.17`](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17), built from source commit `28efa7518e171a618d4dcf9ff3aba58cddaf3296`. GitHub release metadata reports immutable=false and its assets are unsigned. Its Native, Kubernetes-package and source-audit workflows passed; the Native real-etcd job passed, while VM/PITR jobs were skipped. The release includes the auto-discovery known-hosts replay guard, is unsigned and remains a lab artifact only: it does not qualify installation, HA, recovery, Kubernetes lifecycle, supply-chain or production readiness. The machine-readable tracker records the exact asset digests and open gates.

Main contains [PR #122](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/122), merged at `c95511a5f1e1c8ca6aa909b3e69bb21558b00634`, [PR #140](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/140), [PR #143](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/143), [PR #148](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/148), [PR #152](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/152), [PR #154](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/154), [PR #156](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/156) and [PR #158](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/158). The code-bearing handoff commit remains `2ab2ebe5433b938925b4aebd57c84a7939d92a43`; the latest tracker-synchronized Main handoff is `9403d55e2deae30f4c99e889a56cfffbafb0390b`, with this status/roadmap/tracker synchronization following PR #158. Native auto-discovery binds both the explicit `--hosts-file` path and its exact bytes in the private resume journal; changed content is rejected with `AUTO_DISCOVERY_HOSTS_FILE_CONTENT_CHANGED`, and legacy journals without the byte binding fail closed. PR #140 adds fail-closed TCP port-range validation for Native control-plane endpoints. PR #143 makes the Native package `postinst` execute `/usr/bin/werft --help` and `/usr/bin/werft-ops --help` before declaring the package configured, with a release regression test protecting both checks. PR #148 adds a release-contract regression test that covers every service stop/disable action and prevents uninstall scripts from deleting persisted state, identities or workloads. PR #152 adds a release-contract regression test for both Kubernetes recovery/repair systemd templates, preserving their explicit root, token/assets and sandbox boundaries. PR #154 adds hermetic Kubernetes-manager wrapper tests for staged package-root execution and exit-78 fail-closed behavior when Python modules are missing. PR #156 requires the Kubernetes wrapper entrypoint to exist before selecting an installed, staged or source-tree module path and regression-tests incomplete package trees. PR #158 requires the Native `werft-ops` wrapper to find both `werftops/__init__.py` and `werftops/__main__.py` before selecting a module path and regression-tests incomplete package trees. Post-merge Native, Kubernetes-package, source-audit and Private-Alpha workflows passed; real-vm/real-pitr remain skipped. Test17 remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; GitHub release metadata reports immutable=false and its assets are unsigned and does not contain PR #140, PR #143, PR #148, PR #152, PR #154, PR #156 or PR #158; a new candidate is required before live testing the updated package. The production decision remains no-go.

## Latest code handoff (2026-11-21)

PR #160 is merged at [a04b0b4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a04b0b4c9db7f4f0aa5e408446b45cb5fe25dd1a). The Kubernetes-manager `werft-kube plan` command now rejects valid non-object JSON before format dispatch and returns the stable `KUBE_PLAN_OBJECT_REQUIRED` block instead of an uncaught traceback; the regression test covers the JSON response and stderr. This is a CLI error-handling guard only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and does not contain PR #160. Post-merge source, contract, Real-etcd and publication-audit checks passed; `real-vm` and `real-pitr` remain skipped. Production remains no-go.


## Implemented in this increment

Owned sequential worker rollout, separately authorized node maintenance reads and drain,
signed remote staging, conservative uncertain-install recovery, local Docker-smoke command,
restarted observation windows, identity-bound final unlock and a narrowly supported
dev.3-agent/dev.4-controller compatibility edge. Stale probe observations no longer
count as ready in scheduling or discovery. Paused applications require zero live executions.

Both previous and new agent executables were actually built and started using a real
persistent local journal, real TLS and OS processes. The Docker endpoint and etcd store
were fixtures. This is stronger than changing a version string, but NOT real container,
Ubuntu, SSH, hardware, quorum or production upgrade evidence.

The new `werft-ops native-bootstrap` coordinator now covers the intended
three-controller/worker bootstrap flow in code: it resolves an explicit
inventory against a trusted hosts file, performs fail-closed SSH/Ubuntu/systemd/
cgroup-v2 preflight on every target, generates one bound HA kit set, installs
the unchanged package through the existing SSH bootstrap primitive, and resumes
from a private journal without overwriting foreign or incomplete state. The
coordinator has fixture tests only; no real six-host run was executed in this
authoring environment, so this does not close any live qualification gate.

All controllers must already be dev.4 before a dev.3 worker wave starts. General mixed
versions, old controllers accepting new agents, automated controller waves and the
historical dev.2→dev.3 edge are not supported by this compatibility test. Active pinned
or local-volume workloads require separately planned offline maintenance, not forced drain.

## Inherited integrations and boundaries

Native three-host PostgreSQL17/Patroni4 with mandatory watchdog and independent etcd DCS;
pgBackRest/POSIX encrypted backup and PITR adapter; offline CA leaf renewal and combined-PEM
live reload; physical encrypted local-volume archives; own Go TLS ingress; HA/mesh/DNS/
Hetzner tooling. These are not independently qualified multi-host production services.
Database HA runs on dedicated native hosts, not in the ordinary Docker scheduler.
File restore, actual WAL replay and business validation remain separate gates.

## Still missing or unqualified

Replicated generic storage/CSI; qualified physical fencing; complete site-wide DR;
integrated database service lifecycle; production NetworkPolicy and HA ingress endpoint;
full CA rotation/online issuer; automated controller upgrade orchestration; direct
containerd; IONOS/ClusterPilot connector and broader roadmap features. No model size
limit is a measured scalability claim. No SLA/RPO/RTO commitment.

Real Ubuntu/systemd/Docker/SSH/cloud/WireGuard/CoreDNS/PostgreSQL/Patroni/watchdog tests,
three-host failures, actual signed package upgrades, soak/load and independent security
assessment have not passed here. Opt-in etcd/PITR attempts fail explicitly if dependencies
are absent. All production qualification gates remain BLOCKED.

Local compiler: Go1.23.2 on Debian13. Prepared CI: Go1.27.1, not executed here. A separately
supplied `.deb` is unsigned, unqualified and for fresh disposable lab VMs only. Actual
counts and evidence scopes: `validation/TEST-REPORT.md`.



## Latest code handoff (2026-11-21, PR #162)

PR #162 merged at [2ad8daeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2ad8daebed99f8ea2b6735f9f626e500666cd694). The Kubernetes wrapper now requires both `werftops/__init__.py` and `werftops/kube_main.py` before selecting installed, staged or source modules; a missing package marker fails closed with exit 78 and is covered by a regression test. This is a packaging/error-boundary fix for the Kubernetes manager only. Post-merge test, contracts, real-etcd, publication-audit and private-alpha checks passed; real-vm and real-pitr remain skipped because no authorized disposable lab is configured. The immutable test17 candidate is unchanged, and `productionReady=false` remains the honest status.
## Latest code handoff (2026-11-21, PR #164)

PR [#164](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/164) merged at [552a9aeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/552a9aeb46097d703300475ff21c87ecbffa282c). The Kubernetes conformance evidence parser now validates archived `serverversion.json` and `gitVersion` before comparison, returning stable blocked reasons for malformed evidence. Post-merge automated checks passed; real-VM/PITR remain skipped because no authorized disposable lab is configured. Test17 is unchanged and `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #166)

[PR #166](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/166) merged as [e88b667](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e88b6679829be356710cc88a35e090093054ec8b). Kubernetes supply-chain evidence verification now validates top-level and nested SBOM, vulnerability-scan and provenance document shapes before access, returning stable blocked reasons for malformed evidence. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #168)

[PR #168](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/168) merged as [7b1408a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7b1408a38f830405af52da47143cffa6058068c9). The Kubernetes evidence verifier now validates the trust-policy `keys` inventory before iteration and returns stable `TRUST_KEYS_REQUIRED` for null, empty or non-list inventories. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.

## Latest code handoff (2026-11-21, PR #170)

[PR #170](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/170) merged as [289c0f2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/289c0f2c37e4ce011e2c1c4827a2646915c3b340). The Kubernetes evidence verifier now requires every signed environment identity to be a non-empty string and returns stable `EVIDENCE_IDENTITIES_INVALID` for malformed entries. Regression coverage and post-merge automated checks are green.

This is a code-quality handoff only. No live qualification gate was closed: authorized disposable Ubuntu/k0s execution, installation/upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent-review evidence remain open. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` remains the honest status.


## Latest code handoff — PR #172 (2026-11-21)

[PR #172](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/172) merged at [77bdc1d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/77bdc1d1af128f5c98fefec3f6720d74df01b3d7). The Kubernetes evidence verifier now rejects trust-policy key roles and organization metadata unless they are non-empty strings, preserving stable `TRUST_KEY_INVALID` handling. Regression tests cover both malformed trust-key paths. Exact post-merge Kubernetes, Native, Source/Privacy and private-alpha audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520639),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520655),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520708),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959717872).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #174 (2026-11-22)

[PR #174](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/174) merged at [0245997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0245997861b9eb663f261cf0d7bcc5623c4627e1). The Kubernetes supply-chain evidence verifier now rejects CycloneDX SBOM component entries unless each is a JSON object, preserving stable `SBOM_COMPONENT_INVALID` handling. A regression test covers `components: [null]`. Exact post-merge audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222806),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222823),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222792),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964385448).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #176 (2026-11-22)

[PR #176](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/176) merged at [33d8780](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/33d87805b952fcfff1b98ff43e18a60cb041db32). The Kubernetes Trivy-v2 evidence verifier now rejects empty or whitespace-only result targets, preserving stable `VULNERABILITY_RESULT_INVALID` handling. Nullable `Vulnerabilities` fields remain supported; a regression test covers the malformed target. Exact post-merge audits passed:
[Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159822),
[Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159864),
[Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159804),
[Private Alpha](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969356902).

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #179 (2026-11-22)

[PR #179](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/179) merged at [6b44496](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6b44496ed69a0feb25e11e2ba0ea358802dc8945). The Kubernetes Trivy-v2 evidence verifier now rejects boolean, numeric and other scalar `Vulnerabilities` inventories while preserving missing/`null` inventories as empty, with stable `VULNERABILITY_RESULT_INVALID` handling and a regression test. Exact PR checks passed: [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221312), [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221342), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221313); real-VM and real-PITR remained skipped.

This does not qualify production. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains no-go. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.



## Latest code handoff — PR #181 (2026-11-22)

PR [#181](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/181) merged at [f38d33c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f38d33c77394d321ec8229033dda5e48299d16cf). The Kubernetes CycloneDX evidence parser now requires every component object to carry a non-empty string `name`; malformed entries are rejected fail-closed with `SBOM_COMPONENT_INVALID`, and a regression test covers an empty component object.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393959), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393878) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393890). Real-VM and real-PITR remain skipped. This is not SBOM validity, vulnerability clearance or production qualification.

The immutable `v0.2.0-dev.4-test.17` candidate is unchanged at `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #183 (2026-11-22)

PR [#183](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/183) merged at [8c0bc4a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8c0bc4aa21575891eb782ad6943bfe42c24cb4d6). The Kubernetes Trivy-v2 evidence parser now requires each LOW/MEDIUM finding to carry a non-empty string `VulnerabilityID`; malformed findings are rejected fail-closed with `VULNERABILITY_FINDING_INVALID`, and a regression test covers a nameless LOW finding.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729213), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729235) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729267). Real-VM and real-PITR remain skipped. This is not vulnerability clearance or production qualification.

The immutable `v0.2.0-dev.4-test.17` candidate is unchanged at `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #185 (2026-11-22)

PR [#185](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/185) merged at [3cfe2e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3cfe2e9f25b68cce70a8e9684d8dd4dd957c8fa8). The Kubernetes release-candidate evidence parser now requires `sourceRepository` to be a canonical public GitHub repository URL, with an optional `.git` suffix; malformed identities are rejected fail-closed with `SOURCE_REPOSITORY_INVALID`, and a regression test covers a truncated URL.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036663), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036674) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036662). Real-VM and real-PITR remain skipped. This is not provenance validity or production qualification.

The immutable `v0.2.0-dev.4-test.17` candidate is unchanged at `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #187 (2026-11-22)

PR [#187](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/187) merged at [1954916](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/19549167b5a18c1e741d1603aaa990a67e5bbb11). The Kubernetes SLSA-provenance parser now rejects each `resolvedDependencies` entry unless it has a non-empty URI, a non-empty digest object and non-empty string digest values, returning stable `PROVENANCE_DEPENDENCIES_INVALID` handling. Regression coverage protects the malformed-material case.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447134) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447123). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-shape hardening only; it does not close a live qualification gate. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #189 (2026-11-22)

PR [#189](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/189) merged at [93b0cb3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/93b0cb3672cd6889114e2e6f7b5e358057979fdf). The Kubernetes evidence verifier now rejects whitespace-only `builderId` values with stable `BUILD_IDENTITY_REQUIRED` handling, with regression coverage for the malformed identity.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512976), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512956) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512896). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-shape hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #191 (2026-11-22)

PR [#191](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/191) merged at [94b5110](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/94b51103edeaf16e1e381e5acac4232bf2ac58cc). The Kubernetes evidence verifier now rejects empty or whitespace-only digest keys in `resolvedDependencies` entries with stable `PROVENANCE_DEPENDENCIES_INVALID` handling, with regression coverage for malformed digest-key data.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517149) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517249). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-shape hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #193 (2026-11-22)

PR [#193](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/193) merged at [e660826](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e66082608f67f4f51d996f86afc1ce94652b455d). The Kubernetes evidence verifier now rejects candidate `builderId` values with leading or trailing whitespace using stable `BUILD_IDENTITY_REQUIRED` handling, with regression coverage for a non-canonical identity.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520825), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520832) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520854). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is evidence-identity hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #195 (2026-11-22)

PR [#195](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/195) merged at [c587354](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c58735426626ee71dc9755fc3a38a6c7edb6c740). The Kubernetes evidence verifier now requires trust-policy `organization` identifiers to be non-empty and canonically free of leading or trailing whitespace; malformed identities fail closed with stable `TRUST_KEY_INVALID` handling, with regression coverage.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532273), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532243) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532236). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is trust-identity hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Latest code handoff — PR #197 (2026-11-22)

PR [#197](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/197) merged at [71f1dfd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/71f1dfddc2be51ad6a1c54371cac4339c9910167). The production-tracker validator now requires non-empty string lists for `nextAction.blockers`, `nextAction.successCriteria` and every workstream's `requiredGateFamilies`; the previous empty-list `all([])` acceptance is closed with regression tests.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865245), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865193) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865239). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is release-tracker validation hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #199 (2026-11-22)

PR [#199](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/199) merged at [f532b26](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f532b264a9f8bcc20ce26bfe2da6e4ab4debcc9d). The production-tracker validator now rejects empty or whitespace-only decision evidence lists, rollback contracts, next-action evidence strings and gate-family strings. Blocked workstreams reject scalar, object or blank-entry blocker fields with stable `TRACKER_BLOCKERS_INVALID` handling; regression tests cover malformed shapes.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092826), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092830) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092833). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is release-tracker validation hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #201 (2026-11-22)

PR [#201](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/201) merged at [a768d0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a768d0e304bc7c28ca8f3da7732a179e504001e6). The production-tracker validator now requires non-empty `nextAction.summary` and `nextAction.nextStep` strings, with regression coverage for missing actionable text. This closes a fail-open shape where a blocked release handoff could omit the operator-facing next step.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736383), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736359) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736350). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is release-tracker validation hardening only; no qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. Live Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Latest code handoff — PR #209 (2026-11-22)

PR [#209](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/209) merged at [fe052af](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fe052af52ab80509f325b9ebee8338649f49ecdd). The Native API now evaluates mTLS certificate validity through its injected UTC clock, with a regression test for certificates outside that validity window. This is a code-quality/security-boundary handoff only; no qualification gate was closed.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904516), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904485) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904486). Real-VM and real-PITR remain skipped because the authorized disposable runner dispatch is not available through the current connector. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`.


## Latest code handoff — PR #211 (2026-11-22)

PR [#211](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/211) merged as [0a785a8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0a785a85435c6796a34cadd24d66e7c1256f553c). The ingress Gateway now evaluates edge TLS leaf validity through its injected clock, matching the existing snapshot-freshness boundary; `TestServeUsesInjectedClockForCertificateValidity` covers an out-of-window certificate.

Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437255), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437247) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437285). Real-VM and real-PITR were skipped; no live qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. The next candidate must be package-built from `0a785a85435c6796a34cadd24d66e7c1256f553c`.


## Latest code handoff — PR #213 (2026-11-22)

PR [#213](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/213) merged as [ea83bb6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea83bb618edd82586a269930f388a66e04ade566). The Native agent now restores the allocation ID when an engine returns a zero report on failure; this keeps failure reports valid for the heartbeat contract and preserves node liveness. Regression coverage verifies the failed report identity.

Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874344), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874104) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874099). Real-VM and real-PITR were skipped; no live qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and the decision remains `no-go`. The next candidate must be package-built from `ea83bb618edd82586a269930f388a66e04ade566`.

## Latest code handoff — PR #246 (2026-11-23)

PR [#246](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/246) merged as [7154c11](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7154c11c58ec2b77c839b0ec1dd8745c630756e2). The privileged Native `node bundle` path now reads the authority certificate and issuing private key through bounded, no-follow file handling. Private keys require a regular file with mode 0600; final and parent symlinks, oversized inputs and permissive key modes are rejected. Regression coverage is in `internal/setup/setup_test.go`.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45126994589), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45126994424) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45126994355). Post-merge Main checks also passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45127397668), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45127397549) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45127397616). Real-VM and real-PITR remained skipped; no live qualification gate was closed.

The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new candidate must be built from [7154c11c58ec2b77c839b0ec1dd8745c630756e2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7154c11c58ec2b77c839b0ec1dd8745c630756e2) before these Native changes can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. The decision remains `no-go`.


## Latest code handoff — PR #248 (2026-11-23)

PR [#248](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/248) merged as [5c564ac](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5c564acb4972041bc3a9e3733404cc356594b4e7). Native vault key creation and logical/schema/volume backup outputs now use `safefile.CreateExclusive`: parent-chain validation, exclusive no-follow creation, regular-file verification and exact permissions prevent final or parent symlink redirection. Regression tests cover valid creation, existing destinations, final symlinks and parent symlinks.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45134771753), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45134771842) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45134771745). Post-merge Main checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45135169259), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45135169243) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45135169232). Real-VM and real-PITR remain skipped; no live qualification gate was closed.

The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new candidate must be built from [5c564acb4972041bc3a9e3733404cc356594b4e7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5c564acb4972041bc3a9e3733404cc356594b4e7) before this hardening can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. The decision remains `no-go`.


## Latest code handoff — PR #251 (2026-11-23)

PR [#251](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/251) merged as [e0bc69a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e0bc69abf0793b7fbae20301f09be97fc706ace6). Existing Native vault key reads now use `safefile.OpenRead`, so final and parent symlink traversal fails closed while the 32-byte/private-mode contract remains enforced. A regression test creates a valid key behind a symlinked parent and verifies rejection.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142398350), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142398485) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142398600). Post-merge Main checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142835351), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142834906) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45142834912). Real-VM and real-PITR remain skipped; no live qualification gate was closed.

The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new candidate must be built from [e0bc69a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e0bc69abf0793b7fbae20301f09be97fc706ace6) before this Native hardening can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. The decision remains `no-go`.

## Code handoff — PR #299 (2026-11-24)

[PR #299](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/299) merged as [b6ad0aa](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b6ad0aa1baf034407b15be7b194eed476b5a2195). The Native backup CLI now validates the destination before loading or creating the separate backup key. Invalid, colliding, or already-existing destinations therefore fail closed without leaving orphaned key material; regression coverage is in `internal/cli/backup_test.go`.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45408696336), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45408696528) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45408696330). Real-VM and real-PITR were skipped; no live single-host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new immutable candidate must be built from [b6ad0aa](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b6ad0aa1baf034407b15be7b194eed476b5a2195) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. The decision remains `no-go`.


## Latest code handoff — PR #301 (2026-11-24)

[PR #301](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/301) merged as [88daa16](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/88daa16106e73724a6c7b5ad51436aa123b932c). The Native `volume backup` path now rejects an existing or symlinked archive destination before loading or creating the separate encryption key. The exclusive `safefile.CreateExclusive` call remains the race-safe final guard, and regression coverage is in `internal/cli/volume_archive_test.go`.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45419523693), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45419490186) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45419523403). Real-VM and real-PITR were skipped by the workflow; no Single-Host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new immutable candidate must be built from [88daa16106e73724a6c7b5ad51436aa123b932c6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/88daa16106e73724a6c7b5ad51436aa123b932c6) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. The decision remains `no-go`.


## Latest code handoff — PR #303 (2026-11-24)

[PR #303](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/303) merged as [76f6656](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/76f6656ce4c21c67f203f50ad467417fa65835a1). The Native `schema migrate` path now rejects an existing or symlinked backup destination and normalized key/output collisions before local state access, key creation or schema migration. The final `safefile.CreateExclusive` guard remains in place, with regression coverage in `internal/cli/schema_test.go`.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45430965312), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45430965426) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45430965344). Real-VM and real-PITR were skipped by the workflow; no Single-Host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `productionReady=false`; its release metadata is not immutable and its assets are unsigned. A new immutable candidate must be built from [76f6656ce4c21c67f203f50ad467417fa65835a1](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/76f6656ce4c21c67f203f50ad467417fa65835a1) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. The decision remains `no-go`.


## Latest code handoff — PR #310 (2026-11-24)

[PR #310](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/310) merged as [6892578](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/689257882c58acb511d9e4be106e20ea88f18fe8). The privileged secret CLI now rejects extra arguments: `secret list` requires no operands, while `secret put` rejects positional leftovers before reading the private input or loading cluster configuration. Regression coverage is in [internal/cli/cli_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/689257882c58acb511d9e4be106e20ea88f18fe8/internal/cli/cli_test.go).

Exact PR checks passed: [Native test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138695864774), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138695864389), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464555873/job/138695855480) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556095/job/138695854545). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138697069149) and [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138697277903) were skipped; no live Single-Host production gate closed.

The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. A new immutable candidate must be built from `689257882c58acb511d9e4be106e20ea88f18fe8` before this hardening can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. `productionReady=false`; the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.


## Latest code handoff — PR #313 (2026-11-24)

[PR #313](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/313) merged as [02307049](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/02307049c72fc07b0d96926a81a7ce54a6963559). The privileged Native `backup` command now rejects positional leftovers immediately after flag parsing, before loading the separate encryption key, reading cluster state or mutating output. Regression coverage is in [internal/cli/backup_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/02307049c72fc07b0d96926a81a7ce54a6963559/internal/cli/backup_test.go). The first PR run exposed a missing `context` import in that new test; corrected commit `f581975edebb233db418cea7be183b149ccf7c99` passed on rerun.

Exact corrected PR checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475224114/job/138733544212), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475224114/job/138733543730), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475224098/job/138733542950) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475224313/job/138733544148). Post-merge Main checks also passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475656056/job/138735077398), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475656056/job/138735076795), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475655945/job/138735076776) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475656131/job/138735076728). The private-alpha workflow was successful, but it is not a production qualification gate.

[Real-VM](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475656056/job/138736198297) and [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45475656056/job/138736198518) were skipped; no Single-Host production gate closed. The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. A new immutable candidate must be built from `02307049c72fc07b0d96926a81a7ce54a6963559`; `productionReady=false` and the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.


## Native CLI release handoff — PR #315 (2026-11-24)

[PR #315](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/315) merged as [22aacc9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/22aacc9082832c5debdfd6d4753af5e627a7f8c8). The privileged Native `control` and `agent` daemon entry points now reject unexpected positional arguments immediately after flag parsing, before configuration, lock, mTLS, etcd or Docker access. Regression coverage is in [internal/cli/cli_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/22aacc9082832c5debdfd6d4753af5e627a7f8c8/internal/cli/cli_test.go).

PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485407944/job/138769338557), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485408137/job/138769338289) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485407967/job/138769338136). Post-merge Main checks also passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485924593/job/138771150701), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485924592/job/138771153651) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485924586/job/138771150000). Real-vm and real-PITR were skipped; no Single-Host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. Build the next immutable candidate from `22aacc9082832c5debdfd6d4753af5e627a7f8c8`; `productionReady=false` and the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Native CLI argument hardening — PR #318 (2026-11-24)

[PR #318](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/318) merged as [dd94bb4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/dd94bb41f4264b0b463d522d282050c646b52e5c). Native `wait`, `dashboard`, `status`, `tunnel`, `demo` and `node bundle` now reject unexpected positional arguments immediately after flag parsing, before configuration, metadata, network or workload access. Negative regression coverage is in [internal/cli/cli_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/dd94bb41f4264b0b463d522d282050c646b52e5c/internal/cli/cli_test.go).

PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495534346/job/138804884945), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495534341/job/138804884632) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495534555/job/138804889721). Post-merge Main checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495995923/job/138806524918), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495995874/job/138806524314) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495995860/job/138806524987). Real-vm and real-PITR remained skipped; no Single-Host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. Build the next immutable candidate from `dd94bb41f4264b0b463d522d282050c646b52e5c`; `productionReady=false` and the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Latest code handoff — PR #358 (2026-11-25)

[PR #358](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/358) merged as [3c485fb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3c485fb92ee4a5c8dc017aec555e5adcb873d8e7). Idempotency receipts now expire before generic replay checks, and the Secret API applies the same expiry before its direct replay lookup. Keys older than the bounded 24-hour window can therefore be reused instead of remaining permanently occupied. Regression coverage is in `internal/model/model_test.go`.

PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45609603951), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45609604084) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45609603974). Real-vm and real-PITR were skipped; no Single-Host production gate closed. The published `v0.2.0-dev.4-test.17` candidate remains unsigned/non-immutable and bound to an earlier source commit. `productionReady=false`; the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Latest QA handoff — PR #360 (2026-11-25)

[PR #360](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/360) merged as [6d766d4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6d766d44b6c8366e89d812b50ad9006b28797008). Added a control/API regression test proving that a Secret idempotency key can be reused for the next expected version after its receipt exceeds the bounded 24-hour replay window. PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45617899164), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45617899253) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45617899229). Real-vm and real-PITR were skipped; no Single-Host production gate closed. The published `v0.2.0-dev.4-test.17` candidate remains unsigned/non-immutable and bound to an earlier source commit. `productionReady=false`; the decision remains `no-go`.

## Latest code handoff — PR #403 (2026-11-26)

PR [#403](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/403) merged as [96dff4f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/96dff4f49427c3baa2e131272c6455dbda3651e4). The Native etcd client now bounds response reads to the state response budget plus one byte, rejects trailing JSON and case-fold duplicate members with `internal/strictjson`, and decodes only after validation. `internal/store/store_test.go` covers both ambiguous response forms.

Exact checks for the PR head passed: [Native runtime/source/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45843642774), [Kubernetes contracts/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45843642926) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45843642920). The Native run's `test` and `real-etcd` jobs succeeded; `real-vm` and `real-PITR` were skipped. These are code-hardening checks only: no Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with non-immutable metadata and unsigned assets. A new candidate must be built from [96dff4f49427c3baa2e131272c6455dbda3651e4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/96dff4f49427c3baa2e131272c6455dbda3651e4) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Latest operations handoff — PR #405 (2026-11-26)

PR [#405](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/405) merged as [6ce5423e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6ce5423ef2a848e64a69387610f99d20ba4a607e). Native setup no longer treats a positive-revision local agent journal as proof that a worker is connected. It now verifies the authenticated `GET /v1/health` response and requires the exact cluster ID, `ready` status and state schema. Regression coverage rejects wrong cluster, status and schema responses.

Exact checks for the PR head passed: [Native runtime/source/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45853993836), [Kubernetes contracts/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45853993755) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45853993732). The Native run's `test` and `real-etcd` jobs succeeded; `real-vm` and `real-PITR` were skipped. These are code-hardening checks only: no Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with non-immutable metadata and unsigned assets. A new candidate must be built from [6ce5423ef2a848e64a69387610f99d20ba4a607e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6ce5423ef2a848e64a69387610f99d20ba4a607e) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the production decision remains no-go. HA, multi-host and Kubernetes-production remain deferred.


## Latest runtime handoff — PR #408 (2026-11-26)

PR [#408](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/408) merged as [cc0c5b5e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cc0c5b5e835712b819ec227c5d6ca4d7094467ee). The Native agent now validates every persisted journal allocation before startup and every newly accepted journal before persistence. Allocation identity, node ownership, desired/phase values, port bounds, timestamps, resource specification and map-key consistency fail closed with JOURNAL_RECORD_INVALID; malformed durable state cannot reach reconciliation.

Exact checks for the PR head passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45856235848), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45856235446) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45856235860). The Native run's test and real-etcd jobs succeeded; real-vm and real-PITR were skipped. These are CI/code-hardening checks only: no Single-Host production gate closed.

The published v0.2.0-dev.4-test.17 candidate remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296, with non-immutable metadata and unsigned assets. A new immutable candidate must be built from [cc0c5b5e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cc0c5b5e835712b819ec227c5d6ca4d7094467ee) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. productionReady=false; the production decision remains no-go. HA, multi-host and Kubernetes-production remain deferred.


## Latest persistence hardening handoff — PR #410 (2026-11-26)

PR [#410](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/410) merged as [247dd11a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/247dd11a32cfbedd7fb4f7f056b49f0f672e2144). Native etcd state reads now use the strict JSON contract, so unknown persisted state fields fail closed before inventory validation or reconciliation. The first PR attempt exposed an incorrectly escaped JSON fixture and failed at compile; corrected commit `998bef39f58ec5d29002405b4adcc38f0f2a2c17` passed.

Corrected checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45863201801), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45863201851) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45863201751). The Native test and real-etcd jobs succeeded; real-vm and real-PITR were skipped. This is CI/code-hardening evidence only: no Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with non-immutable metadata and unsigned assets. A new immutable candidate must be built from [247dd11a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/247dd11a32cfbedd7fb4f7f056b49f0f672e2144) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.



## Latest Native runtime hardening — PR #412 (2026-11-26)

PR [#412](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/412) merged as [`1f722497`](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1f722497196366881136689d6dad30659abb22e8). The Docker adapter now validates the cluster identity with `model.ValidID` before API negotiation or container-name prefix slicing and returns `CLUSTER_ID_INVALID` without touching Docker for malformed identities. A negative regression test verifies that no adapter request is made.

Exact checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45871614939), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45871614507) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45871614434). The Native run's `real-vm` and `real-PITR` jobs were skipped. This is runtime/security hardening evidence only; no live Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains stale, non-immutable and unsigned. A new immutable candidate must be built from `1f722497196366881136689d6dad30659abb22e8` before live Ubuntu installation, backup/restore, upgrade/rollback or load/soak evidence can cover this change. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.


## Latest Native allocation safety handoff — PR #414 (2026-11-26)

PR [#414](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/414) merged as [`940682d8`](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/940682d868cce16e77bc4f6549c2bd14e6e25b3c). Allocation node selectors are now enforced at both boundaries: the agent rejects a pinned selector that differs from the selected node, and persisted state validation rejects the mismatch before reconciliation. Regression tests cover the assignment and inventory paths.

Exact checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45879376876), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45879376935) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45879377042). The Native `real-vm` and `real-PITR` jobs were skipped. This is runtime/state hardening evidence only; no live Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains stale, non-immutable and unsigned. A new immutable candidate must be built from `940682d868cce16e77bc4f6549c2bd14e6e25b3c` before live Ubuntu installation, backup/restore, upgrade/rollback or load/soak evidence can cover this change. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.


## Latest Native setup hardening — PR #429 (2026-11-27)

[PR #429](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/429) merged as [6cb1436f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6cb1436fc5bf458defeb8260bc75901ae3e96599). The `werft setup --bundle` path now persists the private worker join bundle before registering the node in the control-plane state. A local write failure therefore cannot leave an enrolled worker without usable credentials. Regression tests cover write-before-register ordering and fail-closed registration.

Corrected PR checks passed: [Native/runtime including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45925849361), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45925849407) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45925849350). A previous native attempt exposed an invalid test fixture; it was corrected before merge. real-vm and real-PITR remain skipped, so no live Single-Host production gate closed.

The old v0.2.0-dev.4-test.17 candidate remains stale, non-immutable and unsigned. Build the next immutable candidate from `6cb1436fc5bf458defeb8260bc75901ae3e96599`; productionReady=false and the production decision remains no-go. HA, multi-host and Kubernetes-production remain deferred.

## Latest Native security handoff — PR #431 (2026-11-27)

[PR #431](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/431) merged as [e42ee2a1](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e42ee2a1f9aff03abc6a7b23d130e4d74554f22c). Native join-bundle persistence now uses exclusive creation: an existing destination or symlink cannot be replaced, and node registration remains fail-closed. Regression coverage verifies private permissions, exclusive creation, symlink rejection and that registration is not called after a destination collision.

Exact checks passed: [Native/runtime including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45931400751), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45931400814) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45931400747). The Native test and real-etcd jobs succeeded; real-vm and real-PITR were skipped. This is security/reliability evidence only: no live Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains stale, non-immutable and unsigned. Build the next immutable candidate from `e42ee2a1f9aff03abc6a7b23d130e4d74554f22c` before live Ubuntu installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Latest CI/QA handoff — PR #433 (2026-11-27)

[PR #433](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/433) merged as [b97963a7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b97963a7a43349ef3c66e1f26a62af858129a3de). The Native post-install package smoke test no longer contains a duplicated `werft --help` invocation on one shell line; the installed CLI contract is now explicit and deterministic.

Exact checks passed: [Native/runtime including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45937156110), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45937156087) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45937156140). The Native test and real-etcd jobs succeeded; real-vm and real-PITR were skipped. This is CI/QA evidence only: no live Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains stale, non-immutable and unsigned. Build the next immutable candidate from `b97963a7a43349ef3c66e1f26a62af858129a3de` before live Ubuntu installation, backup/restore, upgrade/rollback or load/soak evidence can cover this workflow correction. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.
## Latest Supply-Chain handoff — PR #435 (2026-11-27)

[PR #435](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/435) merged as [06f9850b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/06f9850bbd97f74682b9d8d84af6d271dbc4e9d7). The Native SPDX SBOM now records the exact SHA-256 checksum of the Debian package in the root package entry and its package comment. Regression tests cover deterministic checksum binding and the generated document shape.

Exact checks passed: [Native/runtime including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45942567592), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45942567598) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45942567619). The Native test and real-etcd jobs succeeded; real-vm and real-PITR were skipped. This is supply-chain hardening evidence only: no live Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains stale, non-immutable and unsigned. A new immutable candidate must be built from `06f9850bbd97f74682b9d8d84af6d271dbc4e9d7` before live Ubuntu installation, backup/restore, upgrade/rollback or load/soak evidence can cover this SBOM change. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Native Docker-runtime hardening — PR #500 (2026-11-28)

[PR #500](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/500) merged as [3544da5b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3544da5bc9807f6fa6e7a5398e5417b0073e9d7e). Docker container-name path construction is now total for malformed short cluster IDs: the adapter returns the existing fail-closed `CLUSTER_ID_INVALID` error instead of panicking while slicing the identifier. Regression coverage proves that both `Ensure` and `Stop` reject the invalid configuration before any Docker adapter mutation.

Exact checks passed: [Native runtime/package workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46105664413) with [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46105664413/job/140857719106) and [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46105664413/job/140857719332), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46105664411/job/140857719214) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46105664373/job/140857719069). The Native `real-vm` and `real-PITR` jobs were skipped. These are automated reliability/security checks only; no live Single-Host production gate closed.

The published `v0.2.0-dev.4-test.17` candidate remains stale, non-immutable and unsigned. Build the next immutable candidate from [3544da5b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3544da5bc9807f6fa6e7a5398e5417b0073e9d7e) before live Ubuntu installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.



## Native Docker log-read hardening — PR #502 (2026-11-28)

[PR #502](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/502) is merged in [7a0c7ca35ab9730c995de1aa811f05cd94a64608](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7a0c7ca35ab9730c995de1aa811f05cd94a64608). The exported Docker runtime method `Logs` now validates allocation IDs before container-name/path construction. Empty, short, non-hex and path-like IDs fail closed with `ALLOCATION_ID_INVALID` without reaching the Docker adapter; regression coverage is in `internal/engine/docker_test.go`.

Automated evidence: Native [run 46109665119](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665119) passed (test [140870152506](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665119/job/140870152506), real-etcd [140870152325](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665119/job/140870152325)); real-vm [140870663493](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665119/job/140870663493) and real-PITR [140870663191](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665119/job/140870663191) were skipped. Kubernetes contracts [140870152159](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665047/job/140870152159) and Source/Privacy [140870152092](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46109665063/job/140870152092) passed.

This is runtime/security hardening only. It closes no live Single-Host Production gate. The historical v0.2.0-dev.4-test.17 candidate remains stale, unsigned and non-immutable; productionReady remains false/no-go. The next candidate must be built from the current Native runtime commit above. HA/Multi-Host and Kubernetes-Production remain deferred.


## 2026-11-28 – PostgreSQL-Readiness Exec-ID-Härtung (PR #504)

[PR #504](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/504) wurde als [bdd0e5496272874b61c4ab6d8a107674397ff54c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bdd0e5496272874b61c4ab6d8a107674397ff54c) in \`main\` übernommen. Der PostgreSQL-Readiness-Pfad akzeptiert Docker-Exec-IDs vor der Interpolation in \`/exec/<id>/start\` und \`/exec/<id>/json\` nur noch als exakt 64-stellige Kleinbuchstaben-Hexwerte. Regressionstests decken nicht-hexadezimale, zu kurze, zu lange und pfadartige Daemon-Antworten ab und stellen sicher, dass kein Start-Request gesendet wird.

Die automatisierten Nachweise sind grün: [Native/runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46119034851) (Test-Job [140899229674](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46119034851/job/140899229674), real-etcd [140899229518](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46119034851/job/140899229518)), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46119034856/job/140899229400) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46119034849). Real-vm und real-PITR wurden übersprungen; dadurch wurde kein Live-Gate geschlossen.

Der veröffentlichte Kandidat \`v0.2.0-dev.4-test.17\` bleibt veraltet, unsigniert und nicht unveränderlich. \`productionReady=false\` und No-Go bleiben unverändert; der nächste Kandidat muss aus dem aktuellen Main-Commit gebaut und anschließend auf Ubuntu 24.04 mit \`run_real_vm_e2e=true\` qualifiziert werden. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.
