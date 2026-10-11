# Werftkern Kubernetes – Betriebsbackend 0.1.0-dev.3

**Entwicklungsversion. Keine Produktionsfreigabe und keine CNCF-Zertifizierung.**
Dieser Teil ergänzt den vorhandenen Native-Kern, er ersetzt ihn nicht. Native bleibt
auf `0.2.0-dev.4`, State-Schema 2. Der neue Befehl heißt **`werft-kube`** und verwendet
**echtes Kubernetes aus k0s**, dessen containerd, etcd, kube-router und CoreDNS. Er ist
kein eigener Kubernetes-API-Nachbau, kein „Kubernetes 2.0“-Upstream und keine konforme
Umbenennung des Native-Schedulers. ClusterPilot wird nicht benötigt; dessen privates
Repository wird nicht eingebunden. Die eigene Lizenz bleibt Apache-2.0.

## Lieferumfang und Voraussetzungen

Enthalten sind ausführbare Python-Verträge, Werkzeuge, Tests und ein separates
Debian/Ubuntu-Paket für den **Managementhost**. Nicht enthalten sind k0s, k0sctl,
kubectl, Helm, age, Sonobuoy, Containerimages, Helm-Charts und Keycloak-Operatormanifeste.
Sie werden vor Verwendung aus geprüften Quellen bereitgestellt und in `assets.json`
mit exakter Version, absolutem Pfad und SHA256 erfasst. Keine `latest`-Auflösung,
kein `curl | bash`, keine unbemerkten Downloads oder erfundenen Release-Digests.
Ein Hash bestätigt Dateiintegrität, nicht Herstellerherkunft oder CVE-Freiheit.
**Das Paket allein baut deshalb noch keinen vollständigen Cluster auf.**

Zielprofil: Linux-Managementhost mit Python >=3.10, PyYAML, OpenSSH und CA-Zertifikaten;
frische dedizierte Ubuntu-24.04-amd64-Zielhosts; root oder freigegebener passwortloser
sudo-Zugang; private, gegenseitig erreichbare IPv4-Adressen; fest verifizierte
Ed25519-SSH-Hostkeys. Der Managementhost muss alle privaten Zieladressen erreichen.
Konkrete k0s-/k0sctl-/Kubernetes-/Chart-/Imagekombinationen sind **noch nicht qualifiziert**.
Helm-Vertrag: Helm 3. Keycloak-CRs benötigen einen geprüften Operator/Server mit
`v2beta1`, Truststores und `db-tls-mode=verify-server` (neuere 26.x-Linie, mindestens
26.7 für diese Datenbank-TLS-Option). Keine generelle Unterstützung aller Versionen.

HA-Profil: genau drei Controller und mindestens ein Worker; für Netze2e und automatische
Reparatur mindestens drei Worker sinnvoll. Lab-Profil: ein Controller und mindestens
ein Worker. Vorab einrichten: hochverfügbarer API-Einstieg, API-DNS, korrekte TLS-SANs,
k0s-Netzwerk-/Firewallfreigaben, Zeitabgleich und Image-/Paketegress. Der API-LB darf
nicht selbst ein unbeachteter Einzel-Ausfallpunkt sein. k0s benötigt je nach Topologie
zusätzlich zum Kubernetes-API-Port die dokumentierten Join-/Konnectivity-Verbindungen.
Diese Freigaben werden nicht pauschal öffentlich geöffnet.

## Installation und erste Befehle

```bash
sudo apt install ./werftkern-kubernetes_0.1.0~dev3_all.deb
werft-kube version
werft-kube --help
```

Das Paket startet **keine** Dienste und verändert keine Cloud oder Zielhosts im
postinst. Arbeitsverzeichnis und Geheimnisse bleiben nur dem ausführenden Benutzer
zugänglich. Empfohlene Pfade:

```
/etc/werftkern/kubernetes/lab/assets.json
/etc/werftkern/kubernetes/lab/admin-ssh
/etc/werftkern/kubernetes/lab/provider-token
/var/lib/werftkern/kubernetes/lab/
```

`assets.json` enthält keine Tokens; seine referenzierten Artefakte müssen dem
Managementbenutzer gehören und dürfen nicht gruppen-/weltbeschreibbar sein. Ein
SSH-Schlüssel und Provider-Token müssen private reguläre Dateien sein (0600).
Beispiele enthalten bewusst nicht ausführbare Platzhalter. Diese ersetzen keine
geprüften Produktversionen, Schlüssel oder Digests.

```bash
werft-kube plan cluster.json
# Prüfausgabe kontrollieren; den echten SHA256 aus der Ausgabe verwenden.
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  create --plan cluster.json --confirm PLAN_SHA256
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json status
```

