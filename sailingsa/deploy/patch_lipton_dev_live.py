#!/usr/bin/env python3
"""Patch live api.py with GET /api/lipton-dev/live. Does not replace the whole file."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
NEEDLE = "def serve_regatta_standalone(slug: str, request: Request):"
HOOK = '''
@app.get("/api/lipton-dev/live")
def api_lipton_dev_live():
    """Lipton -dev live T-/T+ and GPS as received. Does not invent a race or tracks."""
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
    try:
        from lipton_dev_live import live_snapshot as _live_snapshot
        return _JR(_live_snapshot())
    except Exception as err:
        return _JR({"ok": False, "live": True, "waiting": True, "error": str(err)}, status_code=502)


'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if "def api_lipton_dev_live" in text:
        print("already patched")
        return 0
    if NEEDLE not in text:
        print("ERROR: serve_regatta_standalone not found", file=__import__("sys").stderr)
        return 1
    text = text.replace(NEEDLE, HOOK + NEEDLE, 1)
    API.write_text(text, encoding="utf-8")
    print("patched", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
