# Experimentelles Werftkern-Testrelease

Dieses Dokument gilt für den Download eines `-test.N`-Releases. Es ist ein
reproduzierbar gebautes Ubuntu-amd64-Laborartefakt für Wegwerf-VMs. Es ist **keine
Produktionsfreigabe**, kein Supportvertrag und kein Nachweis für HA, Upgrade,
Backup/Restore, Kubernetes-Conformance oder Sicherheit. `productionReady` bleibt
für diese Artefakte `false`.

## Assets und Hashprüfung

Ein Testrelease enthält:

- `werftkern_0.2.0.dev4_amd64.deb` für den getrennten Native-Runtime-Pfad,
- `werftkern-kubernetes_0.1.0.dev3_all.deb` für den getrennten Kubernetes-Manager,
- `werftkern-test-kit-<tag>.tar.gz` mit den passenden Runbooks, Inventaren und
  E2E-Skripten,
- `release-manifest.json` mit Commitbindung und Paket-Hashes sowie `SHA256SUMS`.

Lade die Dateien ausschließlich aus dem GitHub-Release herunter und prüfe vor
der Installation:

```bash
sha256sum -c SHA256SUMS
cat release-manifest.json
```

Die Release-Assets verwenden für GitHub kompatible Dateinamen (Versions-Tilde als Punkt); die lokale Paketversion bleibt davon unberührt. Die Pakete sind unsignierte Entwicklungsartefakte. Der Hash schützt vor
Übertragungsfehlern, ersetzt aber keine Signatur-, Herkunfts- oder
Schwachstellenprüfung.

## Native 3-Controller/3-Worker-Labor

Installiere das Native-Paket nur auf dem Admin-/Managementhost, kopiere es nicht
manuell auf sechs Hosts. Das Paket enthält `werft-ops`; der Koordinator überträgt
das exakt geprüfte Paket selbst:

```bash
sudo apt install ./werftkern_0.2.0.dev4_amd64.deb
cp examples/native-inventory-3m-3w.json /root/native-inventory.json
# Namen, IPs, sshUser, /etc/hosts und /root/.ssh/known_hosts anpassen.
sudo werft-ops native-bootstrap \
  --inventory /root/native-inventory.json \
  --package /root/werftkern_0.2.0.dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json --check-only
sudo werft-ops native-bootstrap \
  --inventory /root/native-inventory.json \
  --package /root/werftkern_0.2.0~dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json
```

`--check-only` schreibt nur den lokalen Journal-/HA-Kit-Zustand und verändert
keine Zielhosts. Danach kann derselbe Befehl ohne `--check-only` fortsetzen.
Bereits korrekt eingerichtete Schritte werden wiederverwendet; fremde,
unvollständige oder unklare Zustände werden absichtlich blockiert. Die Native-
Bootstrap-Anleitung enthält die vollständigen Vorbedingungen und die sichere
Rückabwicklung.

## Kubernetes-3-Controller/3-Worker-Labor

Das Kubernetes-Paket installiert ausschließlich den Managementbaustein. Es
enthält **nicht** k0s, k0sctl, kubectl, Helm, age, Sonobuoy, Images oder Charts.
Diese Trennung verhindert unbemerkte Downloads und nicht überprüfte Lieferketten.
Für einen echten Lauf brauchst du daher:

1. einen Adminhost mit Ubuntu 24.04, Python, OpenSSH und dem Paket;
2. drei frische Ubuntu-24.04-Controller und drei frische Ubuntu-24.04-Worker;
3. einen bereits eingerichteten, gegenseitig erreichbaren privaten API-DNS-/LB-
   Einstieg, verifizierte Ed25519-Hostkeys und einen passwortlosen SSH-Schlüssel;
4. lokal heruntergeladene, exakt gehashte k0s/k0sctl/kubectl/age-Dateien sowie
   die von dir freigegebenen Image-/Chart-Digests.

Beginne mit den Vorlagen aus dem Test-Kit:

```bash
sudo apt install ./werftkern-kubernetes_0.1.0~dev3_all.deb
install -d -m 700 /etc/werftkern/kubernetes/lab /var/lib/werftkern/kubernetes/lab
cp examples/kubernetes/cluster-3m-3w.example.json /root/cluster-3m-3w.json
cp examples/kubernetes/assets-core.example.json /root/assets.json
# Alle Platzhalter durch echte Pfade, Hostkeys, API-DNS, Age-Empfänger und Hashes ersetzen.
chmod 600 /root/assets.json
```

Prüfe zuerst nur den Plan. Die Ausgabe ist eine Bestätigung des Eingabe-Hashes,
nicht die Qualifikation des Zielsystems:

```bash
werft-kube plan /root/cluster-3m-3w.json
PLAN_SHA256="$(werft-kube plan /root/cluster-3m-3w.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha256"])')"
```

Führe anschließend den Lifecycle auf der **Wegwerfumgebung** aus:

```bash
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /root/assets.json create \
  --plan /root/cluster-3m-3w.json --confirm "$PLAN_SHA256"
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /root/assets.json status
```

Für den optionalen echten Datenpfad müssen die beiden Smoke-Images als
`@sha256:`-Digests in `assets.json` ergänzt sein. Erst dann darfst du die
disposable acceptance ausführen:

```bash
CLUSTER_UID="$(sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /root/assets.json status | python3 -c 'import json,sys; print(json.load(sys.stdin)["uid"])')"
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /root/assets.json acceptance run --confirm "DISPOSABLE:$CLUSTER_UID"
sudo werft-kube --root /var/lib/werftkern/kubernetes/lab \
  --assets /root/assets.json backup
```

Ein erfolgreicher `create`, `status` oder Smoke ist nur ein Ergebnis dieses
isolierten Testlaufs. Er schließt keine Produktions-Gates. Nicht getestete
Funktionen wie Upgrade/Rollback, Controllerausfall, Storage, Restore auf einem
neuen Host, Keycloak/SSO, ACME und Sonobuoy bleiben offen. Für Logs, Journale,
Backups und Hostkeys gelten die Datenschutz- und Geheimnisregeln aus
`SECURITY.md`; nichts davon in GitHub-Issues oder Release-Assets hochladen.

## Fehlerbehebung

- `REVIEWED_ASSET_LOCK_REQUIRED`: eine eigene, vollständige `assets.json` mit
  echten Dateien und SHA256 ist erforderlich.
- `FRESH_UBUNTU_HOST_PREFLIGHT_FAILED`: Zielhost ist nicht frisch oder nicht
  Ubuntu 24.04; nicht mit `--force` umgehen.
- `EXACT_PLAN_CONFIRMATION_REQUIRED`: Plan nach der Hashausgabe nicht mehr ändern;
  bei Änderungen den Hash neu berechnen.
- SSH-/Hostkey-Fehler: IP, DNS, Port, Benutzer, `known_hosts` und Schlüssel
  prüfen. Hostkeys nicht per `ssh-keyscan` ungeprüft übernehmen.
