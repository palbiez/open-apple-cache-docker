"""One-shot container init. Runtime state is never erased or recursively chowned."""
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess

CONFIG = Path('/etc/open-apple-cache')
DATA = Path('/var/lib/open-apple-cache')
UID = GID = 10001
GIB = 1024 ** 3


def integer(name, default, minimum=1, maximum=None):
    value = int(os.environ.get(name, default))
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'Invalid {name}')
    return value


def write_json(path, value, mode):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.chmod(temporary, mode)
    os.chown(temporary, UID, GID)
    temporary.replace(path)


def main():
    os.umask(0o077)
    address = ipaddress.IPv4Address(os.environ['CACHE_IP'])
    if address.is_unspecified or address.is_loopback or address.is_multicast or address.is_link_local:
        raise ValueError('CACHE_IP must be a usable fixed LAN IPv4 address')
    networks = [ipaddress.ip_network(n.strip(), strict=True)
                for n in os.environ['ALLOWED_CLIENTS'].split(',') if n.strip()]
    if not networks or any(n.version != 4 or n.prefixlen == 0 for n in networks):
        raise ValueError('ALLOWED_CLIENTS requires explicit IPv4 CIDRs, not a default route')
    if not any(address in n for n in networks):
        raise ValueError('Include the cache host LAN in ALLOWED_CLIENTS')
    admin_port = integer('ADMIN_PORT', '443', maximum=65535)
    maximum = integer('CACHE_MAX_GIB', '50') * GIB
    reserve = integer('RESERVE_GIB', '10') * GIB
    object_maximum = integer('MAX_OBJECT_GIB', '20') * GIB
    downloads = integer('MAX_DOWNLOADS', '2', maximum=64)
    if object_maximum > maximum:
        raise ValueError('MAX_OBJECT_GIB must not exceed CACHE_MAX_GIB')
    for directory in (CONFIG, CONFIG / 'tls', DATA):
        directory.mkdir(parents=True, exist_ok=True)
        os.chown(directory, UID, GID)
        os.chmod(directory, 0o700)
    usage = shutil.disk_usage(DATA)
    if maximum + reserve > usage.total or usage.free < reserve + GIB:
        raise ValueError('Cache filesystem is too small or has insufficient free reserve')

    config = json.loads(Path('/opt/open-apple-cache/config.example.json').read_text())
    config.update({
        'listen': '0.0.0.0:8080', 'admin_listen': '0.0.0.0:8443',
        'admin_url': f'https://{address}' + (f':{admin_port}' if admin_port != 443 else ''),
        'tls_cert_file': str(CONFIG / 'tls/admin.crt'),
        'tls_key_file': str(CONFIG / 'tls/admin.key'),
        'data_dir': str(DATA), 'allowed_clients': ['127.0.0.0/8'] + [str(n) for n in networks],
        'max_bytes': maximum, 'reserve_bytes': reserve,
        'max_object_bytes': object_maximum, 'max_downloads': downloads,
    })
    write_json(CONFIG / 'config.json', config, 0o600)
    cert, key = CONFIG / 'tls/admin.crt', CONFIG / 'tls/admin.key'
    if cert.exists() != key.exists():
        raise ValueError('Incomplete TLS pair; restore certificate and key together')
    renew = not cert.exists()
    if not renew:
        valid = subprocess.run(['openssl', 'x509', '-in', str(cert), '-noout',
                                '-checkend', '2592000'], capture_output=True).returncode == 0
        san = subprocess.run(['openssl', 'x509', '-in', str(cert), '-noout',
                              '-checkip', str(address)], capture_output=True).returncode == 0
        renew = not valid or not san
    if renew:
        cert_tmp, key_tmp = cert.with_suffix('.crt.tmp'), key.with_suffix('.key.tmp')
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-sha256', '-nodes', '-days', '397',
            '-subj', f'/CN={address}/O=Open Apple Cache Test',
            '-addext', f'subjectAltName=IP:{address}',
            '-addext', 'keyUsage=critical,digitalSignature,keyEncipherment',
            '-addext', 'extendedKeyUsage=serverAuth',
            '-keyout', str(key_tmp), '-out', str(cert_tmp),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for temporary, target in ((cert_tmp, cert), (key_tmp, key)):
            os.chmod(temporary, 0o600)
            os.chown(temporary, UID, GID)
            temporary.replace(target)
    write_json(DATA / 'certificate-status.json', {
        'state': 'active', 'mode': 'internal', 'identifier': str(address),
        'message': 'Docker trial: certificate managed by init, not by dashboard. '
                   'Run init periodically; restart cache after certificate replacement.',
    }, 0o600)
    print('Configuration and internal TLS prepared. No account or cache data was reset.')


if __name__ == '__main__':
    main()
