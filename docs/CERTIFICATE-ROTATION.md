# Zertifikatserneuerung — dev.3

Implementiert: neue Leaf-Schlüssel/Zertifikate von derselben OFFLINE-CA, atomarer
Dateiwechsel und Live-Reload für Werftkern-HTTP-Clients und Runtime-Controller.
Nicht implementiert: neue CA-Vertrauenskette, autonomer Enrollment-/Signer-Dienst,
Datenbank-/etcd-Serverzertifikatsrotation oder sofortiger Abbruch aller alten Sessions.

## Einmalige Umstellung auf ein gemeinsames PEM

Die bisherigen Installer erstellen getrennte Zertifikats-/Schlüsseldateien. Dieses
Format funktioniert unverändert, wird jedoch statisch geladen. Zur Live-Erneuerung
müssen `cert` und `key` der jeweiligen Client-/Control-Konfiguration auf DIESELBE
neue absolute Datei zeigen. Die Datei enthält genau ein Leaf und dessen Private Key.

```sh
sudo werft certificate bundle --ca /trusted/ca.crt \
  --cert /private/current.crt --key /private/current.key \
  --out /private/identity.pem
sudo werft certificate inspect --bundle /private/identity.pem
```

Ausgabe und Verzeichnisse gehören dem vorgesehenen Dienstbenutzer, Datei 0600.
Ein bereits vorhandenes Ziel oder Symlink wird nicht überschrieben. Nach manueller
geprüfter Änderung beider Konfigurationspfade muss der betroffene Dienst EINMAL
kontrolliert neu gestartet werden. Unterschiedliche Rollen/Hosts brauchen eigene Bundles;
keine Verteilung eines Adminbundles auf Worker. Danach werden atomare Leafwechsel bei
neuen TLS-Handshakes ohne Prozessneustart gelesen.

## Erneuerung durch den Offline-Aussteller

```sh
sudo werft certificate renew --ca /offline/ca.crt --ca-key /offline/ca.key \
  --bundle /private/identity.pem --out /private/renewed.pem \
  --days 365 --confirm-identity EXACT_CURRENT_CN
```

CA-Schlüssel niemals an alle Worker übertragen. Dieser lokale Pfad benötigt aktuell
den alten privaten Leaf-Bundle beim Aussteller; es ist kein CSR-/Remote-Enrollment-
Protokoll. Transport/Löschung/Schlüsselverwahrung verantwortet der Betreiber.
Erneuerung darf weder CN, Clusterrolle, SANs, EKUs noch Aussteller ändern. Neuer privater
Schlüssel, neue Seriennummer und verlängerte Gültigkeit, begrenzt durch die CA-Laufzeit.
Abgelaufene Leafs können mit noch gültiger vertrauenswürdiger Offline-CA ersetzt werden;
eine abgelaufene CA erfordert ein getrenntes Recoveryverfahren.

Auf dem Ziel den aktuellen öffentlichen SHA256 aus inspect als Compare-and-Swap verwenden:

```sh
sudo werft certificate install --ca /trusted/ca.crt \
  --bundle /private/identity.pem --candidate /private/renewed.pem \
  --expect-cert CURRENT_LEAF_DER_SHA256
```

Der Installer erhält Dateieigentum, verwendet Sperre, fsync und rename und gibt nie
Schlüsselwerte aus. Ein erfolgreicher Wiederholungsaufruf erkennt denselben bereits
installierten Kandidaten. Eine beschädigte Datei führt NICHT zum stillen Fallback auf
alte gecachte Schlüssel. Umgehängte/unsichere Verzeichnisse sind nicht zulässig.
Verzeichnisbesitzer und Hostroot bleiben ausdrücklich vertrauenswürdig.

## Grenzen und echte Tests

Client- und Serverwechsel wurden mit realen lokalen TLS-Verbindungen getestet, ebenso
beschädigte Bundles, abgelaufene/fremde CAs, Rollenwechsel und Schlüssel-/Dateirechte.
Das ist kein echter Mehrhost-Rotationstest. Alte bestehende TLS-Verbindungen behalten
ihre bisherige Authentisierung; API-Ablauf-/Sperrprüfungen gelten weiterhin. Kein
sofortiger Clusterweiter Revocation-Mechanismus. Anti-Rollback-Gedächtnis ist pro Prozess,
nicht als monotone TPM-/Disk-Epoch über jeden Neustart hinweg gesichert. Veraltete PEMs
dürfen deshalb nicht aus Backups blind zurückgespielt werden.
