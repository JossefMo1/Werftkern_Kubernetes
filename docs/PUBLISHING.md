# Veröffentlichung als eigenes Open-Source-Repository

Vorgeschlagener Name: `werftkern`. Der Modulpfad verwendet
`github.com/ClusterPilot-System/werftkern`; dies behauptet nicht, dass dieser Remote
bereits existiert. Bei anderem Eigentümer den Modulpfad und Imports bewusst anpassen.

**Nicht das private ClusterPilot-Repository öffentlich schalten.** Dieses Projekt besitzt eine
separate Historie und keine privaten Geschäftspläne, Keys oder Releaseartefakte daraus.
`LICENSE` ist Apache-2.0, der angepasste Designanteil wird in `NOTICE.md` genannt.
Der Eigentümer muss Rechte und gewünschte Lizenz vor der tatsächlichen Veröffentlichung prüfen.

## Aus der ZIP-Datei

```bash
cd werftkern
git init -b main
git add .
git commit -m "Initial experimental Werftkern source"
gh auth login
bash scripts/publish-github.sh DEIN-ACCOUNT/werftkern --public
```

Oder die separat mitgelieferte Git-Bundle-Historie mit `git clone DATEI.bundle werftkern`
übernehmen, dann das lokale Bundle-Origin entfernen und erst den neuen Remote anlegen.
Eine vorhandene `origin` wird vom Skript nicht überschrieben. Der öffentliche Schritt benötigt
interaktive Bestätigung des exakten Repositorynamens. Keine Tokens in Chat oder Argumente kopieren.

Das Skript erstellt **keine Produktionsrelease**, ändert keine Branchschutzregeln und erfindet
keine GitHub-Actions-Ergebnisse. Eine öffentliche Entwicklungs-Alpha ist zulässig; sie darf nicht
als vollständige Produktionsimplementierung beworben werden.

## Vor öffentlichem Start im GitHub-Repository einstellen

Private Vulnerability Reporting aktivieren; Maintainer/Reviewzuständigkeiten festlegen;
Standardbranch schützen; erforderliche CI-Checks und Review erzwingen; Schreibrechte minimieren.
Privilegierte VM-Tests nur explizit auf ephemeren runnern mit qualifiziertem Source-Commit,
niemals mit Fork-Secrets oder auf produktiven selbstgehosteten runnern ausführen.

## Freigaben

`release/qualification.json` ist absichtlich nicht freigegeben.
`python3 scripts/check-release.py --commit "$(git rev-parse HEAD)"` muss derzeit BLOCKED liefern.
Die Konsistenzprüfung verlangt 52 Planreferenzen, ausgeführte Gates, passenden Commit und
Hashes vorhandener Evidenzdateien. Sie prüft **nicht**, ob jemand einen Testbericht erfunden hat:
Authentizität muss durch geschützte Runner, Provenance und unabhängige Freigabe abgesichert werden.
Keine Selbstattestierung durch Umschalten von `passed` oder `productionReady`.
