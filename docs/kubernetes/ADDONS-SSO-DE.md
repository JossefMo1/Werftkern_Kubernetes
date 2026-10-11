# Add-ons und Keycloak-SSO

**Implementierter Integrationscode, keine produktionsgeprüfte Plattform.**
`werft-kube addons plan --spec addons.json` zeigt Abhängigkeiten und Planhash.
`addons apply --spec ... --confirm HASH` arbeitet mit denselben privaten Cluster-
Credentials und derselben Clustersperre wie Lifecycle/Repair.

## Katalog und tatsächliche Anbindung

| Baustein | Umsetzung | Zusätzliche Voraussetzung |
|---|---|---|
| Traefik | Helm, zwei Replikate, Dashboard-Ingress deaktiviert | Reales Service-LB/NodePort-Routing, DNS und Firewall; kein automatischer Cloud-LB |
| cert-manager | Helm inkl. CRDs, Beibehaltung von CRDs | ACME-Egress, eingehendes HTTP01, gültiges DNS und explizite Produktions-ACME-Einwilligung |
| Keycloak Operator | Geprüfte lokale YAML inkl. CRDs und Deployment | Operator-Namespace `identity`; alle Images gepinnt |
| Keycloak Server | CR, zwei Instanzen, TLS-geprüfte externe PostgreSQL-Verbindung, Edge-Proxy und Netzwerkgrenze | Externe DB inkl. Backup/Restore/HA; Secrets und CA vorab |
| Kubernetes OIDC | Keycloak-Realm, PKCE-Public-Client, API-OIDC und Gruppen-RBAC | Echte Benutzer, MFA/Recovery, gültiger Issuer; Auth-Browserpfad noch ungetestet |
| Grafana | Helmwerte für Keycloak-OAuth, Secretreferenz, exakte Redirect-URI, Viewer/Editor-Zuordnung | kube-prometheus-stack-Chart mit kompatiblem Grafana, explizite Storage- und Retentionwerte |
| Velero | Versioniertes lokales Helm-Chart | Externes Backupziel, Cloud-/Speichertreiber, Secret und Restoreprüfung; Installation ist kein Backup |
| Hetzner CSI | Versioniertes lokales Helm-Chart | Explizite Providercredentials, Treiber-/k0s-Konfiguration und Volume-Tests |
| Argo CD | Versioniertes lokales Helm-Chart | Eigene Sicherheits-/Storage-/SSO-Werte; **kein vorkonfiguriertes Keycloak-SSO in dieser Lieferung** |

Nicht jede beliebige Chartversion/-Wertekombination ist freigegeben. Kubernetes-
Kernservices CNI/DNS/etcd kommen aus k0s, nicht aus diesen optionalen Charts.
Ingress-NGINX ist wegen des angekündigten Wartungsendes nicht Standard.

## Überprüfte Artefakte statt Installationslinks

`assets.json` bindet lokal vorhandene Charts, Operator-YAML und Tools per Version und
SHA256. Images der gerenderten Deployments/Jobs müssen `@sha256:...` tragen.
Daher brauchen viele Charts konkrete Image-Digest-Overrides. Welche Values-Felder
dafür nötig sind, hängt vom festgelegten Chart ab. Automatisch erzeugte Secretwerte
in Chartausgaben sind gesperrt; vorab erzeugte Secrets über `existingSecret` bzw.
das dokumentierte Chartäquivalent anbinden. Die Beispiele sind keine fertigen
Hersteller-Releasewerte. Das Helm-Rendering wird ohne reale Charts hier nicht geprüft.

Chartdateien sind ausführungsnahe, vom Administrator freizugebende Eingaben. Die
Image-/Secretprüfung ist keine vollständige Admission Policy oder Sandbox: CRDs,
RBAC, Hooks, Volumes und privilegierte DaemonSets brauchen einen eigenen Review.
Die automatische Installation beliebiger nicht freigegebener Internet-Charts ist
bewusst nicht implementiert. Helmplugins und Umgebungs-Overrides werden nicht geerbt.

## Upgrade und Fehlersemantik