Der Eingabedialog ist eine Alternative mit bereits vorbereitetem Inventar:

```bash
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  setup --inventory hosts.json --ssh-key /etc/werftkern/kubernetes/lab/admin-ssh --backup-recipient AGE_RECIPIENT
```

Er fragt Clustername, vorhandenen API-DNS-Einstieg, ein lokal freigegebenes Release
und die Planbestätigung. Standard-Pod-/Service-Netze werden auf Überschneidung geprüft.
Abweichende Netze werden vor `create` in einer expliziten Plandatei festgelegt.
Der Dialog ist **kein** fertiger Wizard für alle Cloud-, DB-, IAM- und PKI-Aufgaben.

## Cluster erstellen, aktualisieren und skalieren

`create`, `upgrade`, `scale` und `apply` verwenden dieselbe persistente Lifecycle-
State-Machine. Eine lokale Dateisperre verhindert parallele Prozesse am selben
Managementverzeichnis; eine operationgebundene ConfigMap im Zielcluster sperrt
konkurrierende Manageroperationen. Die Sperre läuft nicht unsicher zeitgesteuert ab.
Andere Administratoren mit direkten Kubernetes-/Cloudrechten bleiben eine externe
Vertrauensgrenze. Keine Multi-Writer-Management-HA zugesagt.

Jeder Auftrag bindet den vollständigen Plan und das Artefaktinventar. etcd-Inhalt und
PKI werden vor einem Upgrade durch `k0sctl backup` gesichert und mit **age** an den
expliziten Empfänger verschlüsselt. Der private Entschlüsselungsschlüssel gehört
nicht in dieses Inventar. Quell- und Zielrelease brauchen eine freigegebene
`upgradeEdges`-Kante. Minor-Versionen dürfen nicht übersprungen, Versionen nicht
herabgesetzt und Topologie/Auth nicht gleichzeitig geändert werden.

```bash
werft-kube plan upgrade.json
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  upgrade --plan upgrade.json --confirm PLAN_SHA256
# Worker im kopierten Plan hinzufügen bzw. entfernen; Controller bleiben identisch.
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  scale --plan scale.json --confirm PLAN_SHA256
```

Scale-down drainiert zuerst **alle** zu entfernenden Worker mittels Eviction API,
ohne `--force` und ohne `--delete-emptydir-data`. PDB-/Datenfehler blockieren. Erst
anschließend setzt k0sctl diese explizit zurück; bloßes Weglassen eines Hosts gilt
nicht als abgeschlossene Entfernung. Scale-down löscht keine Cloud-VMs, Disks oder
Netze – laufende Providerkosten sind separat zu beenden. Scale-up erwartet bereits
bereitgestellte Worker samt geprüften Hostkeys; Fleet-Provisionierung und Repair
sind eigene Abläufe.

Nach Apply werden **alle Controller direkt** über TLS auf API-Bereitschaft, Version
und denselben kube-system-UID geprüft. So kann ein LB keine alte Controller-Version
verbergen. Die erwarteten Worker müssen mit korrektem Namen, Private-IP, Labels,
kubelet-Version und Ready-Zustand erscheinen; CoreDNS-Rollout muss erfolgreich sein.
Drei Beobachtungen ersetzen noch keinen Dauer-/Ausfall-/Datenpfadtest.

Wiederholung desselben unterbrochenen Lifecycle-Plans ist möglich; k0sctl gleicht
Hostzustand deklarativ ab. Nach unklarer Helm- oder Providerwirkung gilt hingegen
Beobachtung statt blindem erneutem Änderungsbefehl. Journale nicht löschen, um Sperren
zu umgehen. Nach Abbruch Originalplan/Artefakte beibehalten und Ursache prüfen.

## Backups und Restoregrenze

```bash
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json backup
```

Ausgabe ist ein verschlüsseltes **Control-Plane-Backup**, einschließlich Schlüsseln.
Es enthält **keine Anwendungsvolumes**. age-Verschlüsselung ist kein unveränderliches
externes Backup, keine Ransomware-Isolation und kein Datenkonsistenzbeweis. Kopien und
Empfängerschlüssel getrennt sichern, Restore praktisch testen.

Ab dev.2 ist ein journalisierter Control-Plane-Restore auf **frische neue Controllerhosts**
implementiert (`werft-kube restore`). Er bindet Backup-Receipt v2, Zielplan, Cluster-UID,
API-Endpunkt und Quellcontroller und wiederholt einen möglicherweise bereits gestarteten
Restore nach unklarem Ergebnis nicht blind. Der API-Endpunkt bleibt identisch. Persistent-
Volumes und externe Datenbanken sind **nicht** Bestandteil dieses Restores; sie benötigen
eigene Backups, Fencing und fachliche Verifikation. Vollständige standortweite DR ist daher
weiterhin nicht freigegeben. Kein pauschaler Rollback durch Installation alter Binaries.

