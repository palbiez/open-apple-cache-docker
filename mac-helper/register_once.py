#!/usr/bin/env python3
import base64
import fcntl
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

APPLE_CERT_URL = "https://lcdn-registration.apple.com/resource/cert.cer"
APPLE_SESSION_URL = "https://lcdn-registration.apple.com/lcdn/session"
APPLE_REGISTER_URL = "https://lcdn-registration.apple.com/lcdn/register"
ROOT = Path(__file__).resolve().parent
STATE = {"cookie": None, "token": None}


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


class Bridge(BaseHTTPRequestHandler):
    def do_GET(self):
        session = self.headers.get("X-MMe-Nas-Session")
        if self.path != "/session" or not session:
            self.send_error(400)
            return
        request = urllib.request.Request(
            APPLE_SESSION_URL,
            data=session.encode("ascii"),
            method="POST",
            headers={"Content-Type": "application/octet-stream"},
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as upstream:
                response_info = json.loads(upstream.read())
                cookies = SimpleCookie()
                for value in upstream.headers.get_all("Set-Cookie", []):
                    cookies.load(value)
            token = cookies["LCDN-Session"].value
            STATE["token"] = token
            STATE["cookie"] = f"LCDN-Session={token}"
            body = json.dumps({"session-info": response_info}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", f"LCDN-Session={token}; Path=/")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_error(502, "session failed")

    def do_POST(self):
        if self.path != "/register" or not STATE["cookie"]:
            self.send_error(409)
            return
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request = urllib.request.Request(
            APPLE_REGISTER_URL,
            data=body,
            method="POST",
            headers={"Content-Type": "application/octet-stream", "Cookie": STATE["cookie"]},
        )
        try:
            try:
                upstream = urllib.request.urlopen(request, timeout=25)
            except urllib.error.HTTPError as error:
                upstream = error
            response = upstream.read()
            self.send_response(upstream.status)
            self.send_header("Content-Type", upstream.headers.get("Content-Type", "application/octet-stream"))
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception:
            self.send_error(502, "registration failed")

    def log_message(self, format, *args):
        pass


def main():
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (ROOT / "register.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        certificate = ROOT / "cert.cer"
        if not certificate.exists() or certificate.stat().st_size < 1000:
            data = urllib.request.urlopen(APPLE_CERT_URL, timeout=25).read()
            temporary = certificate.with_suffix(".tmp")
            temporary.write_bytes(data)
            os.chmod(temporary, 0o600)
            temporary.replace(certificate)

        server = HTTPServer(("127.0.0.1", 0), Bridge)
        thread = threading.Thread(target=lambda: [server.handle_request() for _ in range(2)], daemon=True)
        thread.start()
        port = server.server_address[1]
        with tempfile.TemporaryDirectory(prefix="open-apple-cache-") as directory:
            signed = Path(directory) / "registration.bin"
            command = [str(ROOT / "native-registration"), str(certificate),
                       f"http://127.0.0.1:{port}/session",
                       str(ROOT / "registration.json"), str(signed)]
            completed = subprocess.run(command, timeout=35, capture_output=True, text=True)
            if completed.returncode:
                raise RuntimeError(f"native signer exited {completed.returncode}")
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/register",
                data=base64.b64encode(signed.read_bytes()),
                method="POST",
                headers={"Content-Type": "application/octet-stream"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read())
        thread.join(timeout=2)
        server.server_close()
        interval = int(result.get("heartbeat-interval-seconds", 3300))
        atomic_json(ROOT / "status.json", {
            "state": "registered",
            "registered_at": int(time.time()),
            "heartbeat_interval_seconds": interval,
            "next_refresh_before": int(time.time()) + min(3000, max(900, interval - 300)),
            "push_mode": "heartbeat-fallback",
        })
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        atomic_json(ROOT / "status.json", {
            "state": "error", "failed_at": int(time.time()), "error": str(error)[:240]
        })
        print(f"registration failed: {error}", file=sys.stderr)
        raise SystemExit(1)
