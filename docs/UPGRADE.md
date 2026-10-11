# Update-Abschluss mit Laufzeitprüfung — dev.4

**Same-Schema-Controller-Hostupdater, keine vollständige Upgrade-Orchestrierung.**
`upgrade apply` und `upgrade recover` heben den clusterweiten Wartungs-Lock nicht mehr
nach einem bloßen Status-Read auf. Sie enden in `awaiting-runtime-qualification`.
Der vorherige voreilige Abschluss ist durch Regressionstests abgedeckt.

Signaturprüfung, Installationsjournal und Recoveryargumente: RECOVERY.md.
Vorher Quell-/Ziel-Version, Schema, Agentkompatibilität, Backups und verfügbares Quorum
kontrolliert festlegen. Docker/etcd/PostgreSQL werden vom Paketupdater nicht aktualisiert.
Keine autonome Wiederaufnahme von Datenmigrationen oder Ersatz unbestätigter Writer.

```sh
sudo werft health --all --json --expected-version 0.2.0-dev.4
sudo werft-ops upgrade finish \
  --journal /var/lib/werftkern/updates/ACTUAL_DIGEST/journal.json \
  --confirm-operation ACTUAL_OPERATION_ID
```

`health` kontaktiert jeden KONFIGURIERTEN Endpoint direkt. Ein alter/nicht erreichbarer
Controller kann nicht durch Failover auf einen anderen grünen Controller verborgen
werden. Das erkennt keinen absichtlich aus der Konfiguration weggelassenen Controller.
Eine unabhängige vollständige Topologie-/Quorumprüfung bleibt nötig.

`finish` prüft Paket/Binary/Services, Cluster-ID, Schema und Zielversion aller konfigurierten
Controller. Drei Beobachtungen im Abstand von sechs Sekunden verlangen aktuelle,
fortschreitende Heartbeats, bekannte gesunde Nodes, richtige Workload-UID/Generation/Spec,
passende Replikazahl und tatsächlich ready beobachtete aktive Allocations. Unbekannte
oder veraltete Ausführung blockiert den Abschluss. Pausierte Anwendungen dürfen keine
aktive Allocation haben. Dies ist Laufzeitvertragsprüfung, kein HTTP-/SQL-Geschäftstest.

Der Abschlussintent wird VOR dem Entsperren gespeichert. Geht nur die Antwort auf das
Entsperren verloren, prüft die Wiederholung Zustand/Gesundheit und bereits freien Lock,
ohne blind fremde Locks zu lösen. Ein neuer Lock eines anderen Vorgangs blockiert.
Bereits abgeschlossene Journale liefern nur einen historischen Beleg zurück, keine neue
Gesundheitszusage. Keine automatische ablaufende Wartungs-Lease.

## dev.2 nach dev.3

Beide Versionen nutzen StateSchema2. Der Agentvertrag verlangt dennoch eine EINHEITLICHE
Runtimeversion. **Kein N/N−1- oder ungeprüfter Rolling-Upgradepfad.** Für dev.2→dev.3 ist
koordinierte Offlinewartung aller Runtime-Controller/Agenten erforderlich. Neue Installation
auf isolierten Test-VMs ist die hier beschriebene Laborverwendung. Die gepackte dev.3 ist
unsigniert; sie erfüllt absichtlich NICHT die Signaturvoraussetzung einer Produktionsupdatekette.

Für diesen historischen Übergang weiterhin offen: Worker-Wellen, Canary-Strategie, automatischer Quorumnachweis, vollständige
Migrations-/Rückwegqualifikation, fachliche Anwendungsprobe und getrennte Datenbankupdates.

## dev.4: Worker getrennt koordinieren

[Worker-Updatewellen](WORKER-ROLLOUT.md) erlauben ausschließlich das explizite
Schema2-Protokollfenster dev.3 → dev.4, nachdem alle Controller bereits dev.4 betreiben.
Das ist keine beliebige Versionskompatibilität. Der bisherige hostbezogene Updater
orchestriert noch keine vollständige HA-Controllerwelle. Fehlerbelege/Lock dürfen nicht
entfernt werden, um ein Update zu erzwingen. Ein `.deb`-Dateiname genügt nie zur Freigabe.
