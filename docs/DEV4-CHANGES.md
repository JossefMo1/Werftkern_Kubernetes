# dev.4 — Änderungsschnitt

- Reproduzierter dev.3-Fehler: eine alte Readiness-Beobachtung konnte bei frischem
  Node-Heartbeat als aktuelle Verfügbarkeit zählen. Der Scheduler konnte deshalb eine
  gesunde alte Revision zugunsten einer nur historisch gesunden Surge-Instanz stoppen.
  Scheduler und Discovery verwenden jetzt denselben Frischevertrag. Wiederholte Probes
  behalten ihre ursprüngliche Beobachtungszeit statt durch Empfang neu datiert zu werden.
- Expliziter gleichschemaiger dev.3/dev.4-Agentvertrag. Getestet wird nicht nur eine
  Versionszeichenfolge: ein echtes dev.3-Binary aus Commit 67f5617… wird gestartet,
  beendet und durch das dev.4-Binary ersetzt; Journal/Allocation bleiben erhalten.
  In diesem Test sind TLS und Prozesse real, Docker und etcd aber Testadapter.
- Authentisierte, nodebezogene Leseprojektion `/v1/node-state`; keine fremden
  Node-IDs, Workload-Spezifikationen oder Secret-Werte in der Antwort.
- Operationsgebundener Drain unter weiter gehaltener globaler Wartungssperre;
  unbestätigte Stops und gebundene Workloads bleiben blockierend.
- Sequenzieller signierter Workerupdatekoordinator mit dauerhaftem Journal,
  unveränderlicher Plan-/Trustbindung und beobachtender Wiederaufnahme.
- Lokaler Worker-Smoke über die Docker-Anbindung mit eigener Ownership, HTTP-Prüfung
  und kontrolliertem Cleanup. Implementiert, nicht gegen einen echten Dockerdaemon ausgeführt.
- Tatsächlicher Go→Python-Wirevertrag ist getestet: eine durch `omitempty` ausgelassene
  freie Wartungs-ID wird korrekt erkannt; explizites `null` bleibt ungültig. Das behebt
  blockierten Rolloutstart und eine blockierte Lost-Unlock-ACK-Wiederaufnahme.
- Der echte dev.3-Releaseprüfer authentisiert die Bytes eines gebauten dev.4-.deb
  mit temporärem Testschlüssel und weist eine manipulierte Signatur zurück. Kein
  Produktionsschlüssel, keine freigegebene Signatur und keine dpkg-Installation.
- Readiness-Abnahme akzeptiert pausierte Anwendungen nur bei null laufenden Allocations.

**Nicht neu vorhanden:** allgemeiner replizierter Storage/CSI, voll integrierte DB-Services,
CA-Rotation, vollständige standortweite DR, Workload-NetworkPolicy, HA-Edge, containerd-
Direktadapter, unabhängige Securityqualifikation und echte Ubuntu-/Mehrhostnachweise.
Das ist kein Abschluss des Gesamtmasterplans.