## Add-ons, Zertifikate und SSO

Siehe [ADDONS-SSO-DE.md](ADDONS-SSO-DE.md). Der Katalog enthält Traefik, cert-manager,
Keycloak Operator, kube-prometheus-stack/Grafana, Velero, Hetzner CSI und Argo CD.
Diese sind **nicht alle für Kubernetes erforderlich**. Zusätzliche Controller machen
Backup, Rechte, Updates und Datenverantwortung komplexer. Der native Laufzeitkern
kann diese Helm-Charts nicht ausführen; nur der Kubernetes-Pfad kann das.

## Automatischer Worker-Ersatz

Siehe [REPAIR-DE.md](REPAIR-DE.md). Für ausdrücklich freigegebene **zustandslose**
Hetzner-Worker ist der komplette Operationspfad vom beobachteten Ausfall über
Providerlöschung, VM-Neuanlage, SSH-Bootstrap, Join und Ready-Nachweis implementiert.
Er ist noch nicht gegen echte Provider-/Mehrhost-Ausfälle qualifiziert. Controller,
Datenbanken, unbekannte Nodes und Daten-Workloads werden nicht automatisch zerstört.

## Live-Smoke und Sonobuoy

```bash
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  acceptance run --confirm DISPOSABLE:CLUSTER_UID
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  sonobuoy run --run-id qualification-01 --mode certified-conformance --accept-disruption
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  sonobuoy collect --run-id qualification-01
```

Der Smoke verwendet drei auf verschiedene Worker verteilte HTTP-Pods und einen
wirklichen Client-Job. Er prüft Service-DNS, Service-IP und die direkten Podadressen
auf anderen Nodes. Benötigte Images: gepinntes Kubernetes-agnhost (`/agnhost netexec`)
und BusyBox-kompatibler Client (`/bin/sh`, `nslookup`, `wget`). Job-Erfolg ist nicht
HA, Speicherkorrektheit oder SSO. Testnamespace wird für Diagnose behalten; Cleanup
fordert die gespeicherte Namespace-UID und löscht nie eine fremde Wiederanlage.

Sonobuoy verwendet genau `quick` oder `certified-conformance`, keine Focus-/Skip-
Overrides, kein `--skip-preflight`, keine Plugin-URL. Sonobuoy- und e2e-Image müssen
auf Digests gepinnt sein; der e2e-Katalogschlüssel entspricht der beobachteten
Kubernetes-Patchversion. Andere von Kubernetes-Tests benötigte Testimages müssen
im echten Netz verfügbar sein; ein vollständiger Airgap-Spiegel ist nicht enthalten.

Jeder Lauf bindet Cluster-UID, Namespace-UID, Version und Tools. Abgerufene Archive
werden auf Größe, SHA256 und enthaltene Serverversion geprüft; sie werden nicht
blind extrahiert. Skips außerhalb `[Conformance]` gelten nicht als Conformancefehler;
fehlende, doppelte, fehlerhafte und übersprungene Conformancefälle werden erkannt.
Ein mitgegebenes Sollinventar wird exakt verglichen (`expectedInventoryMatched`), seine Herkunft
aber nicht unabhängig authentifiziert; `fullInventoryVerified` bleibt daher **false**.
Das vollständige offizielle Inventar bleibt eine externe Prüfaufgabe.
**Ein technisch erfolgreicher Test erzeugt niemals `cncfCertified=true`.** Prüfung,
Teilnahmebedingungen und Annahme der Ergebniseinreichung bleiben bei der CNCF. Die
Zertifizierung von k0s überträgt sich nicht automatisch auf Werftkern.

Sonobuoy-Daten enthalten möglicherweise Infrastruktur- und Diagnoseinformationen.
Keine automatische Veröffentlichung oder PR-Einreichung. Erst sichten und sensible
Informationen gemäß Programmanforderungen behandeln. Zertifizierte Tests können
Anwendungen stören; auf isolierten Wegwerf-/Qualifikationsclustern ausführen.

## Status und nicht erfüllte Produktionsgates

Im aktuellen Arbeitslauf keine Cloudressourcen angelegt und kein GitHub-Repository
verändert. Keine echte Kubernetes-Installation, kein Upgrade oder Scale auf VMs,
kein realer Node-Ausfall, keine ACME-Ausstellung, keine SSO-Anmeldung und kein
Sonobuoy-Clusterlauf erfolgreich ausgeführt. Die neuen Unit-/Contracttests benutzen
markierte Kubernetes-/Provider-/Toolantworten. Sie sind keine produktive Abnahme.

