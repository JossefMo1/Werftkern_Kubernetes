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

- Code: [PR #365](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/365), merged commit [fc16c997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fc16c9978741fc9d792da781d1b697b2612af653).
- Runtime/security change: reusable secret staging now binds a manifest to the spec hash and a digest for every secret file; reuse rechecks regular-file type, mode, bounded size and bytes. Content drift fails closed with SECRET_MATERIAL_CONTENT_MISMATCH.
- Regression coverage: TestSecretManifestReuseRejectsContentDrift mutates staged secret bytes and verifies fail-closed reuse.
- PR checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45634285219), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45634285314) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45634285257) — all successful; real-vm/PITR skipped.
- No Single-Host production gate closed. productionReady=false, decision no-go; test.17 remains stale, mutable and unsigned.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from [fc16c997](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fc16c9978741fc9d792da781d1b697b2612af653), then run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The current connector cannot create tags or dispatch workflow_dispatch; that blocker is recorded and not repeated.

# Restore receipt tree-integrity handoff — PR #362 (2026-11-25)

- Code: [PR #362](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/362), merged commit [97d2fd0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/97d2fd03d551df707aeff8895a79e8a179382458).
- Recovery/runtime change: Native volume restore receipts now include a deterministic digest of the extracted data tree (paths, types, permissions, sizes and regular-file bytes). Every retry verifies the receipt before sending the completion acknowledgement; drift, unsafe entries or legacy receipts without a tree digest fail closed and never replace the existing tree.
- Regression coverage: the privileged CLI integration test mutates the extracted tree before a lost-ACK retry and after completion, verifies the integrity error, confirms the pending state is not acknowledged, then confirms a clean retry succeeds.
- PR checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45629127583), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45629127066) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45629128409) — all successful; real-vm/PITR skipped.
- Post-merge Main checks: [Native/runtime + real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45629751096), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45629750862) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45629750919) — all successful; real-vm/PITR skipped.
- No Single-Host production gate closed. `productionReady=false`, decision `no-go`; the published v0.2.0-dev.4-test.17 remains stale, mutable and unsigned.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from [97d2fd0](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/97d2fd03d551df707aeff8895a79e8a179382458), then run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The current connector cannot create tags or dispatch workflow_dispatch; that blocker is recorded and not repeated.

# Failover replay-safety handoff — PR #356 (2026-11-25)

- Code: [PR #356](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/356), merged commit [bc17c84](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bc17c840e8acf22c91f47f354b338f97a8a5a050).
- Runtime/state change: failover retries are allowlisted to GET/HEAD, sequence-safe heartbeat/etcd-range requests, and receipt-backed workload/secret mutations; keyed maintenance, registration, restore and unknown mutations are not replayed after an ambiguous acknowledgement.
- Regression coverage: keyed maintenance is not replayed; keyed secret mutation retries remain supported.
- PR checks: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45598966389), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45598966331), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45598966221) — all successful; real-etcd passed, real-vm/PITR skipped.
- Main checks: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45599427641), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45599428071), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45599427813) — all successful; real-etcd passed, real-vm/PITR skipped.
- No Single-Host production gate closed. productionReady=false, decision no-go; the published v0.2.0-dev.4-test.17 remains stale, mutable and unsigned.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: build one immutable candidate from [bc17c84](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bc17c840e8acf22c91f47f354b338f97a8a5a050), then run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The current connector cannot create tags or dispatch workflow_dispatch; that blocker is recorded and not repeated.

# Allocation spec-integrity handoff — PR #354 (2026-11-25)

- Code: [PR #354](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/354), merged commit [39183a8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/39183a82fb1062674799a3483f5ae30a9e4b2e92).
- Runtime/state change: allocation specs must match the referenced workload's current generation or a retained historical revision; divergent state is rejected before reconciliation and secret/volume authorization.
- PR checks: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45590345023), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45590345226), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45590345089) — all successful; real-etcd passed, real-vm/PITR skipped.
- Main checks: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45590771288), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45590770738), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45590770191) — all successful; real-etcd passed, real-vm/PITR skipped.
- No Single-Host production gate closed. productionReady=false, decision no-go; the published v0.2.0-dev.4-test.17 remains stale, mutable and unsigned.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: create one immutable candidate from [39183a8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/39183a82fb1062674799a3483f5ae30a9e4b2e92), then run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The current connector cannot create tags or dispatch workflow_dispatch; that blocker is recorded and not retried.

---

# Allocation cross-index handoff — PR #352 (2026-11-25)

- Code: [PR #352](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/352), merged commit [408aee6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/408aee69fed10b3974d6022a2e3719a9cd495981).
- Runtime/state change: persisted allocation records are rejected before reconciliation and secret authorization when the allocation name does not match the workload or its generation is ahead of the workload generation; valid current-generation records remain accepted.
- PR checks: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45585269729), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45585269745), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45585269765) — all successful; real-etcd passed, real-vm/PITR skipped.
- Main checks: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45585724784), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45585724789), [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45585724912) — all successful; real-etcd passed, real-vm/PITR skipped.
- No Single-Host production gate closed. `productionReady=false`, decision `no-go`; the published `v0.2.0-dev.4-test.17` remains stale, mutable and unsigned.
- HA/multi-host/quorum and Kubernetes-Production remain deferred outside the first Native scope.
- Next handoff: create one immutable candidate from commit [408aee6](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/408aee69fed10b3974d6022a2e3719a9cd495981), then run candidate-bound Ubuntu installation, backup/restore, upgrade/rollback, bounded soak and signing/provenance checks. The current connector cannot create tags or dispatch workflow_dispatch; that blocker is recorded and not retried.

---

# Idempotency receipt state handoff — PR #349 (2026-11-25)

