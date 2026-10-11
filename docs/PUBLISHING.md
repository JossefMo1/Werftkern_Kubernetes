# Werftkern: Veröffentlichung als eigenständiges Open-Source-Projekt

**Aktuelles Repository:** `JossefMo1/Werftkern_Kubernetes` (zunächst PRIVATE).
Das Repository wurde bereits angelegt; die frühere Anleitung zur Erstellung
eines neuen `ClusterPilot-System/werftkern`-Repositories ist überholt.

**Entscheidung: HOLD für PUBLIC und GitHub Release, bis alle Bedingungen in
[OPEN-SOURCE-LAUNCH-CHECKLIST.md](OPEN-SOURCE-LAUNCH-CHECKLIST.md) erfüllt sind.**

Die Quellen enthalten zwei getrennte, experimentelle Komponenten:
Werftkern Kubernetes `0.1.0-dev.3` (k0s/k0sctl-basiert) und Werftkern
Native Runtime `0.2.0-dev.4` (kein Kubernetes-Ersatz). Die erste angestrebte
öffentliche Quellversion ist `v0.1.0-alpha.1` als ausdrücklich markierte
**Pre-Release**, nicht als Produktions- oder CNCF-Freigabe.

## Rechte und Sicherheitsgrenzen

`LICENSE` nennt Apache-2.0. `NOTICE.md` nennt ClusterPilot-bezogene
Provenienz. Das ist kein unabhängiger Nachweis, dass sämtliche betroffenen
Urheber- und Nutzungsrechte übertragen wurden. Der Repository-Eigentümer
muss diese Rechte sowie Fremdlizenzen und Geheimhaltungsverpflichtungen
explizit bestätigen, bevor die Quellen allgemein zugänglich werden.

Ein ignoriertes Secret kann weiterhin in alten Git-Objekten vorkommen.
Der historische Scanner (`scripts/audit-git-history.py`) erkennt nur
bestimmte Muster. Vertrauliche Inhalte sind unabhängig zu prüfen, betroffene
Schlüssel zu widerrufen und gegebenenfalls die komplette veröffentlichte
Historie vor dem ersten PUBLIC-Schritt neu aufzubauen.

## Automatisierte Schutzmaßnahmen

- `.github/workflows/publication-audit.yml` prüft Quellbaum und
  erreichbare Git-Historie mit readonly Checkout. Die bestehenden
  CI-Workflows prüfen Entwicklungs- und Kontrakttests.
- Die Release-Qualifikation in `release/qualification.json` bleibt
  absichtlich **BLOCKED**. JSON-Felder allein sind keine Freigabe.
- Branchschutz, Pull-Request-Reviews und Dependabot-Einstellungen müssen
  nach dem verfügbaren GitHub-Plan geprüft werden. Auf kostenlosen Plänen
  lässt sich Branchschutz für private Repositories ggf. erst nach dem
  PUBLIC-Schritt aktivieren; in dem Fall zuerst unabhängig prüfen und
  direkt nach PUBLIC konfigurieren. GitHub private Vulnerability Reporting
  ist nur bei öffentlichen Repositories aktivierbar. GitHub Secret
  Scanning/Push Protection für private Repositories hängt vom Plan ab;
  eine unabhängige Vorabprüfung ist daher zwingend.
- Keine öffentlichen Kunden-, Cloud-, Kubeconfig-, SSH-, PKI-, Backup-
  oder persönlichen Daten. Keine privilegierten Tests von fremden Forks
  auf langlebigen selbstgehosteten Runnern.

## Erste Alpha

Die überprüfbaren Versionshinweise befinden sich in
[releases/v0.1.0-alpha.1.md](../releases/v0.1.0-alpha.1.md).
Die exakten Tag-/Release-Befehle und menschlichen Freigaben stehen in der
[Checkliste](OPEN-SOURCE-LAUNCH-CHECKLIST.md).

Ein GitHub-Tag, Release-Artefakt oder erfolgreich durchgelaufener CI-Test
wird durch diese Dokumentation **nicht** behauptet.
