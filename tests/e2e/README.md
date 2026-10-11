# Echte Ubuntu-Qualifikation – hier NICHT ausgeführt

`ubuntu-vm.sh` läuft nur als root und mit `WERFT_DISPOSABLE_VM=1` auf einer frischen,
wegwerfbaren Ubuntu-24.04-amd64-VM mit systemd/cgroup v2. Bestehende Cluster werden abgewiesen.
Die Umgebung benötigt vertrauenswürdige Ubuntu-Paketquellen mit `docker.io` und `etcd-server`.

```bash
sudo env WERFT_DISPOSABLE_VM=1 bash tests/e2e/ubuntu-vm.sh \
  "$PWD/dist/werftkern_0.2.0~dev2_amd64.deb"
```

Der Test installiert echte Pakete, startet echte Dienste, lädt das mitgelieferte Image,
prüft Container-Sicherheitsoptionen und HTTP, startet Controller/Agent/etcd neu,
prüft unveränderte Container-IDs beim Service-Neustart, skaliert, rollt zurück und löscht.
Der Ergebnisdatensatz entsteht ausschließlich auf der tatsächlich ausführenden VM.
Ein abgebrochener Test bleibt fehlgeschlagen. Keine Erfolgsdatei wird vorab mitgeliefert.
Bei Fehlschlag bleiben Schlüssel und Daten zur Diagnose erhalten. VM danach bewusst entsorgen.

## Zusätzliche Multi-VM-Abnahme (offen)

Drei frisch provisionierte VMs im selben privaten Netz verwenden. Controller installieren;
Worker gemäß `docs/INSTALL-UBUNTU-DE.md` beitreten lassen. Dann mindestens prüfen:

1. `demo` mit drei Replikaten läuft verteilt; alle privaten HTTP-Endpoints sind erreichbar.
2. `werft node drain worker-2` erhält Readiness, entfernt erst danach dessen Container.
3. Verbindung eines Workers zur API gezielt unterbrechen: nach >30 Sekunden muss der Node
   `Unknown` sein. Seine Reservierungen bleiben; kein ungeprüfter Ersatz auf einem anderen Node.
4. Verbindung wiederherstellen: derselbe Node/Agent nimmt seine Journal-Identität wieder auf.
5. Neu verbundenes geklontes Agent-InstanceID wird mit `NODE_ALREADY_CLAIMED` abgelehnt.
6. Controllerhost neu starten. Dieselbe Cluster-ID, CA, etcd-Daten und laufende Container erhalten.
7. DNS-/Internet-Ausfall nach Installation: die mitgelieferte Demo braucht keinen Registry-Pull.
8. Docker-Neustart, Diskdruck, Paketupdate/Deinstallation und CA-Ablauf separat qualifizieren.

Diese Anleitung ist kein automatisierter Multi-VM-Test und kein bestehender Erfolgsnachweis.
Keine Produktionsdaten oder bestehenden Unternehmenscluster verwenden.

Alpha2 ergänzt im Skript echte Secretdatei-Bindprüfung per Docker, verschlüsseltes logisches
Backup/Inspect sowie Pause/Resume. Temporäre Secrets/Backupkeys liegen außerhalb der
Evidence-Uploadliste. Auch diese neuen Schritte wurden hier nicht auf Ubuntu ausgeführt.
Ein Hostreboot-/Cross-Host-Restoretest ist damit ausdrücklich noch nicht abgedeckt.