[PR #349](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/349) merged as [5d9813c02d243854d9fa33127b7236274a01257c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5d9813c02d243854d9fa33127b7236274a01257c). Persisted idempotency receipts are now validated fail-closed before reconciliation or backup: request ID, SHA-256 hash, workload or validated secret owner, positive generation, and timestamp are required. Secret mutation receipts retain the explicit `secret:<name>/<version>` owner namespace with name/version validation. Negative coverage covers malformed hash, owner, generation and timestamp plus valid secret-owner compatibility.

PR checks passed: Native [45580938962](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45580938962) (test and real-etcd success; real-vm/PITR skipped), Kubernetes [45580938903](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45580938903), Source/Privacy [45580938754](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45580938754). Post-merge Main checks passed: Native [45581360321](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45581360321) (test and real-etcd success; real-vm/PITR skipped), Kubernetes [45581360550](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45581360550), and Source/Privacy [45581360619](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45581360619).

This closes no Single-Host production gate. The current published `v0.2.0-dev.4-test.17` artifact remains stale, mutable and unsigned; `productionReady=false` and the decision remains no-go. HA, multi-host and Kubernetes-production remain deferred outside the first Native single-host scope.

Next handoff: build an immutable candidate from [5d9813c02d243854d9fa33127b7236274a01257c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5d9813c02d243854d9fa33127b7236274a01257c) and run the exact Ubuntu 24.04 path, then separately complete same-candidate backup/restore, upgrade/rollback, bounded load/soak, signing/provenance, user feedback and final maintainer Go/No-Go. The connector cannot create the authorized tag or dispatch `workflow_dispatch`; this external blocker is documented and not repeated.

# Dashboard future-heartbeat handoff — PR #347 (2026-11-25)

[PR #347](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/347) merged as [c8d06d30dc0b8bcf40f7b93892efe3984afeea67](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c8d06d30dc0b8bcf40f7b93892efe3984afeea67). The Dashboard now rejects invalid or more-than-5-second future node heartbeats, matching the Native controller's scheduling tolerance; earlier UI logic treated a future timestamp as healthy because its age was negative. The browser fixture covers a 6-second future heartbeat and recovery to a current heartbeat. This fixture uses in-memory synthetic state and is not live-cluster evidence.

PR checks passed: Native [45572381574](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45572381574) (test and real-etcd; real-vm/PITR skipped), Kubernetes contracts [45572381543](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45572381543), and Source/Privacy [45572381529](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45572381529). Post-merge Main checks passed: Native [45572767523](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45572767523) (test and real-etcd; real-vm/PITR skipped), Kubernetes [45572767551](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45572767551), and Source/Privacy [45572767538](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45572767538).

No exact-candidate Ubuntu installation, backup/restore, upgrade/rollback, bounded-soak or signed-artifact gate closed. The published v0.2.0-dev.4-test.17 artifact remains stale, mutable and unsigned; productionReady=false and the decision remains no-go. HA, multi-host and Kubernetes-production remain deferred outside the first Native single-host scope.

# Native persisted-state index validation handoff — PR #345 (2026-11-25)

[PR #345](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/345) merged as [a2615800318d582997746f77fc7c4646bb98854c](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/a2615800318d582997746f77fc7c4646bb98854c). The Native state validator now rejects malformed gateway, workload, node, allocation and receipt map indexes and rejects event logs above the bounded 160-entry contract before reconciliation or backup. Regression coverage is in [internal/model/model_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/a2615800318d582997746f77fc7c4646bb98854c/internal/model/model_test.go) (TestStateRejectsIndexMismatches).

PR checks passed: Native [45564320179](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45564320179) (test and real-etcd success; real-vm/PITR skipped), Kubernetes contracts [45564320159](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45564320159), and Source/Privacy [45564320314](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45564320314). Post-merge Main checks passed: Native [45564642192](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45564642192) (test and real-etcd; real-vm/PITR skipped), Kubernetes [45564642195](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45564642195), and Source/Privacy [45564642260](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45564642260).

No Ubuntu installation, backup/restore, upgrade/rollback, bounded-soak or signed-artifact gate closed. The published v0.2.0-dev.4-test.17 artifact remains stale, mutable and unsigned; productionReady=false and the decision remains no-go. HA, multi-host and Kubernetes-production remain deferred outside the first Native single-host scope.

# Native volume-offline fail-closed handoff — PR #343 (2026-11-25)

[PR #343](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/343) merged as [7ca9f5a603a8b69a99b850b74bbe2dd5d2d9ff4f](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/7ca9f5a603a8b69a99b850b74bbe2dd5d2d9ff4f). Native volume-offline maintenance now rejects non-absolute or unresolved Docker mount sources instead of continuing with a lexical path. This makes the guard fail closed when canonicalization is unavailable, preventing a foreign or stale mount from bypassing overlap detection. Regression fixtures now create real temporary paths and cover an unresolved source.

The first PR run [45556326419](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556326419) failed because the old synthetic sibling fixture did not exist on the runner; the fixture was corrected before merge. Final PR checks passed: Native [45556658841](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556658841) (test and real-etcd), Kubernetes [45556658615](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556658615), and Source/Privacy [45556658688](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556658688).

Post-merge Main checks passed: Native [45556987066](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556987066) (test and real-etcd; real-vm and real-PITR skipped), Kubernetes [45556987133](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556987133), and Source/Privacy [45556987395](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45556987395). No Ubuntu installation, backup/restore, upgrade/rollback or bounded-soak gate closed. The published v0.2.0-dev.4-test.17 artifact remains stale, mutable and unsigned; productionReady=false and the decision remains no-go.

# Native rollback atomicity handoff — PR #341 (2026-11-25)

[PR #341](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/341) merged as [e2f64d1092ee6a8b088f79262408dbb5fbb2199b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/e2f64d1092ee6a8b088f79262408dbb5fbb2199b). The Native model now validates archived rollback secrets and volumes before removing history or changing the active spec. A rejected rollback therefore remains side-effect free for direct callers as well as the etcd transaction path. Regression coverage is in [internal/model/model_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/e2f64d1092ee6a8b088f79262408dbb5fbb2199b/internal/model/model_test.go) (TestRollbackValidationFailureDoesNotMutateHistory).

PR checks passed: Native test and real-etcd ([45549728444](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45549728444), [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45549728444/job/138987748236), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45549728444/job/138987747757)); Kubernetes contracts ([45549728277](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45549728277)); Source/Privacy ([45549728284](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45549728284)). Post-merge Main checks also passed: Native test and real-etcd ([45550035506](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45550035506), [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45550035506/job/138988746875), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45550035506/job/138988747292)); Kubernetes contracts ([45550035510](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45550035510)); Source/Privacy ([45550035546](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45550035546)). The Main real-vm and real-PITR jobs were skipped; no Ubuntu installation or backup/restore gate was closed.

The published v0.2.0-dev.4-test.17 artifact remains stale, mutable and unsigned. Rebuild an immutable candidate from Main e2f64d1092ee6a8b088f79262408dbb5fbb2199b before reusing any live qualification evidence. productionReady=false; the decision remains no-go. HA, multi-host and Kubernetes-production remain deferred outside the first Native single-host scope.

# Native dashboard accessibility handoff — PR #339 (2026-11-25)

[PR #339](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/339) merged as [de52c82d69f796e826e7d754d046e09568e9a2de](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/de52c82d69f796e826e7d754d046e09568e9a2de). The local dashboard now exposes polite live announcements for connection and mutation state, contextual accessible names for workload/node actions, table caption/header scopes, a busy state, focus return after closing/submitting the rollout form, and reduced-motion handling. The browser fixture contract covers these semantics.

PR checks passed: Native test/package and real-etcd ([run 45543659980](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543659980), [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543659980/job/138967971174), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543659980/job/138967970914)); Kubernetes contracts ([45543659774](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543659774)); Source/Privacy ([45543659723](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543659723)). Post-merge Main checks passed: Native ([run 45543977277](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543977277), [test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543977277/job/138968997492), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543977277/job/138968996914)), Kubernetes ([45543978665](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543978665)) and Source/Privacy ([45543977135](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543977135)). Main real-vm and real-PITR were skipped ([real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543977277/job/138969934478), [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45543977277/job/138969935044)); the public-repository alpha publisher skipped release creation ([45544027831](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45544027831)).

Local `node --check`, Python compilation and HTML parser checks passed. The local Chromium fixture was attempted but blocked by `TargetClosedError`; this is not browser or live-cluster evidence. No Single-Host production gate closed. The mutable, unsigned [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) still targets an older commit. The production decision remains no-go.

Next handoff: build a fresh immutable candidate from [de52c82d69f796e826e7d754d046e09568e9a2de](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/de52c82d69f796e826e7d754d046e09568e9a2de), then run the exact-candidate Ubuntu 24.04 path and separately complete backup/restore, upgrade/rollback, bounded load/soak, signing/provenance, RC feedback and Go/No-Go. HA/multi-host and Kubernetes Production remain deferred outside this first scope.

# Post-Merge-Nachweis — Native systemd hardening (2026-11-25)

- PR [#337](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/337) merged as [0c26c3cdae9cbe51086de85b7cae71cbf63c85ff](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/0c26c3cdae9cbe51086de85b7cae71cbf63c85ff); the tracker and status now point to the hardened code handoff [#336](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/336).
- Post-merge Main: Native test/package + real-etcd passed ([run 45541303215](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303215), jobs [138960205766](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303215/job/138960205766) and [138960206134](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303215/job/138960206134)); Kubernetes contracts ([45541303232](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303232)) and Source/Privacy ([45541303259](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303259)) passed.
- Main real-vm ([138961198396](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303215/job/138961198396)) and real-PITR ([138961198875](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541303215/job/138961198875)) were skipped because this was a normal push, not an authorized immutable-candidate qualification.
- The private-alpha publisher ([run 45541619379](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45541619379)) correctly created no release because the repository is public. The existing v0.2.0-dev.4-test.17 release remains mutable/unsigned.
- No production gate is closed by this documentation update; Ubuntu installation, exact-candidate restart/recovery, backup/restore, upgrade/rollback, bounded load/soak, signing/provenance, user feedback and maintainer Go/No-Go remain open. `productionReady=false` / `no-go` remain unchanged.

# Native single-host operations handoff — PR #336 (2026-11-25)

[PR #336](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/336) merged as [293d6c76923830ac64df8b67c6cafcdb02396739](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/293d6c76923830ac64df8b67c6cafcdb02396739).

- All five Native systemd units now require consistent kernel/privilege hardening (ProtectKernel*, ProtectClock, LockPersonality, RestrictSUIDSGID, RestrictRealtime, SystemCallArchitectures=native).
- Package-layout contract coverage was added; the pull-request Native test/package and real-etcd jobs passed ([run 45540442228](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45540442228), jobs [138957372510](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45540442228/job/138957372510) and [138957373145](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45540442228/job/138957373145)). Kubernetes contracts ([45540442256](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45540442256)) and Source/Privacy ([45540442304](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45540442304)) passed.
- Real-vm and real-PITR were skipped because this was a pull-request check, not an authorized immutable-candidate qualification run. productionReady=false and the decision remains no-go.
- This hardening does not close Ubuntu installation, exact-candidate Docker/etcd restart, backup/restore, upgrade/rollback, bounded load/soak, signing/provenance, user feedback or maintainer Go/No-Go gates. The existing v0.2.0-dev.4-test.17 artifact set remains mutable and unsigned.

Next handoff: build the next immutable candidate from Main commit 293d6c76923830ac64df8b67c6cafcdb02396739; the current connector cannot create the authorized tag or dispatch workflow_dispatch, so no live-vm claim is made.

# Native single-host release handoff — PR #334 (2026-11-25)

[PR #334](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/334) merged as [fd439384](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/fd439384a19b8aa0a170864675bc6f9e9ddead30). The experimental `-test.N` release workflow now carries the bounded Native SPDX 2.3 document and its SHA-256 sidecar in the manifest and checksum set, and the German runbook documents both assets. This remains experimental evidence plumbing: it does not close OS vulnerability completeness, signing/provenance, exact-candidate Ubuntu installation, Docker/etcd workload lifecycle, backup/restore, upgrade/rollback, load/soak, user feedback or maintainer Go/No-Go.

Main CI for the preceding candidate-bearing code commit [28d4b139](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/28d4b139514e46fbc787e64acf0552d17fc03b83) passed Native source/package and real-etcd, Kubernetes contracts and Source/Privacy checks; real-vm and real-PITR were skipped. The current mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to an older commit, unsigned and non-immutable; the production decision remains no-go.

The next action is to rebuild an immutable candidate from 28d4b139 and run the available Ubuntu 24.04 real-vm path, then complete same-candidate backup/restore, upgrade/rollback, bounded soak and signing/provenance gates. The current connector cannot dispatch workflow_dispatch or create tags; this external blocker is documented and not repeated. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #332 (2026-11-25)

[PR #332](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/332) merged as [28d4b139](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/28d4b139514e46fbc787e64acf0552d17fc03b83). CI now generates a bounded deterministic SPDX 2.3 document and SHA-256 sidecar for the exact Native package build, covering package metadata, declared Debian runtime dependencies and the Go module graph. This is supply-chain evidence plumbing, not a production-readiness claim: OS vulnerability completeness, signing/provenance, Ubuntu installation, Docker/etcd workload lifecycle on the exact candidate, backup/restore, upgrade/rollback, load/soak, user feedback and maintainer Go/No-Go remain open.

Post-merge Main evidence for [Native runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45537412649), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45537412758) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45537412880) passed. The Native real-etcd job passed; real-vm and real-PITR were skipped. The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) is still not an exact candidate for this commit, unsigned and non-immutable; the production decision remains no-go.

The next step is to build an immutable candidate from 28d4b139514e46fbc787e64acf0552d17fc03b83 and run the available Ubuntu 24.04 real-vm path, then complete same-candidate backup/restore, upgrade/rollback, bounded soak and signing/provenance gates. The current connector cannot dispatch workflow_dispatch or create tags; that is a documented external blocker and is not repeated here. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #330 (2026-11-25)

[PR #330](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/330) merged as [545cf797](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/545cf797b30958d1d60e8cf5177ee13c37566e00). Native Debian packaging now validates `SOURCE_DATE_EPOCH`, derives deterministic build metadata, disables VCS stamping, normalizes staging mtimes and passes the fixed epoch to `dpkg-deb`. CI builds the package twice from the same commit and compares SHA-256 digests, emitting `evidence/reproducible-build.json`.

The post-merge Main evidence is explicit: [Native workflow](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813) ([test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813/job/138922880654), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813/job/138922881005) passed; [real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813/job/138923825870) and [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071813/job/138923826982) skipped), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071723) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45530071869) passed. Local release contract tests (139) plus shell/Python syntax, diff, YAML, tracker and scope checks passed; the local Go compiler is unavailable. No Single-Host production gate closed. The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains unsigned and non-immutable.

The next candidate must be rebuilt from `545cf797b30958d1d60e8cf5177ee13c37566e00` before Ubuntu installation, Docker/etcd lifecycle, backup/restore, upgrade/rollback, load/soak, signing and provenance evidence. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #326 (2026-11-25)

[PR #326](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/326) merged as [204f5de](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/204f5de445c275efab544ebe1e5c21f900ca1e68); the reviewed code commit was [5203d77](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5203d773732c539283dd50eaad377cabf74a0c7d). The local dashboard now bounds non-success responses to API codes, explains common state/auth/conflict/maintenance failures in German, clears stale mutation errors after success, exposes connection/error/update live regions, and uses Werftkern Native Runtime branding.

PR checks passed: [Native runtime](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522406209), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522406209/job/138897304439), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522406150/job/138897304096) and [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522406198/job/138897303829). Post-merge Main checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522810685), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522810685/job/138898646219), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522810663/job/138898646069) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522810623/job/138898645365) passed. The Main real-vm and real-PITR jobs were skipped ([real-vm](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522810685/job/138899740715), [real-PITR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45522810685/job/138899741045)); local Chromium could not start (`TargetClosedError`) and therefore is not live evidence.

