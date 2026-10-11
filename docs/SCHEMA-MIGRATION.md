# Offline-Schemamigration dev.1 → dev.2

**Explizite Labor-Migration; noch kein qualifizierter Multi-Host-Upgradepfad.**
Dev.2 verlangt State-Schema2 und genau passende Agentversion mit Heartbeatsequenz. Dev.1
verwendet Schema1 und erfüllt diese neuen Sicherheitsverträge nicht. Derselbe etcd-Key
bleibt absichtlich erhalten: `/werftkern/runtime/v1/state`; `v1` im Pfad bezeichnet nicht
den aktuell gespeicherten Schemainhalt. Keine automatische neue leere Datenbank.

## Voraussetzungen und Reihenfolge

Ein neues isoliertes Testcluster ist der bevorzugte Einstieg. Bestehende Installation nur
nach geprüftem Recoveryplan migrieren. PKI, Vault-Masterkey, Agentkonfigurationen/Journale,
etcd-Snapshot und Anwendungsdaten separat sichern. Einen Snapshot-Restore auf neuen Hosts
kann diese einzelne Schemamigration nicht ersetzen.

Mit **altem** CLI alle Anwendungen pausieren und Stopbestätigungen abwarten. Status muss
keine Allocations mehr enthalten, alle Workloads müssen pausiert sein. Erst danach mit
altem CLI Maintenance halten:

```sh
sudo werft pause APPLICATION_NAME
sudo werft status --json
sudo werft maintenance on --id MAINTENANCE_ID --reason offline-schema-migration
```

Dann **auf allen Hosts** Controller, Agents, Discovery, Ingress, Updateautomatisierung und
sonstige API-Schreiber anhalten; etcd läuft weiter. Kein bloßer Leaderstopp. Wartungs-ID ist
eine echte32-Hex-ID und wird nicht zwischen den Schritten gewechselt. Noch keine neue Binary
in einem automatisch neu startenden Dienst aktivieren.

Neue Binary zunächst nur extrahieren/stagen, nicht die laufende Installation überschreiben:

```sh
dpkg-deb -x werftkern_0.2.0~dev2_amd64.deb ./staged-dev2
sudo ./staged-dev2/usr/bin/werft schema inspect --maintenance-id MAINTENANCE_ID
```

`sourceSha256` aus Inspect exakt verwenden. Lokale Controller-/etcd-TLS-Konfiguration muss
lesbar sein. Schlüssel-/Backup-Elternverzeichnisse vorher privat anlegen.

```sh
sudo ./staged-dev2/usr/bin/werft schema migrate \
  --maintenance-id MAINTENANCE_ID --source-sha256 SOURCE_SHA256 \
  --backup /root/migration/schema1.backup --key-file /root/backup-keys/schema.key
```

Vor Änderung schreibt und fsync't das CLI die **exakten Quellebytes verschlüsselt**, dann
erfolgt ein einzelnes erwartete-Revision-CAS. Fremder Schreiber, abweichender Hash, ungepause
Anwendung, vorhandene Allocation oder Backupfehler blockiert. Bei verlorenem ACK erkennt
ein identischer Folgeaufruf die bereits gespeicherte `migrationSourceHash`. Ein vorhandenes
Backup nach fehlgeschlagenem CAS wird nicht überschrieben; Zustand neu prüfen und ggf.
anderen neuen Backupdateinamen nutzen. Maintenance bleibt aktiv.

Erst danach alle Controller und Agents koordiniert mit dev.2 installieren/starten und
Status prüfen. Maintenance gezielt freigeben, Anwendungen einzeln fortsetzen und echte
Anwendungs-/Datenintegrität prüfen. Kein N/N−1-Rolling-Skew-Support; keinerlei Annahme, dass
ein Versionsmix sicher läuft. Hostpakete, etcd-Mitglieder und Vaultkeys werden vom Befehl
nicht automatisch geändert.

## Recovery und Grenzen

Schema2 kann nicht mit der alten dev.1-Binary betrieben werden. Nicht `schema:1` manuell
zurückschreiben; neue Sicherheitsfelder würden verloren gehen. Ein Rückweg benötigt ein
geprüftes offline etcd-/Konfigurations-/Daten-Restoreverfahren einschließlich Schutz gegen
Altwriter. Das neue Schemaquellbackup ist Format `werftkern-schema-source/v1`, nicht das
normale Konfigurationsbackup und kein automatischer Undo-Befehl.

Logische dev.1-Konfigurationsbackups werden vom neuen Standardimport nicht stillschweigend
konvertiert. Alten Snapshot isoliert mit passender Version lesen und Migration ausdrücklich
planen. Neue dev.2-Konfigurationsbackups benötigen Schema2. Historische Logs bleiben lesbar.

Tests belegen Hashbindung, Pflichtbackup, Konflikt, Replay und Ablehnung aktiver Workloads
gegen Speicherfixtures. Echte etcd-/Ubuntu-/Mehrhostmigration und Rückwiederherstellung sind
noch nicht erfolgreich ausgeführt. Den Standard-Hostupdatebefehl nicht für Schema1→2 nutzen.
