"""Run inside the cache container; write a configured macOS helper ZIP to stdout."""
import argparse
import base64
import io
import ipaddress
import json
from pathlib import Path
import secrets
import sys
import uuid
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-ip', required=True)
    parser.add_argument('--client-network', required=True, action='append')
    parser.add_argument('--cache-port', type=int, default=8080)
    args = parser.parse_args()
    address = ipaddress.IPv4Address(args.cache_ip)
    networks = [ipaddress.IPv4Network(n, strict=True) for n in args.client_network]
    if any(n.prefixlen < 16 or n.prefixlen > 30 for n in networks):
        parser.error('Use explicit client networks with prefixes /16 through /30')
    local = next((n for n in networks if address in n), None)
    if local is None or not 1 <= args.cache_port <= 65535:
        parser.error('Include the cache LAN in client networks and choose a valid port')
    source = Path('/opt/open-apple-cache/mac-helper')
    config = json.loads(Path('/etc/open-apple-cache/config.json').read_text())
    allowed = [ipaddress.IPv4Network(n) for n in config['allowed_clients']]
    if any(not any(n.subnet_of(a) for a in allowed) for n in networks):
        parser.error('A requested client network is outside allowed_clients')
    identity = Path(config['data_dir'], 'cache-id').read_text().strip()
    registration = json.loads((source / 'registration.example.json').read_text())
    registration.update({
        'guid': str(uuid.UUID(identity)).upper(),
        'push-token': base64.b64encode(secrets.token_bytes(32)).decode(),
        'local-addresses': [{'address':str(address),'netmask':str(local.netmask),
                             'port':str(args.cache_port)}],
        'local-ranges': [{'first':str(n.network_address + 1),
                          'last':str(n.broadcast_address - 1)} for n in networks],
    })
    registration['details']['cache-size'] = config['max_bytes']
    install = '''#!/bin/sh
set -eu
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Install Python 3 first'; exit 1; }
xcrun --find clang >/dev/null
sh ./install.sh registration.json
echo 'Helper installed. Check status after a few seconds:'
echo 'cat "$HOME/Library/Application Support/OpenAppleCache/status.json"'
'''
    instructions = '''Open Apple Cache: Mac-Helper

1. ZIP auf dem Mac entpacken, Terminal im entpackten Ordner oeffnen.
2. Falls die Apple-Entwicklerwerkzeuge fehlen: xcode-select --install
   Die Installation abschliessen und danach fortfahren.
3. Im normalen angemeldeten Benutzerkonto ausfuehren (ohne sudo):
      sh INSTALL.command
4. Nach einigen Sekunden pruefen:
      cat "$HOME/Library/Application Support/OpenAppleCache/status.json"
   Erwartet: "state": "registered" und aktueller registered_at-Zeitstempel.
5. Falls noetig Fehlerprotokoll lokal pruefen:
      tail -n 30 "$HOME/Library/Application Support/OpenAppleCache/registration-error.log"
6. Beim Test den eingebauten macOS-Inhaltscache unter Systemeinstellungen >
   Allgemein > Teilen > Inhaltscaching ausschalten, falls er eingeschaltet ist.
7. Danach denselben geeigneten App-/Apple-Download auf zwei Geraeten testen.
   Ein erfolgreicher Smoke-Test allein prueft keine automatische Discovery.

Der Helper wird alle 3000 Sekunden als LaunchAgent des angemeldeten Benutzers
gestartet. MacBook fuer den Ersttest wach und im Netzwerk lassen. Schlafmodus,
Abmeldung und Abwesenheit koennen die Erneuerung unterbrechen.

registration.json enthaelt die Identitaet und Netzwerkwerte dieser Installation.
Dieses konfigurierte Paket und die lokalen Protokolle nicht oeffentlich posten.
Es enthaelt kein Dashboard-Passwort, keine Apple-Sitzung und keine TLS-Schluessel.

Entfernen (auf dem Mac, im gleichen Benutzerkonto):
  launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/org.openapplecache.registration.plist"
  rm "$HOME/Library/LaunchAgents/org.openapplecache.registration.plist"
Die Dateien unter Library/Application Support/OpenAppleCache bleiben erhalten.

Upstream: https://github.com/Mau2rice0/Open-Apple-Cache (MIT, siehe LICENSE.upstream)
'''
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ('install.sh', 'register_once.py', 'native-registration.m',
                     'org.openapplecache.registration.plist', 'README.md'):
            archive.writestr('OpenAppleCache-Helper/' + name, (source / name).read_bytes())
        archive.writestr('OpenAppleCache-Helper/registration.json', json.dumps(registration,indent=2)+'\n')
        archive.writestr('OpenAppleCache-Helper/INSTALL.command', install)
        archive.writestr('OpenAppleCache-Helper/ANLEITUNG.txt', instructions)
        archive.writestr('OpenAppleCache-Helper/LICENSE.upstream', source.parent.joinpath('LICENSE').read_bytes())
    sys.stdout.buffer.write(buffer.getvalue())


if __name__ == '__main__':
    main()
