#!/usr/bin/env python3
"""Exclude bot/admin/probe paths from traffic Most popular Pages (and unified counts)."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

# Exact paths that are CMS/admin scanners — not public SailingSA content.
_BLOCK_EXACT = (
    "/account",
    "/app",
    "/console",
    "/dashboard",
    "/login",
    "/login.html",
    "/manage",
    "/my",
    "/portal",
    "/profile",
    "/settings",
    "/signin",
    "/signup",
    "/register",
    "/user",
    "/user/login",
    "/users",
    "/graphql",
    "/v1/graphql",
    "/class",  # bare; real lists are /classes
    "/club",  # bare; real lists are /clubs
    "/wp",
    "/backend",
    "/cpanel",
    "/webmail",
)


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-path-ok-admin-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    start = text.find("def _lean_traffic_path_ok_sql")
    if start < 0:
        raise SystemExit("path_ok missing")
    end = text.find("\ndef _lean_traffic_gate", start)
    if end < 0:
        raise SystemExit("path_ok end missing")

    in_list = ", ".join(f"'{p}'" for p in _BLOCK_EXACT)
    new_fn = f'''def _lean_traffic_path_ok_sql(col: str, *, pct_escape: bool = False) -> str:
    """Drop development / tooling / bot-probe / admin / asset noise from traffic stats."""
    pct = "%%" if pct_escape else "%"
    return f"""
      AND {{col}} IS NOT NULL AND TRIM({{col}}) <> ''
      AND {{col}} NOT LIKE '/temp-landing{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}clean-trail{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}local-trail{{pct}}'
      AND {{col}} NOT LIKE '/workspace{{pct}}'
      AND {{col}} <> '/workspace'
      AND {{col}} NOT LIKE '/dev-1{{pct}}'
      AND {{col}} NOT LIKE '/traffic{{pct}}'
      AND {{col}} NOT LIKE '/lean-traffic{{pct}}'
      AND {{col}} NOT LIKE '/admin{{pct}}'
      AND {{col}} NOT LIKE '/api/{{pct}}'
      AND {{col}} NOT LIKE '/auth{{pct}}'
      AND {{col}} NOT LIKE '/@{{pct}}'
      AND {{col}} NOT LIKE '/icons/{{pct}}'
      AND {{col}} NOT LIKE '/.{{pct}}'
      AND {{col}} NOT LIKE '//{{pct}}'
      AND {{col}} NOT LIKE '/event-ocr{{pct}}'
      AND {{col}} NOT LIKE '/static/{{pct}}'
      AND {{col}} NOT LIKE '/assets/{{pct}}'
      AND {{col}} NOT LIKE '/sailingsa/{{pct}}'
      AND {{col}} NOT LIKE '/wp-{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}wp-includes{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}wp-admin{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}wp-content{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}wp-login{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}xmlrpc.php{{pct}}'
      AND {{col}} NOT LIKE '/wordpress{{pct}}'
      AND {{col}} NOT LIKE '/phpmyadmin{{pct}}'
      AND {{col}} NOT LIKE '/cgi-bin/{{pct}}'
      AND {{col}} NOT LIKE '/vendor/{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}.php'
      AND {{col}} NOT LIKE '{{pct}}.env{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}.git{{pct}}'
      AND {{col}} NOT LIKE '{{pct}}.zip'
      AND {{col}} NOT LIKE '{{pct}}.sql'
      AND {{col}} NOT LIKE '{{pct}}.bak'
      AND {{col}} NOT LIKE '{{pct}}.json'
      AND {{col}} NOT LIKE '{{pct}}backup{{pct}}'
      AND {{col}} NOT LIKE '/wp-backup{{pct}}'
      AND {{col}} !~ '^/sailor/[0-9]+/?$'
      AND lower(split_part({{col}}, '?', 1)) NOT IN ({in_list})
    """


'''
    # Fix: the f-string above double-escaped wrong. Build carefully.
    # Use .format with doubled braces for SQL f-string body that itself is an f-string in api.py

    new_fn = '''def _lean_traffic_path_ok_sql(col: str, *, pct_escape: bool = False) -> str:
    """Drop development / tooling / bot-probe / admin / asset noise from traffic stats."""
    pct = "%%" if pct_escape else "%"
    return f"""
      AND {col} IS NOT NULL AND TRIM({col}) <> ''
      AND {col} NOT LIKE '/temp-landing{pct}'
      AND {col} NOT LIKE '{pct}clean-trail{pct}'
      AND {col} NOT LIKE '{pct}local-trail{pct}'
      AND {col} NOT LIKE '/workspace{pct}'
      AND {col} <> '/workspace'
      AND {col} NOT LIKE '/dev-1{pct}'
      AND {col} NOT LIKE '/traffic{pct}'
      AND {col} NOT LIKE '/lean-traffic{pct}'
      AND {col} NOT LIKE '/admin{pct}'
      AND {col} NOT LIKE '/api/{pct}'
      AND {col} NOT LIKE '/auth{pct}'
      AND {col} NOT LIKE '/@{pct}'
      AND {col} NOT LIKE '/icons/{pct}'
      AND {col} NOT LIKE '/.{pct}'
      AND {col} NOT LIKE '//{pct}'
      AND {col} NOT LIKE '/event-ocr{pct}'
      AND {col} NOT LIKE '/static/{pct}'
      AND {col} NOT LIKE '/assets/{pct}'
      AND {col} NOT LIKE '/dist/{pct}'
      AND {col} NOT LIKE '/sailingsa/{pct}'
      AND {col} NOT LIKE '/wp-{pct}'
      AND {col} NOT LIKE '{pct}wp-includes{pct}'
      AND {col} NOT LIKE '{pct}wp-admin{pct}'
      AND {col} NOT LIKE '{pct}wp-content{pct}'
      AND {col} NOT LIKE '{pct}wp-login{pct}'
      AND {col} NOT LIKE '{pct}xmlrpc.php{pct}'
      AND {col} NOT LIKE '/wordpress{pct}'
      AND {col} NOT LIKE '/phpmyadmin{pct}'
      AND {col} NOT LIKE '/cgi-bin/{pct}'
      AND {col} NOT LIKE '/vendor/{pct}'
      AND {col} NOT LIKE '{pct}.php'
      AND {col} NOT LIKE '{pct}.env{pct}'
      AND {col} NOT LIKE '{pct}.git{pct}'
      AND {col} NOT LIKE '{pct}.zip'
      AND {col} NOT LIKE '{pct}.sql'
      AND {col} NOT LIKE '{pct}.bak'
      AND {col} NOT LIKE '{pct}.json'
      AND {col} NOT LIKE '{pct}backup{pct}'
      AND {col} NOT LIKE '/wp-backup{pct}'
      AND {col} !~ '^/sailor/[0-9]+/?$'
      AND lower(split_part({col}, '?', 1)) NOT IN (''' + in_list + ''')
    """


'''
    text = text[:start] + new_fn + text[end:]

    # Expand probe blocked exact set so these quarantine on hit
    old_blocked = '''    blocked_exact = {
        "/wp-login.php",
        "/wp-login",
        "/xmlrpc.php",
        "/wp-cron.php",
        "/wp-config.php",
        "/wp-config.php.bak",
        "/wordpress/wp-login.php",
        "/blog/wp-login.php",
        "/phpmyadmin",
        "/pma",
        "/adminer.php",
        "/administrator",
        "/.env",
        "/.git/config",
        "/.git/head",
    }'''
    new_blocked = '''    blocked_exact = {
        "/wp-login.php",
        "/wp-login",
        "/xmlrpc.php",
        "/wp-cron.php",
        "/wp-config.php",
        "/wp-config.php.bak",
        "/wordpress/wp-login.php",
        "/blog/wp-login.php",
        "/phpmyadmin",
        "/pma",
        "/adminer.php",
        "/administrator",
        "/.env",
        "/.git/config",
        "/.git/head",
        "/account",
        "/app",
        "/console",
        "/dashboard",
        "/login",
        "/login.html",
        "/manage",
        "/my",
        "/portal",
        "/profile",
        "/settings",
        "/signin",
        "/signup",
        "/register",
        "/user",
        "/user/login",
        "/users",
        "/graphql",
        "/v1/graphql",
        "/manifest.json",
        "/asset-manifest.json",
        "/webpack-stats.json",
        "/class",
        "/club",
    }'''
    if old_blocked not in text:
        print("WARN: blocked_exact not found for expand")
    else:
        text = text.replace(old_blocked, new_blocked, 1)

    # Also block *.json in probe helper
    if 'if base.endswith(".json"):' not in text[text.find("def _is_probe_blocked_path") : text.find("def _is_probe_blocked_path") + 3500]:
        needle = "    if base.endswith(\".php\"):\n        return True"
        if needle in text:
            text = text.replace(
                needle,
                needle + '\n    if base.endswith(".json"):\n        return True',
                1,
            )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK path_ok admin/bot filter (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
