# Kontrollierte Worker-Updatewellen — dev.4

**Implementiert, aber NICHT auf echten Ubuntu-VMs/Docker/SSH qualifiziert. Kein Produktionsrelease.**
Der Pfad ist auf den gleichschemaigen Übergang **0.2.0-dev.3 → 0.2.0-dev.4** begrenzt.
State-Schema bleibt 2. Keine automatische Rückstufung, keine beliebige N/N−1-Kompatibilität.

## Voraussetzungen und Zuständigkeiten

Alle Controller müssen bereits dev.4 mit Schema2 betreiben. Ihre HTTPS-Endpunkte werden
vor Beginn und vor Abschluss jeweils direkt geprüft; Failover darf keinen alten Controller
verstecken. Die Controlleraktualisierung ist NICHT Bestandteil dieses Workerkoordinators.
Insbesondere orchestriert `upgrade apply` noch keine vollständigen HA-Controllerwellen.
Für den erstmaligen Wechsel auf dev.4 ist ein separat kontrollierter Controller-Wartungsablauf nötig.

Nur dedizierte Worker sind zugelassen. `/etc/werftkern/control.json` sperrt den lokalen
Workerinstaller. Der Plan muss sämtliche verbliebenen dev.3-Worker aufnehmen. Bereits
auf dev.4 laufende Nodes (etwa Controller mit Agent) werden beobachtet, nicht erneut installiert.

Anwendungen auf den geplanten Workern dürfen nicht aktiv an einen Node oder ein lokales
Volume gebunden sein. Keine automatische Verlagerung lokaler Daten. Pausierte Anwendungen
mit bestätigtem Stop sind zulässig. Drain erzwingt keine Eviction: fehlende Reservekapazität,
stale Readiness oder fehlende Stopbestätigungen blockieren. Ein Timeout lässt alles in
kontrollierter Wartung statt den alten Prozess als tot anzunehmen.

Das Zielpaket benötigt ein **gültig signiertes Release-Manifest**. Das bereitgestellte
Labor-.deb ist unsigniert; es ist keine für diesen Updatepfad freigegebene Release.
Der unabhängig verifizierte Ed25519-Public-Key muss bereits auf JEDEM Worker unter
`/etc/werftkern/trust/releases.pem` liegen (root-eigen, nicht gruppen-/weltbeschreibbar).
Der Koordinator vergleicht die Fingerprints und kopiert KEINEN neuen Trustanker auf Hosts.
Der SSH-Zugang und dessen Hostkeys müssen vorab unabhängig geprüft sein. Kein TOFU,
kein `StrictHostKeyChecking=no`, keine Passwortweitergabe. Der SSH-Benutzer benötigt
vorab bewusst eingerichtete nichtinteraktive sudo-Rechte. Keine Cloudkosten durch diesen Code.

## Ablauf

1. Zielartefakt, Quellen, Identitäten und alle Controller prüfen. Planfingerprint bestätigen.
2. Unveränderliche Journalbindung an Plan, Artefaktdigest, Manifest, Signatur und Hosttrust schreiben.
3. Clusterweite, nicht automatisch ablaufende Wartungssperre mit eigener Operations-ID anlegen.
4. Genau einen Worker drainen. Nur betroffene Workloads dürfen innerhalb der Sperre neue
   Allocations erhalten; sämtliche übrigen Mutationen/Schedulingpfade bleiben gesperrt.
5. Replikate ersetzen, Readiness abwarten, alte Instanzen stoppen und Stopbestätigung abwarten.
6. Lokal am Worker nochmals mTLS-Scope, Cluster-/Node-/Instance-ID, Lock und leere eigene
   Dockerinventur prüfen. Exakt den konfigurierten Unix-Socket benutzen.
7. Agent stoppen, Scope erneut prüfen, verifiziertes Paket installieren, Version prüfen, Agent starten.
8. Neuer Controller muss die Zielversion und fortgeschrittene persistente Heartbeatsequenz beobachten.
9. `werft worker-check` startet die mitgelieferte Demo über die echte Docker-Engine-Anbindung,
   prüft lokalen HTTP-Verkehr und löscht die Testinstanz kontrolliert. Ein eigener Namespace
   verhindert Adoption durch den normalen Agenten. Das ist kein DNS-/Inter-Node-/Business-Test.
