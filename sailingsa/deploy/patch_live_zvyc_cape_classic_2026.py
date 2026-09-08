#!/usr/bin/env python3
"""Insert this-URL-only route into live api.py. Does not touch serve_regatta_standalone."""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
NEEDLE = '@app.get("/regatta/{slug}")'
MARKER = "def _zvyc_cape_classic_2026_pending"
INSERT = '''@app.get("/regatta/2026-09-13-zvyc-cape-classic")
@app.head("/regatta/2026-09-13-zvyc-cape-classic")
def _zvyc_cape_classic_2026_pending():
    """This URL only: gold Events Results parent. No results table (event not sailed)."""
    from zvyc_cape_classic_2026 import (
        zvyc_cape_classic_2026_body,
        zvyc_cape_classic_2026_extra_head,
    )
    return _html_with_gold_header(
        "ZVYC Cape Classic | SailingSA",
        zvyc_cape_classic_2026_body(),
        zvyc_cape_classic_2026_extra_head(),
    )


'''


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched")
        return
    if NEEDLE not in text:
        raise SystemExit("needle not found: " + NEEDLE)
    LIVE_API.write_text(text.replace(NEEDLE, INSERT + NEEDLE, 1), encoding="utf-8")
    print("patched", LIVE_API)


if __name__ == "__main__":
    main()
