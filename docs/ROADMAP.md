## 2026-11-27 — Native-Inventur und redigierte State-Antworten fail-closed (PR #474)

[PR #474](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/474) wurde als [d6d730d6f9e4825023a5bbf47cc9ffde62911340](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d6d730d6f9e4825023a5bbf47cc9ffde62911340) gemergt. Native-State-Antworten validieren jetzt die vollständige Workload-/Node-/Allocation-Inventur; der Go-Client behandelt redigierte Secret-Projektionen separat und weist exponierten Ciphertext zurück. Damit sind Architecture, Backend/Runtime, Security und QA gegen manipulierte Inventur außerhalb des etcd-CAS-Pfads abgesichert.

Die finalen PR-Prüfungen bestanden: [Native/runtime + Package-Smoke](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876961), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876993), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46052876906) und Real-etcd im Native-Lauf. Real-VM und real-PITR wurden übersprungen; kein Live-Single-Host-Production-Gate ist geschlossen. Countdown bleibt **9/100**, `productionReady=false`, Go/No-Go `no-go`.

Nächster Schritt: unveränderlichen Kandidaten aus Main **d6d730d6f9e4825023a5bbf47cc9ffde62911340** bauen und auf demselben Kandidaten Ubuntu-Installation, Docker/etcd-Lifecycle, Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM sowie Signierung/Provenienz belegen. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

## 2026-11-27 — Persistierte Event-Records fail-closed (PR #471)

[PR #471](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/471) wurde als [bea5189499275880d66c3c486d1ebc0f98232945](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bea5189499275880d66c3c486d1ebc0f98232945) gemergt. Persistierte Events werden jetzt vor Status-/Backup-/Reconciliation-Pfaden auf gültige IDs, Zeitstempel, begrenzte Längen und control-freie Texte geprüft; Regressionen decken ungültige IDs, Zeitstempel, Steuerzeichen, leere und überlange Felder ab. Kein Live-Single-Host-Production-Gate ist geschlossen.

Exakte Checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46046079313), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46046079314), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46046079372); Real-VM und real-PITR wurden übersprungen. `productionReady=false`, Go/No-Go `no-go`, Countdown **9/100**.

Nächster Schritt: unveränderlichen Kandidaten aus `bea5189499275880d66c3c486d1ebc0f98232945` bauen und anschließend die autorisierte Ubuntu-24.04-Qualifikation einschließlich Docker/etcd, Recovery, Upgrade/Rollback, Load/Soak und Supply-Chain-Nachweisen durchführen. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

## 2026-11-27 — Überlappende persistierte Node-PodCIDRs fail-closed (PR #468)

[PR #468](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/468) wurde als [f2c13bd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f2c13bd3360308ab516b553ae46f0f8a4ac5e857) gemergt. Die Runtime übernimmt die bestehende Registrierungsinvariante für PodCIDR-Überschneidungen jetzt auch in `ValidateInventory`: Überlappende gültige Node-Netze werden vor Reconciliation, Backup-Import oder Commit fail-closed abgelehnt; leere PodCIDRs bleiben für zurückgestellte Profile zulässig.

Die exakten PR-Prüfungen bestanden: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810984), [Kubernetes-Verträge](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810956) und [Source/Privacy-Audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/46037810943). Real-VM und real-PITR wurden übersprungen; diese Härtung schließt kein Live-Single-Host-Production-Gate. Der nächste Release-Schritt bleibt ein unveränderlicher Kandidat aus `f2c13bd3360308ab516b553ae46f0f8a4ac5e857` mit autorisiertem Ubuntu-24.04-Lauf. Backup/Restore, Upgrade/Rollback, Load/Soak, SBOM, Signierung/Provenienz und Maintainer-Go/No-Go bleiben offen.

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