No Single-Host production gate closed. The mutable `v0.2.0-dev.4-test.17` candidate remains unsigned and non-immutable; `productionReady` remains `false` and the decision remains no-go. Rebuild the exact candidate from [204f5de](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/204f5de445c275efab544ebe1e5c21f900ca1e68) before any Ubuntu installation, backup/restore, upgrade/rollback, bounded soak or signing claim.

# Native single-host release handoff — PR #324 (2026-11-25)

[PR #324](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/324) merged as [9671c64](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/9671c64edbe67f02ca18a21244abdd0833c55c5b). Native Operations/Platform state writes and operation locks now create parent components without following symlinks; redirected parents fail closed before state creation. Regression coverage is in [tests/ops/test_common.py](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/9671c64edbe67f02ca18a21244abdd0833c55c5b/tests/ops/test_common.py). Local Python Operations tests passed (92 tests).

PR checks passed: [Native test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45513794953/job/138867917441), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45513794953/job/138867917478), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45513794797/job/138867916877) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45513794823/job/138867916474). Post-merge Main checks also passed: [Native test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45514341484/job/138869799701), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45514341484/job/138869799119), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45514341366/job/138869798624) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45514341376/job/138869798675). Real-vm and real-PITR were skipped; no Single-Host production gate closed.

The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. Build the next immutable candidate from [9671c64edbe67f02ca18a21244abdd0833c55c5b](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/9671c64edbe67f02ca18a21244abdd0833c55c5b) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