10. Mehrere frische, fortschreitende Heartbeats im konfigurierten Beobachtungsfenster prüfen.
11. Worker mit der passenden Sequenz und Version entsperren. Nächster Worker.
12. Vollständigen Cluster erneut prüfen, eigenen Lock lösen, Abschlussbeleg schreiben.

Der Cluster bleibt während der gesamten Welle für neue Benutzeränderungen eingefroren.
Die Hostprüfung belegt keine fachliche Integrität einer Datenbank oder Kundenanwendung;
`businessValidation` bleibt `not-performed`.

## Befehle

`examples/worker-rollout.plan.json` enthält ausschließlich fiktive Identitäten. Alle IDs
und privaten Adressen durch tatsächlich beobachtete Werte ersetzen. Neue Operations-ID
z. B. mit `python3 -c 'import secrets; print(secrets.token_hex(16))'` erzeugen.

```bash
sudo werft health --all --json --expected-version 0.2.0-dev.4
sudo werft-ops rollout plan --file worker-rollout.plan.json

sudo werft-ops rollout apply \
  --file worker-rollout.plan.json \
  --journal /var/lib/werftkern/rollouts/change-001.json \
  --package ./werftkern_0.2.0~dev4_amd64.deb \
  --manifest ./release.json --signature ./release.sig \
  --public-key /etc/werftkern/trust/releases.pem \
  --known-hosts /root/.ssh/known_hosts \
  --confirm-plan HIER_DEN_TATSAECHLICHEN_PLAN_SHA256_EINSETZEN
```

Das signierte Manifestformat bleibt `werftkern-release/v1`; `sources` enthält erlaubte
Debian-Paketversionen (hier `0.2.0~dev3`), `version` die Laufzeitversion und
`packageSha256` den exakten Hash. Der Releaseprüfer akzeptiert keine fehlende Signatur.

## Wiederaufnahme und bewusst blockierende Zustände

Denselben Befehl mit unverändertem Plan/Trust/Artefakten erneut ausführen. Journale nie
löschen, um einen Fehler scheinbar zu beheben. Bei verlorener SSH-Antwort nach Installation
liest der Koordinator nur den Remote-Beleg; er startet KEINE zweite Paketinstallation.
Fehlt der Beleg oder ist dpkg in unklarem Zustand, bleibt `install-intent` blockiert.
Ein Administrator muss auf dem betroffenen Host Paketstatus, Dienst, Daten und Journal
prüfen und einen kontrollierten Reparaturablauf freigeben. Automatische dpkg-Reparatur ist
hier nicht implementiert. Der Clusterlock wird dabei nicht stillschweigend gelöst.

Nach einem Abbruch während des Beobachtungsfensters beginnt dieses erneut. Historische
Grünmeldungen dürfen die neue Beobachtung nicht ersetzen. Verlorene Uncordon-/Unlock-ACKs
sind idempotent wiederholbar. Eine neue fremde Wartungssperre wird niemals gelöst.

Ein abgebrochener Worker-Smoke kann eine eigene, deterministisch identifizierte
Testinstanz zurücklassen. `werft worker-check --operation ID --json` wiederaufnehmen,
nachdem Identität/Lock/Host geprüft sind. Keine fremden Container nach Namen löschen.
Der feste lokale Probeport ist 22999; ein Konflikt blockiert die Probe.

## Sicherheit und Aussagegrenze

Das bestehende installierte Binary prüft zuerst die Signatur des Zielpakets mit dem
bereits vertrauten Workerkey. Erst danach wird der neue Updater aus einem root-eigenen
Stagingverzeichnis des verifizierten Pakets ausgeführt. Für die eigentliche Installation
und lokale Probe erhält der Worker KEINEN Admin-Clientschlüssel des Controllers.

Unabhängig signierte Nachweise, Hardwareattestierung, Böswilligkeit eines root-Benutzers,
Controller-HA-Rollout, Untrusted Multi-Tenancy und automatisch koordinierte Betriebssystem-
oder Dockerupdates sind außerhalb dieses getesteten Vertrags. Echte Mehrhostqualifikation fehlt.
