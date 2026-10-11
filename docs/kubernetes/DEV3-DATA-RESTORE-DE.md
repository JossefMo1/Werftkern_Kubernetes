# Quarantinierter PV-Restore mit tatsächlicher Dateiprüfung

**0.1.0-dev.3 · Implementiert, nur mit API-Testadaptern und lokalen Testdateien geprüft.**
`data-restore` ergänzt den Control-Plane-Restore; es ersetzt keine komplette Datenbank-
oder Standortwiederherstellung. Der bestehende native pgBackRest-/PITR-Betriebspfad
bleibt separat und wurde hier nicht auf PostgreSQL ausgeführt.

## Enger Eingangsvertrag

Vorhandene, administrativ geprüfte Velero-Installation; bestehendes Backup mit
bekannter UID, Spec-Hash und `werftkern.io/source-cluster-uid`-Annotation; keine
Warnungen/Fehler oder Backup-Hooks; ein CSI-Snapshot pro erklärtem PVC; kein FSB,
kein Snapshot Data Mover. Ziel-Cluster-UID muss von der Quelle abweichen. Der
Backup-Metadatensatz ist eine Betreiber-Vertrauensgrenze, kein kryptografischer
Nachweis über den vollständigen Inhalt aller Backupobjekte.

Ein tatsächlich snapshotfähiger CSI-Treiber, Snapshot-Controller, vorhandene
passende StorageClass mit `Immediate`-Binding und zugängliche Snapshotdaten sind
Voraussetzungen. **Hetzner Cloud Volumes bieten laut Provider keine Volumesnapshots.**
Dieser neue CSI-Snapshot-Restore ist daher kein Backupweg für `csi.hetzner.cloud`.
Die Stateful-Reparatur vorhandener Hetzner-Volumes und die Snapshot-Wiederherstellung
sind getrennte Profile. Für Hetzner-Datensicherungen bleiben ein qualifizierter
Dateisicherungs-/Datenbankweg und dessen Integration offen.

## Ablauf

1. Privaten Auftrag, Assetbindung, Ziel-UID, Backup-Metadaten und Snapshotanzahl prüfen.
2. Neue `restore-*`-Namespaces mit Pod-Security `restricted` und Default-Deny-NetworkPolicy
   anlegen. Bereits existierende Namespaces werden nicht übernommen.
3. Velero-Restore ausschließlich für PV/PVC und CSI-Snapshotressourcen anlegen. Keine
   zurückgesicherten Pods, Deployments, Secrets, ServiceAccounts, Rollen oder Hooks ausführen.
4. `Completed` ohne Fehler/Warnungen sowie neue PV-/Volumeidentitäten und gebundene PVCs prüfen.
5. Selbst erzeugte Prüfjobs lesen die neuen PVCs schreibgeschützt. Nicht-root, seccomp,
   keine Capabilities, kein ServiceAccount-Token, CPU/RAM-/Zeitlimits. Die ausgewählten
   relativen Dateipfade werden ohne Symlinkverfolgung geöffnet und per SHA256 geprüft.
6. Tatsächlichen Job-/Pod-Erfolg und unveränderte Pod-, Claim-, Snapshot- und Volumeidentitäten
   prüfen. Ein bloßes Velero-`Completed` ist kein Dateinachweis.
7. Betrieb bleibt quarantiniert; keine Datenbank-Promotion und keine Verkehrsumschaltung.

Die Wirksamkeit der NetworkPolicy setzt einen funktionsfähigen Policy-Datenpfad voraus.
Die API-Existenz einer Policy beweist keine tatsächliche Netzwerkisolation. Dies bleibt
Teil der offenen Livequalifikation. Namespace-Policy, PSA und Prüfjobs werden bei
Wiederaufnahme erneut geprüft, nicht allein anhand ihrer Eigentumsannotation vertraut.

```bash
werft-kube plan data-restore.json
sudo werft-kube --root /var/lib/werftkern/kubernetes/recovery-target \
  --assets /etc/werftkern/kubernetes/recovery-target/assets.json \
  data-restore --spec data-restore.json --confirm EXAKTER_PLAN_SHA256
```

Die Funktion ist schrittweise und kann denselben Auftrag fortsetzen. Verlorene Create-
Antworten werden nur über eindeutige Eigentums- und UID-Nachweise aufgelöst. Extern
entfernte Ressourcen werden nicht blind neu erstellt. Neue Jobversuche nach Fehlern
verlangen einen separat überprüften Auftrag/Zielnamespace. Aufräumen der Quarantäne
und Datenträger erfolgt ausdrücklich, nicht automatisch nach einer Fehlermeldung.

## Nachweisgrenzen

Die geprüften Dateien belegen nur ihre angegebenen Hashes, keine vollständige
Dateisystemkonsistenz, keine Datenbanktransaktionen und keinen erfolgreichen Betrieb
der wiederhergestellten Anwendung. Quelldaten müssen zum gewünschten Sicherungszeitpunkt
konsistent vorliegen. Laufende Datenbanken erfordern ein eigenes DB-Backup-/WAL-/Replay-
Verfahren und fachliche SQL-Prüfungen. Ein fremdes oder unvollständiges Snapshotbackend
wird durch dieses Werkzeug nicht snapshotfähig.

Die getesteten Dateiprüfer liefen tatsächlich auf temporären lokalen Dateien; Symlinks
und falsche Dateiinhalte scheiterten. Kein echtes PVC, CSI-Snapshot oder Velero-Restore
wurde in dieser Arbeitsumgebung ausgeführt.

## Primärquellen

- Velero 1.18 Restore: https://velero.io/docs/v1.18/restore-reference/
- Velero API: https://raw.githubusercontent.com/vmware-tanzu/velero/v1.18.0/pkg/apis/velero/v1/backup_types.go
- Hetzner Volume-Grenzen: https://docs.hetzner.com/cloud/volumes/overview/

Der Treiber `csi.hetzner.cloud` wird für diesen Snapshot-Restore bereits vor der
ersten Kubernetes-Anfrage explizit abgewiesen. Der getrennte Recoverypfad für
bestehende Hetzner-Volumes bleibt davon unberührt.
