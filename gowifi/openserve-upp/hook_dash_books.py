#!/usr/bin/env python3
"""Idempotent hook: Dolibarr books card + clients page label."""
from __future__ import annotations

import os
from pathlib import Path

INDEX = Path(os.environ.get("GOWIFI_DASH_INDEX", "/home/user-data/www/default/dash/index.html"))
CLIENTS = Path(os.environ.get("GOWIFI_DASH_CLIENTS", "/home/user-data/www/default/dash/clients.html"))
SRC_CLIENTS = Path("/root/gowifi-upp/clients.html")
MARKER = "gowifi-dolibarr-books-hook"
CLIENTS_MARK = "gowifi-dolibarr-books-clients"


def _backup(path: Path) -> None:
    bak = path.with_name(path.name + ".bak-dolibarr-books")
    if not bak.exists():
        bak.write_text(path.read_text())


def hook_index(text: str) -> str:
    if MARKER in text:
        return text
    card = (
        f'    <a class="card tap" href="/dash/clients.html" data-hook="{MARKER}" '
        'style="display:block;margin-bottom:10px">\n'
        '      <div class="row"><span class="name">Books</span>'
        '<span class="pill ok">Dolibarr</span></div>\n'
        "      <div class=\"meta\">22 clients · invoices and payments · "
        '<a href="/dolibarr/" style="color:inherit">open ledger</a></div>\n'
        "    </a>\n"
    )
    needle = (
        '    <a class="card tap" href="/dash/clients.html" style="display:block;margin-bottom:10px">\n'
        '      <div class="row"><span class="name">Clients</span>'
    )
    if needle not in text:
        raise SystemExit("clients card not found in index.html")
    return text.replace(needle, card + needle, 1)


def hook_clients(text: str) -> str:
    if CLIENTS_MARK in text:
        return text
    text = text.replace(
        '<div class="sub">One line each · click the name for details</div>',
        '<div class="sub">Dolibarr books · click the name for details · '
        '<a href="/dolibarr/">open ledger</a></div>',
        1,
    )
    text = text.replace(
        '      <a href="/dash/invoices.html">Invoices</a>',
        '      <a href="/dash/invoices.html">Invoices</a>\n'
        '      <a href="/dolibarr/">Dolibarr</a>',
        1,
    )
    old = (
        '      : `${cards.length} clients · ${wifi.length} wifi · ${fibre.length} fibre`\n'
        "  ) + (osBits.length ? ` · ${osBits.join(\" · \")}` : \"\");"
    )
    new = (
        f'      : `${{cards.length}} clients · ${{wifi.length}} wifi · ${{fibre.length}} fibre`\n'
        "  ) + (osBits.length ? ` · ${osBits.join(\" · \")}` : \"\")\n"
        f"    + ((pack.books && pack.books.source===\"dolibarr\") ? "
        f"` · Dolibarr AR ${{money(pack.books.ar)}} · net ${{money(pack.books.net)}}` : \"\"); "
        f"/* {CLIENTS_MARK} */"
    )
    if old not in text:
        raise SystemExit("clients counts line not found")
    return text.replace(old, new, 1)


def apply(path: Path, transform) -> str:
    if not path.exists():
        return f"missing {path}"
    original = path.read_text()
    updated = transform(original)
    if updated == original:
        return f"already {path}"
    _backup(path)
    path.write_text(updated)
    return f"hooked {path}"


def main() -> int:
    print(apply(INDEX, hook_index))
    print(apply(CLIENTS, hook_clients))
    if SRC_CLIENTS.exists() and SRC_CLIENTS.resolve() != CLIENTS.resolve():
        print(apply(SRC_CLIENTS, hook_clients))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
