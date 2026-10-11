# PostgreSQL-HA-Profil — dev.3

**Implementierter Integrationspfad, nicht produktionsqualifiziert.** PostgreSQL 17,
Patroni 4 und ein eigener etcd-3.6+-Verbund laufen als native systemd-Dienste auf drei
DEDIZIERTEN Datenbankhosts. Das ist nicht das bestehende Single-Primary-Dockerprofil.
Werftkern plant diese Postgres-Prozesse nicht als beliebig verschiebbare Allocations.
Replikation/Primary-Wahl übernimmt Patroni, kein neu geschriebener Konsensalgorithmus.
Die angegebenen Versionen sind Kompatibilitätsziele, keine freigegebene Paketmatrix.

## Verträge

Das erzeugte Profil verlangt synchronous_mode und synchronous_mode_strict, einen
synchronen Standby, Timeline-Prüfung, maximale Failover-Lag 0 und keine DCS-Failsafe-
Fortsetzung. Fehlende synchrone Kapazität darf Schreibverfügbarkeit kosten. Das ist
KEINE bedingungslose Null-Datenverlust-Zusage: Sessioneinstellungen, unbestätigte
Transaktionen, gleichzeitige Ausfälle und reale Hardware müssen separat geprüft werden.

`watchdog.mode=required`, `safety_margin=-1`, Gerät `/dev/watchdog`.
**Ein echter Watchdog kann den gesamten Host neu starten.** Installation verlangt die
explizite Bestätigung dieses Effekts. Kein automatisches Laden von softdog, kein
simulierter Watchdog und kein Ausschalten dieser Kontrolle bei Installationsproblemen.
Ein verfügbares Gerät beweist noch nicht seine Wirkung bei VM-Pause/Kernelstillstand;
ein entsprechender Fehler-/Resetnachweis ist vor jeder Produktionsfreigabe Pflicht.

Separate Datenbank- und DCS-CAs; Server- und Client-mTLS. CA-Schlüssel bleiben im
privaten `authority/`-Verzeichnis der Erstellungsstation, nicht in den Hostkits.
Blattzertifikate gelten 90 Tage. Ihre Erneuerung und die CA-Rotation der Datenbank sind
noch kein automatisierter Lifecycle. Runtime-Leaf-Erneuerung in CERTIFICATE-ROTATION.md
ändert diese Datenbankzertifikate nicht.

## Vorbereitung

Frische Ubuntu-24.04-amd64-Hosts mit statischen RFC1918-Adressen und geprüftem privaten
Netz verwenden. PostgreSQL17 unter `/usr/lib/postgresql/17/bin`, Patroni4 unter
`/usr/bin/patroni`, etcd unter `/usr/bin/etcd`, OpenSSL, Benutzer postgres/etcd sowie
ein postgres-eigenes und schreibbares Watchdog-Gerät müssen bereits kontrolliert
bereitgestellt sein. Der Adapter fügt KEINE Paketquellen hinzu.

Plan siehe `examples/database-ha.plan.json`. Adressen und Client-CIDR sind Beispiele,
keine bereits vorhandene Infrastruktur. Auf vertrauenswürdiger Erstellungsstation:

```sh
werft-ops database-ha prepare --plan database-ha.plan.json --out /root/private-db-kits
```

Das Ziel muss neu sein. Private Hostkits enthalten Datenbankpasswörter und Schlüssel.
Nur das Kit des jeweiligen Hosts per hostkeygeprüftem Transport übertragen, niemals
`authority/`, Chat-Upload, öffentliche CI-Artefakte oder Git verwenden.

Auf jedem der drei passenden Hosts, mit dessen tatsächlichem Namen:

```sh
sudo werft-ops database-ha install --kit /root/db-one \
  --confirm-host db-one --accept-watchdog-reset
```

Installation legt ein Intentjournal an, validiert das Patroni-Profil und startet die
Dienste. Ein zweiter Installationsversuch auf vorhandenen/teilweise installierten
Verzeichnissen wird NICHT durch Löschen oder einen neuen leeren Bootstrap repariert.
Status nach Start: `services-started-health-unverified`. Dieser Status ist keine HA-Abnahme.

Hostpfade: `/etc/werftkern-database/NAME`, `/var/lib/werftkern-database/NAME`.
Dienste: `werft-db-NAME-etcd.service`, `werft-db-NAME-patroni.service`.
Port 23901/TCP (DCS), 23902/TCP (Peer) und 8008/TCP (Patroni-mTLS) nur zwischen den drei
DB-Hosts. 5432/TCP nur erlaubte Clients/Replikation, Hostfirewall separat prüfen.
Es wird kein öffentlicher DB-Endpunkt oder automatischer Primary-VIP erstellt.

## Inspektion und geplante Umschaltung

Auf einem zugelassenen DB-Host mit dessen geprüfter mTLS-Identität:

```sh
sudo -u postgres werft-ops database-ha inspect \
  --plan /path/readable/database-ha.plan.json \
  --ca /etc/werftkern-database/shop/patroni/db-ca.crt \
  --cert /etc/werftkern-database/shop/patroni/node.crt \
  --key /etc/werftkern-database/shop/patroni/node.key
```

Prüft drei beobachtete Member, Scope/Name, denselben System-Identifier, genau einen
Primary mit aktuellem DCS-Lock, DCS-Frische und restriktive dynamische Sync-Konfiguration.
Die Beobachtung ist keine atomare globale Momentaufnahme oder ein Watchdogtest.
`bootstrap.dcs` allein setzt spätere DCS-Einstellungen NICHT erneut; Policy-Drift wird
bei Inspektion abgewiesen und muss kontrolliert korrigiert werden.

`database-ha switchover` verwendet dieselben vier Verbindungsargumente, zusätzlich
`--target db-two --journal /private/operation.json --confirm shop:db-two`.
Nur ein beobachteter synchroner Standby ist erlaubt. Nach einer verlorenen POST-Antwort
wird NICHT blind erneut gesendet. Wiederholung desselben Journals prüft den tatsächlich
neuen Primary. Keine erzwungene Failover-/Promotion-Option vorhanden.

## Backup-Anbindung und Grenzen

Siehe POSTGRES-PITR.md. WAL-Archivierung und Repositorypfade müssen auf ALLEN möglichen
Primaries vorbereitet sein. Das strikte systemd-Dateisystemprofil gewährt einem externen
pgBackRest-Repository/Lockpfad nicht automatisch Schreibrechte. Ein geprüftes Drop-in
mit eng begrenzten ReadWritePaths und gemeinsamer Lock-Semantik ist erforderlich; nicht
ProtectSystem deaktivieren. Diese serviceübergreifende Anbindung wird nicht automatisch
als erledigt markiert. Das Repository muss einen eigenständig qualifizierten,
dauerhaften/off-host Storagepfad haben; ein lokales Verzeichnis allein ist kein DR.

Offen: echte Drei-VM-Failover-/Split-Brain-/Watchdogtests, DB-Zertifikatsrotation,
Replikat-Rebuild, koordinierte Major-Upgrades, Primary-Clientrouting, Schutz gegen
Anwendungs-Session-Overrides, Datenbank-Servicecontroller im Werftkern-Wizard und
Standort-DR. Keine RPO-/RTO- oder SLA-Freigabe.

Primärquellen (25.09.2026):
- https://patroni.readthedocs.io/en/latest/watchdog.html
- https://patroni.readthedocs.io/en/latest/replication_modes.html
- https://patroni.readthedocs.io/en/latest/yaml_configuration.html
- https://patroni.readthedocs.io/en/latest/rest_api.html
