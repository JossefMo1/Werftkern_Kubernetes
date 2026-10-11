# WireGuard, geroutete Container und Service-DNS

**Implementierter Integrationspfad, noch nicht real auf mehreren Hosts qualifiziert.**
Es handelt sich um WireGuard plus Docker-Bridges, nicht um einen CNI-/CSI-Kompatibilitätsanspruch.

Voraussetzungen: verifizierte Ubuntu-Paketquellen, `wireguard-tools`, `iproute2`,
`iptables`, Docker und ein separat beschafftes, hash-/signaturgeprüftes CoreDNS-Binary
unter `/usr/local/bin/coredns`. Das Werftkern-Paket enthält CoreDNS nicht.
Kein automatischer Download eines unfixierten fremden Binaries.

```sh
werft-ops network prepare --topology examples/mesh-topology.json --out /root/private-mesh
# Auf jedem passenden Zielhost, VOR ha install:
sudo werft-ops network apply --kit /root/control-1.mesh.json --confirm-host control-1
# Nach ha install, noch BEVOR Anwendungen gestartet werden:
sudo werft-ops network enable-dns --kit /root/control-1.mesh.json
```

Der Plan unterscheidet private Underlay-IP (`endpoint`), WireGuard-IP (`address`),
und eindeutiges Container-Subnetz (`podCidr`). Host- und Podnetz dürfen sich nicht
überschneiden. Standardbeispiele sind Beispiele, nicht freigegebene Kundennetze.
Routing/MTU1380 müssen für die tatsächliche Umgebung geprüft werden. Maximal20 Hosts,
IPv4, eine Region, bekannte vertrauenswürdige Workloads eines Betreibers.

Angelegt werden `wgwerft`, Docker-Netz `werft`, Bridge `wkbr0`, IP-Forwarding und
präzise DOCKER-USER-Freigaben zwischen bekannten Cluster-Subnetzen. Bestehende Firewalls
werden nicht geflusht. Netzwerkänderungen mit aktiven Allocations werden verweigert.
Gleichnamige fremde Netzwerke/WireGuard-Konfigurationen werden nicht übernommen.
Das Setup öffnet keine Cloud-Firewall; UDP51820 muss dort separat erlaubt sein.
Inter-Host-Verkehr läuft verschlüsselt über WireGuard, lokale Bridgekommunikation nicht.
Es gibt noch keine Default-deny-Policy pro Anwendung oder Isolation bösartiger Mandanten.

## DNS

Der authentisierte `/v1/discovery`-Read liefert nur Endpoint-Metadaten, keine Secrets.
Ein Node darf nur Container-IPs aus seinem registrierten PodCIDR melden. CoreDNS liest
atomar erzeugte Zonendateien mit niedriger TTL und periodischem Reload:

- `web.svc.werft.`: A-Records gesunder Endpunkte;
- `_tcp.web.svc.werft.`: SRV-Records mit dem tatsächlichen Port;
- `a-ALLOCATION_ID.svc.werft.`: eindeutiger Endpoint.

Im Mesh-Modus ist der Port der Containerport. Ohne Mesh sind es private Node-IP und
veröffentlichter Hostport; dafür SRV verwenden, nicht eine feste Service-IP annehmen.
Nur die Zone `svc.werft` wird beantwortet. Kein öffentlicher rekursiver Resolver, keine
stillschweigende Weiterleitung fremder DNS-Namen. Anwendungen, die externe Namen brauchen,
benötigen einen zusätzlich qualifizierten Resolverpfad. DNS-Round-Robin ersetzt keinen
Loadbalancer oder Envoy-Ingress und garantiert keine gleichmäßige Lastverteilung.

Der Synchronisierer entzieht nach anhaltenden API-Fehlern die Records, statt unbegrenzt
alte grüne Daten auszuliefern. Node-Health/Readiness-Alter wird serverseitig gefiltert.
BindsTo stoppt CoreDNS bei einem gestoppten Synchronisiererdienst. Ein vollständig
hängender Prozess ist damit nicht unabhängig überwacht; ein Watchdog gehört zur
weiteren Qualifikation. Browser-UI-Tests sind keinerlei Netzwerkbeweis.

## Begrenzter HTTPS-Zugriff

Dev.2 ergänzt einen separaten HTTPS-Reverseproxy, siehe INGRESS.md. Er macht den
WireGuardpfad nicht automatisch sicher/verfügbar und implementiert keine NetworkPolicy.
