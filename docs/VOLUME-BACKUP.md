# Physisches lokales Volume-Backup und Restore

**Entwicklungsfunktion; kein Live-Snapshot, keine Replikation, kein freigegebenes DR.**
Der Pfad sichert tatsächliche reguläre Dateien und Verzeichnisse eines kontrolliert
stillgelegten lokalen Volumes. PostgreSQL muss sauber gestoppt sein; `pg_isready` allein
beweist keine konsistente physische Sicherung. Mehrere Volumes bilden keinen atomaren Snapshot.

## Sicherheits- und Formatgrenzen

Archive enthalten AES-256-GCM-authentisierte 64-KiB-Blöcke und einen verpflichtenden
authentisierten Abschluss. Zufallssalt leitet je Archiv einen eigenen Schlüssel aus einem
separaten 32-Byte-Masterkey ab. Reihenfolge, Header und Abschluss sind gebunden. Integrität
beweist nicht die Vertrauenswürdigkeit der Datenquelle. Keine Eigenbehauptung eines
kryptografischen Audits. Format `WERFTVOL1`, Schema1, noch keine langfristige Kompatibilitätszusage.

Nur private Host-Volumes: keine Symlinks, Hardlinks, Geräte, Sockets, FIFOs oder fremden
Dateisysteme. Keine PostgreSQL-Tablespace-Symlinks. USTAR-formatierbare Dateinamen;
keine ACL/xattr-/Sparse-/Hardlink-Erhaltung. UID/GID stammt aus dem Zielvolume, nicht dem Archiv.
Default 10GiB, 100.000 Einträge, 64 Ebenen; `--max-bytes` erlaubt höchstens1TiB.
Dateimodi erhalten wenigstens Eigentümerzugriff. Diese Grenzen sind keine Lastqualifikation.

## Backup

Auf dem owning Worker sind sowohl seine Agent-Konfiguration als auch ein autorisierter
Admin-Client nötig. Keine dauerhafte Admin-CA/Schlüsselverteilung auf alle Worker einrichten;
für Wartung geschützt bereitstellen und danach entfernen. `WERFT_CONFIG` wählt den Adminclient.
Der Befehl braucht root und Zugriff auf Docker; er führt keine fremden Stop-/Deleteaktionen aus.

Zuerst betreffende Anwendung pausieren, Stopbestätigungen im Status abwarten. Maintenance
verhindert neue Bindings, stoppt aber für sich allein keine laufenden Prozesse. OPERATION_ID
muss eine selbst erzeugte 32-stellige Hex-ID sein; behalten, bis Wartung vollständig beendet ist.

```sh
sudo werft pause postgres
sudo werft status --json
sudo werft maintenance on --id OPERATION_ID --reason volume-backup
sudo werft volume backup pgdata --agent-config /etc/werftkern/agent.json \
  --file /root/backups/pgdata.wva --key-file /root/backup-keys/volumes.key \
  --maintenance-id OPERATION_ID
```

Elternverzeichnisse vorher geschützt anlegen. Archiv und Schlüssel außerhalb des Volumeroots,
in getrennten Dateien speichern; der Backupbefehl erzeugt einen fehlenden Schlüssel.
EXCL-Ausgabe verhindert Überschreiben. Ausgabe-Hash und Header getrennt aufbewahren.
Offsite-Kopie prüfen; Schlüssel separat redundant sichern. Archiv enthält sensible Daten trotz
Verschlüsselung, Metadaten im Header bleiben lesbar. Niemals Schlüssel in Git/Supportbundles.

Ein geteilter/exklusiver IO-Lock koordiniert mit dem Agent. Alle laufenden/restartbaren
Docker-Mounts, auch fremde und Mounts übergeordneter Pfade inklusive `/`, werden geprüft.
Ein beliebiger weiterer Hostprozess oder bösartiger root kann diese Sperre umgehen; der
Operator muss fremde Writer ausschließen. Keine Zusage gegen einen kompromittierten Host.

## Restore in NEUES Zielvolume

Quelle wirksam stilllegen/gegen Wiederanlauf sichern. Ein offline Archiv erledigt kein
Source-Fencing. Auf dem Zielcluster neues Volume anlegen, bevor Maintenance aktiviert wird:

```sh
sudo werft volume create restored-pgdata --node TARGET_NODE_ID --uid 999 --gid 999
sudo werft maintenance on --id TARGET_MAINTENANCE_ID --reason volume-restore
sudo werft volume restore restored-pgdata --agent-config /etc/werftkern/agent.json \
  --file /root/backups/pgdata.wva --key-file /root/backup-keys/volumes.key \
  --maintenance-id TARGET_MAINTENANCE_ID --operation-id RESTORE_OPERATION_ID
```

Node-ID und zwei Operations-IDs sind echte32-Hex-Werte. Das Ziel muss uninitialisiert und
unbenutzt sein; kein In-place-Overwrite produktiver Daten. Die API reserviert RestoreID/Hash
und markiert `Initialized=true, restoreComplete=false` **vor** dem Dateischreiben. Dadurch
kann ein abgebrochener Restore nicht als leeres Initialvolume gestartet werden.

Entschlüsselung läuft in ein neues verborgenes Verzeichnis. Nach vollständiger Integritäts-
und Pfadprüfung: Eigentum, fsync, Identitätsmarker und Receipt, atomare Umbenennung, API-ACK.
Bei verlorener Abschlussantwort exakt dieselbe ID, Datei, Ziel- und Maintenance-ID wiederholen.
Eine passende dauerhafte Receipt erlaubt ACK-Wiederholung ohne erneutes Überschreiben.
Widerspruch blockiert. Fehlerhafte Archive löschen nur ihre neue Staging-Kopie, nie das Ziel.

Maintenance kontrolliert freigeben; Zielmanifest auf das neue Volume/Node abbilden; Quelle
weiter isoliert lassen; Anwendung starten und SQL/Datei-/Transaktionsprüfungen durchführen.
Automatische Anwendungsfreigabe, physisches Fencing, Datenbank-Recovery und RPO/RTO werden
nicht aus einem erfolgreichen Datei-ACK abgeleitet. `Initialized` ist kein Integritätsbeweis.

Die Root-CLI-Integration testet echte Dateien, Verschlüsselung und mTLS plus verlorenes ACK,
aber mit Docker/etcd-Testadaptern. Ein erfolgreicher realer VM-/PostgreSQL-Restore fehlt.
