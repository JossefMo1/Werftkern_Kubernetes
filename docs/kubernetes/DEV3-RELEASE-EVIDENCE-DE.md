# Signierte Freigabenachweise, ohne erfundene Produktionsfreigabe

**Der Prüfer verifiziert Signaturen und Dateibindungen. Er führt keine Livequalifikation
aus und beweist nicht, dass ein autorisierter Unterzeichner wahrheitsgemäß berichtet.**
Eine CNCF-Annahme oder unabhängige Sicherheitsprüfung lässt sich nicht durch Signieren
synthetischer Testdaten ersetzen.

```bash
werft-kube qualification --candidate /secure/candidate/candidate.json \
  --trust /etc/werftkern/release-trust/trust.json --trust-sha256 FREIGEGEBENER_TRUST_SHA256
```

Der Trust-Pfad muss außerhalb des Kandidatenverzeichnisses liegen. Der von einem
vertrauenswürdigen Kanal erhaltene SHA256 bindet die gesamte Trust-Konfiguration.
Sie enthält freigegebene Public-Key-Hashes, Rollen, Organisationen und Gültigkeitsfristen.
Das Kandidatenpaket kann nicht seine eigenen Freigabeschlüssel mitbringen. Private
Signierschlüssel gehören nicht auf Worker, in den Source-Tree oder in dieses Paket.

## Kryptografischer Vertrag

Format `werftkern-gate-evidence/v1`, Signatur über kanonische JSON-Bytes (sortierte
Schlüssel, ASCII-Escaping, kompakte Separatoren, keine NaN-/Infinity-Zahlen). Ed25519
über OpenSSL; Base64-Signatur im Envelope. Dies ist ein eigener Verifikationsvertrag,
**kein Sigstore-Bundle, keine DSSE-Implementierung und keine SLSA-Level-Zertifizierung**.
Produzenten müssen diese exakten Bytes signieren. Der Prüfer signiert nicht selbst.

Jeder Nachweis bindet Gate, Commit, Paket-SHA256, Assets-SHA256, Anfang/Ende,
Umgebungsart/Identitäten und Hashes der Rohbelege. Es gelten kurze Gültigkeitsfristen,
keine mehrfachen Gates, keine Symlink-/Traversalreferenzen und keine stillen fehlenden
Belege. Getrennte Rollen: Builder, Qualifier, unabhängiger Reviewer, Release-Manager
und Zertifizierungsprüfer. Builder und unabhängiger Reviewer dürfen weder dieselbe
Schlüsselidentität noch dieselbe konfigurierte Organisation haben. Ob die behauptete
organisatorische Unabhängigkeit wirklich vorliegt, bleibt externe Governance.

## 14 zwingende Gates

`ubuntu-e2e`, `ha-chaos`, `cloud-lifecycle`, `controller-stateful-recovery`,
`pv-database-restore`, `sso-rbac`, `acme`, `sonobuoy-conformance`, `upgrade-rollback`,
`load-soak`, `supply-chain`, `independent-security`, `cncf-acceptance`, `release-approval`.

Real-Gates akzeptieren keine Umgebungsart `fixtures`. Eine signierte Behauptung
`real-vm` ersetzt aber nicht den externen Review der Rohbelege. Der Supply-Chain-Nachweis
muss nichtleere CycloneDX-, Trivy-v2- und in-toto/SLSA-Provenancedokumente enthalten.
Artifact, Builder, Sourcecommit und Asset-Lock werden verglichen. HIGH, CRITICAL und
UNKNOWN-Vulnerabilities blockieren. Das ist eine konservative Parser-/Policyprüfung,
kein durch diesen Prüfer ausgeführter Vulnerability-Scan. Abdeckung und Aktualität der
Scanner-Datenbank/Abhängigkeiten müssen im freigegebenen Build-/Reviewprozess belegt sein.

Die CNCF-Prüfung benötigt einen Verweis auf eine konkrete offizielle Conformance-PR
und einen autorisierten externen Entscheidungsnachweis. Der Offlineprüfer fragt den
Mergezustand nicht online ab und erteilt niemals selbst eine Zertifizierung.

## Ergebnis und reale Lieferkette

Bei vollständigen, gültig signierten Belegen: `SIGNED_EVIDENCE_VERIFIED` und
`eligibleForReleaseReview=true`. Das ist ein Eingang für eine geschützte menschliche
Releasefreigabe, nicht deren Ersatz. `productionReady` und `cncfCertified` werden
von diesem Werkzeug niemals auf true gesetzt. Fehlende Gates liefern Exit3/BLOCKED;
ungültige Eingaben oder Signaturen Exit2/BLOCKED.

Der alte Konsistenzprüfer in `scripts/check-release.py` setzt ebenfalls keine
Produktionsfreigabe mehr allein aus JSON-Statuswerten. Bestehende Tests wurden an
diesem tatsächlichen Verhalten erneut ausgeführt.

In diesem Arbeitslauf wurden echte temporäre Ed25519-Testschlüssel/Signaturen erzeugt
und manipulierte Signaturen abgewiesen. Die signierten Testaussagen waren ausdrücklich
synthetisch. Es gibt **keine Produktionssignatur, keine durchgelaufene signierte CI,
keinen neuen CVE-Scan und keine unabhängige Freigabe**. Das gelieferte `.deb` bleibt
unsigniert. Die vorhandene GitHub-CI wurde nicht gestartet.

## Primärquellen

- SLSA Provenance: https://slsa.dev/spec/v1.1/provenance
- Sigstore-Verifikation (für späteren geschützten Signierworkflow): https://docs.sigstore.dev/cosign/verifying/verify/
- CNCF-Verfahren: https://github.com/cncf/k8s-conformance/blob/master/instructions.md
