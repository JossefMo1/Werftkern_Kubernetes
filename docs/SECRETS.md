# Versionierte Secrets

## Vertrag

`werft secret put NAME --file FILE [--expected-version N]` schreibt eine neue unveränderliche
Version. Erstfassung erwartet 0, nächste Version erwartet 1 usw. Die geschützte Eingabedatei
enthält 1–4096 Bytes. Maximal 128 Versionen im Cluster; maximal acht unterschiedliche Namen je
Workload. Zustandsgrößenlimits gelten zusätzlich. Die CLI gibt nur Name/Version zurück.

Die API erwartet `PUT /v1/secrets/{name}` mit Admin-mTLS, Idempotency-Key,
`expectedVersion` und JSON-base64 `value`. Diese Codierung ist keine Verschlüsselung;
Transport wird mit TLS geschützt, gespeicherte Werte werden mit AES-256-GCM verschlüsselt.
Der zusätzliche Kontext bindet das Chiffrat an Cluster, Name und Version. Nonces sind zufällig.

```json
"secrets": [{"name":"database","version":1}]
```

Der zugewiesene Agent erhält nur diese Versionen über die mTLS-geschützte Allocationroute.
Admin-Status, Dashboard, Journal, Containerlabels und Backup-Metadaten zeigen keine Klartextwerte.
Allein ein eigenes Nodezertifikat berechtigt nicht zum Lesen fremder Allocationwerte.

## Auf dem Worker

`/run/werftkern/secrets` muss tmpfs und privat (0700) sein. Staging erzeugt zunächst
vollständige Dateien und Identitätsmanifest, danach erfolgt Rename. Der Container erhält nur
seine Allocation als read-only Bind unter `/run/secrets`. Einzeldateien sind für seine Non-root-UID
lesbar; der private Hostelternpfad verhindert Zugriff anderer normaler Hostbenutzer.
Root bzw. der Container selbst können ihre Werte weiterhin lesen.

Secret-tragende Container verwenden **keinen Docker-Autostart**: Nach Hostreboot muss der Agent
zuerst tmpfs-Dateien neu beschaffen, bevor er den Container startet. Ist die Control Plane nicht
erreichbar und die tmpfs-Kopie verloren, bleibt der Neustart blockiert. Ohne Hostreboot darf
der Agent seine bereits vollständig materialisierte identische Version wiederverwenden.
Dies ist ein bewusster Verfügbarkeits-/Vertraulichkeitskompromiss, kein Offline-Recovery-Versprechen.

Delete/Stop räumt die Allocationdateien auf. Eine Sperre am Controller entfernt nicht sofort
Werte von isolierten oder kompromittierten Hosts. Anwendungen können eigene Werte protokollieren.
Keine Host-Swap-/Memory-Dump-Sicherheit oder externe HSM-Key-Verwahrung zugesagt.

## Rotation und Löschen

Neue Secretversion schreiben, Workload mit expliziter neuer Referenz aktualisieren, Rollout prüfen.
Alte Versionen bleiben referenzierbar für Rollbacks. `secret delete NAME VERSION` verweigert
referenzierte Versionen; die höchste Version bleibt als monotone Generationsgrenze erhalten.
Ein automatischer Vault-Masterkey-Rotationsdienst und Secret-Tombstone-GC sind noch nicht enthalten.
Vaultverlust ohne korrektes verschlüsseltes Backup bedeutet Verlust der Entschlüsselbarkeit.

## Evidenzgrenze

Kryptografie-, Autorisierungs-, Staging-, Replay-, Dateirechte- und Cleanup-Tests laufen lokal.
Der Dockeradapter wurde mit einer HTTP-Fixture geprüft. Echter Docker-Bind-Mount, systemd-/tmpfs-
Hostreboot und Multi-Node-Recovery sind noch nicht qualifiziert.
