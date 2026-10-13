#!/usr/bin/env python3
"""Surgical live patch: register TSL team-racing routes. Does not replace api.py.

  python3 sailingsa/deploy/patch_live_mac_tsl_results.py /var/www/sailingsa/api/api.py

Also copy:
  sailingsa/backend/tsl_team_racing.py → /var/www/sailingsa/sailingsa/backend/
  js/mac-tsl-admin.js → /var/www/sailingsa/js/

Do not run until tests are reported. Never scp the short repo api.py over live.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "TSL_TEAM_RACING_ROUTES_v1"
BLOCK = '''
# TSL_TEAM_RACING_ROUTES_v1 — extra routes only; does not replace fleet / Appendix A.
try:
    from sailingsa.backend.tsl_team_racing import register_tsl_routes
    register_tsl_routes(
        app,
        get_db_connection=get_db_connection,
        return_db_connection=return_db_connection,
        is_super_admin=_session_role_is_super_admin,
        table_exists=table_exists,
        column_exists=column_exists,
    )
except Exception as _tsl_exc:
    print(f"[tsl] routes not registered: {_tsl_exc}", flush=True)
'''

ADMIN_JS = '<script src="/js/mac-tsl-admin.js?v=20261014f" defer></script>'
CARDS_JS = '<script src="/js/mac-tsl-live-cards.js?v=20261012o" defer></script>'


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_live_mac_tsl_results.py /path/to/api.py", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    orig = path.read_text(encoding="utf-8")
    text = orig
    if MARKER not in text:
        text = text.rstrip() + "\n" + BLOCK
        print("append TSL route registration")
    else:
        print("skip routes: already registered")
    if CARDS_JS in text and ADMIN_JS not in text:
        text = text.replace(CARDS_JS, CARDS_JS + ADMIN_JS)
        print("inject mac-tsl-admin.js")
    elif ADMIN_JS in text:
        print("skip admin js: already injected")
    else:
        print("note: live-cards pin not found — run patch_live_mac_tsl_wc_event_url.py first")
    if text == orig:
        print("No changes (already patched).")
        return 0
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path} ({len(orig.splitlines())} -> {len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
