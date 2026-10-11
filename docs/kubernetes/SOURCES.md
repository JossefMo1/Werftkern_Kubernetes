# Technische Primärquellen

Abgerufen am 25. September 2026. Dokumentation ist kein geprüfter Artefakt-Digest und
kein Beweis, dass die hier implementierte Integration bereits live funktioniert.

- k0sctl Konfiguration, OpenSSH-Transport, Reset, Backup/Restore und Apply:
  https://github.com/k0sproject/k0sctl
- k0s-Versionen und Komponenten:
  https://k0sproject.io/
- k0s Backupgrenzen (PV-Daten nicht enthalten):
  https://docs.k0sproject.io/stable/backup/
- k0s OIDC:
  https://docs.k0sproject.io/v1.35.5%2Bk0s.0/examples/oidc/oidc-cluster-configuration/
- Kubernetes Drain / Eviction:
  https://kubernetes.io/docs/reference/kubectl/generated/kubectl_drain/
- Ingress-NGINX Ruhestand:
  https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/
- Traefik Helm:
  https://github.com/traefik/traefik-helm-chart
- cert-manager Helm/CRDs:
  https://cert-manager.io/docs/installation/helm/
- Keycloak Operator, externe DB, TLS, Forwarded-Header-Sicherheitsgrenze:
  https://www.keycloak.org/operator/basic-deployment
- Keycloak Truststores / Datenbank-TLS:
  https://www.keycloak.org/server/keycloak-truststore
  https://www.keycloak.org/server/db
  https://www.keycloak.org/operator/advanced-configuration
- Keycloak Realm-Import:
  https://www.keycloak.org/operator/realm-import
- Sonobuoy Run- und Retrieve-Flags:
  https://sonobuoy.io/docs/v0.57.4/cli/sonobuoy_run/
  https://sonobuoy.io/docs/v0.57.4/cli/sonobuoy_retrieve/
- Sonobuoy JSONL-Ergebnisse / Status:
  https://sonobuoy.io/docs/v0.57.4/results/
  https://sonobuoy.io/docs/main/cli/sonobuoy_status/
- CNCF Konformitätsprogramm / Einreichungsanforderungen:
  https://www.cncf.io/training/certification/software-conformance/
  https://github.com/cncf/k8s-conformance/blob/master/instructions.md
- Hetzner Cloud API:
  https://docs.hetzner.cloud/reference/cloud

Keine Namens-/Markenfreigabe oder Übernahme einer Herstellerzertifizierung. Die
Generierung eines Berichts, ein Helm-Release oder ein Git-Commit sind keine Prüfung
bzw. Freigabe durch CNCF oder die jeweiligen Hersteller.
