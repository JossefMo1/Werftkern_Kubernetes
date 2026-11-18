# Werftkern: Veröffentlichung als eigenständiges Open-Source-Projekt

**Aktuelles Repository:** `JossefMo1/Werftkern_Kubernetes` (PUBLIC seit
2026-10-15 auf ausdrückliche Anweisung des Repository-Eigentümers). Das
Repository wurde bereits angelegt; die frühere Anleitung zur Erstellung eines
neuen `ClusterPilot-System/werftkern`-Repositories ist überholt.

**Entscheidung: PUBLIC-Source ist erfolgt; Produktionsfreigabe bleibt HOLD, bis
alle Bedingungen in [OPEN-SOURCE-LAUNCH-CHECKLIST.md](OPEN-SOURCE-LAUNCH-CHECKLIST.md)
und den Produktionsqualifikationsverträgen erfüllt sind.**

Die Quellen enthalten zwei getrennte, experimentelle Komponenten:
Werftkern Kubernetes `0.1.0-dev.3` (k0s/k0sctl-basiert) und Werftkern
Native Runtime `0.2.0-dev.4` (kein Kubernetes-Ersatz). Die öffentlichen
Quell-Prereleases `v0.1.0-alpha.1`, `v0.1.0-alpha.2` und `v0.1.0-alpha.3`
existieren bereits. `release/alpha-version.txt` nennt aktuell
`v0.1.0-alpha.3`. Diese Tags bleiben
unverändert. Neue Dokumentationsänderungen sind erst nach Merge auf `main`
sichtbar und gehören nicht rückwirkend zu diesen Releases. Eine öffentliche
Quell-Alpha ist keine Produktions- oder CNCF-Freigabe.

## Rechte und Sicherheitsgrenzen

`LICENSE` nennt Apache-2.0. `NOTICE.md` nennt ClusterPilot-bezogene
Provenienz. Das ist kein unabhängiger Nachweis, dass sämtliche betroffenen
Urheber- und Nutzungsrechte übertragen wurden. Der Repository-Eigentümer muss
diese Rechte sowie Fremdlizenzen und Geheimhaltungsverpflichtungen weiterhin
für jede Produktions- oder kommerzielle Freigabe explizit bestätigen. Die
Public-Sichtbarkeit ist kein solcher Nachweis.

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
- Branchschutz, Pull-Request-Reviews, Dependabot, Secret Scanning, Push
  Protection und Private Vulnerability Reporting sind nach der Public-
  Umstellung live verifiziert; ein unabhängiger Reviewer für die geschützte
  PR-Pipeline muss noch hinzugefügt werden.
- Keine öffentlichen Kunden-, Cloud-, Kubeconfig-, SSH-, PKI-, Backup-
  oder persönlichen Daten. Keine privilegierten Tests von fremden Forks
  auf langlebigen selbstgehosteten Runnern.

## Bestehende Alpha-Releases

Die überprüfbaren Versionshinweise befinden sich in
[releases/v0.1.0-alpha.1.md](../releases/v0.1.0-alpha.1.md),
[releases/v0.1.0-alpha.2.md](../releases/v0.1.0-alpha.2.md) und
[releases/v0.1.0-alpha.3.md](../releases/v0.1.0-alpha.3.md).
Die Freigaben und Schritte für den PUBLIC-Wechsel stehen in der
[Checkliste](OPEN-SOURCE-LAUNCH-CHECKLIST.md).

Der [Prüfbericht vom 12. Oktober 2026](validation/PUBLICATION-REVIEW-2026-10-12.md)
trennt nachgewiesene GitHub-Ergebnisse von offenen Freigaben. Der PUBLIC-Wechsel
am 2026-10-15 hat bestehende Tags, Releases und erreichbare Historie öffentlich
gemacht. Bei jeder weiteren Veröffentlichung müssen daher nicht nur die aktuelle
README, sondern auch alle erreichbaren Refs geprüft werden.

## Go module identity

For commits after the issue #6 module migration, the canonical Go module and
internal imports use `github.com/JossefMo1/Werftkern_Kubernetes`, matching the
actual GitHub remote. The earlier private `v0.1.0-alpha.1` tag predates this
migration, so do not retroactively claim that it used the new module path.
This does not establish endorsement by Kubernetes or ClusterPilot.
