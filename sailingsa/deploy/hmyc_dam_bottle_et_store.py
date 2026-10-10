#!/usr/bin/env python3
"""Dam Bottle ET + corrected-time store. Not gold api.py."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
PATHS = {"/api/hmyc-dam-bottle-et", "/api/hmyc-dam-bottle-et/"}
STORE = Path("/var/www/sailingsa/assets/hmyc-dam-bottle-et.json")
MAX = 32 * 1024


def read_store():
    if not STORE.is_file():
        return {"store": {}, "rid": "2026-10-10-hmyc-dam-bottle-sprints"}
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"store": {}, "rid": "2026-10-10-hmyc-dam-bottle-sprints"}


def write_store(payload):
    if not isinstance(payload, dict):
        raise ValueError("object required")
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(STORE)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "https://sailingsa.co.za")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "https://sailingsa.co.za")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] not in PATHS:
            self._send(404, '{"ok":false}')
            return
        self._send(200, json.dumps(read_store(), ensure_ascii=False))

    def do_POST(self):
        if self.path.split("?", 1)[0] not in PATHS:
            self._send(404, '{"ok":false}')
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX:
            self._send(400, '{"ok":false,"error":"size"}')
            return
        try:
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            write_store(payload)
        except Exception as exc:
            self._send(400, json.dumps({"ok": False, "error": str(exc)}))
            return
        self._send(200, '{"ok":true}')


if __name__ == "__main__":
    STORE.parent.mkdir(parents=True, exist_ok=True)
    if not STORE.is_file():
        write_store({"store": {}, "rid": "2026-10-10-hmyc-dam-bottle-sprints"})
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
