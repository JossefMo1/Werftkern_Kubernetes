# Dev.3: kontrollierter Controller- und Stateful-Ersatz

**Implementierter Entwicklungsstand, nicht auf echten Cloudhosts qualifiziert.**
Werftkern Kubernetes 0.1.0-dev.3 verwendet k0s/k0sctl. Native Runtime 0.2.0-dev.4
bleibt getrennt. Alle folgenden Operationen können nach ausdrücklicher Freigabe
reale Server dauerhaft löschen und kostenpflichtigen Ersatz erzeugen.

## Controller: genau ein Ausfall im Drei-Controller-Profil

`controller-replace` unterstützt ausschließlich reine, verwaltete Hetzner-Controller
in einem vorhandenen Drei-Controller-Cluster. Zwei Überlebende müssen direkt über TLS
Cluster-UID, Version und identische etcd-Peers bestätigen. Bei Quorumverlust wird kein
Member entfernt; weder `force-new-cluster` noch automatische Neuinitialisierung existieren.

Ablauf: genaue Planbestätigung → Wartungssperre → verschlüsseltes Backup von einem
Überlebenden → Kontrollobjekt-UID binden → Providerlöschung → zwei getrennte bestätigte
Abwesenheitsbeobachtungen → UID-gebundene ControlNode-Entfernung → `k0s etcd leave`
auf einem Überlebenden → Memberabwesenheit auf beiden Überlebenden → frische VM →
hostkeygeprüfter Bootstrap → k0sctl-Reconciliation → drei direkt geprüfte Controller
und drei erwartete etcd-Peers → Inventarcommit → Entsperren.

Ein verlorenes `etcd leave`-Ergebnis wird beobachtet, nicht erneut gesendet. Ist der
alte Peer weiterhin sichtbar, blockiert der Vorgang. Bei verlorenem Provider-DELETE
wird ebenfalls nicht blind wiederholt. Ein vor dem Senden persistierter Intent kann
nach einem Absturz absichtlich manuelle Prüfung erfordern. Sicherheit geht vor Liveness.

```bash
werft-kube plan controller-replace.json
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /etc/werftkern/kubernetes/lab/assets.json \
  controller-replace --spec controller-replace.json \
  --token-file /etc/werftkern/kubernetes/lab/provider-token --confirm EXAKTER_PLAN_SHA256
```

Denselben bestätigten Auftrag wiederholen, bis er abgeschlossen ist oder begründet
blockiert. Ein abgeschlossenes Journal liefert nur einen historischen Beleg, keine
neue Gesundheitsaussage. Der automatische Watcher übernimmt die Wiederholung nach
expliziter Policy-Freigabe. Kombinierte Controller/Worker und fremde Controller sind
nicht zugelassen. SSH-/API-Identitätsfehler werden nicht als Maschinenversagen gewertet.

## Stateful: vorhandene Datenträger behalten, nicht Datenbanken neu erfinden

`stateful-replace` ist bewusst ein enges Profil: explizit eingeschriebene StatefulSets
mit genau einer Replica, `csi.hetzner.cloud`, gebundene RWO/RWOP-PVCs, Filesystem-Volumes,
ReclaimPolicy `Retain`, eindeutige Claim-/PV-/Provideridentitäten und gleicher Standort.
Die PVs benötigen `werftkern.io/recovery-cluster-uid`; Provider-Volumes brauchen die
Labels `werftkern-cluster` und `werftkern-pv-uid`. Das StatefulSet trägt
`werftkern.io/recovery-profile=hetzner-csi-single-writer`. Werftkern setzt diese
sicherheitsrelevanten Einschreibungen nicht ungefragt auf fremde Bestandsressourcen.
Mehrere Pods dürfen sich keinen der eingeschriebenen Single-Writer-PVCs teilen.

Vor Freigabe muss im Clusterplan stehen:

```json
"storageRecovery": {"disableForceDetachOnTimeout": true}
```

Diese Änderung separat mit dem normalen Plan-/Apply-Pfad ausrollen. Werftkern prüft
zusätzlich auf jedem Controller die **laufenden** kube-controller-manager-Argumente
via hostkeygeprüftem SSH. Nur die gewünschte Konfiguration einzutragen genügt nicht.
Mit fehlender oder abgeschalteter Timeout-Sperre erfolgt keine automatische Reparatur.

