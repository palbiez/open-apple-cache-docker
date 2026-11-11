# Mac-Helper für die automatische Apple-Discovery

Der Docker-Dienst benötigt zusätzlich den macOS-Helper aus dem Upstream-Projekt.
Ohne erfolgreiche Registrierung entdecken Apple-Geräte den Linux-Cache nicht
automatisch. Ein grüner Container-Healthcheck und der Smoke-Test prüfen diese
Registrierung nicht.

## Vorbereitetes Paket auf dem Mac installieren

Das lokal vorbereitete ZIP `OpenAppleCache-Helper.zip` auf den Mac übertragen und
entpacken. Im angemeldeten Benutzerkonto ein Terminal im Ordner
`OpenAppleCache-Helper` öffnen. Falls die Apple-Entwicklerwerkzeuge fehlen:

```sh
xcode-select --install
```

Die Installation abschließen. Python 3 muss mit `python3 --version` erreichbar
sein. Dann ohne `sudo`:

```sh
sh INSTALL.command
```

Nach einigen Sekunden den Status prüfen:

```sh
cat "$HOME/Library/Application Support/OpenAppleCache/status.json"
```

Erwartet: `"state": "registered"` mit aktuellem `registered_at`-Zeitstempel.
Fehler lokal prüfen:

```sh
tail -n 30 "$HOME/Library/Application Support/OpenAppleCache/registration-error.log"
launchctl print "gui/$(id -u)/org.openapplecache.registration"
```

Das MacBook beim ersten Test wach und im Netzwerk lassen. Der LaunchAgent
erneuert die Registrierung alle 3000 Sekunden. Schlafmodus, Abmeldung und
Abwesenheit können die Erneuerung unterbrechen. Das Intervall ist keine
zugesicherte Ablaufzeit der Registrierung.

Falls Apples eigenes Inhaltscaching auf dem Mac aktiviert ist, für den Test unter
Systemeinstellungen → Allgemein → Teilen → Inhaltscaching deaktivieren. Danach
denselben geeigneten öffentlichen App-/Apple-Download auf zwei Geräten anfordern
und die Cachetreffer beobachten. Mehrere Minuten für die Discovery einplanen.

## Paket aus dem laufenden Container erzeugen

`prepare_mac_helper.py` liest die persistente Cache-ID, die Kapazität und die
Helper-Dateien aus dem vorhandenen Image. Es verändert den Dienst nicht und gibt
ein ZIP aus. IP und Clientnetze müssen zur eigenen Installation passen.
In einer POSIX-Shell im Deploymentordner:

```sh
docker compose exec -T cache python3 - \
  --cache-ip 192.168.1.50 --client-network 192.168.1.0/24 \
  < prepare_mac_helper.py > OpenAppleCache-Helper.zip
```

Bei mehreren Clientnetzen `--client-network` wiederholen. Für einen abweichenden
öffentlichen Downloadport zusätzlich `--cache-port` verwenden. Beim Routerbetrieb
die LAN-Adresse des Gateways und dessen Downloadport angeben; der HTTPS-Port der
Verwaltung ist kein Downloadport.

Das konfigurierte ZIP enthält die Installationsidentität, lokale Netze und einen
zufälligen Platzhalter-Push-Token. ZIP und erzeugte `registration.json` privat
aufbewahren. Dashboard-Kennwort, TLS-Schlüssel und Apple-Sitzungstoken werden nicht
in das Paket übernommen. Vorhandene Registrierungseinstellungen auf dem Mac vor
einer erneuten Installation sichern; der Upstream-Installer ersetzt diese.

## Smoke-Test

Im Container, unabhängig von externen Gateway-Ports:

```sh
docker compose exec -T cache python3 /opt/open-apple-cache/scripts/smoke.py \
  --cache http://127.0.0.1:8080
```

Erwartet: `passed: true`, `MISS`, danach `HIT` und eine korrekte Range-Antwort.
Vom LAN den öffentlichen HTTP-Downloadport verwenden. `connection refused` bei
`127.0.0.1:8446` ist beim Gatewaybetrieb erwartbar: Dieser Listener gehört dem
separaten Gateway. Seine externe Adresse muss aus dem Backendnetz nicht
erreichbar sein.

Upstream-Anleitung: https://github.com/Mau2rice0/Open-Apple-Cache/blob/68c69e693877f6351b960b755784852f55aa854f/mac-helper/README.md
