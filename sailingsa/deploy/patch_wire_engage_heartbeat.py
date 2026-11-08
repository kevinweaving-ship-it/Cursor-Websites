#!/usr/bin/env python3
"""Wire engage merge into normal _touch_public_presence path."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    text = API.read_text(encoding="utf-8")
    old = """        visitor_id = _resolve_public_visitor_id(cur, request, ip)
        _upsert_public_session(cur, visitor_id, p, ua, ip)
        conn.commit()
        return visitor_id
"""
    new = """        visitor_id = _resolve_public_visitor_id(cur, request, ip)
        _upsert_public_session(cur, visitor_id, p, ua, ip)
        try:
            _lean_ensure_page_hit_engagement_column(cur)
            eng = str(request.query_params.get("engage") or "")
            if eng:
                _lean_merge_open_hit_engagement(cur, ip=ip, visitor_id=visitor_id or "", engage_raw=eng)
        except Exception:
            pass
        conn.commit()
        return visitor_id
"""
    # Only in _touch_public_presence — first occurrence after def is leave-then-normal
    i = text.find("def _touch_public_presence")
    j = text.find("def _set_public_visitor_cookie", i)
    chunk = text[i:j]
    if "engage_raw=eng" in chunk:
        print("already wired")
        return
    if old not in chunk:
        raise SystemExit("upsert/commit block not found in touch")
    chunk2 = chunk.replace(old, new, 1)
    text = text[:i] + chunk2 + text[j:]
    shutil.copy2(API, API.with_suffix(f".bak-engage-wire-{stamp}"))
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK engage wired into heartbeat path")


if __name__ == "__main__":
    main()