# Native single-host release handoff — PR #322 (2026-11-24)

[PR #322](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/322) merged as [80c091e](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/80c091e03d1c7687c46a7ca4543f55b34d281bfe). The Native secret/mTLS boundary now validates the complete SecretRoot parent chain after directory creation; operator-provided symlinked parents fail closed, cleanup uses the same validated/default root, and [internal/engine/secrets_test.go](https://github.com/JossefMo1/Werftkern_Kubernetes/blob/80c091e03d1c7687c46a7ca4543f55b34d281bfe/internal/engine/secrets_test.go) covers parent redirection.

PR checks passed: [Native test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45506603126/job/138843311356), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45506603126/job/138843311828), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45506603116/job/138843310531) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45506603184/job/138843310358). Post-merge Main checks also passed: [Native test](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45507116192/job/138845062804), [real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45507116192/job/138845063194), [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45507116073/job/138845062009) and [Source/Privacy publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45507115923/job/138845061874). Real-vm and real-PITR were skipped; no Single-Host production gate closed.

The mutable [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, with `immutable=false` and unsigned assets. Build the next immutable candidate from [80c091e03d1c7687c46a7ca4543f55b34d281bfe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/80c091e03d1c7687c46a7ca4543f55b34d281bfe) before live installation, backup/restore, upgrade/rollback or load/soak evidence can cover this hardening. `productionReady=false`; the decision remains `no-go`. HA, multi-host and Kubernetes-production remain deferred.

# Latest code handoff — PR #308 (2026-11-24)

PR [#308](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/308) merged as [c0e7b30](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/c0e7b30320f46562177b837f1a0afaf01bf7de17). Native volume backup now rejects missing, non-directory and symlinked archive parents before creating a separate backup key; the existing output-exists and race-safe safefile.CreateExclusive checks remain in place. Regression coverage is in internal/cli/volume_archive_test.go.

PR checks passed: [Native runtime/package and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45454133889) — compile/race/static/package checks and real-etcd **success**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45454133869) — **success**; [Source/Privacy/publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45454133920) — **success**. Real-vm and real-PITR were explicitly skipped. No Single-Host production gate closed.

The mutable, unsigned v0.2.0-dev.4-test.17 candidate remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296 and cannot evidence c0e7b30320f46562177b837f1a0afaf01bf7de17. productionReady=false and the decision remains no-go.

Next handoff: build an immutable candidate from c0e7b30320f46562177b837f1a0afaf01bf7de17, run the existing Ubuntu 24.04 path against that exact candidate, then complete backup/restore, upgrade/rollback, bounded load/soak, signing/provenance and Go/No-Go. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Latest code handoff — PR #305 (2026-11-24)

PR [#305](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/305) merged as [ea980c4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea980c46e04b7939251d9e787f8635b69d2d29d5). Native backup creation and schema migration now reject absolute key/output aliases, missing parents and symlinked parents before creating a new backup key or mutating source state. The final safefile.CreateExclusive call remains the race-safe write guard. Regression coverage is in internal/cli/backup_test.go, internal/cli/schema_test.go and internal/safefile/file_test.go.

PR checks passed: [Native runtime/package and real-etcd](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45443014723) — compile/race/static/package checks and real-etcd **success**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45443013024) — **success**; [Source/Privacy/publication audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45443013302) — **success**. Real-vm and real-PITR were explicitly skipped. No Single-Host production gate closed.

The mutable, unsigned v0.2.0-dev.4-test.17 candidate remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296; it cannot evidence [ea980c4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea980c46e04b7939251d9e787f8635b69d2d29d5). productionReady=false and the decision remains no-go.

Next handoff: build an immutable candidate from [ea980c4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/ea980c46e04b7939251d9e787f8635b69d2d29d5), run the existing Ubuntu 24.04 path against that exact candidate, then complete backup/restore, upgrade/rollback, bounded load/soak, signing/provenance and Go/No-Go. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

# Current main handoff — PR #297 (2026-11-24)

PR [#297](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/297) merged as [70c97f3](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/70c97f3d48bf785a697f01fdf35e0896b3ae68bf). Native failover now fails closed for unkeyed etcd `POST /v3/kv/txn` retries after a lost acknowledgement; only an explicit `Idempotency-Key` permits replay. Regression coverage is in `internal/failover/transport_test.go` (`TestEtcdTxnWithoutIdempotencyKeyIsNotReplayed`).

PR checks passed: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45397864977) — compile/race/static/package checks and real-etcd **success**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45397864834) — **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45397864852) — **success**. Real-vm and real-PITR were explicitly skipped. No Single-Host production gate closed.

