# Ubuntuinstallation — Werftkern 0.2.0-dev.4

Zielprofil: frische Ubuntu24.04-LTS-amd64-VM, systemd, cgroupv2. Nicht real in dieser
Erstellungsumgebung qualifiziert. Keine bestehende ClusterPilot-/Kubernetes-/Docker-
Produktion dafür verwenden. Das separat gelieferte Paket ist unsigniert und mit der
verfügbaren Go1.23.2-Labortoolchain gebaut. Erst mit aktueller unterstützter Toolchain
neu bauen und die echte VM-Testmatrix durchlaufen.

```sh
bash scripts/build-deb.sh
sudo apt update
sudo apt install ./dist/werftkern_0.2.0~dev4_amd64.deb
sudo werft setup
```

Der Basisdialog fragt nur neuer Cluster oder Workerbeitritt und die lokale private IPv4.
CA, Zertifikate, Node-/Cluster-ID, Vaultkey und systemd-Konfiguration entstehen automatisch.
Einzelhosttest darf Loopback verwenden; Mehrhostpläne benötigen echte private Adressen.
Ubuntu-Paketquellen müssen Docker, etcd und Python bereitstellen. Kein ungeprüftes
Hinzufügen fremder APT-Quellen. Pfade `/etc/werftkern`, `/var/lib/werftkern`, `/run/werftkern`.

```sh
sudo werft demo --wait
sudo werft status
sudo werft endpoints demo
sudo werft dashboard
```

Dashboard standardmäßig auf127.0.0.1:8787 mit lokalem Code. Bei Remotehost einen
hostkeygeprüften SSH-Tunnel verwenden; Admin-Dashboard nicht öffentlich exposen.

Drei-Controller-Setup: HA.md. Mesh/DNS: NETWORK.md. Persistente Daten: STORAGE.md.
Cloud-VMs: CLOUD.md. Updates/Restore: RECOVERY.md. Diese Erweiterungen brauchen zusätzliche
Betreiberangaben; Netzwerk-/SSH-Vertrauen, Datenverantwortung und Kosten werden nicht
durch unsichere Defaults übersprungen. `werft-ops --help` zeigt die Betriebsbefehle.

Vorhandene alpha1/alpha2-Installationen bleiben unangetastet. Es gibt keine automatische
In-place-Migration der alten Pfade, IDs, API-Namensräume oder Pakete. Neues Projekt,
neuer Testcluster. Eine Deinstallation löscht weder Volumedaten noch Schlüssel noch
verwaltete Container automatisch; vor Löschung den eigenen Daten-/Cleanupplan ausführen.

**Bestehendes Werftkern dev.1:** Schema2 wird nicht automatisch eingespielt.
Vor jedem Paketwechsel SCHEMA-MIGRATION.md lesen; alle Writer offline und Apps pausiert.
Neue Funktionen: VOLUME-BACKUP.md und INGRESS.md. HTTPS-Ingress verwendet separate
Credentials und explizite TLS-Dateien, nicht den Admin-Dashboardprozess.

Dev.2→dev.3 bleibt Schema2, verlangt jedoch einheitliche Agent-/Controller-Versionen
und eine koordinierte Offlinewartung; kein ungeprüftes In-place-/Rolling-Upgrade.
Neue Betriebsfunktionen: DATABASE-HA.md (eigene DB-Hosts), POSTGRES-PITR.md,
CERTIFICATE-ROTATION.md und UPGRADE.md. Sie werden nicht still im Basiswizard aktiviert.
Patroni/PostgreSQL17/pgBackRest und ein qualifizierter Watchdog sind separate Voraussetzungen.


## Neuinstallation gegenüber dev.3→dev.4-Workerupdate

Die Paketbeispiele oben sind für eine **frische Test-VM**. Kein ungeprüftes Überschreiben
bestehender Cluster. Schema 2 bleibt bestehen; dev.4-Controller akzeptieren ausdrücklich
dev.3- und dev.4-Agenten. Umgekehrt ist das nicht freigegeben. Alle konfigurierten
Controller müssen vor der Workerwelle dev.4 melden. Erst danach den signierten,
plan-/identitätsgebundenen Ablauf in `WORKER-ROLLOUT.md` verwenden.

Dieser Ablauf verlangt bereits vertrauenswürdig verteilte Release-Public-Keys und
geprüfte SSH-Hostschlüssel. Das hier angebotene **unsignierte** Laborpaket kann nicht
ungeprüft als Produktionsupdate freigegeben werden. Signaturgültigkeit allein ersetzt
keine reale Hostqualifikation.
