# Automatischer Node-Ersatz: Grenzen und Betrieb

Das neue Repair-Verfahren betrifft ausschließlich dedizierte **zustandslose
Hetzner-Kubernetes-Worker** mit lokal gespeicherter Provider-ID und verifizierten
Eigentumslabels. Es läuft nicht im Native-Scheduler und ist nicht für Controller,
PostgreSQL-/Keycloak-Datenbankhosts oder beliebige verlorene PV-Nodes freigegeben.
Es ist im Beispiel standardmäßig deaktiviert.

## Ablauf

1. Erreichbare, gesunde Kubernetes-API und dieselbe Clusteridentität prüfen.
2. Wiederholte NotReady-Beobachtungen über mindestens 300 Sekunden. Stichproben
   liegen mindestens 30 Sekunden auseinander. Lücken und Identitätswechsel setzen
   die Beobachtung zurück; rückwärts laufende Uhr blockiert das Budget.
3. Mehrheits-/Mindestkapazität, tägliches Ersatzlimit, Cooldown und Wartungssperren
   prüfen. MaxUnhealthyPercent bleibt unter 50 %. Keine Massenlöschung bei Netzausfall.
4. Eindeutige Node-UID, Server-ID, Name, Pool und Providerlabels prüfen, cordonieren.
   Unbekannte/Stateful-Owner, PVC, hostPath, emptyDir und ephemere Datenvolumes blockieren.
   VolumeAttachments sowie vorhandene lokale PVs blockieren ebenfalls konservativ.
5. Aktuelle Providerpreise gegen freigegebene Kostenobergrenze prüfen. Die alte VM
   durch einen einmalig protokollierten DELETE entfernen. Ein unbekanntes Ergebnis
   wird beobachtet, **nicht** durch blinde weitere Löschungen ersetzt.
6. Erst nach eindeutigem Provider-404 der exakten Server-ID den alten Kubernetes-Node
   mit UID-Precondition entfernen. Ein bloß ausgeschalteter Server genügt nicht.
7. Neue VM mit Operationslabels, eigenem vorab erzeugtem Ed25519-SSH-Hostkey und
   bestehender privater Netz-/Firewall-/Benutzerkey-Konfiguration erzeugen. Der
   Provider erhält das Hostkeymaterial über seinen cloud-init-Kanal. Dieser Kanal
   und Providerkonto sind ausdrücklich Teil des Vertrauensbereichs.
8. Mehrdeutige Create-Antwort: nur exakt passende eigene Ressource übernehmen;
   fehlt sie noch, warten/prüfen statt erneut kostenpflichtig anlegen.
9. Über fest geprüften SSH-Hostkey k0s installieren/joinen. Neuer Node muss andere UID,
   erwartete Version, Labels, Private-IP und Ready-Zustand besitzen. Inventar atomar
   aktualisieren, Operationsnachweis sichern, Sperre aufheben.

**Wichtig:** Kubernetes selbst kann Pods bereits vor diesem VM-Verfahren verlagern.
Das Warten auf Providerlöschung garantiert nur die Reihenfolge dieser VM-Mutation,
keine Exactly-once-Ausführung aller Anwendungen und kein Storage-Fencing. Auch bei
zustandslosen Diensten müssen externe Nebenwirkungen idempotent sein. Pod-Inventur
ist eine Momentaufnahme; Betreiber müssen verhindern, dass zwischen Prüfung und
Löschung neue Daten-Workloads manuell auf dem gesperrten Node gestartet werden.
Kube-system-DaemonSets sind als vertraute Plattformdienste ausgenommen. Allgemeine
bösartige Multi-Tenancy wird dadurch nicht abgesichert.

## Voraussetzungen und Kosten

`repair.enabled=true` ist nur gemeinsam mit `acceptDeleteAndCosts=true`, expliziter
VM-Vorlage und Limits zulässig. Das ist die Betreiberfreigabe zur **irreversiblen
Löschung und kostenpflichtigen Neuanlage**, keine bloße Anzeigeoption. Controller,
Datenhosts und fremde Server dürfen diese Workerlabels nicht erhalten. Beispielwerte
sind nicht als freigegebene Providerobjekte zu verwenden.

Vorhanden sein müssen private Hetzner-Netze/Subnetze, Firewall und Benutzer-SSH-Key.
Neue VMs erhalten **keine öffentliche IP**. Private Erreichbarkeit vom Manager und
NAT-/Image-/Paketegress sind erforderlich und werden nicht automatisch bereitgestellt.
Die Preisprüfung betrachtet den ausgewählten Server-/Standort-Monatspreis aus der
Providerantwort. Nicht berücksichtigt sind Kontosteuern außerhalb dieser Angabe,
zusätzliche Storage-/Netz-/Backupressourcen und sämtliche bereits laufenden Flottenkosten.
`maxPerDay` und Cooldown begrenzen neue Reparaturoperationen; ein angefangener Auftrag
behält dieselbe Identität. Keine Geld-zurück- oder Obergrenzengarantie des Providers.

```bash
werft-kube --root /var/lib/werftkern/kubernetes/lab --assets /etc/werftkern/kubernetes/lab/assets.json \
  repair once --token-file /etc/werftkern/kubernetes/lab/provider-token
```

Erst nach echten Wegwerf-Cluster-Fehlertests den installierten systemd-Dienst explizit
aktivieren. Die Paketinstallation selbst aktiviert ihn nicht:

```bash
sudo systemctl enable --now werftkern-kube-repair@lab.service
sudo journalctl -u werftkern-kube-repair@lab.service
```

`watch` führt denselben persistenten Ablauf aus, nicht einen zweiten simplen
„NotReady -> create“-Pfad. Fehler bleiben sichtbar, nicht als Erfolg simuliert.
Nach einem unklaren DELETE kann der Auftrag absichtlich hängen, statt weitere
Mutationen auszulösen. Manuelle Recovery erfordert Provider-/Nodeidentitätsprüfung,
Journalsicherung und einen überprüften Änderungsplan; nicht einfach Journal löschen.

## Initiale Flotte

`provision --blueprint ... --confirm HASH --token-file ...` erstellt eine freigegebene
initiale Flotte mit denselben idempotenten Identitätsverträgen. Der gesamte geplante
Serverpreis wird vor der ersten Anlage gegen `maxFleetMonthlyEUR` geprüft. Vorhandene
fremde Ressourcen werden nicht übernommen. Ausgabe ist `fleet-plan.json` und eine
Liste der Controller-IP-Adressen. API-LB und DNS danach verifizieren, erst dann
`create` ausführen. Provisionierung ist nicht automatisch API-LB-, DNS- und vollständige
Plattformbereitstellung; Scale-up-VM-Automation über denselben initialen Blueprint
ist nicht unterstützt. Von Werftkern entfernte, aber nicht gelöschte VMs kosten weiter.
