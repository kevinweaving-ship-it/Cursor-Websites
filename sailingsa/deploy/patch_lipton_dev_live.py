#!/usr/bin/env python3
"""Patch live api.py with GET /api/lipton-dev/live?history=. Does not replace the whole file."""
from __future__ import annotations

import re
import sys
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
NEEDLE = "def serve_regatta_standalone(slug: str, request: Request):"
HOOK = '''
@app.get("/api/lipton-dev/live")
def api_lipton_dev_live(request: Request):
    """Lipton live T-/T+ and GPS as received. Does not invent a race or tracks."""
    import sys as _sys
    from pathlib import Path as _P
    for p in (
        _P("/var/www/sailingsa/sailingsa/scripts"),
        _P("/var/www/sailingsa/scripts"),
        _P(__file__).resolve().parent.parent / "sailingsa" / "scripts",
    ):
        s = str(p)
        if p.is_dir() and s not in _sys.path:
            _sys.path.insert(0, s)
    from fastapi.responses import JSONResponse as _JR
    hist = str(request.query_params.get("history") or "") in ("1", "true", "yes")
    try:
        from lipton_dev_live import live_snapshot as _live_snapshot
        return _JR(_live_snapshot(history=hist))
    except Exception as err:
        return _JR({"ok": False, "live": True, "waiting": True, "error": str(err)}, status_code=502)


'''


def _replace_live_fn(text: str) -> str:
    pat = re.compile(
        r'\n@app\.get\("/api/lipton-dev/live"\)\n'
        r'def api_lipton_dev_live\([\s\S]*?\n(?=\n(?:def |@app\.))',
        re.M,
    )
    if pat.search(text):
        return pat.sub("\n" + HOOK.lstrip("\n"), text, count=1)
    return text.replace(NEEDLE, HOOK + NEEDLE, 1)


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if "def api_lipton_dev_live" in text and "history=hist" in text:
        print("live history already patched")
        return 0
    if NEEDLE not in text:
        print("ERROR: serve_regatta_standalone not found", file=sys.stderr)
        return 1
    text = _replace_live_fn(text)
    if "history=hist" not in text:
        print("ERROR: history query not patched", file=sys.stderr)
        return 1
    API.write_text(text, encoding="utf-8")
    print("patched live history", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
