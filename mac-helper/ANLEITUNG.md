# Mac-Helper installieren

Der Helper registriert den Linux-/Docker-Cache bei Apple. Erst nach erfolgreicher
Registrierung können Apple-Geräte ihn automatisch entdecken. Er läuft als
LaunchAgent im angemeldeten Benutzerkonto und erneuert die Registrierung alle
3000 Sekunden. Das MacBook für den ersten Test wach und im selben Netz lassen.

## 1. Voraussetzungen auf dem Mac

Terminal öffnen und prüfen:

```sh
python3 --version
xcrun --find clang
```

Falls die Apple-Entwicklerwerkzeuge fehlen, `xcode-select --install` ausführen
und die Installation abschließen. Der Helper verwendet private macOS-AuthKit-
Schnittstellen; das Projekt ist experimentell. Er benötigt keine Eingabe des
Cache-Dashboard-Kennworts und kein im Paket gespeichertes Apple-Passwort.

## 2. Dateien und eigene Konfiguration

Das öffentliche ZIP `downloads/OpenAppleCache-Helper.zip` enthält Quellcode,
eine neutrale `registration.example.json`, diese Anleitung und die Upstream-
Lizenz. Es enthält keine vorkonfigurierte private `registration.json`.

ZIP entpacken. Im Terminal `cd ` eingeben, den entpackten Ordner
`OpenAppleCache-Helper` ins Terminal ziehen und Enter drücken.

**Falls ein persönlich vorbereitetes Paket bereits `registration.json` und
`INSTALL.command` enthält:** Abschnitt 3 verwenden; keine neue Identität erzeugen.

Für das öffentliche Quellpaket die eigenen Werte einsetzen, zum Beispiel:

```sh
python3 configure.py --address 192.168.1.50 \
  --network 192.168.1.0/24 --cache-gib 50 --port 8080
```

`--address` ist die für Apple-Geräte erreichbare IPv4-Adresse des Cache-Hosts
oder seines Gateways. `--port` ist dessen HTTP-Downloadport; der HTTPS-Port des
Dashboards gehört hier nicht hinein. Weitere Clientnetze mit wiederholtem
`--network` ergänzen. Nur Netze registrieren, die der Cache tatsächlich erlaubt.
`--cache-gib` muss der konfigurierten Cachekapazität entsprechen.

Optional `--guid` mit der stabilen Cache-ID angeben; 32 Hex-Zeichen und UUID-
Schreibweise sind zulässig. Ohne diese Option wird einmal eine neue UUID
erzeugt, wie in der Upstream-Anleitung. `configure.py` überschreibt keine
vorhandene Registrierung. Die private `registration.json` lokal prüfen und
aufbewahren, statt bei jeder Installation eine neue Identität anzulegen.

Alternativ erzeugt `prepare_mac_helper.py` im laufenden Cache-Container ein
persönlich vorkonfiguriertes ZIP; siehe die beigefügte `HELPER.md` beziehungsweise
die Anleitung im Docker-Repository.

## 3. Im normalen Benutzerkonto installieren

Ohne `sudo`:

```sh
sh install.sh registration.json
```

Im persönlich vorbereiteten Paket funktioniert auch `sh INSTALL.command`.
Der Installer kompiliert den nativen Helper und legt diese Dateien an:

- `~/Library/Application Support/OpenAppleCache/`
- `~/Library/LaunchAgents/org.openapplecache.registration.plist`

Eine erneute Installation ersetzt vorhandene Registrierungseinstellungen dort.
Bestehende Einstellungen vorher privat sichern.

## 4. Registrierung und echte Downloads prüfen

Nach einigen Sekunden:

```sh
cat "$HOME/Library/Application Support/OpenAppleCache/status.json"
```

Erwartet: `"state": "registered"` und ein aktueller `registered_at`-Zeitstempel.
Bei einem Fehler:

```sh
tail -n 30 "$HOME/Library/Application Support/OpenAppleCache/registration-error.log"
launchctl print "gui/$(id -u)/org.openapplecache.registration"
```

Falls Apples eigenes Inhaltscaching aktiviert ist, für den Test unter
**Systemeinstellungen → Allgemein → Teilen → Inhaltscaching** ausschalten. Sonst
kann der Mac seinen eigenen Cache bevorzugen. Nach erfolgreicher Registrierung
einige Minuten warten, danach denselben geeigneten App-/Apple-Download auf zwei
Geräten testen und Cachetreffer sowie übertragene Bytes im Dashboard prüfen.
Bereits vollständig installierte Updates werden dadurch nicht erneut geladen.

Ein erfolgreicher Smoke-Test beweist die direkte Cachefunktion. Die automatische
Discovery muss mit echten Geräten geprüft werden. Bei mehreren Internetzugängen
müssen außerdem Registrierung und Client-Discovery zum passenden öffentlichen
Netzanschluss passen. Schlafmodus, Abmeldung und Offlinebetrieb des MacBooks
können die Erneuerung unterbrechen; das Intervall von 50 Minuten ist keine
zugesicherte Ablaufzeit der Registrierung.

## 5. Helper stoppen

Im gleichen Benutzerkonto:

```sh
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/org.openapplecache.registration.plist"
```

Die lokalen Dateien bleiben erhalten. Für eine dauerhafte Deinstallation danach
die genannte plist-Datei entfernen. Protokolle und private Registrierung nicht
öffentlich hochladen.

Upstream: [Mau2rice0/Open-Apple-Cache](https://github.com/Mau2rice0/Open-Apple-Cache),
Commit `68c69e693877f6351b960b755784852f55aa854f`. Die übernommenen Helperdateien
stehen unter der beiliegenden MIT-Lizenz `LICENSE.upstream`. Diese Dockerfassung
ändert den AuthKit-Code nicht. Eine Installation auf macOS wurde beim Erstellen
des Pakets nicht ausgeführt.
