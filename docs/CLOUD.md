# Cloudbereitstellung und SSH-Bootstrap

Enthalten ist ein ausführender Hetzner-HTTP-Adapter, kein bloßer Planexport. **In dieser
Auslieferung wurden keine Provideraufrufe durchgeführt und keine kostenpflichtigen
Ressourcen erzeugt.** Die reale API-/Account-/Quotaqualifikation steht aus.

```sh
werft-ops cloud plan --file examples/hetzner-plan.json
# Nur nach Prüfung von Kosten, Region, Image, Netz und Firewall:
werft-ops cloud apply --file /root/reviewed-plan.json --journal /root/provision.json \
  --token-file /root/hetzner.token --confirm-plan EXAKTER_PLAN_SHA256 --accept-costs
```

Das Token muss in einer eigenen regulären Datei mit Modus0600 liegen. Nicht als Argument,
Umgebungsvariable, URL oder GitHub-Secret in ungeschützten Fork-Workflows einsetzen.
Die API-URL ist fest; Redirects werden nicht gefolgt. Providerantworten mit Secrets
werden nicht in Fehlerausgaben kopiert. Der Plan besitzt ein Maximum von20 VMs.
Vorhandenes privates Netzwerk mit Subnetz, Firewall und SSH-Key werden anhand ihrer
expliziten IDs geprüft. Standort und numerische Image-ID werden fixiert. Der Plan
liefert **keine aktuelle Preisberechnung**. Öffentliche IPv4 für Paketzugriff ist im
Implementierungspfad aktiviert; Firewallzugriff muss bereits passend eingeschränkt sein.

VM-CREATE wird vor dem Aufruf persistent journalisiert. Bei verlorener Antwort führt
der nächste Lauf nur eine Namen-/Label-/ID-/Image-/Netzprüfung aus. Erzeugung wird nicht
blind wiederholt. Ein unklarer oder noch nicht sichtbarer Providerzustand blockiert.
Fremde vorhandene Ressourcen werden nicht adoptiert, kein Destroy/Terminate ausgeführt.
Manuelle Auflösung von Quota-/abgelehnten Create-Intents ist noch kein vollautomatischer
Reconciler. AWS/Azure/IONOS, dynamische Preis-/Imagewahl, automatische Netzwerk- und
Firewallerstellung sowie VM-Skalierung fehlen.

Die gespeicherten privaten Adressen sind Input für Mesh-/HA-Topologien. Für SSH-Bootstrap:

```sh
werft-ops bootstrap --host /root/host-spec.json --package ./werftkern.deb \
  --kit /root/control-1.kit.json --known-hosts /root/verified_known_hosts \
  --confirm-host control-1
```

Host-Spezifikation: `name`, `address` (erreichbare SSH-IP), `sshUser`, `packageSha256`.
SSH-Schlüssel und Hostkeys müssen zuvor über einen vertrauenswürdigen Kanal eingerichtet
sein. Kein StrictHostKeyChecking=no, kein ungeprüftes ssh-keyscan, keine Passwortkopie.
Der SSH-Bootstrap überträgt ein gehashtes Paket und Kit, verwendet `sudo -n` und führt
`werft ha install` aus. Das vorausgesetzte sichere SSH-Vertrauen und ein eventuell
benötigtes WireGuard-Bootstrap werden nicht heimlich durch unsichere Defaults ersetzt.
Hashprüfung beim Transfer ist kein Ersatz für eine vertrauenswürdig signierte Release.
