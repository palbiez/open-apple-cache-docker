"""Check both local listeners, including TLS trust, not Apple registration."""
import ssl
import urllib.request

with urllib.request.urlopen('http://127.0.0.1:8080/', timeout=3) as response:
    assert response.status == 200
context = ssl.create_default_context(cafile='/etc/open-apple-cache/tls/admin.crt')
# Connect locally, validate the generated certificate chain; LAN SAN is checked by clients.
context.check_hostname = False
with urllib.request.urlopen('https://127.0.0.1:8443/', context=context, timeout=3) as response:
    assert response.status == 200
