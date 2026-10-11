# Werftkern Kubernetes 0.1.0-dev.2

Entwicklungsstand, keine Produktionsfreigabe.

- Control-Plane-Backup-Receipt v2 bindet Cluster-UID, Quellplan und Controlleradressen.
- Neuer restart-sicherer `restore`-Workflow für frische Zielcontroller. Mehrdeutige
  Restore-Ausführung wird nur beobachtet, nie blind erneut ausgeführt.
- HA-Pläne müssen eine API-HA-Strategie deklarieren. Neben externem LB unterstützt der
  Renderer k0s Keepalived-CPLB mit privater VRRP-Passdatei sowie NLLB/Envoy für Worker.
- Neuer `cloud-scale`-Workflow verbindet Hetzner-Provisionierung mit dem bestehenden
  Kubernetes-Lifecycle. Providerlöschung erfolgt erst nach Kubernetes-Scale-down.
- Produktionsstatus bleibt blockiert: keine echte VM-/Netz-/Restore-/Providerabnahme.