Eigene Helmreleases besitzen eine operationgebundene Description und persistierte
Revision. Fremde Releases werden nicht übernommen. `--atomic --wait` ist kein
Datenbank-Rollback und macht CRD-Migrationen nicht rückgängig. Nach einem verlorenen
Helm-ACK liest die Wiederholung Releasezustand und Operationsbindung. Pending/Failed
oder widersprüchliche Releases werden nicht blind erneut aktualisiert. Die
Clustersperre bleibt für Diagnose stehen. `helm status`, Journale und Events prüfen;
keine Dateien löschen, um einen unklaren Installationszustand zu verschleiern.

## Keycloak-Datenbank und Netzwerk

In `identity` müssen die referenzierten DB-Secrets `username` und `password` sowie
die CA-Datei `ca.crt` bereits bestehen. Der Keycloak Operator verwaltet **keine**
Datenbank. Es gibt keinen stillen Dev-Postgres und kein Standardpasswort.
`db-tls-mode=verify-server` und die Secret-basierte Truststore-Konfiguration sind
Teil des CR-Vertrags. Versionskompatibilität praktisch prüfen.

TLS endet standardmäßig am Traefik-Ingress. Der folgende HTTP-Upstream ist **nicht**
automatisch verschlüsselt. Die NetworkPolicy begrenzt Keycloak-HTTP auf den vertrauten
Ingress-Namespace; Identitäts-Namespace, Operator und Ingress werden ausschließlich
von Administratoren verwaltet. Ungeprüfte Ingress-Ressourcen oder gleichberechtigte
Nutzer in `identity` könnten diese Vertrauensgrenze umgehen. Interne TLS-Verschlüsselung,
Egress-Policies, administrative UI-Beschränkung und deren echte Wirksamkeit sind
zusätzliche Produktionsaufgaben. Der ausgewählte CNI muss Policies wirklich durchsetzen.

## Realm und SSO

Das Realm wird einmal über `KeycloakRealmImport` erzeugt. Ein später geänderter
Realmplan wird geblockt – Import ist kein laufender Realm-Reconciler. Keine
Benutzer oder Standardpasswörter werden angelegt. Der Operator erzeugt seine
Bootstrap-Admincredentials; diese vor Produktion ablösen und MFA aktivieren.

Der Public-Client `werft-kubectl` verwendet Authorization Code + PKCE S256 und
Loopback-Redirects für das Benutzergerät. Password Grant ist aus. `viewers` wird
als `oidc:viewers` an die Kubernetes-Rolle `view` gebunden, nicht `cluster-admin`.
Ein Benutzer erhält dadurch keine pauschalen Cluster-Adminrechte. Gruppenmanagement
und weitergehende Namespace-Berechtigungen erfolgen ausdrücklich.

Für Grafana werden ein eigener Clientsecret und ein Break-Glass-Adminpasswort
zufällig erzeugt und privat gespeichert. Secretreferenzen statt Werte in Helmfiles.
Realm- und Grafana-Secretkopien haben getrennte Namespaces. Ein vorhandenes Secret
bei fehlender lokaler Wiederherstellungsdatei wird nicht still ersetzt. Rotation
ist noch ein koordinierter Betreiberprozess, kein fertiger automatischer SSO-Lifecycle.

```bash
werft-kube --root ROOT --assets ASSETS addons apply --spec addons.json --confirm HASH
werft-kube --root ROOT --assets ASSETS sso plan
werft-kube --root ROOT --assets ASSETS sso enable --confirm OIDC_PLAN_HASH
werft-kube --root ROOT --assets ASSETS sso client-config --out user-kubeconfig.json
```

Die Benutzerkubeconfig enthält **keinen Admin-Clientschlüssel**. Sie verlangt den
separat überprüften `kubectl oidc-login`-Client auf dem Benutzergerät. Danach echte
Anmeldung und Rechte prüfen:

```bash
KUBECONFIG=user-kubeconfig.json kubectl auth whoami
KUBECONFIG=user-kubeconfig.json kubectl auth can-i list pods --all-namespaces
KUBECONFIG=user-kubeconfig.json kubectl auth can-i get secrets --all-namespaces
```

Für reine Viewer muss der letzte Test `no` liefern. Grafana-Login, Logout,
Tokenablauf, MFA, Recovery und verbotene Aktionen separat testen. Eine erfolgreiche
Issuer-Discovery und `Ready`-Pods sind **kein** erfolgreicher Benutzer-Login.
