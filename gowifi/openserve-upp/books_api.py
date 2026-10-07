#!/usr/bin/env python3
"""Dash books API. Browser talks to /dash/api/books; this process talks to
Dolibarr on 127.0.0.1 only.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from dolibarr_local import all_invoices, thirdparties
from publish_dolibarr_books import load_books, totals

LISTEN = os.environ.get("BOOKS_API_LISTEN", "127.0.0.1:8797")


def snapshot() -> dict:
    """Prefer loopback REST for third parties; money totals stay on-box SQL
    so unused customer credits (no REST list) still match the statement.
    """
    parties = thirdparties(limit=100)
    invs = all_invoices()
    books = load_books()
    summary = totals(books)
    summary["via"] = "local-api+socket"
    summary["thirdparties"] = len(parties)
    summary["invoices"] = len(invs)
    clients = []
    for party in parties:
        name = party.get("name") or party.get("nom") or ""
        rec = books.get(name) or {}
        clients.append(
            {
                "id": party.get("id") or party.get("rowid"),
                "name": name,
                "billed": rec.get("billed", 0),
                "paid": rec.get("paid", 0),
                "due": rec.get("due", 0),
                "advance": rec.get("advance", 0),
                "paid_up": rec.get("paid_up", False),
                "balance_label": rec.get("balance_label", "—"),
            }
        )
    return {"books": summary, "clients": clients}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in {"/", "/health", "/books/health"}:
                self._send(200, {"ok": True, "listen": LISTEN, "backend": "dolibarr-local"})
                return
            if path in {"/books", "/dash/api/books"}:
                self._send(200, snapshot())
                return
            self._send(404, {"error": "not found"})
        except Exception as exc:
            traceback.print_exc()
            self._send(500, {"error": str(exc)})


def serve() -> None:
    host, port_s = LISTEN.rsplit(":", 1)
    httpd = ThreadingHTTPServer((host, int(port_s)), Handler)
    print(f"books-api {LISTEN} (Dolibarr loopback only)", flush=True)
    httpd.serve_forever()


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args and args[0] == "serve":
        serve()
        return 0
    print(json.dumps(snapshot(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