Noch offen: qualifizierte vollständige Abhängigkeits-/Image-Releases, sicherer
Erstbetrieb ohne vorbereitete Infrastruktur, automatische API-LB-/DNS-Bereitstellung,
Controllerersatz, Daten-/Volume-sicherer automatischer Stateful-Nodeersatz, vollständige
DB-/PV-DR, tatsächliche SSO-Login- und Policy-Negativtests, generische Add-on-Updates
mit CRD-/Datenmigration, unabhängiger Sicherheitsreview, CVE-/Supply-Chain- und
Last-/Dauernachweise. Keine unbelegte SLA-, RPO-, RTO- oder Kompatibilitätsgarantie.

## Neu in 0.1.0-dev.3: HA-Einstieg, Cloud-Scale und Control-Plane-Restore

Ein HA-Plan muss jetzt ausdrücklich angeben, wie der API-Einstieg hochverfügbar ist.
`haControlPlane.mode=external` bindet Werftkern an einen bereits qualifizierten externen
Loadbalancer. Alternativ kann `mode=k0s-vip` in einem geeigneten gemeinsamen L2-Netz die
von k0s bereitgestellte Keepalived-Control-Plane-Load-Balancing-Funktion aktivieren. In
diesem Modus wird zusätzlich k0s Node-Local Load Balancing mit Envoy aktiviert. Der VRRP-
`authPass` wird nicht im Plan gespeichert; der Plan referenziert eine private Datei. Er ist
nur ein Schutz gegen versehentliche VRRP-Konflikte, kein kryptografisches Geheimnis. Der
gewählte VIP muss vom Betreiber reserviert und routbar sein. Multicast-/VRRP-Unterstützung
ist vor Produktion im realen Netz zu testen.

Cloudgestütztes Worker-Scaling ist ein separater, bestätigungspflichtiger Vorgang:

```bash
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  cloud-scale --spec cloud-scale.json --token-file /etc/werftkern/kubernetes/lab/provider-token \
  --confirm CLOUD_SCALE_OPERATION_HASH
```

Scale-up provisioniert neue Hetzner-Worker innerhalb der Kostenobergrenze und fügt sie
erst danach über den normalen Lifecycle hinzu. Scale-down drainiert und entfernt Nodes
zuerst aus Kubernetes. Erst nach erfolgreich committedem Zielplan wird die zugehörige,
Werftkern-eigene Provider-VM gelöscht. Nach einem mehrdeutigen DELETE-Ergebnis wird der
DELETE-Aufruf nicht wiederholt; permanente Abwesenheit muss beobachtet werden.

Control-Plane-DR verwendet ab dev.2 Backup-Receipts v2. Sie binden Cluster-UID, Version,
API-Endpunkt, Quellplan und Quellcontroller. Restore ist ausschließlich auf neue, frische
Controllerhosts mit unverändertem API-Endpunkt zulässig:

```bash
werft-kube --root /var/lib/werftkern/kubernetes/recovered --assets /etc/werftkern/kubernetes/recovered/assets.json \
  restore --plan recovered-plan.json --backup-dir /secure/backup-01 \
  --identity /secure/age-recovery.key --confirm RESTORE_OPERATION_HASH
```

Der Hash wird aus Backup-Receipt, Zielplan und geprüftem Assetinventar berechnet. Ein
möglicherweise bereits gestarteter `k0sctl --restore-from`-Vorgang wird nach einem
unklaren Ergebnis niemals blind wiederholt. Der Manager versucht dann ausschließlich,
den erwarteten Cluster mit derselben kube-system-UID zu beobachten. Ist das nicht
möglich, bleibt der Vorgang für Operatorprüfung gesperrt.

**Restore-Grenze:** Das Verfahren stellt k0s-Control-Plane-Zustand und PKI wieder her,
nicht PersistentVolumes oder externe Datenbanken. Diese Daten benötigen eigene
Backups, Fencing und fachliche Verifikation, bevor Produktionstraffic freigegeben wird.


## Dev.3 Recovery und Freigabe

Neue Befehle: `controller-replace`, `stateful-replace`, `recovery-watch`,
`data-restore`, `qualification`. Erst die [Recovery-Voraussetzungen](DEV3-RECOVERY-DE.md),
[PV-Restore-Grenzen](DEV3-DATA-RESTORE-DE.md) und [Vertrauenskonfiguration](DEV3-RELEASE-EVIDENCE-DE.md)
prüfen. Neue Dienste bleiben deaktiviert. Laufende dev.2-Cloudoperationen ohne
Credentialbindung niemals durch nachträgliches Erfinden eines Journalfelds freigeben.
Dieser Stand ist nicht produktionsqualifiziert. Das Managementpaket enthält keine
geprüfte Kubernetes-/Chart-/Image-Lieferkette und keinen automatischen unabhängigen Review.
