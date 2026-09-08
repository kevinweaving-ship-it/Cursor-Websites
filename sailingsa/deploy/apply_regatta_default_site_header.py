#!/usr/bin/env python3
"""Make every /regatta/{slug} page use the default Sailing SA header.

Live currently wraps only Lipton with header.html (Sign Up / Login) and
puts "← Back to Search" on every other event. That is not the default.

Usage (on live, after api.py backup):
  python3 apply_regatta_default_site_header.py /var/www/sailingsa/api/api.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

OLD_BACK = (
    "        back_link = '' if _is_lipton else '<a href=\"/\" class=\"back-to-home\">← Back to Search</a>'\n"
)
NEW_BACK = (
    "        # Default for ALL events: Sailing SA site header. No Back to Search.\n"
    "        back_link = ''\n"
)

OLD_WRAP = '''        print("REGATTA: total route time", round(time.time() - start_time, 3))
        if _is_lipton:
            _fb_lipton_head = _fb_og_head_for(
                "regatta",
                str(canonical_slug),
                f"{escaped_title} | SailingSA",
                f"Regatta results: {escaped_title}.",
                canonical_url,
                source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name),
            )
            extra_head = (
                f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
                f"<style>{_RESULT_SHEET_CSS}</style>"
            )
            resp = _html_with_gold_header(f"{escaped_title} | SailingSA", page_inner, extra_head)
            html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
            import facebook_og as _fb
            html = _fb.inject_facebook_head(html, _fb_lipton_head)
            return HTMLResponse(html)
        doc = (
            "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><title>"
            f"{escaped_title} | SailingSA</title>"
            f"<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">"
            + _fb_og_head_for("regatta", str(canonical_slug), f"{escaped_title} | SailingSA", f"Regatta results: {escaped_title}.", canonical_url, source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name))
            + "<link rel=\\"icon\\" href=\\"/favicon.ico\\" sizes=\\"any\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"16x16\\" href=\\"/favicon-16.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"32x32\\" href=\\"/favicon-32.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"48x48\\" href=\\"/favicon-48.png\\"><link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\"><link rel=\\"apple-touch-icon\\" href=\\"/apple-touch-icon.png\\">"
            "<link rel=\\"icon\\" type=\\"image/png\\" sizes=\\"192x192\\" href=\\"/favicon-192.png\\">"
            f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
            f"<style>{_RESULT_SHEET_CSS}</style></head><body>"
            f"{page_inner}"
            "</body></html>"
        )
        return HTMLResponse(doc)
'''

NEW_WRAP = '''        print("REGATTA: total route time", round(time.time() - start_time, 3))
        _fb_regatta_head = _fb_og_head_for(
            "regatta",
            str(canonical_slug),
            f"{escaped_title} | SailingSA",
            f"Regatta results: {escaped_title}.",
            canonical_url,
            source_url=_fb_og_regatta_left_url(str(regatta_id), ev_name or event_name),
        )
        extra_head = (
            f"<script type=\\"application/ld+json\\">{json.dumps(json_ld)}</script>"
            f"<style>{_RESULT_SHEET_CSS}</style>"
        )
        resp = _html_with_gold_header(f"{escaped_title} | SailingSA", page_inner, extra_head)
        html = resp.body.decode("utf-8") if isinstance(resp.body, (bytes, bytearray)) else str(resp.body or "")
        import facebook_og as _fb
        html = _fb.inject_facebook_head(html, _fb_regatta_head)
        return HTMLResponse(html)
'''


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if NEW_BACK in text and NEW_WRAP in text and OLD_BACK not in text and OLD_WRAP not in text:
        print(f"Already patched {path}", file=sys.stderr)
        return
    if OLD_BACK not in text:
        raise SystemExit(f"ERROR: back_link block not found in {path}")
    if text.count(OLD_BACK) != 1:
        raise SystemExit(f"ERROR: back_link block matched {text.count(OLD_BACK)} times")
    if OLD_WRAP not in text:
        raise SystemExit(f"ERROR: wrap block not found in {path}")
    if text.count(OLD_WRAP) != 1:
        raise SystemExit(f"ERROR: wrap block matched {text.count(OLD_WRAP)} times")
    text = text.replace(OLD_BACK, NEW_BACK, 1).replace(OLD_WRAP, NEW_WRAP, 1)
    ast.parse(text)
    path.write_text(text, encoding="utf-8")
    print(f"Patched {path}", file=sys.stderr)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: apply_regatta_default_site_header.py /path/to/api.py", file=sys.stderr)
        return 2
    apply(Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