[PR #449](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/449) wurde als [5e5f1fd93d4618bd9e187615fffdb08fbee0a9e1](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5e5f1fd93d4618bd9e187615fffdb08fbee0a9e1) gemergt. Der Native-CLI-Befehl `maintenance` validiert Positionsargumente, Operation-ID und Reason vor Konfigurations-/Netzwerkzugriff. Native/runtime inklusive real-etcd, Kubernetes-Contracts und Source/Privacy liefen erfolgreich ([45986242284](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242284), [45986242341](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242341), [45986242331](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45986242331)); real-vm und real-PITR waren übersprungen. Damit wird kein Live-Single-Host-Gate geschlossen. Countdown bleibt **9/100**, `productionReady=false`, Go/No-Go bleibt No-Go. Als nächstes muss ein unveränderlicher Kandidat aus `5e5f1fd93d4618bd9e187615fffdb08fbee0a9e1` gebaut und der autorisierte Ubuntu-24.04-`run_real_vm_e2e=true`-Lauf ausgeführt werden. HA, Multi-Host und Kubernetes-Production bleiben Erweiterungspfad.

## 2026-11-27 — Recovery-Seal nil-State fail-closed (PR #446)

[PR #446](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/446) wurde als [cdfc82d970eef770157ae9c41d9bafa142d90707](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cdfc82d970eef770157ae9c41d9bafa142d90707) gemergt. `internal/recovery.Seal` weist nil-Zustände vor der Inventarprüfung mit `BACKUP_STATE_INVALID` zurück; der Regressionstest stellt den fail-closed-Vertrag sicher. Native/runtime inklusive real-etcd, Kubernetes-Contracts und Source/Privacy liefen erfolgreich ([45977295315](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295315), [45977295203](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295203), [45977295206](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45977295206)); real-vm und real-PITR waren übersprungen. Damit wird kein Live-Single-Host-Gate geschlossen. Countdown bleibt **9/100**, `productionReady=false`, Go/No-Go bleibt No-Go. Als nächstes muss ein unveränderlicher Kandidat aus `cdfc82d970eef770157ae9c41d9bafa142d90707` gebaut und der autorisierte Ubuntu-24.04-`run_real_vm_e2e=true`-Lauf ausgeführt werden. HA, Multi-Host und Kubernetes-Production bleiben Erweiterungspfad.

## 2026-11-27 — Native-Backup-Profil fail-closed (PR #443)

- [PR #443](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/443) ist als [551162dd598d1860ec9537a8cdb3bca365b56bb4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/551162dd598d1860ec9537a8cdb3bca365b56bb4) gemergt. Der Native-CLI-Backup-/Restore-Pfad validiert Quell-, Ziel- und Folgezustand gegen `ValidateNativeSingleHost`; mehrknotige oder ungültige Zustände werden vor Persistenz bzw. CAS-Übernahme abgewiesen.
- Die PR-Läufe [Native/runtime inklusive real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45969482513), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45969482599) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45969482748) waren erfolgreich. real-vm und real-PITR wurden übersprungen; dies ist keine Live-Gate-Evidenz.
- Countdown bleibt **9/100**, `productionReady=false`, Entscheidung `no-go`. Der alte Kandidat `v0.2.0-dev.4-test.17` ist für diesen Code veraltet, unsigniert und nicht unveränderlich. Nächster Roadmap-Schritt ist ein neuer unveränderlicher Kandidat aus Main `551162dd598d1860ec9537a8cdb3bca365b56bb4`, danach der autorisierte Ubuntu-24.04-Lauf.

## Native Single-Host startup-state boundary — PR #441 (2026-11-27)

[PR #441](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/441) merged as [52dff842451a1bf3c4709acf1c1651c02cd9c2d7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/52dff842451a1bf3c4709acf1c1651c02cd9c2d7). The Native control process now validates persisted state against the single-host profile before serving traffic, and setup resume performs the same fail-closed check. Exact checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45961609946), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45961610067) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45961610025). Real-vm and real-PITR were skipped, so no live production gate closed. The published test.17 candidate remains stale, unsigned and non-immutable; `productionReady=false`, countdown **9/100**. Next: build one immutable candidate from current Main and run the authorized Ubuntu 24.04 `run_real_vm_e2e=true` path; backup/restore, upgrade/rollback, bounded soak and signed provenance remain open. HA, quorum and Kubernetes-production remain deferred.

## Native Single-Host admission profile — PR #439 (2026-11-27)

[PR #439](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/439) merged as [5d848c585aa24b065bd1807aeab550482dd6ff6c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5d848c585aa24b065bd1807aeab550482dd6ff6c). The actual Native control process now opts into explicit single-host admission limits (NativeMaxNodes=1, NativeMaxWorkloads=20, NativeMaxAllocations=50), while generic model bounds remain available for deferred multi-host expansion tests. Exact Native/runtime + real-etcd, Kubernetes contract and source/privacy checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45955910147), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45955915226), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45955915225). Real-vm and real-PITR were skipped; no live Single-Host gate closed. The stale test.17 candidate remains out of date. Next: build one immutable candidate from current Main and run the authorized Ubuntu 24.04 real-vm path with run_real_vm_e2e=true; backup/restore, upgrade/rollback, bounded soak and signed provenance remain open. HA, multi-host and Kubernetes-production remain deferred.

## Native Single-Host Release-Handoff — PR #437 (2026-11-27)

Die persistierte Allocation-Kapazität entspricht jetzt dem verbindlichen Native-Single-Host-Limit von 50. Ein Regressionstest belegt, dass die Runtime den 51. Eintrag ablehnt. [PR #437](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/437) wurde als [0ce8e8254a073464081211ad4920262d47b68cf0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0ce8e8254a073464081211ad4920262d47b68cf0) gemergt; Native/runtime + real-etcd, Kubernetes-Contracts und Source/Privacy liefen erfolgreich (Runs [45949044127](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45949044127), [45949044133](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45949044133), [45949044189](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45949044189)). real-vm und real-PITR wurden übersprungen; kein Live-Production-Gate ist geschlossen.

Der nächste Release-Schritt ist ein frischer unveränderlicher Kandidat aus Main **0ce8e8254a073464081211ad4920262d47b68cf0**, anschließend Ubuntu-24.04-Installation/E2E, Backup/Restore, Upgrade/Rollback, begrenzter Load/Soak und signierte Artefakte/Provenienz auf demselben Commit. `productionReady=false`, Countdown **9/100**. HA/Multi-Host, Quorum und Kubernetes-Production bleiben Erweiterungspfade außerhalb des ersten Releases; der Connector kann den autorisierten Tag bzw. `workflow_dispatch` nicht ausführen und wiederholt diesen Blocker nicht.

## Release-Handoff 2026-11-27 — PR #426

Die Native-Restore-Integritätsprüfung begrenzt jetzt Bytes, Einträge und Tiefe auf dieselben Grenzen wie das Volume-Archiv. Dadurch bleibt ein ACK-Replay bei manipulierten oder lokal vergrößerten Restore-Daten fail-closed. [PR #426](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/426) wurde als [124a176fd9a6897ae9931c32070e1b7a74fdfb43](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/124a176fd9a6897ae9931c32070e1b7a74fdfb43) gemergt; der exakte Head [8dd7bfd74d3b455c7a5a2adf6da9eb9bb5ff7687](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8dd7bfd74d3b455c7a5a2adf6da9eb9bb5ff7687) lief durch [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45919510060), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45919510070) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45919510172) erfolgreich; real-vm und real-PITR wurden übersprungen.

Die Änderung verbessert Recovery, Backend/Runtime und Security, ist aber keine Live-Qualifikation. Der nächste Release-Schritt bleibt ein unveränderlicher Kandidat aus Main **124a176fd9a6897ae9931c32070e1b7a74fdfb43** mit autorisiertem Ubuntu-24.04-Lauf (`run_real_vm_e2e=true`), anschließend separat belegtem Backup/Restore, Upgrade/Rollback, Load/Soak und signierten Artefakten/Provenienz. Der Connector kann Tag und `workflow_dispatch` nicht ausführen; dieser Blocker ist dokumentiert und wird nicht wiederholt. Countdown: **9/100**.

## Release-Handoff 2026-11-27 — PR #424

Docker-Antwortgrenzen im Native-Runtime-Adapter sind jetzt fail-closed: Image-Pull- und Image-Load-Streams werden auf feste Größen begrenzt, strict JSON validiert und auf Fehler-/Mehrdeutigkeitsereignisse geprüft; Container-Logs werden ebenfalls begrenzt. [PR #424](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/424) wurde als [7e07433ca88a8c00dba699260a2f97f2394deb4a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7e07433ca88a8c00dba699260a2f97f2394deb4a) gemergt; der exakte Head [ee2f90a166760369a89d64cb8ce46850bc7f6963](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ee2f90a166760369a89d64cb8ce46850bc7f6963) lief durch [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45913630095), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45913630058) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45913630098) erfolgreich; real-vm und real-PITR wurden übersprungen.

Die Änderung verbessert Backend/Runtime und Security, ist aber keine Live-Qualifikation. Der nächste Release-Schritt bleibt ein unveränderlicher Kandidat aus Main **7e07433ca88a8c00dba699260a2f97f2394deb4a** mit autorisiertem Ubuntu-24.04-Lauf (`run_real_vm_e2e=true`), anschließend separat belegtem Backup/Restore, Upgrade/Rollback, Load/Soak und signierten Artefakten/Provenienz. Der Connector kann Tag und `workflow_dispatch` nicht ausführen; dieser Blocker ist dokumentiert und wird nicht wiederholt. Countdown: **9/100**.

## Release-Handoff 2026-11-26 — PR #422

PostgreSQL-Operationspfade behandeln jetzt ungültige Endpunkte, WireGuard-Routen und Client-Ausgaben fail-closed. [PR #422](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/422) wurde als [796f26e2ddcf754b02c007af4ce0f025d4a87da9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/796f26e2ddcf754b02c007af4ce0f025d4a87da9) gemergt; der exakte Head [318f46820542aa05c0f91b199e2ec3ceae1052c7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/318f46820542aa05c0f91b199e2ec3ceae1052c7) lief durch Native/runtime + real-etcd, Kubernetes-Contracts und Source/Privacy erfolgreich. real-vm und real-PITR wurden übersprungen.

Diese Härtung ist kein Production-Gate. Der nächste priorisierte Schritt bleibt ein unveränderlicher Kandidat aus Main [796f26e2ddcf754b02c007af4ce0f025d4a87da9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/796f26e2ddcf754b02c007af4ce0f025d4a87da9) mit kandidatengebundener Ubuntu-Installation, Docker-/etcd-Lifecycle, Backup/Restore, Upgrade/Rollback, Load/Soak sowie signierten Artefakten und Provenienz. Der Connector kann den autorisierten Tag bzw. `workflow_dispatch` nicht ausführen; der Blocker wird nicht wiederholt. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

## Release-Handoff 2026-11-26 — PR #420

PITR-Konfigurationsfehler werden im aktuellen Main fail-closed behandelt: ungültiges UTF-8 im privaten Cipher-Secret und nicht numerische Ports erhalten stabile Blocked-Codes. [PR #420](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/420) ist als [15ceb4ec891387268e816a79366dec1768917c0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/15ceb4ec891387268e816a79366dec1768917c0e) gemergt; Native/runtime + real-etcd, Kubernetes-Contracts und Source/Privacy liefen erfolgreich, real-vm und real-PITR waren übersprungen.

Diese Härtung ist kein Production-Gate. Der nächste priorisierte Schritt bleibt ein unveränderlicher Kandidat aus diesem Main-Commit mit kandidatengebundener Ubuntu-Installation, Docker-/etcd-Lifecycle, Backup/Restore, Upgrade/Rollback, Load/Soak sowie signierten Artefakten und Provenienz. Der Connector kann den autorisierten Tag bzw. `workflow_dispatch` nicht ausführen; der Blocker ist dokumentiert und wird nicht wiederholt. HA/Multi-Host und Kubernetes-Production bleiben Erweiterungspfade.

# Native Single-Host Release-Handoff — PR #418 (2026-11-26)

[PR #418](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/418) wurde als [4224039d0addb0a541785a94b3dd3e3983a4b61e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/4224039d0addb0a541785a94b3dd3e3983a4b61e) gemergt. Native Bootstrap weist ungültiges UTF-8 in lokalen Hosts-/Known-Hosts-Dateien und Remote-Preflight-Ausgaben fail-closed zurück; Regressionen verwenden echte ungültige Bytes.

Die exakten Prüfungen [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45893968020), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45893968015) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45893968183) waren erfolgreich. `real-vm` und `real-PITR` waren übersprungen. Dies ist Operations-/CI-Härtung und schließt kein Single-Host-Production-Gate. Der Kandidat `v0.2.0-dev.4-test.17` bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.

Nächster Schritt: neuen unveränderlichen Kandidaten aus Main 4224039d0addb0a541785a94b3dd3e3983a4b61e bauen und alle kandidatengebundenen Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- und Signatur-/Provenance-Gates ausführen. HA/Multi-Host/Quorum und Kubernetes-Production bleiben späterer Erweiterungspfad.

# Native Single-Host Release-Handoff — PR #416 (2026-11-26)

[PR #416](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/416) wurde als [2627e37201db7ebfdbc31b0a05c9f331d9eef6df](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2627e37201db7ebfdbc31b0a05c9f331d9eef6df) gemergt. Persistierte Allocation-Phasen werden jetzt vor Inventory-Validierung und Reconciliation gegen die explizite State-Machine geprüft; leere oder unbekannte Werte failen geschlossen. Regressionstests decken die ungültigen Phasen ab und aktualisieren die State-Fixtures.

Die exakten Prüfungen [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45887037586), [Kubernetes-Contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45887037581) und [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45887037638) waren erfolgreich; `real-vm` und `real-PITR` waren übersprungen. Das ist CI-/Code-Härtung und schließt kein Single-Host-Production-Gate. Der Kandidat `v0.2.0-dev.4-test.17` bleibt stale, unsigniert und nicht unveränderlich; `productionReady=false`, Entscheidung `no-go`.

Nächster Schritt: einen neuen unveränderlichen Kandidaten aus Main 2627e37201db7ebfdbc31b0a05c9f331d9eef6df bauen und alle kandidatengebundenen Ubuntu-, Backup/Restore-, Upgrade/Rollback-, Load/Soak- und Signatur-/Provenance-Gates ausführen. HA/Multi-Host/Quorum und Kubernetes-Production bleiben späterer Erweiterungspfad.

# Native single-host release handoff — PR #330 (2026-11-25)

[PR #330](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/330) merged as [545cf797](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/545cf797b30958d1d60e8cf5177ee13c37566e00). The release path now treats reproducibility as a build property: `scripts/build-deb.sh` accepts a validated `SOURCE_DATE_EPOCH`, uses deterministic metadata and `-buildvcs=false`, normalizes package mtimes and passes the epoch to `dpkg-deb`. CI performs two clean package builds and compares their SHA-256 digests before writing reproducible-build evidence.

This improves the Release/Supply Chain and Operations layers without overstating qualification. Main evidence: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813) passed; [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813/job/138923825870) and [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813/job/138923826982) were skipped. [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071723) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071869) passed. The next product step is to build an immutable candidate from `545cf797b30958d1d60e8cf5177ee13c37566e00` and run the existing Ubuntu 24.04 real-vm workflow with the exact candidate identity.

No Single-Host gate is closed by this handoff: installation, workload/restart, backup/restore, upgrade/rollback, bounded load/soak, signing/provenance, maintainer approval and user feedback remain open. HA, multi-host, quorum and Kubernetes-production stay on the later roadmap.

# Native single-host release handoff — PR #326 (2026-11-25)

[PR #326](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/326) merged as [204f5de](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/204f5de445c275efab544ebe1e5c21f900ca1e68). Dashboard errors are now bounded to API codes and presented with German operator guidance; status/error/update announcements are accessible live regions, successful mutations clear stale alerts, and Werftkern branding is consistent.

PR and post-merge Main Native/real-etcd, Kubernetes contract and Source/Privacy checks passed. Real-vm and real-PITR were skipped, and local Chromium could not start; these results do not close a Single-Host production gate. The mutable test.17 candidate remains unsigned/non-immutable and `productionReady=false`. Build the next immutable candidate from [204f5de](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/204f5de445c275efab544ebe1e5c21f900ca1e68) before live installation, backup/restore, upgrade/rollback, bounded soak and signing evidence. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #324 (2026-11-25)

[PR #324](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/324) merged as [9671c64](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/9671c64edbe67f02ca18a21244abdd0833c55c5b). State/journal writes and operation locks now fail closed on symlinked parent components, preventing redirected local state creation.

PR and post-merge Main checks passed for Native, real-etcd, Kubernetes contracts and Source/Privacy; real-vm and real-PITR remain skipped, so no Single-Host production gate closed. Rebuild an immutable candidate from [9671c64edbe67f02ca18a21244abdd0833c55c5b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/9671c64edbe67f02ca18a21244abdd0833c55c5b) before installation, backup/restore, upgrade/rollback, bounded load/soak and signing evidence. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #322 (2026-11-24)

[PR #322](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/322) merged as [80c091e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/80c091e03d1c7687c46a7ca4543f55b34d281bfe). Secret staging and cleanup now fail closed when the configured SecretRoot or any parent is a symlink; the default root is applied consistently and a regression test covers operator-provided redirection.

PR and post-merge Main checks passed for Native, real-etcd, Kubernetes contracts and Source/Privacy. Real-vm and real-PITR remain skipped, so no Single-Host production gate closed. Rebuild an immutable candidate from [80c091e03d1c7687c46a7ca4543f55b34d281bfe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/80c091e03d1c7687c46a7ca4543f55b34d281bfe) before installation, backup/restore, upgrade/rollback, bounded load/soak and signing evidence. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #308 (2026-11-24)

PR [#308](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/308) merged as [c0e7b30](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c0e7b30320f46562177b837f1a0afaf01bf7de17). Volume archive backup now fails closed before key creation when the archive parent is missing, non-directory or symlinked. Regression tests cover missing and symlinked parents.

The Native code checks and real-etcd passed in [run 45454133889](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45454133889), contracts passed in [run 45454133869](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45454133869), and source/publication audit passed in [run 45454133920](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45454133920). Real-vm and real-PITR were skipped; no Single-Host production gate closed.

The next release step is an exact immutable candidate from c0e7b30320f46562177b837f1a0afaf01bf7de17 and candidate-bound Ubuntu 24.04 qualification. Backup/restore, upgrade/rollback, bounded load/soak, signed provenance and maintainer approval remain open. HA/multi-host and Kubernetes Production remain deferred outside the first scope.

# Native single-host release handoff — PR #305 (2026-11-24)

PR [#305](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/305) merged as [ea980c4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea980c46e04b7939251d9e787f8635b69d2d29d5). Backup creation and schema migration now fail closed before key creation when the output aliases the key by absolute path or when its parent is missing or symlinked. The regression tests cover backup, schema and trusted-file parent validation.

The Native code checks and real-etcd passed in [run 45443014723](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45443014723), contracts passed in [run 45443013024](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45443013024), and source/publication audit passed in [run 45443013302](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45443013302). Real-vm and real-PITR were skipped; no Single-Host production gate closed.

The next release step is an exact immutable candidate from ea980c46e04b7939251d9e787f8635b69d2d29d5 and candidate-bound Ubuntu 24.04 qualification. Backup/restore, upgrade/rollback, bounded load/soak, signed provenance and maintainer approval remain open. HA/multi-host and Kubernetes Production remain deferred outside the first scope.

# Current main handoff — PR #297 (2026-11-24)

The Native failover transport now fails closed for unkeyed etcd transaction retries after a lost acknowledgement; keyed requests remain replayable through the existing idempotency contract. The regression test is tracked in [PR #297](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/297), merged as [70c97f3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/70c97f3d48bf785a697f01fdf35e0896b3ae68bf).

This is runtime/reliability hardening only. Native/Kubernetes/source checks passed, but real-vm, backup/restore, upgrade/rollback, bounded load/soak, signed provenance and maintainer approval remain open. The next release step is an exact immutable candidate from `70c97f3d48bf785a697f01fdf35e0896b3ae68bf` and candidate-bound Ubuntu 24.04 qualification; HA/multi-host and Kubernetes Production remain deferred outside the first scope.

# Production qualification evidence review (2026-11-24, Run #1662)

GitHub Actions [Run #1662](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45372806861) was manually dispatched with `run_real_vm_e2e=true` from Main commit `7f1a81ae8eba7042c3c1440ba4151a5a84acd903`. The `actual-ubuntu-vm-evidence` artifact (workflow artifact `14909024562`) contains `ubuntu-vm-result.json` with `status=passed`, exit code 0, Ubuntu 24.04 amd64, Docker Engine 28.0.4, etcd 3.4.30 and package SHA-256 `05042f7c02465c012a34a230a00185b77f014f778de874ed10937e457deb3623`.

This is genuine single-host installation/runtime evidence for that unchanged commit; it does not certify HA or multi-node networking. Main now contains PR #292 recovery hardening and is at [18c0c3d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/18c0c3dd74d263ab155f8988d3a432a44887fdc6), so the run cannot close the current exact-candidate gate. The stale evidence is recorded for traceability only; `productionReady=false` and the decision remains `no-go`.

Next handoff: build an immutable candidate from [479f4be](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/479f4beaecb919b7b376300927282262a7213530), rerun the same Ubuntu path against that exact candidate, then complete backup/restore, upgrade/rollback, bounded load/soak, signing/provenance and Go/No-Go.

# Latest code handoff (2026-11-24, PR #292)

PR [#292](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/292) merged as [479f4be](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/479f4beaecb919b7b376300927282262a7213530). Native restore mapping now fails closed for every workload with an explicit source node selector unless a target-node mapping is provided, including workloads without volumes. This prevents a paused restore from retaining a stale source-node reference. Regression coverage is in `internal/recovery/mapping_test.go`.

Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45379013283) — compile/race/static/package checks and real-etcd **success**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45379013752) — **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45379013761) — **success**. Native real-vm and real-PITR were explicitly skipped. No Single-Host production gate closed.

The mutable, unsigned `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and cannot evidence this Main commit. `productionReady=false` and the decision remains `no-go`. Fresh Ubuntu installation/reinstallation, Docker/etcd lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed SBOM/provenance, release-candidate feedback and maintainer approval remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [479f4be](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/479f4beaecb919b7b376300927282262a7213530) and dispatch `ci.yml` with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not claim skipped jobs or the private alpha workflow as live qualification evidence.

# Latest code handoff (2026-11-24, PR #289)

PR [#289](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/289) merged as [2d5b982](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2d5b9828f0cd696380259b93ac586ad2d14b31cb). Native release verification now bounds package hashing to 256 MiB before digest verification and rejects oversized regular files with stable `PACKAGE_TOO_LARGE` handling. The sparse-file regression test `TestVerifyRejectsOversizedPackageBeforeHashing` protects this fail-closed resource boundary.

Exact PR checks passed: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45315680883) with [real-etcd success](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45315680883), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45315680853) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45315680843). Native real-vm and real-PITR were explicitly skipped.

No Single-Host qualification gate closed. The mutable, unsigned `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Fresh Ubuntu installation/reinstallation, Docker/etcd lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed SBOM/provenance, release-candidate feedback and maintainer approval remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [2d5b9828f0cd696380259b93ac586ad2d14b31cb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2d5b9828f0cd696380259b93ac586ad2d14b31cb) and dispatch `ci.yml` with `run_real_vm_e2e=true` when workflow-dispatch access is available. Do not claim skipped jobs or the private alpha workflow as live qualification evidence.

# Latest code handoff (2026-11-24, PR #287)

PR [#287](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/287) merged as [d286279a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d286279a8e9a1728910204293380c6dcf3953f10). Native `werft release verify` now validates all required manifest, signature, public-key and package paths plus positional arguments before reading any file, returning stable `RELEASE_ARGUMENTS_INVALID` for incomplete input. The regression test `TestReleaseCommandRejectsIncompleteInputBeforeReadingFiles` covers the fail-closed path.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308382126) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308382080) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308382109) **success**. Post-merge Main checks also passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308989520), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308989479) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45308989539).

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [d286279a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d286279a8e9a1728910204293380c6dcf3953f10) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-24, PR #285)

PR [#285](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/285) merged as [e564148b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e564148b89a883190aa116ea5848540ebd48c922). Native certificate dispatch now rejects unknown operations before reading the configured CA certificate. The regression test `TestCertificateUnknownOperationFailsBeforeCARead` proves malformed input returns `UNKNOWN_CERTIFICATE_OPERATION` even when the CA path is unavailable.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45292645090) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45292645074) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45292645094) **success**. Post-merge Main checks also passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45293062402), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45293062401) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45293062474).

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [e564148b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e564148b89a883190aa116ea5848540ebd48c922) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-23, PR #282)

PR [#282](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/282) merged as [8800325a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8800325ab64dd701a69d65a39f332e6153c9da0d). Native `volume`, `secret` and `gateway` dispatch now rejects unknown actions before loading admin configuration or attempting controller access. A regression table uses an unavailable configuration path and verifies stable fail-closed errors for all three command families. This removes an unnecessary configuration/control-plane side effect from malformed CLI input.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152469) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152601) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152514) **success**. The documented second self-review was recorded on the PR; GitHub correctly disallows self-approval.

This defensive CLI change closes no Single-Host qualification gate. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope. Next handoff: build a new immutable candidate from [8800325a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8800325ab64dd701a69d65a39f332e6153c9da0d) and use the existing ephemeral Ubuntu path when dispatch access is available. Do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-23, PR #279)

PR [#279](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/279) merged as [bfc74495](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bfc74495a3248d98df9cfc770eac3a519811e2d0). Native node drain|uncordon|revoke NAME now validates the policy action before loading admin configuration or reading controller state. Malformed two-argument actions therefore fail closed without an unnecessary control-plane request. TestNodePolicyBody covers all supported bodies and the NODE_ACTION_UNKNOWN contract.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274712039) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274712036) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274711955) **success**.

This defensive CLI change closes no Single-Host qualification gate. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296, reports immutable=false and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope. Next handoff: build a new immutable candidate from [bfc74495](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bfc74495a3248d98df9cfc770eac3a519811e2d0) and use the existing ephemeral Ubuntu path when dispatch access is available. Do not start a seven-VM HA or Kubernetes lab for this first release.
# Latest code handoff (2026-11-23, PR #277)

PR [#277](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/277) merged as [2c4cbd4e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2c4cbd4ec54e63b52e45dde557809dfa13d2b88e). Native gateway enrollment now reads controller state before creating the credential directory or writing mTLS files. A transient controller/API failure therefore leaves no incomplete directory that blocks a safe retry with the same gateway identity. The generated ingress example was extracted into a deterministic helper and regression-tested for stable CIDR de-duplication, scoped routes and gateway/client identity.

PR checks:
- Native runtime/package [45264880235](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45264880235) — **success**; compile, race/static checks, package smoke checks and reachable Go vulnerability check passed; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45264880291](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45264880291) — **success**.
- Source/Privacy audit [45264880241](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45264880241) — **success**.

The first PR attempt exposed a source-transfer error in the remote Go blob; the Native compile check failed, the exact blob was republished, and the corrected head passed all available PR workflows before merge. This is recorded as a corrected publication defect, not as a production qualification result. The connector exposed no post-merge Main workflow runs for [2c4cbd4e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2c4cbd4ec54e63b52e45dde557809dfa13d2b88e) at handoff time.

No Single-Host qualification gate closed. The unchanged [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [2c4cbd4e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2c4cbd4ec54e63b52e45dde557809dfa13d2b88e) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM lab for this first release.

# Latest code handoff (2026-11-23, PR #274)

PR [#274](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/274) merged as [960ddafc](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/960ddafc6ab99b883ebdb2c180be41e71d3a071f). Native volume archive CLI dispatch now rejects unknown actions before root, state, Docker or filesystem access; a regression test covers the fail-closed boundary. The initial blob transfer was truncated and caught by CI; the complete file was republished before merge.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629415) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629612) **success**; [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629987) **success**. Post-merge Main checks also passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254149973), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254150050) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254149998). The [alpha publication guard](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254244539) passed and skipped source-only publication because no release was created.

This closes no Single-Host qualification gate. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new immutable candidate from [960ddafc](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/960ddafc6ab99b883ebdb2c180be41e71d3a071f) and use the existing ephemeral Ubuntu path when dispatch access is available. Do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-23, PR #272)

PR [#272](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/272) merged as [d92c922f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d92c922fa8f1d46fc98e9dd5580124dacfdba001). Native `CreateBundle` now validates the join-bundle output destination before loading PKI material or registering the worker through `POST /v1/nodes`. Empty paths, existing destinations, final symlinks and symlinked parents are rejected; regression coverage verifies safe missing paths and each rejection case. This prevents a deterministic remote registration without a materialized local bundle.

PR checks:
- Native runtime/package [45244001391](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244001391) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45244001496](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244001496) — **success**.
- Source/Privacy audit [45244001445](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244001445) — **success**.

Post-merge Main checks:
- Native runtime/package [45244598160](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244598160) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45244598234](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244598234) — **success**.
- Source/Privacy audit [45244598089](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45244598089) — **success**.

The roadmap remains **No-Go**: no Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope. Next handoff: build a new immutable candidate from [d92c922f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/d92c922fa8f1d46fc98e9dd5580124dacfdba001) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #270)

PR [#270](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/270) merged as [f7ab7e5a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f7ab7e5a0d3f10a6fa182222fb24c61c5dbb6b85). Native worker join-bundle input now uses no-follow safefile.OpenRead and bounded strict-JSON parsing from the opened descriptor. Final and parent symlink redirection, group-readable inputs and oversize bundles are rejected; regression coverage pins those cases and the exact 32 KiB boundary.

PR checks:
- Native runtime/package [45233988541](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45233988541) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45233988578](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45233988578) — **success**.
- Source/Privacy audit [45233988580](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45233988580) — **success**.

Post-merge Main checks:
- Native runtime/package [45234652978](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45234652978) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45234652991](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45234652991) — **success**.
- Source/Privacy audit [45234653067](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45234653067) — **success**.

This defensive change closes no Single-Host qualification gate. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296, reports immutable=false and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff (2026-11-23, PR #268)

PR [#268](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/268) merged as [f73662f4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f73662f4e957cf0489319d34445715d17c626cd4) with no-follow safefile directory locking, parent-chain validation, regular-file/0600/owner checks and a parent-symlink regression test. PR Native, Kubernetes and Source/Privacy checks passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220888940), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220888882), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220889258)). Post-merge Main checks also passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221411990), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221412038), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221412406)); Native real-etcd passed while real-vm/PITR remain skipped.

This handoff closes no production gate. The old v0.2.0-dev.4-test.17 release remains non-immutable and unsigned, so a new candidate must be built from f73662f4 before live qualification. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.
# Latest code handoff (2026-11-23, PR #266)

PR [#266](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/266) merged as [cdc929e8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cdc929e8651bef08ee4744edc234fa4c52f9ff35) with no-follow local lock handling, parent-chain validation, regular-file/0600/owner checks and final/parent symlink regression coverage. PR Native, Kubernetes and Source/Privacy checks passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211017062), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211016964), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211016962)). Post-merge Main checks also passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279490), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279129), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279244)); Native real-etcd passed while real-vm/PITR remain skipped.

This handoff closes no production gate. The old v0.2.0-dev.4-test.17 release remains non-immutable and unsigned, so a new candidate must be built from cdc929e8 before live qualification. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.
# Latest code handoff (2026-11-23, PR #264)

PR [#264](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/264) merged as [1b24e6cd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1b24e6cd7b0f38c13797f2ab161a609e2641ca48) with no-follow admin-certificate input and regression coverage for final and parent symlink paths. PR Native, Kubernetes and Source/Privacy checks passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198552808), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198553068), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198552768)). Post-merge Main checks also passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052283), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052324), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052375)); Native real-etcd passed while real-vm/PITR remain skipped.

This handoff closes no production gate. The old v0.2.0-dev.4-test.17 release remains non-immutable and unsigned, so a new candidate must be built from 1b24e6cd before live qualification. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.

# Latest code handoff (2026-11-23, PR #262)

PR [#262](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/262) merged as [b99d5b8d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b99d5b8d25b839f94fc1ed1e3c82cc658c74f4fe) with no-follow demo-archive verification and regression coverage for final and parent symlink paths. PR Native, Kubernetes and Source/Privacy checks passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154392), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154412), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154242)). Post-merge Main checks also passed ([Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685437), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685472), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685479)); Native real-etcd passed while real-vm/PITR remain skipped.

This handoff closes no production gate. The old v0.2.0-dev.4-test.17 release remains non-immutable and unsigned, so a new candidate must be built from b99d5b8d before live qualification. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.

# Latest code handoff (2026-11-23, PR #260)

PR [#260](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/260) merged as [5cfd4726](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5cfd47267648840f57d947e2bc9f14443e2bf2b2). Native `werft assess` inventory inputs now use no-follow regular-file access, with regression coverage for valid, final-symlink and parent-symlink paths. Required PR and post-merge Main checks are green: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128482), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128580) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128505); real-vm/PITR remain skipped.

This defensive input hardening does not close a Single-Host gate. The next candidate must be rebuilt from [5cfd4726](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5cfd47267648840f57d947e2bc9f14443e2bf2b2). Fresh Ubuntu install/reinstall, Docker/etcd lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability and final Go/No-Go evidence remain open. HA, multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff (2026-11-23, PR #257)

PR [#257](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/257) merged as [bafbf1e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bafbf1e98d93490282117b36a26a89eb3f51581b). Native secret-directory reuse now uses no-follow, bounded manifest reads and enforces the expected regular 0400 manifest. A regression test covers a symlinked manifest. Required PR and post-merge Main checks are green: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170406716), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170406949) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170407002); real-vm/PITR remain skipped.

This defensive hardening does not close a Single-Host gate. The next candidate must be rebuilt from [bafbf1e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bafbf1e98d93490282117b36a26a89eb3f51581b). Fresh Ubuntu install/reinstall, Docker/etcd lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability and final Go/No-Go evidence remain open. HA, multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff (2026-11-23, PR #255)

PR [#255](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/255) merged as [e1586312](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e15863120152e08e280c65e8d00b00d27c06ea61). The Native `apply DATEI.json` path now opens manifest inputs through `safefile.OpenRead`, rejecting final and parent symlink traversal before a mutating manifest is parsed. Regression coverage verifies a valid file and both symlink forms. Stdin input (`-`), strict JSON, size limits, API contracts and state schema are unchanged.

Post-merge Main checks:
- [Native runtime/package 45160914694](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45160914694) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45160914910](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45160914910) — **success**.
- [Source/Privacy audit 45160914778](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45160914778) — **success**.

No Single-Host qualification gate closed. The existing `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [e1586312](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e15863120152e08e280c65e8d00b00d27c06ea61) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #253)

PR [#253](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/253) merged as [39965f40](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/39965f40c5103e64cfe563da4d4631df9032fb6a). Native volume restore archive inputs now use `safefile.OpenRead`, rejecting final and parent symlink traversal before archive bytes are consumed. A focused regression covers a valid archive and a parent-symlink path. Archive format, restore state and authorization policy are unchanged.

Post-merge Main checks:
- [Native runtime/package 45151283506](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45151283506) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45151283604](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45151283604) — **success**.
- [Source/Privacy audit 45151283665](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45151283665) — **success**.

No Single-Host qualification gate closed. The existing `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [39965f40](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/39965f40c5103e64cfe563da4d4631df9032fb6a) and use the existing ephemeral Ubuntu path when dispatch access is available.

## Latest code handoff (2026-11-23, PR #244)

PR [#244](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/244) merged as [6faf2fbe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6faf2fbe819ae7a0775d27727986bc02be07228e). Native ingress gateway credentials now use no-follow certificate/private-key reads, while edge TLS PEM loading is bounded and refuses final and parent symlinks. Regression tests cover valid pairs and symlinked certificate/key paths. This is defensive PKI hardening; no production gate is closed.

Exact PR checks:
- [Native PR 45120310439](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310439) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes PR 45120310428](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310428) — **success**.
- [Source/Privacy PR 45120310459](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310459) — **success**.

Exact post-merge Main checks:
- [Native Main 45120597182](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597182) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main 45120597181](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597181) — **success**.
- [Source/Privacy Main 45120597194](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597194) — **success**.

The roadmap remains **No-Go** until a new immutable candidate is built from [6faf2fbe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6faf2fbe819ae7a0775d27727986bc02be07228e) and the scoped live gates (fresh Ubuntu install, Docker/etcd workload lifecycle, restart, local backup/restore, single-host upgrade/rollback, bounded load/soak, signed artifacts/provenance and final Go/No-Go) are evidenced for that unchanged candidate. HA, multi-host and Kubernetes Production remain deferred outside the first Native scope.

## Latest code handoff (2026-11-23, PR #242)

PR [#242](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/242) merged as [485fcfd2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/485fcfd2b9f53abc857dfe19d66e8741981aa864). Native certificate bundle/renew/install now opens CA and leaf certificate inputs through `safefile.OpenRead`, refusing final and parent symlinks and enforcing a bounded 1 MiB read. Regression tests cover both symlink forms. This is a defensive input-hardening change; no production qualification gate is closed.

Exact PR checks:
- [Native PR 45115171200](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171200) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes PR 45115171140](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171140) — **success**.
- [Source/Privacy PR 45115171174](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171174) — **success**.

Exact post-merge Main checks:
- [Native Main 45115468629](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468629) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main 45115468670](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468670) — **success**.
- [Source/Privacy Main 45115468624](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468624) — **success**.

The roadmap remains **No-Go** until a new immutable candidate is built from [485fcfd2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/485fcfd2b9f53abc857dfe19d66e8741981aa864) and the scoped live gates (fresh Ubuntu install, Docker/etcd workload lifecycle, restart, local backup/restore, single-host upgrade/rollback, bounded load/soak, signed artifacts/provenance and final Go/No-Go) are evidenced for that unchanged candidate. HA, multi-host and Kubernetes Production remain deferred outside the first Native scope.

## Latest code handoff (2026-11-23, PR #239)

PR [#239](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/239) merged as [43bcfb46](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/43bcfb468680d976b181a5ca8a745d55bd1d63ff). Native backup inspect/restore inputs now use `safefile.OpenRead`, refusing final and parent symlinks and enforcing the bounded read after opening; regression tests cover the boundary. The corrected head passed the Native, Kubernetes and Source/Privacy checks.

Exact Main checks:
- [Native runtime/package 45108824975](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108824975) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts/package 45108825010](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108825010) — **success**.
- [Source/Privacy audit 45108824979](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108824979) — **success**.

No qualification gate was closed. The current `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and remains `productionReady=false`/No-Go. The next candidate must be built from `43bcfb468680d976b181a5ca8a745d55bd1d63ff`; live installation, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability and final Go/No-Go remain open. The connector cannot dispatch `ci.yml`, so no live gate is implied.

# Masterplan traceability

## Latest code handoff (2026-11-23, PR #237)

PR [#237](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/237) merged as [6463c29d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6463c29de2a1bfcb6c9e7dbcfbfeae26585d427d). Native `werft release verify` now uses `safefile.OpenRead` for manifest, signature and public-key inputs, rejecting final/parent symlinks and enforcing the size limit after opening. Regression coverage protects both symlink forms and the limit.

Exact Main checks:
- [Native runtime/package 45103114622](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114622) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts/package 45103114692](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114692) — **success**.
- [Source/Privacy audit 45103114649](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114649) — **success**.

No qualification gate was closed. The current `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and remains `productionReady=false`/No-Go. The next candidate must be built from `6463c29de2a1bfcb6c9e7dbcfbfeae26585d427d`; live installation, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability and final Go/No-Go remain open. The connector cannot dispatch `ci.yml`, so no live gate is implied.

## Previous code handoff (2026-11-23, PR #230)

PR [#230](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/230) merged as [397e0ff](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/397e0ff6de39404f631aab92c12ed9719108c617). Native release verification now opens candidate packages through `safefile.OpenRead`, rejecting final symlinks, symlinked parent paths and non-regular files before hashing. Regression coverage protects both symlink shapes.

Exact PR checks passed: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446362), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446302) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45085446373). Real-etcd passed; real-VM and real-PITR were skipped. The first attempt's self-introduced formatting error was corrected before the final green checks. This is release-artifact path hardening only: `v0.2.0-dev.4-test.17` remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `immutable=false` and unsigned, and no qualification gate was closed. Build the next candidate from `397e0ff6de39404f631aab92c12ed9719108c617` before live evidence can cover this fix.

## K20-001 — Review-Baseline und Ausführungspfade verifizieren

**partial**. Separate Alpha neu gebaut/getestet; private C#-DI nicht erneut ausgeführt.

## K20-002 — ADRs, Invarianten und Threat Model festlegen

**partial**. Architektur-/Threat-Grenzen dokumentiert, kein unabhängiger Review.

## K20-003 — Management auf .NET 10 LTS migrieren

**not-implemented-or-not-executed**. Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen.

## K20-004 — Native-Modul und versionierte Buildgrenzen anlegen

**partial**. Eigenes Go-Modul und Paket/CI vorhanden, Managementintegration fehlt.

## K20-005 — Versioniertes Runtime-Ressourcenmodell definieren

**partial**. Schema2 adds gateway ACLs, ordered heartbeats and restore receipts; explicit offline migration. Bounded model, no full ecosystem parity.

## K20-006 — etcd-State-Adapter und revisionssicheren Watch implementieren

**partial**. etcd-CAS über ein Stateobjekt; kein revisionssicherer Watch.

## K20-007 — Admission, Autorisierung und Idempotenz sichern

**partial**. Admin/Node/Gateway mTLS ACL and negative tests; still no tenant/workspace IAM or independent security review.

## K20-008 — Native-CLI für Apply, Status und Delete liefern

**partial**. CLI Apply/Status/Delete vorhanden; kein echtes Ubuntu-Gate.

## K20-009 — Einmaliges Enrollment und mTLS-Nodeidentität umsetzen

**partial**. Node join credentials plus offline-CA leaf renewal, atomic combined PEM install and real local TLS reload tests. No online enrollment service, full CA or multi-host rotation qualification.

## K20-010 — Agentprotokoll mit Allocation- und Epoch-Verträgen umsetzen

**partial**. Explicit state-schema2 dev.3/dev.4 protocol edge, tested with actual old/new agent executables and real mTLS; Docker/etcd fixtures. No general version guarantee.

## K20-011 — Durables Agentjournal und Replay entwickeln

**partial**. Journal/sequence durable replay and terminal-report rejection; real Docker/host recovery not qualified.

## K20-012 — Echten Container-Lifecycle über containerd integrieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-013 — Nodeinventar und Ressourcenreservierung modellieren

**partial**. Nodekapazität und Reservierungen; keine umfassende Hostdruckmessung.

## K20-014 — Deterministischen Scheduler mit atomarem Binding implementieren

**partial**. Reproduced/fixed stale-readiness retirement defect; lock-owned selective drain and CAS/scope tests. Real Raft/VM qualification remains absent.

## K20-015 — Level-basierten Reconciler und Revisionsstatus implementieren

**partial**. Periodischer Soll-/Ist-Abgleich; kein Watch-/vollständiger Controllervertrag.

## K20-016 — Löschsemantik, Tombstones und Ressourcen-GC absichern

**partial**. Stop/Deletion/Journal; historische State-/Tombstone-GC begrenzt.

## K20-017 — Lokalen CNI-Vertrag und Attachment-Cleanup implementieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-018 — Nodeübergreifendes Netz, IPAM und WireGuard qualifizieren

**partial**. WireGuard/routed Docker bridge preparation/apply code; no live mesh/MTU/firewall tests.

## K20-019 — Default-deny-Policies und Quarantäne einführen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-020 — CoreDNS-Service-Discovery ohne Kubernetes anbinden

**partial**. CoreDNS zone generator and authenticated discovery API; no live CoreDNS/multi-node proof.

## K20-021 — Envoy-Ingress, TLS und reale Verkehrsprüfung integrieren

**partial**. Scoped Go HTTPS ingress with actual local TLS/HTTP route tests. Deliberate alternative to Envoy; no public DNS/VM, ACME, HA edge or traffic qualification.

## K20-022 — Versionierte Secretbereitstellung auf Allocations begrenzen

**partial**. AES-GCM-Versionen, Allocation-ACL und tmpfs-Staging; echte Mountqualifikation fehlt.

## K20-023 — Startup-, Readiness- und Liveness-Semantik testen

**partial**. Readiness freshness unified, repeated observations keep original timestamp; full startup/liveness policy remains incomplete.

## K20-024 — Rolling Update, Drain und Image-Rollback liefern

**partial**. Rolling Update, Drain/Rollback, Pause; reale VM-Gates fehlen.

## K20-025 — Native-RuntimeTarget und Hetzner-Provisionierung integrieren

**partial**. Standalone Hetzner HTTP adapter and intent journal; no live calls or ClusterPilot connector.

## K20-026 — Management-Outbox und Runtime-Statusprojektion implementieren

**not-implemented-or-not-executed**. Externe/private Managementintegration nicht Teil dieser eigenständigen Codebasis; ursprüngliches Ziel offen.

## K20-027 — Native-Workload- und Diagnoseansichten entwickeln

**partial**. Eigenes minimales Dashboard, nicht vollständige Management-UI.

## K20-028 — Management- und Runtime-Berechtigungen negativ prüfen

**partial**. Negative Admin/Node- und Scope-Tests; keine Management-/Multi-Tenant-IAM.

## K20-029 — Drei-Controller-HA und unabhängiges Bootstrap liefern

**partial**. Three-controller kits and install path with TLS etcd peers; no actual quorum tests.

## K20-030 — Metriken, Korrelation und Supportbundle integrieren

**partial**. Gebundene Metriken/Ereignisse, kein vollständiger Support-/Tracepfad.

## K20-031 — Partition- und Quorumverlustverhalten qualifizieren

**partial**. Konservativer Unknown-Zustand; kein echtes Quorum-/Partition-Gate.

## K20-032 — Backup/Restore mit neuer Recovery-Epoch umsetzen

**partial**. Encrypted config/file backups and pgBackRest isolated PITR adapter; real WAL replay test blocked by absent binaries. No full-site DR.

## K20-033 — Signierte Native-Releases und Lieferkettenevidenz aufbauen

**partial**. Paket/Quellcodechecks/Releaseblockade; keine Signaturen/Provenancefreigabe.

## K20-034 — Ubuntu-, RHEL- und root/sudo-Installationsprofile qualifizieren

**partial**. Ubuntu-Setupcode, keine tatsächliche Ubuntu-/RHEL-Qualifikation.

## K20-035 — N/N−1-Protokoll, Canary-Updates und sichere Migration testen

**partial**. Sequential signed worker updater, owned drain, scoped host verification, local Docker/HTTP smoke code, persisted observation/recovery. Command fixtures pass; actual Ubuntu/SSH/Docker and controller-wave qualification NOT done.

## K20-036 — Airgap-Bundle und Offline-Recovery qualifizieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-037 — Deterministischen Zustands- und Nachrichtensimulator erstellen

**partial**. Reale Prozesstests mit Protokollfixtures; kein vollständiger Zustandsraum-Simulator.

## K20-038 — Fault-Injection-Suite auf echten VMs ausführen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-039 — Kapazitäts-, Latenz- und Betriebsvergleich messen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-040 — Externen Sicherheitsreview mit Remediation abschließen

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.

## K20-041 — Read-only Kubernetes-Migrationsassessor entwickeln

**partial**. Offline-JSON-Assessor ohne Werte; kein automatischer Import.

## K20-042 — Parallele Migration und Routing-Rollback proben

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-043 — Zehn Problemgespräche und zwei Designpartner validieren

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.

## K20-044 — Begrenzten bezahlten Designpartner-Pilot durchführen

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.

## K20-045 — Nodegebundene persistente Volumes als eigene Klasse ergänzen

**partial**. Node-bound persistent directories plus encrypted physical file archive/restore, IO locks and lost-ACK receipts. Real container/host/data-loss qualification absent.

## K20-046 — Unabhängige Writer-Fencing-Capability implementieren

**partial**. Native Patroni profile requires a watchdog; no real watchdog/fencing validation and no general orchestrator fencer.

## K20-047 — Einen CSI-Treiber vollständig qualifizieren

**partial**. Hetzner hcloud-csi 2.24.2 ist als enger Kandidat mit festem Chart-Digest,
k0s-Kubelet-Pfad und konservativer `Retain`-StorageClass ausgewählt. Sechs OCI-Index-
Digests und ein reproduzierbarer, hashgebundener Helm-Render sind geprüft. Signaturen,
Vulnerability-Clearance sowie reale Provision/Attach/Mount/Expansion/Failure/Backup/
Restore-Qualifikation fehlen. Ein statischer Fail-closed-Audit bindet RBAC, einen dedizierten
Node-ServiceAccount ohne automatischen Token-Mount, privilegierten Node-Treiber, HostPaths
und MountPropagation. `RuntimeDefault` ist auf Pod-Ebene für die nicht privilegierten
Container gebunden; der privilegierte Node-Treiber bleibt eine explizite Ausnahme.
Die immutable linux/amd64 Manifest-/Config-Kette ist zusätzlich geprüft: Alle sechs
Images verwenden explizit oder implizit root, und das Upstream-Chart bietet keine
SecurityContext-Werte je Container. Pod-weites `runAsNonRoot` bleibt deshalb bewusst
blockiert. Ein Post-Renderer akzeptiert nur den exakten geprüften Eingangs-Hash, macht
alle Root-Identitäten explizit und erzwingt für die sieben nicht privilegierten
Containerinstanzen `allowPrivilegeEscalation: false`, den Drop aller Capabilities und
`RuntimeDefault` auf Container-Ebene. Der privilegierte Node-Treiber bleibt die eng
gebundene Ausnahme. Alle acht gerenderten Container-Instanzen besitzen fail-closed
geprüfte CPU-/Memory-Requests und -Limits als konservative Startbudgets. Deren Eignung
ist nicht gemessen; echte Last-, Soak- und Laufzeittests sowie non-root-fähige
Container-Identitäten bleiben offen. Keine Produktionsfreigabe.

## K20-048 — Ein Stateful-Profil mit Replikation und Restore freigeben

**partial**. Native PostgreSQL17/Patroni4 synchronous HA profile and pgBackRest PITR adapter implemented; no actual database/HA/replay qualification.

## K20-049 — Jobs und CronJobs mit expliziter Retry-Semantik entwickeln

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-050 — Regelbasiertes App- und Node-Autoscaling ergänzen

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-051 — Ein GPU-Workloadprofil qualifizieren

**not-implemented-or-not-executed**. Nicht implementiert bzw. nicht durchgeführt.

## K20-052 — Enge GA anhand der Freigabegates entscheiden

**not-implemented-or-not-executed**. Externer Review, Kundenarbeit oder Freigabeentscheidung; nicht durch Code erzeugt.



## Latest code handoff (2026-11-21)

PR #160 is merged at [a04b0b4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a04b0b4c9db7f4f0aa5e408446b45cb5fe25dd1a). It hardens the Kubernetes-manager plan parser against valid non-object JSON and adds a regression test for the stable fail-closed response. This does not alter either component version, the immutable test17 candidate, or any production gate. Post-merge required checks passed; the privileged live jobs remain skipped. The next evidence-bearing step is an expressly authorized disposable Ubuntu/k0s run, not another readiness claim.


## Latest code handoff (2026-11-21, PR #162)

PR #162 merged at [2ad8daeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/2ad8daebed99f8ea2b6735f9f626e500666cd694). It hardens Kubernetes-manager wrapper resolution against incomplete Python package trees and adds a regression test for a missing package marker. Required automated checks passed; privileged real-VM/PITR jobs remain skipped. This does not alter component versions, the immutable test17 candidate, or any production qualification gate. The next evidence-bearing step remains an expressly authorized disposable Ubuntu/k0s run.
## Latest code handoff (2026-11-21, PR #164)

PR #164 merged at [552a9aeb](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/552a9aeb46097d703300475ff21c87ecbffa282c). The Kubernetes conformance evidence parser now validates archived `serverversion.json` and `gitVersion` before comparison, returning stable blocked reasons for malformed evidence. Post-merge automated checks passed; real-VM/PITR remain skipped because no authorized disposable lab is configured. Test17 is unchanged and `productionReady=false` remains the honest status. The next evidence-bearing step is a new immutable candidate from this package-bearing main commit, followed by an expressly authorized disposable Ubuntu/k0s run.

## Code handoff — PR #166 (2026-11-21)

PR [#166](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/166) merged at [e88b667](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e88b6679829be356710cc88a35e090093054ec8b). The Kubernetes evidence verifier now fails closed for malformed top-level and nested SBOM, vulnerability-scan and provenance documents, with regression tests and green post-merge checks.

The next evidence step is a new immutable candidate built from `e88b667`. The existing `v0.2.0-dev.4-test.17` candidate remains unchanged and unqualified. Live Ubuntu/k0s, recovery, HA, load/soak, supply-chain signing/provenance and independent-review gates remain open until reproduced on authorized disposable infrastructure.

## Code handoff — PR #168 (2026-11-21)

PR [#168](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/168) merged at [7b1408a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7b1408a38f830405af52da47143cffa6058068c9). The Kubernetes evidence verifier now fails closed when the trust-policy `keys` inventory is null, empty or not a list, with regression coverage for the stable `TRUST_KEYS_REQUIRED` result.

The next evidence step is a new immutable candidate built from `7b1408a`. The existing `v0.2.0-dev.4-test.17` candidate remains unchanged and unqualified. Live Ubuntu/k0s, recovery, HA, load/soak, signed supply-chain provenance and independent-review gates remain open until reproduced on authorized disposable infrastructure.

## Code handoff — PR #170 (2026-11-21)

PR [#170](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/170) merged at [289c0f2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/289c0f2c37e4ce011e2c1c4827a2646915c3b340). The Kubernetes evidence verifier now fails closed when signed environment identities are not non-empty strings, with regression coverage for `EVIDENCE_IDENTITIES_INVALID`.

The next evidence step is a new immutable candidate built from `289c0f2`. The existing `v0.2.0-dev.4-test.17` candidate remains unchanged and unqualified. Live Ubuntu/k0s, recovery, HA, load/soak, signed supply-chain provenance and independent-review gates remain open until reproduced on authorized disposable infrastructure.


## Code handoff — PR #172 (2026-11-21)

[PR #172](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/172) merged as [77bdc1d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/77bdc1d1af128f5c98fefec3f6720d74df01b3d7). The Kubernetes evidence verifier now fails closed when trust-policy key roles or organization metadata are not non-empty strings, preserving the stable `TRUST_KEY_INVALID` reason. Two regression tests cover malformed roles and organization values before gate authorization and trust-separation checks.

Exact post-merge checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520639), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520655), [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959520708) and [private alpha audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44959717872). This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.


## Code handoff — PR #174 (2026-11-22)

[PR #174](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/174) merged as [0245997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0245997861b9eb663f261cf0d7bcc5623c4627e1). The Kubernetes supply-chain evidence verifier now rejects non-object entries in CycloneDX SBOM component arrays with stable `SBOM_COMPONENT_INVALID` handling and regression coverage.

Exact post-merge checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222806), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222823), [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964222792) and [private alpha audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44964385448). This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.


## Code handoff — PR #176 (2026-11-22)

[PR #176](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/176) merged as [33d8780](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/33d87805b952fcfff1b98ff43e18a60cb041db32). The Kubernetes Trivy-v2 evidence verifier now fails closed for empty or whitespace-only result targets with stable `VULNERABILITY_RESULT_INVALID` handling and regression coverage. Nullable `Vulnerabilities` fields remain supported.

Exact post-merge checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159822), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159864), [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969159804) and [private alpha audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44969356902). This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.

## Code handoff — PR #179 (2026-11-22)

[PR #179](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/179) merged as [6b44496](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6b44496ed69a0feb25e11e2ba0ea358802dc8945). The Kubernetes Trivy-v2 evidence verifier now accepts only a list or explicit null for each `Vulnerabilities` inventory; boolean, numeric and other scalar values fail closed with stable `VULNERABILITY_RESULT_INVALID` handling. Regression coverage protects the boolean case while preserving nullable Trivy output.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221312), [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221342) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44973221313); real-VM and real-PITR remained skipped. This is a code-quality/security-boundary handoff only: the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed.



## Code handoff — PR #181 (2026-11-22)

[PR #181](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/181) merged at [f38d33c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f38d33c77394d321ec8229033dda5e48299d16cf). The Kubernetes CycloneDX evidence verifier now requires every component entry to contain a non-empty string `name`; empty or malformed entries fail closed with stable `SBOM_COMPONENT_INVALID` handling. A regression test protects the empty-object path.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393959), [Native runtime/package, including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393878) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44982393890). Real-VM and real-PITR jobs were skipped because no authorized disposable lab is configured.

This is a code-quality/security-boundary handoff only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false`, the decision remains `no-go`, and no live qualification gate was closed. A new immutable candidate is required before any live evidence can cover this merge.

## Code handoff — PR #183 (2026-11-22)

[PR #183](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/183) merged as [8c0bc4a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8c0bc4aa21575891eb782ad6943bfe42c24cb4d6). The Kubernetes Trivy-v2 evidence verifier now requires each LOW/MEDIUM finding to carry a non-empty string `VulnerabilityID`; malformed findings fail closed with stable `VULNERABILITY_FINDING_INVALID` handling. A regression test protects a nameless LOW finding.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729213), [Native runtime/package, including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729235) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44986729267). Real-VM and real-PITR jobs were skipped because no authorized disposable lab is configured.

This is a code-quality/security-boundary handoff only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false`, the decision remains `no-go`, and no live qualification gate was closed. A new immutable candidate is required before live evidence can cover this merge.

## Code handoff — PR #185 (2026-11-22)

[PR #185](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/185) merged as [3cfe2e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/3cfe2e9f25b68cce70a8e9684d8dd4dd957c8fa8). The Kubernetes release-candidate verifier now requires `sourceRepository` to be a canonical public GitHub repository URL, with an optional `.git` suffix; truncated identities fail closed with stable `SOURCE_REPOSITORY_INVALID` handling. A regression test protects the malformed URL path.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036663), [Native runtime/package, including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036674) and [source/privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44991036662). Real-VM and real-PITR jobs were skipped because no authorized disposable lab is configured.

This is a code-quality/security-boundary handoff only. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false`, the decision remains `no-go`, and no live qualification gate was closed. A new immutable candidate is required before live evidence can cover this merge.

## Code handoff — PR #187 (2026-11-22)

[PR #187](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/187) merged at [1954916](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/19549167b5a18c1e741d1603aaa990a67e5bbb11). The Kubernetes SLSA-provenance parser now validates every `resolvedDependencies` material: URI must be a non-empty string, the digest object must be non-empty, and every digest value must be a non-empty string. Malformed materials fail closed with `PROVENANCE_DEPENDENCIES_INVALID`; a regression test covers empty URI/digest data.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447134) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/44995447123). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a fail-closed evidence-shape hardening only. It does not establish signed provenance, vulnerability clearance or production qualification. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #189 (2026-11-22)

[PR #189](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/189) merged at [93b0cb3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/93b0cb3672cd6889114e2e6f7b5e358057979fdf). The Kubernetes evidence verifier now rejects whitespace-only `builderId` values with stable `BUILD_IDENTITY_REQUIRED` handling; a regression test protects the fail-closed identity boundary.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512976), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512956) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45000512896). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow evidence-shape hardening only. It does not establish provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #191 (2026-11-22)

[PR #191](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/191) merged at [94b5110](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/94b51103edeaf16e1e381e5acac4232bf2ac58cc). The Kubernetes SLSA-provenance parser now rejects empty or whitespace-only digest keys in `resolvedDependencies` entries with stable `PROVENANCE_DEPENDENCIES_INVALID` handling; a regression test covers the malformed digest-key shape.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517185), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517149) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45004517249). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow evidence-shape hardening only. It does not establish signed provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #193 (2026-11-22)

[PR #193](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/193) merged at [e660826](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e66082608f67f4f51d996f86afc1ce94652b455d). The Kubernetes evidence verifier now rejects candidate `builderId` values with leading or trailing whitespace using the stable `BUILD_IDENTITY_REQUIRED` contract; a regression test covers the non-canonical identity shape.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520825), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520832) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45009520854). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow evidence-identity hardening only. It does not establish signed provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #195 (2026-11-22)

[PR #195](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/195) merged at [c587354](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c58735426626ee71dc9755fc3a38a6c7edb6c740). The Kubernetes evidence verifier now requires trust-policy `organization` identifiers to be non-empty and canonically free of leading or trailing whitespace; malformed identities fail closed with `TRUST_KEY_INVALID`. A regression test covers the boundary.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532273), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532243) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45014532236). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow trust-identity hardening only. It does not establish signed provenance, live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.


## Code handoff — PR #197 (2026-11-22)

[PR #197](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/197) merged at [71f1dfd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/71f1dfddc2be51ad6a1c54371cac4339c9910167). The production-tracker validator now requires non-empty string lists for `nextAction.blockers`, `nextAction.successCriteria` and every workstream's `requiredGateFamilies`; the previous empty-list `all([])` acceptance is closed with regression tests.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865245), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865193) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45019865239). Real-VM and real-PITR were skipped because no authorized disposable lab is configured.

This is a narrow release-tracker validation hardening only. It does not establish live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Code handoff — PR #199 (2026-11-22)

[PR #199](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/199) merged at [f532b26](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f532b264a9f8bcc20ce26bfe2da6e4ab4debcc9d). The production-tracker validator now rejects empty or whitespace-only decision evidence lists, rollback contracts, next-action evidence strings and gate-family strings. Blocked workstreams also reject scalar, object or blank-entry blocker fields with stable `TRACKER_BLOCKERS_INVALID` handling; regression tests cover the malformed shapes.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092826), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092830) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45025092833). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is a narrow release-tracker validation hardening only. It does not establish live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Code handoff — PR #201 (2026-11-22)

[PR #201](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/201) merged at [a768d0e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a768d0e304bc7c28ca8f3da7732a179e504001e6). The production-tracker validator now requires non-empty `nextAction.summary` and `nextAction.nextStep` strings, with regression coverage for missing actionable text. This closes a fail-open shape where a blocked release handoff could omit the operator-facing next step.

Exact PR checks passed: [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736383), [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736359) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45029736350). Real-VM and real-PITR remain skipped because no authorized disposable lab is configured.

This is a narrow release-tracker validation hardening only. It does not establish live qualification or production readiness. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains `no-go`. Authorized disposable Ubuntu/k0s installation, upgrade/rollback, backup/restore, HA/partition, load/soak, signed provenance and independent review remain open.

## Code handoff — PR #209 (2026-11-22)

[PR #209](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/209) merged at [fe052af](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fe052af52ab80509f325b9ebee8338649f49ecdd). The Native API mTLS identity boundary now uses the injected UTC clock for certificate validity, with regression coverage for an out-of-window certificate. Exact PR checks passed: [Native runtime/package including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904516), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904485) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45042904486); real-VM and real-PITR remain skipped. This is a code-quality/security-boundary handoff only; the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed. The next evidence step is a new immutable candidate from `fe052af52ab80509f325b9ebee8338649f49ecdd`, followed by the scoped Ubuntu single-host run and remaining backup/restore, upgrade/rollback, bounded soak and signing gates.


## Code handoff — PR #211 (2026-11-22)

[PR #211](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/211) merged as [0a785a8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0a785a85435c6796a34cadd24d66e7c1256f553c). The ingress Gateway now evaluates edge TLS leaf validity through its injected clock, with regression coverage for an out-of-window certificate. Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437255), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437247) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45046437285); real-VM and real-PITR were skipped. This is a code-quality/security-boundary handoff only; the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed. The next evidence step is a new immutable candidate from `0a785a85435c6796a34cadd24d66e7c1256f553c`, followed by the scoped Ubuntu single-host run and remaining backup/restore, upgrade/rollback, bounded soak and signing gates.


## Code handoff — PR #213 (2026-11-22)

[PR #213](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/213) merged as [ea83bb6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea83bb618edd82586a269930f388a66e04ade566). The Native agent now restores the allocation ID when an engine returns a zero report on failure, with regression coverage for the strict heartbeat identity contract. Exact PR checks passed: [Native test and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874344), [contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874104) and [publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45051874099); real-VM and real-PITR were skipped. This is a code-quality/reliability handoff only; the immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, `productionReady=false`, and no live qualification gate was closed. The next evidence step is a new immutable candidate from `ea83bb618edd82586a269930f388a66e04ade566`, followed by the scoped Ubuntu single-host run and remaining backup/restore, upgrade/rollback, bounded soak and signing gates.

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


## Native single-host release handoff — PR #301 (2026-11-24)

[PR #301](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/301) merged as [88daa16](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/88daa16106e73724a6c7b5ad51436aa123b932c). The Native `volume backup` command now performs a fail-closed output preflight before key creation, preventing orphan encryption keys when an operator reuses an existing or symlinked archive path. Regression coverage is in `internal/cli/volume_archive_test.go`.

The PR's Native/real-etcd, Kubernetes contract and Source/Privacy/publication checks passed; real-VM and real-PITR remained skipped. This is a reliability/security hardening handoff, not a production-gate closure. The next release step is to rebuild one immutable candidate from commit `88daa16106e73724a6c7b5ad51436aa123b932c6`, run the existing Ubuntu 24.04 real-vm job and collect same-candidate installation, backup/restore, upgrade/rollback, bounded load/soak and signed-provenance evidence. HA, multi-host and Kubernetes-production remain deferred.


## Native single-host release handoff — PR #303 (2026-11-24)

[PR #303](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/303) merged as [76f6656](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/76f6656ce4c21c67f203f50ad467417fa65835a1). The Native `schema migrate` command now performs a fail-closed destination preflight before key creation and migration, preventing orphan key material and non-persistable migration work when an operator reuses an existing or symlinked backup path. Regression coverage is in `internal/cli/schema_test.go`.

The PR's Native/real-etcd, Kubernetes contract and Source/Privacy/publication checks passed; real-VM and real-PITR remained skipped. This is a reliability/security hardening handoff, not a production-gate closure. The next release step is to rebuild one immutable candidate from commit `76f6656ce4c21c67f203f50ad467417fa65835a1`, run the existing Ubuntu 24.04 real-vm job and collect same-candidate installation, backup/restore, upgrade/rollback, bounded load/soak and signed-provenance evidence. HA, multi-host and Kubernetes-production remain deferred.


## Latest code handoff — PR #310 (2026-11-24)

[PR #310](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/310) merged as [6892578](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/689257882c58acb511d9e4be106e20ea88f18fe8). The privileged secret CLI now rejects extra arguments: `secret list` requires no operands, while `secret put` rejects positional leftovers before reading the private input or loading cluster configuration. Regression coverage is in [internal/cli/cli_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/689257882c58acb511d9e4be106e20ea88f18fe8/internal/cli/cli_test.go).

Exact PR checks passed: [Native test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138695864774), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138695864389), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464555873/job/138695855480) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556095/job/138695854545). [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138697069149) and [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45464556202/job/138697277903) were skipped; no live Single-Host production gate closed.

The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. A new immutable candidate must be built from `689257882c58acb511d9e4be106e20ea88f18fe8` before this hardening can be covered by live installation, backup/restore, upgrade/rollback or load/soak evidence. `productionReady=false`; the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.


## Native single-host release handoff — PR #313 (2026-11-24)

PR [#313](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/313) merged as [02307049](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/02307049c72fc07b0d96926a81a7ce54a6963559). The privileged `backup` command now rejects unexpected positional arguments before key loading, state access or output mutation; regression coverage was added. The corrected PR checks and post-merge Main checks passed for Native, real-etcd, contracts and Source/Privacy. Real-VM and real-PITR remained skipped, so no Single-Host production gate closed. Build the next immutable candidate from `02307049c72fc07b0d96926a81a7ce54a6963559` and keep the decision no-go until same-candidate installation, backup/restore, upgrade/rollback, bounded soak, signing and maintainer approval are evidenced.


## Native CLI release handoff — PR #315 (2026-11-24)

[PR #315](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/315) merged as [22aacc9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/22aacc9082832c5debdfd6d4753af5e627a7f8c8). The privileged Native `control` and `agent` daemon entry points now reject unexpected positional arguments immediately after flag parsing, before configuration, lock, mTLS, etcd or Docker access. Regression coverage is in [internal/cli/cli_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/22aacc9082832c5debdfd6d4753af5e627a7f8c8/internal/cli/cli_test.go).

PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485407944/job/138769338557), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485408137/job/138769338289) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485407967/job/138769338136). Post-merge Main checks also passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485924593/job/138771150701), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485924592/job/138771153651) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45485924586/job/138771150000). Real-vm and real-PITR were skipped; no Single-Host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. Build the next immutable candidate from `22aacc9082832c5debdfd6d4753af5e627a7f8c8`; `productionReady=false` and the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Native CLI argument hardening — PR #318 (2026-11-24)

[PR #318](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/318) merged as [dd94bb4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/dd94bb41f4264b0b463d522d282050c646b52e5c). Native `wait`, `dashboard`, `status`, `tunnel`, `demo` and `node bundle` now reject unexpected positional arguments immediately after flag parsing, before configuration, metadata, network or workload access. Negative regression coverage is in [internal/cli/cli_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/dd94bb41f4264b0b463d522d282050c646b52e5c/internal/cli/cli_test.go).

PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495534346/job/138804884945), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495534341/job/138804884632) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495534555/job/138804889721). Post-merge Main checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495995923/job/138806524918), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495995874/job/138806524314) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45495995860/job/138806524987). Real-vm and real-PITR remained skipped; no Single-Host production gate closed.

The mutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. Build the next immutable candidate from `dd94bb41f4264b0b463d522d282050c646b52e5c`; `productionReady=false` and the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

## Latest Native hardening handoff — PR #405 (2026-11-26)

PR [#405](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/405) merged as [6ce5423e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6ce5423ef2a848e64a69387610f99d20ba4a607e). Worker setup readiness now requires an authenticated `/v1/health` response with the expected cluster identity, `ready` status and state schema; a local positive-revision journal is no longer sufficient. Regression tests cover wrong cluster, status and schema.

Exact PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45853993836), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45853993755) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45853993732). `real-vm` and `real-PITR` were skipped, so no Single-Host production gate was closed.

Next release work remains bound to a new immutable candidate built from the current Main handoff. The old `v0.2.0-dev.4-test.17` candidate is not immutable and its assets are unsigned. Backup/restore, upgrade/rollback, load/soak, signed provenance, maintainer feedback and Go/No-Go remain open. `productionReady=false`; the production decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.


## Latest runtime hardening handoff — PR #408 (2026-11-26)

PR [#408](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/408) merged as [cc0c5b5e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cc0c5b5e835712b819ec227c5d6ca4d7094467ee). Durable Native agent journal records are validated fail-closed before startup and before persistence, covering allocation identity, node ownership, desired/phase values, port bounds, timestamps, resource specification and map-key consistency.

Exact PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45856235848), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45856235446) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45856235860). real-vm and real-PITR were skipped; no Single-Host production gate closed.

The old v0.2.0-dev.4-test.17 candidate remains non-immutable and unsigned, so a new immutable candidate is required from [cc0c5b5e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cc0c5b5e835712b819ec227c5d6ca4d7094467ee) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. productionReady remains false and Go/No-Go remains no-go. HA, multi-host and Kubernetes-production remain deferred.


## Latest persistence hardening handoff — PR #410 (2026-11-26)

PR [#410](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/410) merged as [247dd11a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/247dd11a32cfbedd7fb4f7f056b49f0f672e2144). Native etcd state reads now use the strict JSON contract and reject unknown persisted fields before inventory validation or reconciliation. The first fixture attempt failed compile because the JSON string was not escaped; corrected commit 998bef39 passed.

Corrected checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45863201801), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45863201851) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45863201751). real-vm and real-PITR were skipped; no Single-Host production gate closed.

The old v0.2.0-dev.4-test.17 candidate remains non-immutable and unsigned, so a new immutable candidate is required from [247dd11a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/247dd11a32cfbedd7fb4f7f056b49f0f672e2144) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. productionReady remains false and Go/No-Go remains no-go. HA, multi-host and Kubernetes-production remain deferred.



## Native single-host release handoff — PR #412 (2026-11-26)

PR [#412](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/412) merged as [`1f722497`](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1f722497196366881136689d6dad30659abb22e8). Docker cluster identities are now validated before Docker API negotiation and before the name prefix slices the identifier; malformed values fail closed with `CLUSTER_ID_INVALID`, with a regression test proving no Docker adapter call occurs.

The exact PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45871614939), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45871614507) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45871614434). `real-vm` and `real-PITR` were skipped, so this handoff closes no live Single-Host production gate.

The next release step is to rebuild one immutable candidate from `1f722497196366881136689d6dad30659abb22e8` and run the authorized Ubuntu 24.04 real-vm path, then collect same-candidate installation, backup/restore, upgrade/rollback, bounded load/soak and signed-provenance evidence. HA, multi-host and Kubernetes-production remain deferred.


## Native single-host release handoff — PR #414 (2026-11-26)

PR [#414](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/414) merged as [`940682d8`](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/940682d868cce16e77bc4f6549c2bd14e6e25b3c). The selected node and an optional workload node selector must now agree in both the agent assignment boundary and persisted inventory validation; otherwise reconciliation fails closed. Regression coverage was added for each boundary.

The exact PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45879376876), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45879376935) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45879377042). `real-vm` and `real-PITR` were skipped, so this handoff closes no live Single-Host production gate.

The next release step is to rebuild one immutable candidate from `940682d868cce16e77bc4f6549c2bd14e6e25b3c` and run the authorized Ubuntu 24.04 real-vm path, then collect same-candidate installation, backup/restore, upgrade/rollback, bounded load/soak and signed-provenance evidence. HA, multi-host and Kubernetes-production remain deferred.


## Native single-host release handoff — PR #429 (2026-11-27)

[PR #429](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/429) merged as [6cb1436f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6cb1436fc5bf458defeb8260bc75901ae3e96599). The Native werft setup --bundle path now writes the private worker join bundle before control-plane node registration, preventing orphaned node records when local persistence fails. Regression tests verify ordering and fail-closed behavior.

Corrected checks passed: [Native/runtime including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45925849361), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45925849407) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45925849350). The first native attempt failed only because its write-failure fixture allowed parent creation; that fixture was corrected and the successful run is the evidence of record. Real-VM and real-PITR remain skipped; this hardening closes no live production gate.

The next step is to build a fresh immutable candidate from `6cb1436fc5bf458defeb8260bc75901ae3e96599`, run the authorized Ubuntu 24.04 real-vm path and collect same-candidate installation, backup/restore, upgrade/rollback, bounded load/soak and signed-provenance evidence. HA, multi-host and Kubernetes-production remain deferred.

## Native single-host release handoff — PR #431 (2026-11-27)

[PR #431](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/431) merged as [e42ee2a1](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e42ee2a1f9aff03abc6a7b23d130e4d74554f22c). The Native join-bundle path now creates the private output exclusively and refuses existing destinations or symlinks before node registration. This closes a concrete credential-overwrite/idempotency risk while keeping registration fail-closed.

Exact PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45931400751), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45931400814) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45931400747). Real-vm and real-PITR were skipped, so no live Single-Host qualification gate closed. The next release step is to build a fresh immutable candidate from `e42ee2a1f9aff03abc6a7b23d130e4d74554f22c` and run the authorized Ubuntu 24.04 real-vm path with `run_real_vm_e2e=true`; backup/restore, upgrade/rollback, bounded soak and signed provenance remain open. HA, multi-host and Kubernetes-production remain deferred.

## Native release-pipeline handoff — PR #433 (2026-11-27)

[PR #433](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/433) merged as [b97963a7](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b97963a7a43349ef3c66e1f26a62af858129a3de). The post-APT Native package smoke step now executes one unambiguous `werft --help` command instead of a duplicated shell-line invocation. This removes a CI false-positive risk and keeps package verification deterministic.

Exact PR checks passed: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45937156110), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45937156087) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45937156140). Real-vm and real-PITR were skipped, so no live Single-Host qualification gate closed. The next release step is still to build a fresh immutable candidate from `b97963a7a43349ef3c66e1f26a62af858129a3de` and run the authorized Ubuntu 24.04 real-vm path with `run_real_vm_e2e=true`; backup/restore, upgrade/rollback, bounded soak and signed provenance remain open. HA, multi-host and Kubernetes-production remain deferred.
## Native supply-chain release handoff — PR #435 (2026-11-27)

[PR #435](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/435) merged as [06f9850b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/06f9850bbd97f74682b9d8d84af6d271dbc4e9d7). The Native SPDX SBOM now binds the root package entry to the exact Debian package SHA-256, while preserving the explicit statement that OS vulnerability, signing, provenance and production gates are separate. Regression coverage exercises checksum generation and metadata binding.

Exact PR checks passed: [Native/runtime including real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45942567592), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45942567598) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45942567619). Real-vm and real-PITR were skipped, so no live Single-Host qualification gate closed. The next step is to build one fresh immutable candidate from `06f9850bbd97f74682b9d8d84af6d271dbc4e9d7` and run the authorized Ubuntu 24.04 real-vm path with `run_real_vm_e2e=true`; backup/restore, upgrade/rollback, bounded load/soak and signed provenance remain open. HA, multi-host and Kubernetes-production remain deferred.

