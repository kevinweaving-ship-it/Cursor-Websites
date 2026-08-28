#!/usr/bin/env python3
"""Public / -dev / former -old Lipton slugs = playback HTML. Never weather."""
from __future__ import annotations

import re
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

PLAYBACK_FN = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Playback HTML only. Weather/event page is deleted."""
    from pathlib import Path as _P
    names = (
        _P("/var/www/sailingsa/lipton-dev.html"),
        _P("/var/www/sailingsa/frontend/lipton-dev.html"),
    )
    headers = {"Cache-Control": "no-store"}
    if not public:
        headers["X-Robots-Tag"] = "noindex, nofollow"
    for p in names:
        try:
            if p.is_file():
                from fastapi.responses import HTMLResponse as _HR
                return _HR(p.read_text(encoding="utf-8"), headers=headers)
        except OSError:
            continue
    from fastapi.responses import HTMLResponse as _HR2
    return _HR2("Lipton playback page missing", status_code=500)


'''

EARLY = '''def serve_regatta_standalone(slug: str, request: Request, *, allow_lipton_event: bool = False):
    slug_s = str(slug or "").strip()
    if slug_s in (
        "2026-08-29-lipton-challenge-cup",
        "2026-08-29-lipton-challenge-cup-old",
    ):
        return serve_lipton_dev_playback_page(request, public=True)
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
    return _serve_regatta_standalone_impl(slug, request)


'''

EARLY_NO_IMPL = '''def serve_regatta_standalone(slug: str, request: Request, *, allow_lipton_event: bool = False):
    slug_s = str(slug or "").strip()
    if slug_s in (
        "2026-08-29-lipton-challenge-cup",
        "2026-08-29-lipton-challenge-cup-old",
    ):
        return serve_lipton_dev_playback_page(request, public=True)
    if slug_s == "2026-08-29-lipton-challenge-cup-dev":
        return serve_lipton_dev_playback_page(request, public=False)
'''


def _fn_span(text: str, name: str, start_at: int = 0) -> tuple[int, int] | None:
    m = re.search(rf"^def {name}\(", text[start_at:], re.M)
    if not m:
        return None
    start = start_at + m.start()
    rest = text[start + 1 :]
    m2 = re.search(r"\n(?=def |\n@app\.)", rest)
    if not m2:
        return start, len(text)
    return start, start + 1 + m2.start() + 1


def _replace_fn(text: str, name: str, new: str) -> str:
    found = False
    while True:
        span = _fn_span(text, name)
        if not span:
            break
        found = True
        start, end = span
        text = text[:start] + new.rstrip() + "\n\n" + text[end:]
        # Only keep the replacement; drop later duplicates.
        later = _fn_span(text, name, start + len(new))
        while later:
            s2, e2 = later
            text = text[:s2] + text[e2:]
            later = _fn_span(text, name, start + len(new))
        break
    if found:
        return text
    i = text.find("def serve_regatta_standalone")
    if i < 0:
        raise SystemExit(f"ERROR: {name} not found")
    return text[:i] + new.rstrip() + "\n\n" + text[i:]


def _strip_public_hijack(text: str) -> str:
    """Watchers inject public=True → event HTML. Cut that out of playback fn."""
    hijacks = [
        "    if public:\n"
        "        # LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True must still render the live board.\n"
        '        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)\n',
        "    if public:\n"
        "        # LIPTON_PUBLIC_NOT_DEV hijack public=True must still render the live board.\n"
        '        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)\n',
        "    if public:\n"
        '        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)\n',
        "    if public:\n"
        "        return _serve_regatta_standalone_impl(LIPTON_PUBLIC_SLUG, _request)\n",
    ]
    for h in hijacks:
        text = text.replace(h, "")
    return text


def _guard_impl(text: str) -> str:
    """Even if nginx proxies, impl must not emit weather HTML for Lipton slugs."""
    m = re.search(r"def _serve_regatta_standalone_impl\([^\n]*\):\n", text)
    if not m:
        return text
    head = text[m.end() : m.end() + 500]
    if "serve_lipton_dev_playback_page(request, public=True)" in head:
        return text
    inject = (
        "    slug_s = str(slug or \"\").strip()\n"
        "    if slug_s in (\n"
        "        \"2026-08-29-lipton-challenge-cup\",\n"
        "        \"2026-08-29-lipton-challenge-cup-old\",\n"
        "    ):\n"
        "        return serve_lipton_dev_playback_page(request, public=True)\n"
        "    if slug_s == \"2026-08-29-lipton-challenge-cup-dev\":\n"
        "        return serve_lipton_dev_playback_page(request, public=False)\n"
    )
    return text[: m.end()] + inject + text[m.end()]


def _kill_old_weather_css(text: str) -> str:
    text = text.replace(
        "th.crew-col,td.crew-col{white-space:normal;width:auto;text-align:left}",
        "th.crew-col,td.crew-col{white-space:nowrap;text-align:left}",
    )
    text = text.replace(
        "html,body{background:#ffffff;color:#1a2750;font-family:system-ui,sans-serif;margin:0;padding:0;width:100%;max-width:100%;overflow-x:hidden}",
        "html,body{background:#ffffff;color:#1a2750;font-family:system-ui,sans-serif;margin:0;padding:0;width:100%;max-width:100%;overflow-x:auto}",
    )
    return text


def _ok(text: str) -> bool:
    if "def serve_lipton_dev_playback_page" not in text:
        return False
    pb = text.split("def serve_lipton_dev_playback_page", 1)[-1][:900]
    if "LIPTON_PUBLIC_NOT_DEV" in pb or "lipton-dev.html" not in pb:
        return False
    if "_serve_regatta_standalone_impl" in pb:
        return False
    after = text.split("def serve_regatta_standalone", 1)[-1][:900]
    if "LIPTON_PUBLIC_NOT_DEV" in after:
        return False
    if "allow_lipton_event = True" in after:
        return False
    if "2026-08-29-lipton-challenge-cup-old" not in after:
        return False
    if "serve_lipton_dev_playback_page(request, public=True)" not in after:
        return False
    return True


def main() -> int:
    text = API.read_text(encoding="utf-8")
    text = _kill_old_weather_css(text)
    text = _replace_fn(text, "serve_lipton_dev_playback_page", PLAYBACK_FN)
    text = _strip_public_hijack(text)
    if "def _serve_regatta_standalone_impl" in text:
        text, n = re.subn(
            r"def serve_regatta_standalone\([\s\S]*?\n\n(?=def _serve_regatta_standalone_impl)",
            EARLY,
            text,
            count=1,
        )
    else:
        text, n = re.subn(
            r"def serve_regatta_standalone\([\s\S]*?\n(?=    start_time = )",
            EARLY_NO_IMPL,
            text,
            count=1,
        )
    if n != 1:
        # Live fork: prepend early returns after the def line.
        m = re.search(r"def serve_regatta_standalone\([^\n]*\):\n", text)
        if not m:
            print("ERROR: serve_regatta_standalone missing", flush=True)
            return 1
        inject = (
            "    slug_s = str(slug or \"\").strip()\n"
            "    if slug_s in (\n"
            "        \"2026-08-29-lipton-challenge-cup\",\n"
            "        \"2026-08-29-lipton-challenge-cup-old\",\n"
            "    ):\n"
            "        return serve_lipton_dev_playback_page(request, public=True)\n"
            "    if slug_s == \"2026-08-29-lipton-challenge-cup-dev\":\n"
            "        return serve_lipton_dev_playback_page(request, public=False)\n"
        )
        body_start = m.end()
        head = text[body_start:body_start + 700]
        if "serve_lipton_dev_playback_page(request, public=True)" not in head:
            text = text[:body_start] + inject + text[body_start:]
        # Strip the old-page remap if it is still sitting after the inject.
        text = text.replace(
            "    if slug_s == LIPTON_OLD_SLUG:\n"
            "        slug_s = LIPTON_PUBLIC_SLUG\n"
            "        slug = LIPTON_PUBLIC_SLUG\n"
            "        allow_lipton_event = True\n",
            "",
        )
        text = text.replace(
            '    if slug_s == "2026-08-29-lipton-challenge-cup-old":\n'
            '        slug_s = "2026-08-29-lipton-challenge-cup"\n'
            '        slug = "2026-08-29-lipton-challenge-cup"\n'
            "        allow_lipton_event = True\n",
            "",
        )
    text = _strip_public_hijack(text)
    text = _guard_impl(text)
    n_pb = len(re.findall(r"^def serve_lipton_dev_playback_page\(", text, re.M))
    print("playback_fn_count", n_pb)
    if n_pb != 1:
        print("ERROR: expected 1 playback fn", flush=True)
        return 1
    if not _ok(text):
        print("ERROR: API still serves old page", flush=True)
        after = text.split("def serve_regatta_standalone", 1)[-1][:900]
        print(after)
        return 1
    API.write_text(text, encoding="utf-8")
    print("API public/-old/-dev = playback; weather gone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
