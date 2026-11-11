"""Render the two Nginx listeners from .env; never read runtime credentials."""
import argparse
import ipaddress
from pathlib import Path
import tempfile

BEGIN = '# BEGIN OPEN-APPLE-CACHE (managed from cachingserver/.env)'
END = '# END OPEN-APPLE-CACHE'


def read_env(path):
    values = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, value = line.split('=', 1)
        values[name.strip()] = value.strip().strip('"\'')
    return values


def render(values):
    address = ipaddress.IPv4Address(values['CACHE_IP'])
    backend = ipaddress.IPv4Address(values['CACHE_BACKEND_IP'])
    ports = [int(values[name]) for name in ('CACHE_PORT', 'ADMIN_PORT')]
    if ports[0] == ports[1] or any(not 1024 <= port <= 65535 for port in ports):
        raise ValueError('Choose distinct CACHE_PORT/ADMIN_PORT in 1024..65535')
    if {8443, 8444, 8445, 9443}.intersection(ports):
        raise ValueError('8443/8444/8445/9443 are already used by existing gateway services')
    allowed = values['ALLOWED_CLIENTS'].split(',')
    allowed += [values['WIREGUARD_NETWORK']] if values.get('WIREGUARD_NETWORK') else []
    networks = [ipaddress.ip_network(value.strip(), strict=True) for value in allowed]
    if any(network.version != 4 or network.prefixlen == 0 for network in networks):
        raise ValueError('Explicit IPv4 client networks are required')
    access = '\n'.join(f'    allow {network};' for network in networks) + '\n    deny all;'
    headers = '''        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;'''
    return f'''{BEGIN}
# Client subnet checks happen here; the app records the proxy as its client.
server {{
    listen {address}:{ports[0]};
{access}
    location ~ ^/_(auth|admin|cache)(/|$) {{ return 403; }}
    location / {{
{headers}
        proxy_set_header X-Forwarded-Proto http;
        proxy_pass http://{backend}:8080;
        proxy_request_buffering off;
        proxy_buffering off;
    }}
}}
server {{
    listen {address}:{ports[1]} ssl;
{access}
    location = / {{ return 302 /_cache/; }}
    location / {{
{headers}
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass https://{backend}:8443;
        # Match existing Portainer: private upstream with application TLS.
        proxy_ssl_verify off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }}
}}
{END}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path(__file__).with_name('.env'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('gateway.apple-cache.conf'))
    args = parser.parse_args()
    text = render(read_env(args.env_file))
    # Init owns the directory; uploads can leave an existing root-owned fragment.
    # Replace atomically so the unprivileged renderer does not need root access.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                     dir=args.output.parent, delete=False) as temporary:
        temporary.write(text)
    Path(temporary.name).replace(args.output)
    print(f'Gateway listeners rendered: {args.output.name}')


if __name__ == '__main__':
    main()
