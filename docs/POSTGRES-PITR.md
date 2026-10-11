# PostgreSQL Point-in-Time-Recovery — dev.3

**Ausführbarer pgBackRest-Adapter, reale WAL-Recovery hier noch nicht nachgewiesen.**
PostgreSQL17 und ein geprüftes pgBackRest2.59.1+ sind Voraussetzungen, keine automatisch
installierten Abhängigkeiten. Datei-Restore, WAL-Replay und Anwendungsfreigabe sind
getrennte Zustände. Dieser Adapter führt keine Promotion aus.

## Repository und Konfiguration

Befehle für Datenbankaktionen als OS-Benutzer `postgres` ausführen. Private Dateien und
leeres Includeverzeichnis gehören diesem Benutzer; Modus 0600 bzw. 0700. Ein zufälliges
Repositorygeheimnis wird separat sicher verwahrt; niemals Passwörter in CLI-Argumente,
Logs, Source oder Evidence schreiben. Das verschlüsselte POSIX-Repository benötigt
unabhängig gesicherten/off-host Speicher, Kapazität und getestete Dateisystemsemantik.
Es ist kein automatisch erzeugtes S3-/Multi-Node-Storagebackend.

`examples/pitr.plan.json` zeigt die sechs exakt zulässigen Felder. Das Datenverzeichnis,
Unixsocket und der Port müssen zur tatsächlichen Quellinstanz passen.

```sh
sudo -u postgres werft-ops pitr prepare --plan /path/pitr.plan.json \
  --cipher-file /private/pgbackrest-cipher --out /private/pgbackrest.conf
```

Der Adapter erzeugt eine private INI-Datei und `/private/pgbackrest.conf.d` als leeres,
privates Includeverzeichnis. Zusätzliche Include-Konfigurationen und Umgebungsvariablen
können sonst Sicherheitsoptionen überschreiben: die Ausgabe wird kontrolliert validiert,
ambient PGBACKREST_*/PG*-Umgebungen werden für ausgeführte Befehle entfernt.
Die Vertrauensgrenze bleibt der administrative Besitzer von Konfiguration und Repository.

Vor `initialize` müssen WAL-Archivierung (`archive_mode=on`) und ein passendes,
festes `archive_command` auf den Datenbankhosts vorbereitet sein. Ein solches Kommando
verwendet dieselbe Konfiguration, dasselbe Includeverzeichnis und dieselbe Stanza mit
`pgbackrest ... archive-push %p`. Bei Patroni ist die Änderung im dynamischen DCS-Profil
und auf allen potenziellen Primaries zu koordinieren; Bootstrap-YAML allein reicht
nach der Erstinitialisierung nicht. systemd-ReadWritePaths, Lockpfade und Dateirechte
müssen die vorgesehenen Pfade erlauben. Kein automatischer Neustart einer Produktiv-DB.

```sh
sudo -u postgres werft-ops pitr initialize \
  --config /private/pgbackrest.conf --stanza shop
sudo -u postgres werft-ops pitr backup \
  --config /private/pgbackrest.conf --stanza shop --journal /private/full-backup.json
```

`initialize` führt stanza-create und eine tatsächliche Archivprüfung aus. Backup
verlangt genau ein neues, eindeutig zugeordnetes Backupset und schreibt dessen Label,
System-Identifier und Katalogfingerprint in ein Journal. Erster leerer Katalogstatus 2
ist nur VOR dem ersten Backup zulässig, niemals als gesunder Restore-Nachweis.
Ein unterbrochenes Backupjournal wird nicht durch einen unkontrollierten zweiten Lauf
überschrieben; Repositoryzustand zunächst separat prüfen.

## Zeitgebundener Restore

Einzelner separater, isolierter Wiederherstellungshost ohne Zugriff auf produktive
Daten-/Tablespacepfade. Das ursprüngliche PGDATA darf dort nicht existieren. Leeres neues
Ziel, neuer Journalpfad außerhalb von Daten und Repository. Gleiche PG-Hauptversion,
explizites Backup-Label, erwarteter Datenbank-System-Identifier und Zielzeit mit Zeitzone.
Verwende Werte aus dem tatsächlichen Backup, keine erfundenen Labels/IDs.

```sh
sudo -u postgres werft-ops pitr restore \
  --config /private/pgbackrest.conf --stanza shop \
  --label ACTUAL_BACKUP_LABEL --system-id ACTUAL_SYSTEM_ID \
  --time ACTUAL_ISO_TIMESTAMP_WITH_TIMEZONE \
  --target /var/lib/postgresql/recovery-check \
  --journal /private/restore-check.json \
  --confirm shop:/var/lib/postgresql/recovery-check
```

Schutz: kein --force, kein --delta, kein Restore über Quelldaten. Explizites Set,
`target-action=pause`, `archive-mode=off`, `hot_standby=on`, keine aktive Primary-Verbindung
und Tablespace-Mapping in einen neuen Zielbaum. Bei Fehler bleiben Journal und
Teilziel für Untersuchung erhalten. Ein Wiederholungsaufruf überschreibt sie nicht.

**Tablespaces, die erst nach Backupbeginn erstellt wurden, werden laut pgBackRest
NICHT durch tablespace-map-all umgebogen.** Das erklärt die Pflicht zur isolierten
Wiederherstellungsumgebung. Das CLI kann keine VM-/Mount-Namespace-Isolation aus der
bloßen Abwesenheit eines Pfades beweisen. Es darf nicht auf der Produktionsmaschine
oder mit gemounteten Original-Tablespaces ausgeführt werden.

Nach `files-restored-wal-replay-required` PostgreSQL noch NICHT produktiv starten.
Ein qualifizierter Operator prüft Konfiguration, Includes, Preload-Libraries, SSLpfade,
Tablespaces, Archivquelle und Netzisolation. Dann isoliert mit Unixsocket und deaktiviertem
TCP-Listener starten. Der Adapter startet keinen Server aus möglicherweise alten
Backup-Konfigurationen.

```sh
sudo -u postgres werft-ops pitr verify-replay \
  --journal /private/restore-check.json --socket /isolated/socket --port 55432
```

Die SQL-Prüfung verlangt richtiges data_directory und System-Identifier, Recovery-Modus,
wirklich pausiertes Replay, richtige Zielzeit, target_action=pause und archive_mode=off.
Ergebnis `replay-paused-application-validation-required` bedeutet NICHT fachlich korrekte
Daten oder abgeschlossene Migration. Fachprüfung, Quell-Fencing, Freigabe, kontrollierte
Promotion und Verkehrsumstellung folgen außerhalb dieses Adapters.

## Ausführbarer Realtest

`tests/integration/real_pitr.py` verwendet echte postgres-/initdb-/psql-/pgBackRest-
Prozesse. Auf einem ausschließlich dafür bereitgestellten Host als postgres:

```sh
WERFT_DISPOSABLE_VM=1 python3 tests/integration/real_pitr.py \
  --evidence /writable/private/real-pitr.json
```

Er schreibt vor/nach einer Zielzeit zwei Transaktionen, sichert und archiviert WAL,
restauriert ein neues Verzeichnis, prüft echten pausierten Replay sowie den exakt
erwarteten Transaktionsbestand und verweigerte Schreibzugriffe. Keine Testdoubles.
Alles synthetisch und auf EINEM Host, kein Patroni-/Cross-Host-DR-/Watchdognachweis.
Fehlende Abhängigkeiten: BLOCKED/Exit3, niemals Skip/Pass. Hier blockiert.

Primärquelle (25.09.2026): https://pgbackrest.org/command.html
Insbesondere restore, target-action, tablespace-map-all, config-include-path.
