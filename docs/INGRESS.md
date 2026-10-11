# Separater HTTPS-Ingress

Experimenteller Go-HTTP-Reverse-Proxy. Er benötigt weder Kubernetes noch einen öffentlich
exponierten Adminclient. Er ist **kein Envoy**, kein Loadbalancer-VIP und keine NetworkPolicy.

## Getrennte Identität anlegen

Auf einem Controller mit Adminclient und lokaler Client-CA:

```sh
sudo werft gateway enroll --name edge-1 --services web,api --out /root/edge-1
sudo werft gateway list
```

Das neue private Verzeichnis enthält gateway.crt/key, ca.crt, gateway.json und
`ingress.example.json`. Beitrittswiederholung benutzt denselben Pfad/ID; unbekannte oder
unvollständige vorhandene Verzeichnisse werden nicht überschrieben. Ein optionaler
fehlgeschlagener Register-ACK erfordert Wiederholung mit demselben Verzeichnis.

Nur autorisierte Dienste in die Allowlist aufnehmen. Gateway darf daraus Discovery lesen,
aber keinen Clusterstatus, keine fremden Dienste/Secrets, keine Node-Heartbeats und keine
Admin-Mutationen. Sperren: `sudo werft gateway revoke GATEWAY_ID`. Rücknahme ist bei isoliertem
Gateway erst nach dessen nächster fehlgeschlagener Abfrage/Frischefrist wirksam, nicht instantan.

## Konfiguration

Dateien sicher auf den Edgehost übertragen. Keine private CA mitliefern. In
`ingress.example.json` die generierten `client`- und `gatewayId`-Werte behalten; ändern:

```json
{
  "listen": "10.10.0.20:8443",
  "public": false,
  "certificate": "edge.crt",
  "privateKey": "edge.key",
  "allowedCidrs": ["10.10.0.11/32", "10.10.0.12/32"],
  "upstreamMode": "private-http",
  "routes": [
    {"host": "app.example.org", "service": "web"},
    {"host": "api.example.org", "service": "api"}
  ]
}
```

Das ist ein Ausschnitt, nicht Ersatz der vollständigen Datei: `client` und `gatewayId`
bleiben zwingend. Exakte private Node-/Pod-CIDRs aus eigener Topologie übernehmen. Zertifikat
und Schlüssel von eigener geprüfter CA/Issuer bereitstellen; alle Routen müssen im SAN stehen.
Keine automatisierte ACME-Registrierung, Domainbuchung oder Zertifikatsrotation. A/AAAA-Einträge
und Portzuordnung sind bewusst externe Betreiberentscheidungen. IPv4-Upstreams, Ports>=1024.

```sh
sudo werft ingress --config /root/edge-1/ingress.example.json
```

Der Prozess läuft im Vordergrund; der Betreiber kann ihn als separat gehärteten Dienst mit
Zugriff ausschließlich auf diese Identität betreiben. Keine automatische Public-Freigabe.
`public:true` ist eine explizite Wahl für nicht-private Bindings, kein Firewall- oder TLS-Trustnachweis.
Kein Admin-Dashboard auf diesem Listener. Kein Adminzertifikat als Ersatzgateway erlaubt.

## Verhalten und Grenzen

TLS mindestens1.3, gültiges Leaf/SAN beim Start. HTTP-Host muss TLS-SNI entsprechen; keine
Wildcard-/beliebigen Proxyziele. Aufrufe gehen nur an derzeit zulässige private Endpoints.
Discoveryalle3s; Fehler entziehen Routen, maximal15s Snapshotfrische. Wiederherstellung nach
kurzer Störung akzeptiert dieselbe unveränderte Revision; veraltete Inhalte bleiben verboten.

Readiness beeinflusst Routing, ist aber kein fachlicher Transaktions-/Verfügbarkeitsbeweis.
POST wird nicht bewusst wiederholt; Anwendungsidempotenz bleibt notwendig. Authorization und
Cookies der Anwendung bleiben erhalten; gefälschte Forwarding-/Proxyidentität wird ersetzt.
8MiB Requestmaximum, bekannte Content-Length,16KiB Header,256 gleichzeitige Anfragen,
begrenzte Verbindungs-/Antwortzeiten. Streaming, WebSocket, HTTP-Upgrade, CONNECT, TRACE
und Requests unbekannter Länge sind nicht unterstützt. Keine vollständige HTTP/2-/gRPC-Zusage.

TLS endet am Edge. `private-http` ist Klartext auf dem Transport bis zum Worker, sofern der
separat konfigurierte/qualifizierte WireGuardpfad ihn nicht schützt. Private IP allein ist
keine Verschlüsselung. Kein automatisch durchgesetztes mTLS zur Anwendung.

Lokal getestet: echte TLS-Anfragen/HTTP-Upstreams, Header, SNI, Frische, ACL und abgebrochener
POST. Nicht getestet: reale Worker-Container, öffentliche DNS/TLS, Mesh, zwei Edgehosts,
DoS/WAF, Dauertest und unabhängige Sicherheitsprüfung.
