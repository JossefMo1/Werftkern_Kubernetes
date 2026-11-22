# Offizieller Production-Scope

Der erste Production-Release von Werftkern wird offiziell auf den **Native-Single-Host-Betrieb** konzentriert. Damit wird die Version hauptsächlich produktiv nutzbar, ohne nicht belegte HA-, Multi-Host- oder Kubernetes-Versprechen abzugeben.

Der maschinenlesbare Vertrag ist release/native-production-scope.json. Er beschreibt den Production-Zielumfang; er setzt productionReady nicht automatisch auf true. Das geschieht erst nach der Qualifikation eines unveränderten Kandidaten.

## Production im ersten Release

| Bereich | Unterstützter Umfang |
| --- | --- |
| Produktpfad | Native Werftkern-Runtime |
| Host | Frisches Ubuntu 24.04 LTS amd64 mit systemd und cgroup v2 |
| Topologie | Ein Controller und ein lokaler Worker auf einem Host |
| Runtime | Docker Engine, etcd, mTLS, CLI und lokales Dashboard |
| Vertrauen | Ein vertrauenswürdiger Administrator und vertrauenswürdige Workloads |
| Limits | 1 Node, 20 Workloads, 50 Allocations, 900.000 State-Bytes |
| Betrieb | Installation, lokaler Workload-Lifecycle, Neustart/Wiederanlauf, lokales Backup/Restore, unterstütztes Paket-Upgrade und Rollback nach bestandener Qualifikation |

Das ist ein echter Production-Zielumfang für geeignete Single-Host-Workloads. Die Release Notes müssen die Grenzen ausdrücklich nennen; es gibt keine allgemeine HA- oder SLA-Zusage.

## Nicht Bestandteil dieses Production-Releases

- Multi-Host-HA, drei Controller, Quorum- und Netzwerkpartitionstoleranz
- automatischer Quorum-Verlustausgleich
- Restore auf einen anderen Host und vollständige Site-Disaster-Recovery
- produktiver Kubernetes-Manager/k0s-Lifecycle
- Cloud-Provisioning und Provider-Recovery
- PostgreSQL-/Patroni-HA und qualifiziertes PITR
- Air-Gap-Betrieb, GPU-Workloads, Native-Autoscaling und hostile Multi-Tenancy
- CNCF-Zertifizierung oder unabhängiges Security-Audit

Diese Bereiche bleiben geplante beziehungsweise experimentelle Erweiterungen. Sie blockieren den ersten Native-Single-Host-Release nicht, dürfen aber auch nicht als bestanden dargestellt werden.

## Verbindliche Production-Gates

Für denselben unveränderten Commit und dieselben Artefakte müssen mindestens folgende Nachweise vorliegen:

- reproduzierbarer Build, Commit-/Artefakt-Digest und SBOM;
- grüne Unit-, Race-, Static-, Source- und Vulnerability-Prüfungen;
- reale Installation auf einem frischen, entbehrlichen Ubuntu-24.04-Host;
- realer Docker-/etcd-Betrieb mit Workload-Lifecycle und Neustart;
- lokales Backup/Restore mit Integritätsprüfung;
- unterstütztes Single-Host-Upgrade und Rollback;
- begrenzter Single-Host-Load-/Soak-Test;
- sichere Defaults und negative Autorisierungstests;
- signierte oder anderweitig verifizierbare Release-Artefakte und Provenienz;
- vollständige Single-Host-Runbooks, Release-Notes und abschließende Go/No-Go-Prüfung.

Die vorhandene CI kann den Single-Host-E2E-Lauf auf einem ephemeren ubuntu-24.04-Runner ausführen. Dafür sind keine sieben VMs erforderlich. Der Lauf muss ausdrücklich gestartet und an den exakten Release-Kandidaten gebunden werden.

## Weiterer Weg

Nach diesem Release kann der Supportumfang schrittweise erweitert werden:

1. Native Single-Host Production
2. Native Multi-Host/HA
3. Kubernetes-Production
4. Cloud-, Recovery- und erweiterte Datenbankprofile

Der bisherige vollständige Masterplan in release/production-scope.json bleibt als späterer HA-/Kubernetes-Qualifikationsvertrag erhalten.