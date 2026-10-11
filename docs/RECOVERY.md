# Updates, Recovery und Datenerhalt

**Kein vollständiges Disaster-Recovery-Produkt.** Implementiert sind separat:
logisches, verschlüsseltes Runtime-Konfigurationsbackup; konservative Referenzzuordnung
auf ein neues Ziel; PostgreSQL-Dump/Restore; signierte Paketprüfung und ein begrenzter
Controller-Host-Update-/Recoveryablauf. Reale Upgrade-/Restorequalifikation fehlt.

## Konfiguration

```sh
sudo werft backup create --out /root/config.backup --key-file /root/offline-backup.key
sudo werft backup inspect --file /root/config.backup --key-file /root/offline-backup.key
# Nur gegen einen neuen, leeren Zielcluster:
sudo werft backup restore --file /root/config.backup --key-file /root/offline-backup.key \
  --target-cluster TARGET_CLUSTER_ID --mapping /root/restore-map.json
```

Ein Mapping enthält `nodes` (alteID → neueID) und `volumes` (alterName → neuerName).
Zielnodes und freie Zielvolumes müssen zuvor registriert sein. Eigentum wird neuen
Workload-UIDs zugewiesen. Historische Specs werden verworfen, damit Rollback nicht alte
Storagebezüge reaktiviert. Anwendungen bleiben pausiert. Kein alter Node, Allocation,
Zertifikat oder Containerzustand wird als neuer legitimer Writer ausgegeben.

Die Zuordnung restauriert **keine Datenbytes** und löst **kein Source-Fencing** aus.
Für Datenbankmigration: Source-Dump → Zielisolierung → neue Ziel-Datenbank bereitstellen →
SQL-Restore und fachlich prüfen → Traffic umschalten. PostgreSQL-Backupdetails: STORAGE.md.
Für kontrolliert offline gehaltene reguläre Volumedaten existiert jetzt der separate
physische Pfad in VOLUME-BACKUP.md. Er ersetzt weder Live-Snapshots noch Standort-DR.
Nur ein Konfigurationsbackup ist kein ausreichender Schutz produktiver Daten.

## Signierte Hostupdates

Das Release-Manifest (`werftkern-release/v1`) enthält Version, Debian-Paketversion,
SHA256, Schema2, erlaubte Quell-Paketversionen und amd64. Eine Ed25519-Signatur wird
über die **exakten Manifestbytes** geprüft. Der öffentliche Schlüssel wird vom Betreiber
separat als vertrauenswürdig installiert. Private Releasekeys gehören nie ins Repository.

```sh
werft release verify --manifest release.json --signature release.sig \
  --public-key /root/trusted-release-public.pem --package target.deb
sudo werft-ops upgrade apply --manifest release.json --signature release.sig \
  --public-key /root/trusted-release-public.pem --package target.deb --confirm-version VERSION
```

Die Operation schreibt ein lokales Journal, nimmt einen clusterweiten Wartungs-Lock,
erstellt ein logisches Konfigurationsbackup, stoppt nur die lokalen Runtime-Dienste,
installiert das Paket und prüft Status/Version. Der Lock bleibt danach bestehen;
`upgrade finish` in UPGRADE.md prüft die Laufzeit vor der Freigabe. Docker, etcd und
Datenbankdaten werden dabei nicht aktualisiert. Bestehende Prozesse werden nicht allein
wegen einer Managementwartung getötet. Neue Deployments/Bindings sind eingefroren.

Der Wartungs-Lock hat absichtlich keinen automatischen Timeout. Ein abgebrochener
Paketwechsel darf nicht durch einen gleichzeitigen zweiten Hostwechsel verschlimmert
werden. Journal und Lock-ID stehen lokal unter `/var/lib/werftkern/updates/DIGEST/`.
Bei Fehlschlag bleiben Daten und Freeze erhalten. Wiederherstellung mit explizit
signiertem Reparatur-/Rollbackpaket desselben Schemas:

```sh
sudo werft-ops upgrade recover --journal /var/lib/werftkern/updates/DIGEST/journal.json \
  --package repair.deb --manifest repair.json --signature repair.sig \
  --public-key /root/trusted-release-public.pem --confirm-operation OPERATION_ID
```

Das Verfahren gilt nur für Controllerhosts mit Admin-Konfiguration. Worker-Update-
Orchestrierung, Canary-Wellen, automatisch bewiesene verbleibende Quorumgesundheit,
Forward-only-Datenmigrationen und autonome Wiederaufnahme sämtlicher Crashpunkte sind
noch nicht fertig. Der Betreiber muss die anderen Controller vor jedem Wechsel prüfen.
Der zusätzliche finale Check umfasst Versionen, frische Heartbeats und Allocationzustände,
aber **kein** Anwendungs-E2E oder Datenbankrollback. Siehe UPGRADE.md.

Kompletter Standortverlust benötigt zusätzlich unabhängige PKI-/Keybackups, etcd-
Snapshots, Images, Vault-Masterkey und Anwendungsdaten mit geprobter Recovery. Dafür
existiert hier kein qualifiziertes Gesamt-RPO/RTO. Niemals einen leeren etcd-State
initialisieren, um verschwundene produktive Zustände zu übergehen.

## Schemawechsel

Dev.1→dev.2 erfordert die explizite Offline-Prozedur in SCHEMA-MIGRATION.md.
Der Same-Schema-Hostupdater darf sie nicht ersetzen.
