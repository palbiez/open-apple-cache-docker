# Apple-Inhaltscache zusammen mit Squid und PAC

**Betriebsstand vom 12.11.2026:** Im bisherigen Prüfnetz wurde die Proxy-
Verteilung auf Nutzerwunsch zurückgenommen. Die PAC ist wieder auf dem Stand vor
der Apple-Ausnahme, alle DHCP-PAC-Angebote sind entfernt. Squid läuft weiterhin
optional. Fest eingetragene Client-Proxys/PAC-URLs müssen separat deaktiviert
werden. Der Apple-Go-Dienst wurde dabei nicht zurückgesetzt.

Die nachfolgende selektive Ausnahme bleibt ein optionales Einbaubeispiel für
Netze mit beibehaltenem Proxy; sie beschreibt nicht mehr die aktive Standort-PAC.

Ein Apple-Inhaltscache kann neben einem allgemeinen Webproxy, einer Docker-
Registry und Paket-Caches betrieben werden. Die Clientkonfiguration bestimmt,
welche Verbindung welchen Dienst verwendet.

Für Apple wird in der PAC `DIRECT` gewählt. Dadurch kann das Apple-Gerät seine
native Cache-Erkennung verwenden und geeignete Downloads zum registrierten
Inhaltscache schicken. Andere Apple-Verbindungen erreichen direkt ihr Ziel.
`DIRECT` erzwingt daher weder einen Cachetreffer noch das Caching aller Inhalte.

Der Go-Dienst verarbeitet Apple-Asset-Anfragen mit GET/HEAD. Er ist kein
allgemeiner Forwardproxy für CONNECT-Tunnel. Ein PAC-Eintrag
`PROXY YOUR-CACHE-IP:8080` oder ein Squid-Parent auf diesem Port stellt die native
Erkennung und das Apple-Assetprotokoll nicht her.

## Ausnahme in eine vorhandene PAC einbauen

Kopiere die Funktion aus [examples/apple-direct.js](examples/apple-direct.js)
in deine bestehende PAC. Ergänze in `FindProxyForURL` nach der HTTP(S)-Prüfung
und vor DNS-Auflösung und Proxy-Auswahl:

```javascript
if (isAppleServiceHost(host)) return "DIRECT";
```

Alle übrigen bestehenden Entscheidungen beibehalten, einschließlich lokaler
Ziele und anderer Dienste. Der Apple-Cache selbst muss direkt erreichbar sein;
bei privaten Cacheadressen übernimmt das normalerweise die vorhandene Ausnahme
für lokale Ziele. Nicht die ganze PAC durch die einzelne Hilfsfunktion ersetzen.

Die Funktion erfasst diese Domainfamilien samt Basisdomain und Subdomains:

- `apple.com`, `itunes.com`, `mzstatic.com`, `cdn-apple.com`
- `icloud.com`, `icloud-content.com`, `apple-cloudkit.com`
- Zusätzlich exakt `appldnld.apple.com.edgesuite.net`.

Die Regeln umfassen insbesondere `lcdn-locator.apple.com`, `serverstatus.apple.com`,
`lcdn-registration.apple.com`, `iosapps.itunes.apple.com` sowie Update-CDNs.
Es gibt keine pauschale Ausnahme für geteilte Drittanbieter-CDNs.
`apple.com.example.org` und ähnlich benannte Fremddomains werden nicht erfasst.

## Client und Prüfschritte

Auf iPhone/iPad im WLAN HTTP-Proxy „Automatisch“ mit deiner PAC-URL verwenden.
Nach Änderungen WLAN neu verbinden beziehungsweise das Gerät neu starten.
Falls die bisherige PAC weiterverwendet wird, einen Versionsparameter an der
PAC-URL erneuern, etwa `?v=20261111-apple`. Ein manueller IP/Port-Proxy wertet die
PAC-Ausnahmen nicht aus.

Prüfe, dass die PAC als `application/x-ns-proxy-autoconfig` und ohne dauerhafte
Zwischenspeicherung ausgeliefert wird. Im Test muss sie Folgendes entscheiden:

| Ziel | Ergebnis |
| --- | --- |
| Apple-Locator und App-/Update-CDNs | `DIRECT` |
| Lokale Cacheadresse | `DIRECT` |
| Andere Ziele | bisherige Proxy-/Direktregel |

Danach echten Appdownload am Client starten und dessen Anfrage mit Gateway- und
Cache-Logs abgleichen. Ein erster gespeicherter Download ist `MISS`; ein
wiederholter identischer geeigneter Inhalt kann `HIT` sein. Mehrere Geräte oder
Appnamen allein garantieren keine identischen Pakete.

PAC-Regeln gelten nur für Programme, die sie auswerten. Docker-Daemon und APT
können eigene Registry-/Mirror-/Proxyeinstellungen verwenden; diese werden
durch die Apple-Ausnahme nicht ersetzt.

Die hier gezeigte Hilfsfunktion entspricht der am 11.11.2026 geprüften Regel.
44 Routingfälle unter Windows JScript und 10 Fälle mit der tatsächlich
ausgelieferten PAC unter Windows WinHTTP waren erfolgreich. Normale Proxy-
Entscheidungen und Squid-HTTP/HTTPS blieben funktionsfähig. Der native iPhone-
Download nach Erneuerung der PAC ist separat zu prüfen.

## Quellen

[Apple: Inhaltscaching planen und konfigurieren](https://support.apple.com/de-de/guide/deployment/depe9b5c1aab/web)
empfiehlt direkte Clientverbindungen zum Inhaltscache.
[Apples Hostliste](https://support.apple.com/en-us/101555) nennt die Erkennungs-
und Downloadziele.
[Mozilla dokumentiert die PAC-Rückgabewerte](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Proxy_servers_and_tunneling/Proxy_Auto-Configuration_PAC_file).
Stand der Prüfung: 11.11.2026.
