#!/usr/bin/env python3
"""Create a private registration.json on the Mac; never overwrite an existing one."""
import argparse
import base64
import ipaddress
import json
import os
from pathlib import Path
import secrets
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address', required=True, help='Client-reachable cache IPv4 address')
    parser.add_argument('--network', action='append', required=True, help='Allowed client IPv4 CIDR; repeat for more networks')
    parser.add_argument('--cache-gib', type=int, required=True)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--guid', help='Optional stable cache UUID or 32 hex digits')
    args = parser.parse_args()
    address = ipaddress.IPv4Address(args.address)
    networks = [ipaddress.IPv4Network(n, strict=True) for n in args.network]
    local = next((n for n in networks if address in n), None)
    if local is None or any(n.prefixlen < 16 or n.prefixlen > 30 for n in networks):
        parser.error('Include the cache LAN; use client IPv4 networks with /16 through /30')
    if args.cache_gib < 1 or not 1 <= args.port <= 65535:
        parser.error('Use a positive cache size and a valid TCP port')
    root = Path(__file__).resolve().parent
    data = json.loads((root / 'registration.example.json').read_text())
    data.update({
        'guid':str(uuid.UUID(args.guid) if args.guid else uuid.uuid4()).upper(),
        'push-token':base64.b64encode(secrets.token_bytes(32)).decode(),
        'local-addresses':[{'address':str(address),'netmask':str(local.netmask),'port':str(args.port)}],
        'local-ranges':[{'first':str(n.network_address+1),'last':str(n.broadcast_address-1)} for n in networks],
    })
    data['details']['cache-size'] = args.cache_gib * 1024**3
    destination = root / 'registration.json'
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.error('registration.json already exists; preserve its stable identity and edit deliberately')
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        json.dump(data, output, indent=2)
        output.write('\n')
    print('Created private registration.json. Review it locally, then run: sh install.sh registration.json')


if __name__ == '__main__':
    main()
