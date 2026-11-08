#!/usr/bin/env python3
"""Fix Most popular / bucket 500: hard-coded %clean-trail% broke pct_escape=True queries."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-pct-escape-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    old = (
        "      AND {col} NOT LIKE '%clean-trail%'\n"
        "      AND {col} NOT LIKE '%local-trail%'"
    )
    new = (
        "      AND {col} NOT LIKE '{pct}clean-trail{pct}'\n"
        "      AND {col} NOT LIKE '{pct}local-trail{pct}'"
    )
    if old not in text:
        if new in text:
            print("already fixed")
        else:
            raise SystemExit("clean-trail LIKE lines not found")
    else:
        text = text.replace(old, new, 1)

    # Remove temporary traceback print if present
    tb = (
        "    except Exception as e:\n"
        "        import traceback as _tb\n"
        "        _tb.print_exc()\n"
        "        return JSONResponse({\"ok\": False, \"error\": str(e)[:200]}, "
        "status_code=500, headers={\"Cache-Control\": \"no-store\"})\n"
        "    finally:\n"
        "        if conn:\n"
        "            return_db_connection(conn)\n"
        "\n\n# Kill legacy disabled API winners"
    )
    tb_clean = (
        "    except Exception as e:\n"
        "        return JSONResponse({\"ok\": False, \"error\": str(e)[:200]}, "
        "status_code=500, headers={\"Cache-Control\": \"no-store\"})\n"
        "    finally:\n"
        "        if conn:\n"
        "            return_db_connection(conn)\n"
        "\n\n# Kill legacy disabled API winners"
    )
    if tb in text:
        text = text.replace(tb, tb_clean, 1)

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
