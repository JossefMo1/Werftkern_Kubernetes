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

Lade alle fünf Release-Assets ausschließlich aus dem GitHub-Release herunter.
`release-manifest.json` gehört absichtlich zum Prüfumfang von `SHA256SUMS`; wenn
diese Datei fehlt, ist die Hashprüfung unvollständig.

Für dieses Release kannst du die Dateien so herunterladen und anschließend das
Test-Kit entpacken:

```bash
TAG=v0.2.0-dev.4-test.16
BASE="https://github.com/JossefMo1/Werftkern_Kubernetes/releases/download/${TAG}"

wget \
  "${BASE}/werftkern_0.2.0.dev4_amd64.deb" \
  "${BASE}/werftkern-kubernetes_0.1.0.dev3_all.deb" \
  "${BASE}/werftkern-test-kit-${TAG}.tar.gz" \
  "${BASE}/release-manifest.json" \
  "${BASE}/SHA256SUMS"

sha256sum -c SHA256SUMS
cat release-manifest.json
tar -xzf "werftkern-test-kit-${TAG}.tar.gz"
```

Die Release-Assets verwenden für GitHub kompatible Dateinamen (Versions-Tilde als Punkt); die lokale Paketversion bleibt davon unberührt. Die Pakete sind unsignierte Entwicklungsartefakte. Der Hash schützt vor
Übertragungsfehlern, ersetzt aber keine Signatur-, Herkunfts- oder
Schwachstellenprüfung.

## Native 3-Controller/3-Worker-Labor

Installiere das Native-Paket nur auf dem Admin-/Managementhost, kopiere es nicht
manuell auf sechs Hosts. Das Paket enthält `werft-ops`; der Koordinator überträgt
das exakt geprüfte Paket selbst. Der Post-Install-Schritt prüft beide
Kommandos. Das Paket fordert außerdem `openssh-client` an und prüft
`ssh` im Post-Install-Schritt. Wenn `apt` die Installation nicht erfolgreich
abschließt, darf der Bootstrap nicht fortgesetzt werden. Die automatische Discovery benötigt keine manuell gepflegten IP- oder
Hostname-Einträge in `/etc/hosts`. Sie liest ausschließlich bereits
vertrauenswürdige SSH-Endpunkte aus `/root/.ssh/known_hosts`, ordnet sie über
Alias- und read-only Remote-Hostname-Probes eindeutig den Controller-/Worker-
Rollen zu und ergänzt daraus das Inventar. Eine vorhandene `/etc/hosts`-
Zuordnung wird nur auf Konsistenz geprüft. Der Preflight prüft beide
SSH-Endpunkte (Hostname und IP), vergleicht den Remote-Hostnamen und schreibt
die Beobachtungen ins Journal. Eine fehlende, mehrdeutige, widersprüchliche oder
nicht vertrauenswürdige Zuordnung blockiert fail-closed.

Vor dem Lauf müssen die Ziel-Endpunkte bereits über einen vertrauenswürdigen
Kanal in `known_hosts` aufgenommen worden sein. Werftkern fügt keine
unbekannten Schlüssel hinzu und verwendet kein blindes `ssh-keyscan` als
Vertrauensentscheidung.

Die automatische Discovery ergänzt IPs, SSH-Ziele und Remote-Hostnamen ohne
manuelle Inventaränderung:

```bash
sudo apt-get update
sudo apt install --reinstall ./werftkern_0.2.0.dev4_amd64.deb
test -x /usr/bin/werft-ops || {
  echo "werft-ops fehlt: apt hat das Native-Paket nicht vollständig installiert." >&2
  dpkg-query -W -f='Status: ${Status}\n' werftkern 2>/dev/null || true
  exit 1
}
command -v werft-ops
command -v ssh
sudo werft-ops --help >/dev/null

# Optional: logisches 3m/3w-Profil aus dem Test-Kit; es enthält keine IPs.
sudo werft-ops native-bootstrap \
  --auto-discover \
  --inventory examples/native-inventory-3m-3w.json \
  --package /root/werftkern_0.2.0.dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json --check-only
sudo werft-ops native-bootstrap \
  --auto-discover \
  --inventory examples/native-inventory-3m-3w.json \
  --package /root/werftkern_0.2.0.dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json

# Ohne Inventardatei wird das eingebaute 3m/3w-Profil verwendet.
sudo werft-ops native-bootstrap \
  --auto-discover \
  --package "$PWD/werftkern_0.2.0.dev4_amd64.deb" \
  --journal /root/werft-native-bootstrap-test16.json --check-only
sudo werft-ops native-bootstrap \
  --auto-discover \
  --package "$PWD/werftkern_0.2.0.dev4_amd64.deb" \
  --journal /root/werft-native-bootstrap-test16.json
```

`--check-only` schreibt nur den lokalen Journal-/HA-Kit-Zustand und verändert
keine Zielhosts. Danach kann derselbe Befehl ohne `--check-only` fortsetzen.
Bereits korrekt eingerichtete Schritte werden wiederverwendet; fremde,
unvollständige oder unklare Zustände werden absichtlich blockiert. Die Native-
Bootstrap-Anleitung enthält die vollständigen Vorbedingungen und die sichere
Rückabwicklung.

Bei einer Wiederaufnahme wird ein vorhandenes generiertes Auto-Discovery-Inventar
wiederverwendet. Wenn dabei ein anderer `--known-hosts`-Pfad angegeben wird, bricht
Werftkern mit `AUTO_DISCOVERY_KNOWN_HOSTS_CHANGED` ab, statt die neue Vertrauensdatei
still zu ignorieren. Für einen neuen Vertrauensbestand muss ein neues Journal in
einer Wegwerfumgebung verwendet werden.

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
sudo apt install ./werftkern-kubernetes_0.1.0.dev3_all.deb
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
- `werft-ops: command not found`: die Paketinstallation wurde nicht abgeschlossen. Nicht mit `native-bootstrap` fortfahren; zuerst `sudo apt install --reinstall ./werftkern_0.2.0.dev4_amd64.deb` erfolgreich beenden und den `/usr/bin/werft-ops`-Check wiederholen.
