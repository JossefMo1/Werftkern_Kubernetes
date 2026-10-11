# Werftkern Kubernetes 0.1.0-dev.2 — tatsächlicher Entwicklungs- und Teststand

**NOT_PRODUCTION_READY · keine CNCF-Zertifizierung.** Stand: 26. September 2026.

## Neu implementiert

- Kontrollierter k0s-Control-Plane-Restore aus verschlüsseltem Backup-Receipt v2.
  Restore bindet Cluster-UID, Zielplan, Quellcontroller, API-Endpunkt, Release und
  Assetinventar; er ist nur auf frischen neuen Controllerhosts zulässig. Nach einem
  möglicherweise bereits gestarteten Restore wird ausschließlich beobachtet, nicht
  blind erneut mutiert.
- HA-Pläne deklarieren nun eine API-HA-Strategie. `external` verlangt einen extern
  verantworteten HA-Einstieg; `k0s-vip` rendert k0s Keepalived CPLB plus Node-Local
  Load Balancing/Envoy. VRRP-Passmaterial wird aus einer privaten lokalen Datei gelesen.
- Cloudgestütztes Hetzner-Worker-Scaling verbindet VM-Erzeugung/-Löschung mit dem
  Kubernetes-Lifecycle. Scale-down committed zuerst Drain/Nodeentfernung und löscht
  danach nur eindeutig zugehörige Provider-VMs. Ein unklarer DELETE wird nicht wiederholt.
- Backup-Receipts wurden auf `werftkern-kube-backup/v2` erweitert.

## Tatsächlich ausgeführte Prüfungen dieses Quellstands

| Prüfung | Ergebnis | Aussagegrenze |
|---|---|---|
| Kubernetes-Python-Suite | **90 Tests bestanden** | Kubernetes, SSH, Helm, Provider, Sonobuoy und k0sctl sind in diesen Tests markierte Adapter/Fixtures. |
| Native Go-Suite mit Race Detector | **175 Haupttest- und 110 Untertestergebnisse; 22 Pakete bestanden; 0 Fail/Skip** | Enthält Prozesshelfer/Fuzzseeds; nicht 285 unabhängige E2E-Szenarien. |
| Native Python-Betriebsbefehle | **64 Tests bestanden** | Host/Provider/DB-Antworten überwiegend Fixtures gemäß jeweiligem Testvertrag. |
| Release-/Publikationsguards | **7 Tests bestanden** | Mechanische Konsistenz, keine unabhängige Securityfreigabe. |
| Browser-DOM | **11 Prüfungen bestanden** | Synthetische In-Memory-API; kein Live-Kubernetes-Cluster. |
| Public-source-Lint | **249 Dateien gescannt, 0 Findings** | Begrenzter Pattern-/Quellscan, kein IP-/Lizenz-/Secrets-Audit durch Dritte. |
| Python/Shell/JavaScript-Syntax | bestanden | Kein Host-/Cloudbetrieb. |

Die Restore-Regressionen prüfen insbesondere exakte Bestätigung vor Mutation,
Hashmanipulation, Verbot gleicher Quellcontroller, Zielmanager mit bestehendem Cluster,
Original-Cluster-UID sowie den Fall einer verlorenen/unklaren `k0sctl restore`-Antwort.
Die HA-Tests prüfen Strategiepflicht, VIP-Adresskollisionen und die gerenderte CPLB-/NLLB-
Konfiguration. Cloud-Scale-Tests prüfen Kosten-/Delete-Freigaben, Create→Join, Kubernetes-
Entfernung vor Providerlöschung und kein wiederholtes DELETE nach unklarer Antwort.

## Nicht real qualifiziert

Kein echter k0s-/k0sctl-/Kubernetes-Cluster wurde in diesem Arbeitslauf installiert.
Kein tatsächlicher Control-Plane-Restore, kein VRRP/Keepalived-Failover, kein Hetzner-
Scale-Vorgang, kein Sonobuoy-Lauf, keine ACME-Ausstellung und kein Keycloak-Login wurden
auf realen Hosts ausgeführt. Der verbundene DigitalOcean-Zugang meldete in der Kontoinfo
weiterhin einen Warnstatus/Droplet-Limit-Hinweis, während die Droplet-Liste leer zurückkam;
diese widersprüchliche externe Kontolage wurde nicht als Testumgebung interpretiert. Es
wurden keine Cloudressourcen verändert, angelegt oder gelöscht.

Weiter offen bleiben unter anderem: automatischer Controllerersatz, daten-/volume-sicherer
Stateful-Nodeersatz, vollständige PV-/DB-DR-Verifikation, hochverfügbarer Edge für alle
unterstützten Netze, generische NetworkPolicies, SSO-E2E für den gesamten Add-on-Katalog,
vollständig qualifizierte Tool-/Chart-/Image-Matrix, echte Ubuntu-/Reboot-/Partition-/
Upgrade-/Restore-/Last-/Dauertests, aktuelle signierte Lieferkette und unabhängige
Sicherheitsprüfung.

`productionReady`, `fullMasterplanComplete` und `cncfCertified` bleiben daher **false**.
