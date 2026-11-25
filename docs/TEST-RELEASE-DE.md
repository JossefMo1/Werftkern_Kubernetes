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
- `werftkern-native.spdx.json` als gebundene SPDX-2.3-Übersicht des Native-Pakets,
- `werftkern-native.spdx.sha256` als Hash des SBOM-Dokuments,
- `werftkern-test-kit-<tag>.tar.gz` mit den passenden Runbooks, Inventaren und
  E2E-Skripten,
- `release-manifest.json` mit Commitbindung und Paket-Hashes sowie `SHA256SUMS`.

Lade alle sieben Release-Assets ausschließlich aus dem GitHub-Release herunter.
`release-manifest.json` gehört absichtlich zum Prüfumfang von `SHA256SUMS`; wenn
diese Datei fehlt, ist die Hashprüfung unvollständig.

Für dieses Release kannst du die Dateien so herunterladen und anschließend das
Test-Kit entpacken:

```bash
TAG=v0.2.0-dev.4-test.17
BASE="https://github.com/JossefMo1/Werftkern_Kubernetes/releases/download/${TAG}"

wget \
  "${BASE}/werftkern_0.2.0.dev4_amd64.deb" \
  "${BASE}/werftkern-kubernetes_0.1.0.dev3_all.deb" \
  "${BASE}/werftkern-native.spdx.json" \
  "${BASE}/werftkern-native.spdx.sha256" \
  "${BASE}/werftkern-test-kit-${TAG}.tar.gz" \
  "${BASE}/release-manifest.json" \
  "${BASE}/SHA256SUMS"

sha256sum -c SHA256SUMS
sha256sum -c werftkern-native.spdx.sha256
cat release-manifest.json
tar -xzf "werftkern-test-kit-${TAG}.tar.gz"
```

Die Release-Assets verwenden für GitHub kompatible Dateinamen (Versions-Tilde als Punkt); die lokale Paketversion bleibt davon unberührt. Die Pakete sind unsignierte Entwicklungsartefakte. Das SBOM ist absichtlich auf Paketmetadaten, deklarierte Debian-Abhängigkeiten und den Go-Modulgraphen begrenzt; es ersetzt weder eine vollständige OS-Schwachstellenprüfung noch Signatur-, Herkunfts- oder Produktionsfreigaben. Die Hashes schützen vor Übertragungsfehlern.

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
manuelle Inventaränderung. `werft-ops` wird erst durch die Paketinstallation
bereitgestellt; ein Aufruf davor darf daher noch mit `command not found`
scheitern. Erst die erfolgreiche Installation und die folgenden Pfadprüfungen
bestätigen, dass der Adminhost bereit ist:

```bash
sudo apt-get update
sudo apt-get install --reinstall ./werftkern_0.2.0.dev4_amd64.deb
test -x /usr/bin/werft-ops || {
  echo "werft-ops fehlt: apt hat das Native-Paket nicht vollständig installiert." >&2
  dpkg-query -W -f='Status: ${Status}\n' werftkern 2>/dev/null || true
  exit 1
}
command -v werft-ops
command -v ssh
sudo werft-ops --help >/dev/null

# Saubere Entfernung des Native-Pakets prüfen.
sudo apt-get remove -y werftkern
test "$(dpkg-query -W -f='Status: ${Status}\\n' werftkern 2>/dev/null || true)" != "install ok installed"
hash -r
! command -v werft-ops
! command -v werft

# Für den weiteren Labortest wieder installieren.
sudo apt-get install --reinstall ./werftkern_0.2.0.dev4_amd64.deb
test "$(dpkg-query -W -f='Status: ${Status}\\n' werftkern)" = "install ok installed"
test -x /usr/bin/werft-ops
command -v werft-ops
