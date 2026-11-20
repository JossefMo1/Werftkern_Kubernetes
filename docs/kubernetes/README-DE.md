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
Die [Core-Zielmatrix](../../release/kubernetes-target-matrix.json) schlägt
`v1.37.2+k0s.1`, k0sctl `v0.33.1` und kubectl/Kubernetes `v1.37.2`
mit festen Upstream-Digests vor. Als enges Storage-Kandidatenprofil ist außerdem
hcloud-csi `2.24.2` mit dem digestgebundenen offiziellen Chart, k0s-Kubelet-Pfad
und einer nicht standardmäßigen `Retain`-StorageClass ausgewählt. Die Binaries
wurden damit noch nicht ausgeführt oder signaturgeprüft; Chart und Images sind
hash- beziehungsweise digestgebunden gerendert. Alle Live-Storage-Gates bleiben
offen. Die Matrix ist deshalb weder Supportzusage noch Upgrade- oder Produktionsevidenz.
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
sudo apt install ./werftkern-kubernetes_0.1.0.dev3_all.deb
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

## Kandidatenprofil für persistente Volumes

Der ausgewählte, noch nicht qualifizierte Pfad verwendet ausschließlich Hetzner
Cloud Volumes über hcloud-csi `2.24.2`. Das offizielle Chart ist in
`assets.example.json` mit dem vom GitHub-Release-API gemeldeten SHA256 gebunden.
Die Wertevorlage `hcloud-csi-values.example.yaml` setzt für k0s
`node.kubeletDir: /var/lib/k0s/kubelet`, zwei Controller-Replikate und eine
nicht standardmäßige StorageClass `werftkern-hcloud-retain` mit `Retain`.
Das Chart selbst erzwingt `WaitForFirstConsumer` und Volume-Expansion.
`release/hcloud-csi-image-lock.json` erfasst die sechs eindeutigen Images des
Upstream-Values-Git-Blobs. `scripts/check-hcloud-csi-image-lock.py` blockiert
unvollständige Inventare, mutable Tags sowie ein gerendertes Manifest mit Tag-Images
oder nicht freigegebenen Images. Die sechs OCI-Index-Digests sind gebunden, nachdem
der jeweilige Registry-Header mit dem SHA-256 des empfangenen Manifest-Bodys
übereinstimmte. `--verify-registry` wiederholt diese Online-Prüfung und erkennt
Tag-Drift. Das ist weder Signatur- noch Schwachstellenprüfung; da das Chart noch
nicht angewendet wurde, bleibt jede Live-Qualifikation offen. Das SHA256-geprüfte
Chart wurde mit Helm `v3.22.1`, Kubernetes-Ziel `1.37.2` und diesen Werten
digestgebunden gerendert. Das exakte Ergebnis liegt unter
`release/evidence/hcloud-csi-2.24.2-render.yaml`; Lock und Prüfer binden Chart-,
Values-, Tool- und Manifest-Hash sowie das exakte Image-Multiset. Zusätzlich wird der
separat verwaltete `werftkern-hcloud-csi-node`-ServiceAccount hashgebunden in den Render
aufgenommen; `node.serviceAccountName` wählt ihn explizit aus und sein
`automountServiceAccountToken: false` verhindert den automatischen API-Token-Mount.

`release/hcloud-csi-security-policy.json` und
`scripts/check-hcloud-csi-security-policy.py` halten die statische Vertrauensgrenze
fail-closed fest: keine RBAC-Wildcards oder Secret-Rechte, keine Host-Network/PID/IPC-
Freigabe und ausschließlich der erwartete privilegierte Node-Treiber mit `/dev`, den
vier k0s-HostPaths und dem bidirektionalen Kubelet-Mount. Die Prüfung bleibt bewusst
**nicht bestanden**: Der Node-Token-Mount ist statisch deaktiviert und beide Workloads
setzen `RuntimeDefault` auf Pod-Ebene. Das schützt die nicht privilegierten Container,
erzwingt wegen Kubernetes-Privileged-Semantik aber keinen Seccomp-Filter für den
privilegierten CSI-Node-Treiber. Container-SecurityContexts und die live gemessene
Eignung der Ressourcenbudgets waren offen. Der deterministische Post-Renderer
`scripts/harden-hcloud-csi-render.py` akzeptiert jetzt nur den exakten geprüften
Eingangs-Hash und die vollständige erwartete Workload-/Containergrenze. Er macht alle
Root-Identitäten explizit. Für die sieben nicht privilegierten Containerinstanzen
erzwingt er `allowPrivilegeEscalation: false`, den Drop aller Capabilities und
`RuntimeDefault` auf Container-Ebene. Beim privilegierten Node-Treiber bleibt bewusst
nur der geprüfte Root-/Privileged-Kontext; ein stilles Abschwächen oder Erweitern wird
abgelehnt. Das ist keine Non-root- oder Laufzeitqualifikation. Die Werte setzen für jede
der acht gerenderten Container-Instanzen explizite CPU-/Memory-Requests und -Limits. Der
Prüfer bindet diese Budgets exakt und lehnt fehlende oder veränderte Werte ab. Es sind
konservative Startwerte ohne Last- oder Soak-Nachweis; ihre Eignung für Produktion
bleibt deshalb ausdrücklich unqualifiziert.

`release/hcloud-csi-runtime-profile.json` bindet zusätzlich für `linux/amd64` den
Index-, Plattform-Manifest- und Config-Digest sowie `User` und Entrypoint aller sechs
Images. `scripts/check-hcloud-csi-runtime-profile.py` prüft diese Kette fail-closed und
kann sie mit `--verify-registry` direkt gegen die Registries wiederholen. Alle geprüften
Configs starten derzeit explizit mit `User: 0` oder implizit mit leerem `User` als root.
Da das Upstream-Chart keine SecurityContext-Werte je Container anbietet, darf
`runAsNonRoot` nicht auf Pod-Ebene aktiviert oder als erfüllt gemeldet werden: Die
digestgebundenen Workloads würden so nicht starten. Der Post-Renderer erlaubt enge
root-kompatible Kontexte, ersetzt aber keine non-root-fähigen Images. Vor einer
Non-root-Aussage sind ein geprüfter Image-/Template-Pfad für getrennte
Container-Identitäten und ein echter Lauf auf einem entbehrlichen Cluster erforderlich.
Das ist weder Admission-, Laufzeit-, CSI-Kompatibilitäts- noch Penetrationstest.

Das Hetzner-Token wird als bereits vorhandenes Secret `kube-system/hcloud`
erwartet und gehört niemals in `assets.json`, Wertevorlagen, Logs oder Git.
Dieser Pfad ist ReadWriteOnce und kann ein Volume nur an einen Server gleichzeitig
anhängen. Hetzner stellt für Volumes keine Backups oder Snapshots bereit. Ein
Control-Plane-Backup enthält die Volumes ebenfalls nicht. Vor jeder Freigabe sind
deshalb mindestens reproduzierbares Chart-Rendering, vollständige Image-Digests, Provision/Attach/
Mount, Expansion, Node-Ausfall mit sicherem Reattach, `Retain`-Verhalten sowie
anwendungskonsistentes Backup und Restore auf einem neuen Cluster real auszuführen.

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

