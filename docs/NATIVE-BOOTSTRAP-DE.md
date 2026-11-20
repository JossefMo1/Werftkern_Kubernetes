# Automatischer Native-Bootstrap (Labor)

Der vorhandene Einzelhost-Befehl `werft-ops bootstrap` installiert ein Paket
und ein bereits erzeugtes HA-Kit über zuvor geprüfte SSH-Verbindungen. Der
Orchestrator `werft-ops native-bootstrap` bündelt diesen Schritt für ein
Inventar mit drei Controllern und mindestens einem Worker.

## Was automatisch geprüft wird

1. Die Inventardatei und die angegebene Hosts-Datei werden strikt validiert.
   Jeder Name muss auf genau eine private IPv4-Adresse zeigen. Rollen werden
   nicht aus Namen erraten; sie stehen ausdrücklich im Inventar.
2. Alle Hosts werden vor der ersten Mutation mit `BatchMode`,
   `StrictHostKeyChecking=yes`, einer festen `known_hosts`-Datei und
   `sudo -n` geprüft.
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

## Inventar

`examples/native-inventory-3m-3w.json` zeigt die Struktur für drei
controller-only Master und drei Worker. Die Adressen werden aus
`hostsFile` aufgelöst; optionale `address`-Werte müssen exakt mit der Datei
übereinstimmen. Die `known_hosts`-Datei muss vor dem Lauf über einen
vertrauenswürdigen Kanal gepflegt werden. Die Software führt kein blindes
`ssh-keyscan` und keine Passwortkopie aus.

## Ausführung

Zuerst nur prüfen:

```sh
sudo werft-ops native-bootstrap \
  --inventory /root/native-inventory.json \
  --package /root/werftkern_0.2.0~dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json \
  --check-only
```

Nach der Prüfung denselben Befehl ohne `--check-only` wiederholen:

```sh
sudo werft-ops native-bootstrap \
  --inventory /root/native-inventory.json \
  --package /root/werftkern_0.2.0~dev4_amd64.deb \
  --journal /root/werft-native-bootstrap.json
```

Ein Wiederaufruf verwendet dasselbe Journal. Inventar, Hosts-Datei,
`known_hosts` oder Paket dürfen nach dem ersten Lauf nicht ausgetauscht
werden. Unklare Remote-Ergebnisse werden zur manuellen Prüfung angehalten.

Das Paket bleibt ein unsigniertes Laborpaket. Der Befehl ist eine
Bootstrap-/E2E-Hilfe und setzt weder `productionReady` noch irgendein
Qualification-Gate auf bestanden.