The mutable, unsigned `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; it cannot evidence Main `70c97f3d48bf785a697f01fdf35e0896b3ae68bf`. `productionReady=false` and the decision remains `no-go`. Build the next immutable candidate from the current Main commit before any live qualification claim.

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

PR [#282](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/282) merged as [8800325a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8800325ab64dd701a69d65a39f332e6153c9da0d). Native `volume`, `secret` and `gateway` dispatch now rejects unknown actions before loading admin configuration or attempting controller access. A regression table uses an unavailable configuration path and verifies stable fail-closed errors for all three command families.

PR checks: [Native runtime/package](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152469) **success** with real-etcd **success** and real-vm/PITR **skipped**; [Kubernetes contracts](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152601) **success**; [Source/Privacy audit](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45284152514) **success**. The documented second self-review was recorded on the PR; GitHub correctly disallows self-approval.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [8800325a](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/8800325ab64dd701a69d65a39f332e6153c9da0d) and use the existing ephemeral Ubuntu path with `run_real_vm_e2e=true` when workflow-dispatch access is available; do not start a seven-VM HA or Kubernetes lab for this first release.

# Latest code handoff (2026-11-23, PR #279)

PR [#279](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/279) merged as [bfc74495](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bfc74495a3248d98df9cfc770eac3a519811e2d0). Native node drain|uncordon|revoke NAME now validates the policy action before loading admin configuration or reading controller state. Malformed two-argument actions therefore fail closed without an unnecessary control-plane request. TestNodePolicyBody covers all supported bodies and the NODE_ACTION_UNKNOWN contract.

PR checks:
- Native runtime/package [45274712039](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274712039) — **success**; compile, race/static checks, package smoke checks and reachable Go vulnerability check passed; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45274712036](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274712036) — **success**.
- Source/Privacy audit [45274711955](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45274711955) — **success**.

No Single-Host qualification gate closed. The unchanged [v0.2.0-dev.4-test.17 candidate](https://github.com/JossefMo1/Werftkern_Kubernetes/releases/tag/v0.2.0-dev.4-test.17) remains bound to 28efa7518e171a618d4dcf9ff3aba58cddaf3296, reports immutable=false and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, service/etcd restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

Next handoff: build a new immutable candidate from [bfc74495](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bfc74495a3248d98df9cfc770eac3a519811e2d0) and use the existing ephemeral Ubuntu path with run_real_vm_e2e=true when workflow-dispatch access is available; do not start a seven-VM lab for this first release.
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

PR checks:
- Native runtime/package [45253629415](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629415) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45253629612](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629612) — **success**.
- Source/Privacy audit [45253629987](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45253629987) — **success**.

Post-merge Main checks:
- Native runtime/package [45254149973](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254149973) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45254150050](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254150050) — **success**.
- Source/Privacy audit [45254149998](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254149998) — **success**.
- Alpha publication guard [45254244539](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45254244539) — **success**; source-only publication was **skipped** because no new release was created.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

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

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native scope.

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

PR [#268](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/268) merged as [f73662f4](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/f73662f4e957cf0489319d34445715d17c626cd4). Native `safefile.DirectoryLock` now validates absolute, clean and non-symlink parent directories before and after creation, opens lock files with no-follow/close-on-exec flags, and rejects non-regular files, non-0600 modes or unexpected owners. Regression coverage verifies a parent-symlink lock directory is rejected.

PR checks:
- Native runtime/package [45220888940](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220888940) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45220888882](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220888882) — **success**.
- Source/Privacy audit [45220889258](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45220889258) — **success**.

Post-merge Main checks:
- Native runtime/package [45221411990](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221411990) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45221412038](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221412038) — **success**.
- Source/Privacy audit [45221412406](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45221412406) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed artifacts/provenance and Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.
# Latest code handoff (2026-11-23, PR #266)

PR [#266](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/266) merged as [cdc929e8](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/cdc929e8651bef08ee4744edc234fa4c52f9ff35). Native `werft control` and agent local-lock paths now validate absolute, clean and non-symlink parent directories before and after creation, open lock files with no-follow/close-on-exec flags, and reject non-regular files, non-0600 modes or unexpected owners. Regression coverage verifies final and parent symlink rejection.

PR checks:
- Native runtime/package [45211017062](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211017062) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45211016964](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211016964) — **success**.
- Source/Privacy audit [45211016962](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45211016962) — **success**.

Post-merge Main checks:
- Native runtime/package [45212279490](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279490) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45212279129](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279129) — **success**.
- Source/Privacy audit [45212279244](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45212279244) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed artifacts/provenance and Go/No-Go remain open. HA/multi-host and Kubernetes Production remain deferred outside the first Native Single-Host scope.
# Latest code handoff (2026-11-23, PR #264)

PR [#264](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/264) merged as [1b24e6cd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1b24e6cd7b0f38c13797f2ab161a609e2641ca48). The `werft doctor` path now reads the configured admin certificate through `safefile.OpenRead` with a regular-file and 64 KiB size bound before parsing. Final and parent symlink redirection is rejected consistently with other credential paths. Regression coverage verifies a valid certificate and both symlink forms.

PR checks:
- Native runtime/package [45198552808](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198552808) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45198553068](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198553068) — **success**.
- Source/Privacy audit [45198552768](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45198552768) — **success**.

Post-merge Main checks:
- Native runtime/package [45199052283](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052283) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45199052324](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052324) — **success**.
- Source/Privacy audit [45199052375](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45199052375) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [1b24e6cd](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/1b24e6cd7b0f38c13797f2ab161a609e2641ca48) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #262)

PR [#262](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/262) merged as [b99d5b8d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b99d5b8d25b839f94fc1ed1e3c82cc658c74f4fe). The packaged demo archive verification path now opens the archive through `safefile.OpenRead` before hashing, rejecting final and parent symlink redirection and non-regular inputs consistently with Docker image loading. Regression coverage verifies a valid archive and both symlink forms.

PR checks:
- Native runtime/package [45189154392](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154392) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45189154412](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154412) — **success**.
- Source/Privacy audit [45189154242](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189154242) — **success**.

Post-merge Main checks:
- Native runtime/package [45189685437](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685437) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- Kubernetes contracts [45189685472](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685472) — **success**.
- Source/Privacy audit [45189685479](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45189685479) — **success**.

No Single-Host qualification gate closed. The unchanged v0.2.0-dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; immutable=false and unsigned assets mean it cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [b99d5b8d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/b99d5b8d25b839f94fc1ed1e3c82cc658c74f4fe) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #260)

PR [#260](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/260) merged as [5cfd4726](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5cfd47267648840f57d947e2bc9f14443e2bf2b2). The read-only `werft assess DATEI.json` path now opens Kubernetes inventory files through `safefile.OpenRead`, rejecting final and parent symlink redirection before bounded assessment. Regression coverage verifies a valid inventory and both symlink forms. Input size limits, strict JSON, read-only behavior and the migration assessment contract are unchanged.

PR checks:
- [Native runtime/package 45179199727](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45179199727) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45179199695](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45179199695) — **success**.
- [Source/Privacy audit 45179199809](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45179199809) — **success**.

Post-merge Main checks:
- [Native runtime/package 45180128482](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128482) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45180128580](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128580) — **success**.
- [Source/Privacy audit 45180128505](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45180128505) — **success**.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [5cfd4726](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/5cfd47267648840f57d947e2bc9f14443e2bf2b2) and use the existing ephemeral Ubuntu path when dispatch access is available.

# Latest code handoff (2026-11-23, PR #257)

PR [#257](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/257) merged as [bafbf1e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bafbf1e98d93490282117b36a26a89eb3f51581b). Native secret-directory reuse now opens `.manifest` through `safefile.OpenRead`, rejecting final and parent symlink redirection. Reuse additionally requires a regular 0400 manifest with the exact expected hash length and a bounded read. Regression coverage rejects a symlinked manifest. Allocation APIs, state schema, stdin input, Kubernetes manager behavior and production flags are unchanged.

PR checks:
- [Native runtime/package 45169953738](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45169953738) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45169953783](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45169953783) — **success**.
- [Source/Privacy audit 45169953690](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45169953690) — **success**.

Post-merge Main checks:
- [Native runtime/package 45170406716](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170406716) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts 45170406949](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170406949) — **success**.
- [Source/Privacy audit 45170407002](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45170407002) — **success**.

No Single-Host qualification gate closed. The unchanged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and cannot evidence this newer Main commit. Fresh Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle, restart, local backup/restore, upgrade/rollback, bounded load/soak, signed provenance and final Go/No-Go remain open. Next handoff: build a new candidate from [bafbf1e9](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/bafbf1e98d93490282117b36a26a89eb3f51581b) and use the existing ephemeral Ubuntu path when dispatch access is available.

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

PR [#244](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/244) merged as [6faf2fbe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6faf2fbe819ae7a0775d27727986bc02be07228e). Native ingress gateway credentials now use the existing no-follow certificate/private-key readers, and edge TLS PEM loading uses bounded no-follow reads instead of path-based `tls.LoadX509KeyPair`. Regression coverage rejects final and parent symlinks for edge certificates and private keys. No certificate format, routing policy or qualification claim changed.

PR checks:
- [Native PR run 45120310439](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310439) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes PR run 45120310428](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310428) — **success**.
- [Source/Privacy PR run 45120310459](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120310459) — **success**.

Post-merge Main checks:
- [Native Main run 45120597182](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597182) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main run 45120597181](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597181) — **success**.
- [Source/Privacy Main run 45120597194](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45120597194) — **success**.

Production remains **not ready**: the immutable/signed release candidate, fresh Ubuntu installation, backup/restore, upgrade/rollback, bounded load/soak and final Go/No-Go evidence are still open. The tagged dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and cannot evidence this newer Main commit. Next handoff: build a new candidate from [6faf2fbe](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6faf2fbe819ae7a0775d27727986bc02be07228e), then run the existing ephemeral Ubuntu path when dispatch access is available.

## Latest code handoff (2026-11-23, PR #242)

PR [#242](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/242) merged as [485fcfd2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/485fcfd2b9f53abc857dfe19d66e8741981aa864). Native `certificate bundle/renew/install` now reads CA and leaf certificate inputs through `safefile.OpenRead`, rejecting final and parent symlinks and enforcing a 1 MiB input bound. Regression coverage rejects both symlink forms. The change does not alter certificate formats or qualification claims.

PR checks:
- [Native PR run 45115171200](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171200) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes PR run 45115171140](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171140) — **success**.
- [Source/Privacy PR run 45115171174](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115171174) — **success**.

Post-merge Main checks:
- [Native Main run 45115468629](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468629) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main run 45115468670](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468670) — **success**.
- [Source/Privacy Main run 45115468624](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45115468624) — **success**.

Production remains **not ready**: the immutable/signed release candidate, fresh Ubuntu installation, backup/restore, upgrade/rollback, bounded load/soak and final Go/No-Go evidence are still open. The tagged dev.4-test.17 candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296` and must not be treated as evidence for this newer Main commit. Next handoff: build a new candidate from [485fcfd2](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/485fcfd2b9f53abc857dfe19d66e8741981aa864), then run the existing ephemeral Ubuntu path when dispatch access is available.

