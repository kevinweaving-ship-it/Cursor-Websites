#!/usr/bin/env python3
"""Make Avg/pd visible on the same breaker line as since restore.

Live: cache-bust app.js/css (old ?v= was still serving the previous JS) and stop
the header from clipping the extra meter span.
"""
from __future__ import annotations

from pathlib import Path

HTML = Path("/var/www/sailingsa/arial/index.html")
CSS = Path("/var/www/sailingsa/arial/arial.css")

OLD_HEAD = """#arial-breaker .activity-head {
    flex-wrap: wrap;
}
"""

NEW_HEAD = """#arial-breaker .activity-head {
    flex-wrap: wrap;
    overflow: visible;
    align-items: center;
}

#arial-breaker .breaker-on {
    flex: 1 1 100%;
    justify-content: flex-start;
    max-width: 100%;
    overflow: visible;
}
"""


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    html2 = (
        html.replace("arial.css?v=250", "arial.css?v=251")
        .replace("app.js?v=261", "app.js?v=262")
        .replace(
            'id="breaker-avg-pd" title="This month: kWh ÷ calendar days so far (SAST)" hidden>—',
            'id="breaker-avg-pd" title="This month: kWh ÷ calendar days so far (SAST)">—',
        )
    )
    if "app.js?v=262" not in html2:
        if "app.js?v=262" in html:
            print("html cache already bumped")
        else:
            raise SystemExit("cache query strings not found")
    else:
        bak = HTML.with_name(HTML.name + ".bak-avg-pd-v")
        if not bak.exists():
            bak.write_text(html, encoding="utf-8")
        HTML.write_text(html2, encoding="utf-8")
        print("html cache bumped to css 251 / js 262")

    css = CSS.read_text(encoding="utf-8")
    if "#arial-breaker .breaker-on" in css and "flex: 1 1 100%" in css:
        print("css already patched")
        return
    if OLD_HEAD not in css:
        raise SystemExit("breaker activity-head css block not found")
    bak = CSS.with_name(CSS.name + ".bak-avg-pd")
    if not bak.exists():
        bak.write_text(css, encoding="utf-8")
    CSS.write_text(css.replace(OLD_HEAD, NEW_HEAD, 1), encoding="utf-8")
    print("css patched")


if __name__ == "__main__":
    main()
