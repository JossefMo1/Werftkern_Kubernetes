# Drei-Controller-Control-Plane

## Implementiert

`werft ha prepare` erzeugt einen gemeinsamen Cluster mit drei separaten API-Server-
und etcd-Peer-Identitäten, einem vollständigen dreiteiligen etcd-Bootstrap und mehreren
Client-Endpunkten. Genau ein Controller enthält die einmalige Seed-Datei und die
CA-Signierschlüssel. Worker erhalten keine Signierschlüssel. Alle Controller besitzen
denselben Vault-Masterkey; diese Hosts sind ein gemeinsamer administrativer Trustbereich.

Alle Controller dürfen im kleinen unterstützten Datenmodell reconcile ausführen.
Eine etcd-CAS-Transaktion schützt die gesamte State-Version einschließlich Reservierung.
Es wird **kein eigener Raft-Konsens** implementiert und kein konkurrierender Cache als
Schreibautorität behandelt. Keine Leader-Lease wird als Beweis für Writer-Fencing verkauft.

## Aufbau

Vorbereitete Hosts müssen private Adressen haben, gegenseitig erreichbar sein und
Ubuntu24.04/amd64/systemd/cgroupv2 verwenden. Beim Mesh-Profil zuerst WireGuard/Bridges
anlegen; `address` im HA-Plan ist dann die WireGuard-Adresse.

```sh
werft ha prepare --topology examples/ha-topology.json --out /root/private-ha-kits
# Auf JEDEM Zielhost, nur dessen Datei übertragen, Modus 0600:
sudo werft ha install --kit /root/control-1.kit.json --confirm-host control-1
# Nachdem alle drei etcd-Hosts gestartet wurden, auf dem Seed-Controller:
sudo werft ha init
sudo werft status
```

Welche Datei den Seed enthält, ist lokal in den privaten Kits sichtbar. Beim Beispiel
ist es der lexikografisch erste Controller. Dateien enthalten private Schlüssel;
nie in Git, CI-Artefakte, Supportberichte oder Chat hochladen. Kits getrennt sichern
oder nach verifiziertem Bootstrap entfernen. Die aktuelle Kit-Erzeugung besitzt noch
keinen Online-Enrollment-/automatischen Zertifikatsrotationsdienst.

Ports: API7443, etcd-Client23791, etcd-Peer23801, bei Mesh UDP51820; nur freigegebene
private Quellen. Keine Verbindung benötigt einen öffentlichen Kubernetes-Endpunkt.
Die Clients verwenden direkt mehrere Endpunkte; ein einzelner Loadbalancer ist keine
versteckte HA-Voraussetzung. Dashboard/Shell bleiben an den jeweiligen Host gebunden.

`ha install` verweigert vorhandene Konfiguration oder Cluster-Memberdaten. Teilkopien
werden durch `ha-installing.json` erkennbar; automatische Wiedervergabe neuer Schlüssel
ist verboten. `ha init` markiert einen Initialisierungsversuch vor dem ersten etcd-CAS.
Unklare Ergebnisse werden nicht durch erneute leere Initialisierung kaschiert.

## Aussagegrenzen

Die HA-Kit-/Client-/CAS-Tests sind keine echten Raft-, Quorum-, Fsync-, Reboot- oder
Netzwerkpartitionstests. Es wurden hier keine drei etcd-Server gestartet. Ein verlorenes
Quorum blockiert im Entwurf Reads/Mutationen; schon laufende Workloads bleiben lokal.
Ein unerreichbarer Worker wird NICHT automatisch als abgeschaltet behandelt.
Bei lokalen Volumes bleibt Ersatz auf fremden Nodes blockiert. Datenbank-HA ist nicht
Teil dieses Control-Plane-HA-Pfads. Member-Ersatz, Zertifikatsrotation, automatische
etcd-Upgrades und standortübergreifende Disaster Recovery bleiben eigene offene Arbeiten.

## Dev.2-Ausfallvertrag und Evidenz

Node-Sperre ist kein Fencing. Standard behält unbekannte Allocations samt Reservierung.
Nur explizit duplikattolerante zustandslose Anwendungen dürfen mit
`replacementPolicy: duplicate-safe` während einer Partition zusätzlich laufen.
Schema2/Heartbeatsequenz verlangt passende Agentversion. Kein unterstützter Versionsmix.
Die neue Real-etcd-Testsuite beendet echte Prozesse, wurde hier aber mangels etcd nicht
ausgeführt. Single-Host-Quorumtests ersetzen keine separate-Host-Hochverfügbarkeit.