## Latest code handoff (2026-11-23, PR #239)

PR [#239](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/239) merged as [43bcfb46](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/43bcfb468680d976b181a5ca8a745d55bd1d63ff). Native `backup inspect/restore --file` now opens privileged backup inputs through `safefile.OpenRead`, rejecting final and parent symlinks and enforcing the existing 3x `MaxPlaintext` limit after opening. Regression tests cover both symlink forms and regular-file reads. The first CI attempt exposed a self-introduced truncated-file error; it was corrected before the merged head.

PR and post-merge required checks:
- [Native PR](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108527662) and [Native Main](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108824975) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes Main](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108825010) — **success**.
- [Source/Privacy Main](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45108824979) — **success**.

No qualification gate was closed. The tagged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, reports `immutable=false` and unsigned assets, and remains `productionReady=false`/No-Go. The next candidate must be built from `43bcfb468680d976b181a5ca8a745d55bd1d63ff`. Live Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability, user feedback and final Go/No-Go remain open. The connector still cannot dispatch `ci.yml`; this is a blocker, not a passed gate.

# Aktuelle Production-Entscheidung — 23.11.2026

## Latest code handoff (2026-11-23, PR #237)

PR [#237](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/237) merged as [6463c29d](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/6463c29de2a1bfcb6c9e7dbcfbfeae26585d427d). Native `werft release verify` liest Manifest-, Signatur- und Public-Key-Eingaben jetzt über `safefile.OpenRead`, weist finale und übergeordnete Symlinks ab und erzwingt das Größenlimit auch nach dem Öffnen. Regressionstests decken beide Symlinkformen und das Limit ab.

Exact Main checks for the merge commit:
- [Native runtime/package 45103114622](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114622) — **success**; real-etcd **success**, real-vm/PITR **skipped**.
- [Kubernetes contracts/package 45103114692](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114692) — **success**.
- [Source/Privacy audit 45103114649](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103114649) — **success**.

Private alpha publication jobs [45103144455](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103144455), [45103152906](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103152906) and [45103316680](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45103316680) completed successfully but are not stable release or production evidence. No qualification gate was closed. The immutable `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`; `productionReady=false` and the decision remains **no-go**.

The next candidate must be package-built from `6463c29de2a1bfcb6c9e7dbcfbfeae26585d427d`. Live Ubuntu installation/deinstallation/reinstallation, Docker/etcd workload lifecycle and restart, backup/restore, upgrade/rollback, bounded load/soak, signed provenance/immutability, user feedback and final Go/No-Go remain open. The current GitHub connector still cannot dispatch `ci.yml`; this is a blocker, not a passed gate.

## Previous handoff history
## Previous handoff history

## Latest code handoff (2026-11-23, PR #232)

PR [#232](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/232) merged as [29418520](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/29418520bc4198a2e8102fe7518ef8e1e23893fe). Native `Docker.Load` now opens local image archives through `safefile.OpenRead`, refusing final symlinks and symlinked parent paths before Docker ingestion; regression tests cover both paths.

Exact PR checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091069067), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091068980) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091069003). Post-merge Main checks passed: [Native](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091414068), [Kubernetes](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091414150) and [Source/Privacy](https://github.com/JossefMo1/Werftkern_Kubernetes/actions/runs/45091414089). Real-etcd passed; real-vm and real-PITR were skipped.

This is security-boundary hardening only. The tagged `v0.2.0-dev.4-test.17` candidate remains bound to `28efa7518e171a618d4dcf9ff3aba58cddaf3296`, its release metadata reports `immutable=false` and unsigned assets, `productionReady=false`, and no qualification gate was closed. The next candidate must be built from `29418520bc4198a2e8102fe7518ef8e1e23893fe`; live installation, backup/restore, upgrade/rollback, bounded load/soak, signing/provenance and final Go/No-Go remain open.


Der offizielle erste Production-Scope ist jetzt **Native Single-Host Production**. Die Hauptversion soll produktiv nutzbar sein, aber nur innerhalb dieses ausdrücklich dokumentierten Umfangs. HA/Multi-Host, Kubernetes-Production und Site-Recovery sind zurückgestellt und keine Blocker für den ersten Native-Release.

Der aktuelle Status bleibt **No-Go**, bis der exakte Native-Kandidat die Single-Host-Gates, Signierung, Runbooks und Go/No-Go-Prüfung bestanden hat. Die alten Full-Masterplan-Einträge darunter sind historische Nachweise; sie gelten nicht mehr als Pflichtumfang für den ersten Release.

The scope decision is recorded in [PR #203](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/203), merged at
`f75845424286c1c8bed6c9ef17d2b172066e6309`. The current tagged candidate remains
older and must not be treated as evidence for this changed scope; GitHub release metadata reports immutable=false and its assets are unsigned.

The tracker contract is hardened by [PR #204](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/204), merged at
`83c06425600749418994d34a1f197d4ad64f6d50`; the follow-up documentation synchronization is
tracked in PR #205. The candidate remains an older, unsigned lab artifact and does not
qualify any Native Single-Host gate.

The next live candidate must be built from package-bearing Main code handoff `29418520bc4198a2e8102fe7518ef8e1e23893fe`; documentation-only Main commits may have newer SHAs, so evidence must bind the runner-reported `GITHUB_SHA` and package digest rather than a guessed predecessor. The current connector cannot dispatch `ci.yml`, so this remains a documented blocker rather than a passed gate.


## Previous code handoff (2026-11-23, PR #230)

PR [#230](https://github.com/JossefMo1/Werftkern_Kubernetes/pull/230) merged as [397e0ff](https://github.com/JossefMo1/Werftkern_Kubernetes/commit/397e0ff6de39404f631aab92c12ed9719108c617). Native release verification now opens the candidate package through `safefile.OpenRead`, which validates non-symlink parent components, refuses final symlinks and rejects non-regular files before hashing. Regression coverage protects both final-package and parent-symlink paths.

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