Ablauf: Inventar und Benutzerfreigabe → Cordon → VM-Fencing → neue VM bereitstellen
und beitreten lassen → Abwesenheit des alten Hosts erneut prüfen → erst dann
`node.kubernetes.io/out-of-service:NoExecute` → CSI-Detach und alte Podentfernung
beobachten → UID-gebundene Nodeentfernung → unveränderte PV/PVC-/Volumeidentitäten,
neuen Pod-Owner, Ready-Status und tatsächliche neue VolumeAttachment/Providerzuordnung
prüfen → Inventarcommit. CSI-Finalizer werden nicht erzwungen entfernt. Fehlende
Datenträger werden nicht als leere Ersatzdatenträger neu angelegt.

```bash
werft-kube plan stateful-replace.json
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /etc/werftkern/kubernetes/lab/assets.json \
  stateful-replace --spec stateful-replace.json \
  --token-file /etc/werftkern/kubernetes/lab/provider-token --confirm EXAKTER_PLAN_SHA256
```

**Keine Zusage:** allgemeine Datenbank-HA, Datenkonsistenz, PITR, Zero-Downtime,
RPO/RTO, Multicloud-Fencing oder fremde Storage-Treiber. Eine Ready-Anwendung ist kein
SQL-Integritätsnachweis. Providerbestätigte Löschung ist eine konkrete Vertrauensgrenze,
kein physischer Beweis unabhängig vom Provider. Administratoraktionen außerhalb des
Managers können seine Invarianten verletzen. Tokenwechsel während laufender destruktiver
Operationen wird ausdrücklich blockiert: ein 404 unter einem anderen Projekt ist
kein Fencingnachweis. Schlüsselrohwerte werden nicht ins Journal geschrieben.

## Unbeaufsichtigte Wiederholung nach vorab freigegebener Policy

```bash
werft-kube plan recovery-policy.json
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /etc/werftkern/kubernetes/lab/assets.json \
  recovery-watch once --policy recovery-policy.json \
  --token-file /etc/werftkern/kubernetes/lab/provider-token
```

`watch` statt `once` führt die Schleife mit 30 Sekunden Abstand aus. Das ist ein
lokaler Dienst, keine Chat-Aufgabe. `enabled` und `acceptDeleteAndCosts` müssen beide
explizit gesetzt sein; ausgelieferte Beispiele bleiben deaktiviert. Die optionale
Unit `werftkern-kube-recovery@.service` wird vom Paket niemals automatisch gestartet.

Persistente Beobachtungen, Mindestdauer (mindestens 300 Sekunden), Mindestanzahl,
Mindestkapazität, Ausfallquote, Cooldown und tägliches Startlimit begrenzen die Aktionen.
Identitätswechsel und Beobachtungslücken setzen das Ausfallfenster zurück. Der
`maxAdditionalMonthlyEUR`-Wert begrenzt die Summe der **monatlichen VM-Preisobergrenzen
für die in den letzten 24 Stunden begonnenen Ersatzvorgänge**. Er ist kein globales
Rechnungslimit und umfasst nicht bestehende Volumes, Traffic, Steuernänderungen oder
andere Kontonutzung. Unklare Vorgänge erhalten keine automatische Budgetrückerstattung.

## Vorhandene Operationen / Upgrade von dev.2

Die Journale binden jetzt den Providerzugang. Unfertige alte Lösch-/Create-Vorgänge
ohne diese Bindung verlangen manuelle Prüfung; niemals den Fingerprint nachträglich
blind eintragen. Koordinierte Wartung: laufende Operationen abschließen/prüfen, beide
Watcher anhalten, private Zustandsdateien sichern, Paket aktualisieren, Plan/Assets
prüfen, anschließend nur ausdrücklich freigegebene Dienste starten. Kein Live-Upgrade-
Nachweis wurde hier erbracht.

Belegte Fehlerkorrekturen: Cloud-Scale-Replay nach Inventarcommit; ein zweiter Scale-
Auftrag darf nicht den alten Abschluss zurückgeben; Cleanup bleibt unter Prozesslock;
Control-Plane-Restore-Replay erkennt seinen eigenen Commit; geänderte Cloudcredentials
autorisieren keine Abwesenheitsannahme. API-/Cloud-Vertragstests, keine echten Provideraktionen.

## Primärquellen

- k0s Controller Removal: https://docs.k0sproject.io/stable/remove_controller/
- Kubernetes Node Shutdowns: https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/
- k0s-Konfiguration: https://docs.k0sproject.io/stable/configuration/

Geprüft am 26.09.2026. Quellen beschreiben Komponentenverträge, nicht eine Werftkern-Freigabe.
