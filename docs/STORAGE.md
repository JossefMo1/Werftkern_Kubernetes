# Persistente Volumes und PostgreSQL

## Tatsächlicher Umfang

Nodegebundene Verzeichnisse, keine replizierten Blockgeräte und kein CSI-Treiber.
Ein Volume wird nur einem Workload zugeordnet, ist auf einen Node fixiert und darf
maximal eine Replik haben. Änderungen verwenden Stop → bestätigtes Stopped → Start,
nicht Surge. Das verursacht bewusst Unterbrechungen. Bei unerreichbarem altem Writer
bleibt die Wiederbereitstellung gesperrt; eine Lease ist kein physisches Fencing.

```sh
sudo werft status --json
sudo werft volume create pgdata --node NODE_ID --uid 999 --gid 999
# Passwortdatei selbst erzeugen, Modus 0600, nicht in Git ablegen:
sudo werft secret put postgres-password --file /root/pg-password
sudo werft database manifest postgres --image IMAGE_AT_SHA256_DIGEST \
  --node NODE_ID --volume pgdata --uid 999 > /root/postgres.json
sudo werft apply /root/postgres.json
sudo werft wait postgres
```

`IMAGE_AT_SHA256_DIGEST` und `NODE_ID` müssen durch tatsächlich geprüfte Werte ersetzt
werden. Das Image muss PostgreSQL17, den erwarteten Startvertrag und den gewählten
Nicht-root-UID/GID unterstützen; ein Digest allein prüft keine fachliche Eignung.
Die Anwendung nutzt den privaten Endpoint oder den CoreDNS-SRV-Eintrag.

Die Daten liegen unter `/var/lib/werftkern/volumes/VOLUME_ID/data`. Ein Identitätsmarker
bindet Verzeichnis, Cluster, Node und UID/GID. Nach der erstmaligen Bestätigung gilt
`Initialized=true`. Fehlt anschließend das Verzeichnis, wird **nicht** stillschweigend
eine leere Datenbank erstellt. Stop/Delete des Containers löscht diese Daten nicht.
Ein bereits referenziertes Volume kann nicht freigegeben werden. Bewusste Freigabe
nach Entfernen aller Referenzen: `werft volume release NAME --id VOLUME_ID`.
Die Freigabe löscht ebenfalls keine Daten. Es existiert absichtlich kein Remote-Wipe.

Keine Speicherquota, Snapshotreplikation, automatisches Filesystem-Resize, Datenbank-
Primary-Wahl, PITR oder Host-Fencing. Der Datenbank-Readinesscheck verwendet `pg_isready`;
das ist keine Probe fachlicher SQL-Transaktionen und kein Integritätsaudit.

## Logischer Backup-/Restorepfad

`werft-ops postgres` benötigt die verifizierten PostgreSQL-Clientprogramme ab17.
Unterstützte Transportprofile: `loopback` (gegebenenfalls durch geprüften SSH-Tunnel),
`wireguard` (tatsächliche Route muss über wgwerft gehen) oder `tls` mit eigener CA und
verify-full. Keine Klartextpasswörter in Kommandozeile oder Reports. Passfile und
Verbindungs-JSON müssen private, eigene Dateien sein. Beispielkonfiguration:

```json
{"host":"127.0.0.1","port":22000,"user":"postgres","database":"app","transport":"loopback"}
```

```sh
sudo werft-ops postgres backup --config /root/source-db.json \
  --passfile /root/pgpass --archive /root/backups/app.dump
sudo werft-ops postgres restore --config /root/isolated-target-db.json \
  --passfile /root/pgpass --archive /root/backups/app.dump --confirm-database restored_app
```

Das Ziel muss als neue, leere, von Anwendungen isolierte Datenbank existieren. Source
und Target dürfen nicht identisch sein. Der Restore prüft Hash und eine leere Relation-
inventur und führt `pg_restore --single-transaction --exit-on-error --no-owner --no-acl`
aus. Das ist kein vollständiger Beweis, dass das Ziel frei von jedem benutzerdefinierten
Objekt ist; nur neue, eigene Zieldatenbanken verwenden. Archive aus fremden, nicht
vertrauenswürdigen Quellen können beim SQL-Restore Code ausführen: vorher prüfen.

Backup enthält eine Datenbank, nicht Rollen, Tablespaces, mehrere atomar koordinierte
Datenbanken, WAL-Historie oder Plattform-PKI. Dumps sind sensible **unverschlüsselte**
Dateien mit Modus0600; für Offsite-Storage separat verschlüsseln. SHA-256 erkennt lokale
Änderungen, authentisiert aber keinen externen Backup-Ersteller. Ein kopiertes Dump samt
geändertem Hash ist keine vertrauenswürdige Wiederherstellung. Nach SQL-Restore sind
fachliche Lese-/Schreibprüfungen und ein kontrollierter Traffic-Cutover erforderlich.
Die lokalen Tests verwenden Befehlsadapter; hier wurde kein echter PostgreSQL-Server
gebootet, gesichert oder restauriert.

## Offline-Archiv tatsächlicher Volumedaten

Dev.2 ergänzt `werft volume backup`/`restore`: VOLUME-BACKUP.md. Pending Restore
blockiert Wiederanlauf; vorhandene Daten werden nie überschrieben. Keine Live-Snapshots,
Datenbank-HA oder PITR. Für den PostgreSQL-Dateirestore ist sauberes Stoppen Voraussetzung.
