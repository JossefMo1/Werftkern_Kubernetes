# Automatischer Native-Bootstrap (Labor)

Der vorhandene Einzelhost-Befehl `werft-ops bootstrap` installiert ein Paket
und ein bereits erzeugtes HA-Kit über zuvor geprüfte SSH-Verbindungen. Der
Orchestrator `werft-ops native-bootstrap` bündelt diesen Schritt für ein
Inventar mit drei Controllern und mindestens einem Worker. Der bevorzugte
`--auto-discover`-Modus benötigt keine manuell eingetragenen IP-Adressen oder
Hostnamen. Er verwendet ausschließlich bereits vertrauenswürdige SSH-Endpunkte
aus `known_hosts`, prüft sie read-only und erzeugt daraus ein gebundenes
Inventar. Eine vorhandene `/etc/hosts`-Zuordnung wird als zusätzliche
Plausibilitätsprüfung verwendet, ist aber im Auto-Modus nicht erforderlich.

## Was automatisch geprüft wird

1. Die Inventardatei und die angegebene Hosts-Datei werden strikt validiert.
   Jeder Profilname muss auf genau eine private IPv4-Adresse zeigen. Diese
   Adresse muss außerdem mit einem exakten Eintrag in `known_hosts` übereinstimmen.
   Rollen werden nicht aus Namen erraten; sie stehen ausdrücklich im Inventar.
2. Jeder Host wird vor der ersten Mutation zweimal mit `BatchMode`,
   `StrictHostKeyChecking=yes`, einer festen `known_hosts`-Datei und `sudo -n`
   geprüft: einmal über den Hostnamen und einmal über die aufgelöste IP. Der
   gemeldete Remote-Hostname muss bei beiden Verbindungen identisch sein
   und zum erwarteten Profilnamen (oder zu `expectedHostname`) passen. Eine
   veraltete oder vertauschte `/etc/hosts`-Zuordnung wird dadurch vor jeder
   Host-Mutation mit `REMOTE_HOSTNAME_PROFILE_MISMATCH` blockiert.
3. Jeder Host muss Ubuntu 24.04, systemd und cgroup v2 melden. Hostname,
   Paket-/Konfigurationszustand und unterbrochene HA-Installationen werden
   protokolliert.
4. Der Orchestrator erzeugt genau ein gemeinsames HA-Kit-Set und bindet den
   unveränderten Paket-Hash, die Inventar-, Topologie- und `known_hosts`-Hashes
   in ein privates Journal.
5. Bereits konfigurierte Hosts desselben Cluster-IDs werden übersprungen.
   Ein fremder Cluster, vorhandene Daten ohne Konfiguration oder ein
   `ha-installing.json` blockieren. Es gibt kein Überschreiben und keinen
   blinden Wiederholungsversuch.
6. Nach dem Staging wird der Seed initialisiert und `health --all --json`
   sowie `status --json` werden gegen die erwartete Cluster-ID geprüft.

## Automatische Host-Erkennung

Im Auto-Modus werden die folgenden Schritte automatisch ausgeführt:

1. private IPv4-Endpunkte aus der geprüften `known_hosts`-Datei lesen;
2. logische Profilnamen zunächst über vertrauenswürdige Aliase und anschließend
   über read-only Remote-Hostname-Probes zuordnen;
3. Namensformen wie `worker-1` und `worker1` sicher gleich behandeln;
4. jeden Kandidaten mit `StrictHostKeyChecking=yes`, `BatchMode` und
   `sudo -n` auf Ubuntu 24.04, systemd und cgroup v2 prüfen;
5. Controller-/Worker-Rollen nur bei eindeutiger Zuordnung übernehmen;
6. das automatisch erzeugte Inventar unter `<journal>.inventory.json` speichern
   und gemeinsam mit `known_hosts`, Topologie und Paket-Hash im Journal binden.

Es gibt kein blindes `ssh-keyscan`, kein Vertrauen auf unbekannte Schlüssel und
kein unkontrolliertes Netzwerkscanning. Sind mehrere Hosts derselben Rolle nicht
eindeutig zuordenbar, blockiert Werftkern mit einem klaren Fehler statt zufällig
IP-Adressen oder Rollen zu wählen.

## Rollenprofil und manuelles Inventar

`examples/native-inventory-3m-3w.json` zeigt die Struktur für drei
controller-only Master und drei Worker. Das Profil enthält im Auto-Modus nur
logische Hostnamen und Rollen; Adressen und SSH-Ziele werden automatisch
ergänzt. Die `known_hosts`-Datei muss vor dem Lauf über einen vertrauenswürdigen
Kanal gepflegt werden. Für streng manuelle Läufe können weiterhin `hostsFile`
und explizite `address`-Werte verwendet werden.

## Ausführung

Automatischer Lauf mit dem mitgelieferten 3-Controller-/3-Worker-Profil:

```sh
sudo werft-ops native-bootstrap \
  --auto-discover \
  --inventory examples/native-inventory-3m-3w.json \
  --package /root/werftkern_0.2.0.dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json \
  --check-only
```

Wenn kein Profil angegeben wird, verwendet `--auto-discover` automatisch ein
eingebautes 3m/3w-Profil mit dem SSH-Benutzer `ubuntu`:

```sh
sudo werft-ops native-bootstrap \
  --auto-discover \
  --package /root/werftkern_0.2.0.dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json \
  --check-only
```

Nach erfolgreicher Prüfung denselben Befehl ohne `--check-only` wiederholen:

```sh
sudo werft-ops native-bootstrap \
  --auto-discover \
  --inventory examples/native-inventory-3m-3w.json \
  --package /root/werftkern_0.2.0.dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json
```

Ein Wiederaufruf verwendet dasselbe Journal und dasselbe automatisch erzeugte
Inventar. Inventar, `known_hosts` oder Paket dürfen nach dem ersten Lauf nicht
ausgetauscht werden. Unklare Remote-Ergebnisse werden zur Prüfung angehalten.

Das Paket bleibt ein unsigniertes Laborpaket. Der Befehl ist eine
Bootstrap-/E2E-Hilfe und setzt weder `productionReady` noch irgendein
Qualification-Gate auf bestanden.
