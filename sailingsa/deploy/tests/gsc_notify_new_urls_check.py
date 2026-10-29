"""New sitemap URLs trigger an index PUT, never the Indexing API."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sailingsa.tools.gsc_daily.notify_new_urls import collect_locs, prioritize, run


def _write_child(root: Path, name: str, urls: list[str]) -> None:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        parts.append(f"  <url><loc>{u}</loc></url>")
    parts.append("</urlset>")
    (root / name).write_text("\n".join(parts) + "\n")


def test_collect_ignores_child_sitemap_locs():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write_child(
            root,
            "sitemap-regattas.xml",
            [
                "https://sailingsa.co.za/regatta/2026-10-24-vyc-tour-de-vlei",
                "https://sailingsa.co.za/sitemap-core.xml",
            ],
        )
        locs = collect_locs(root)
        assert locs == ["https://sailingsa.co.za/regatta/2026-10-24-vyc-tour-de-vlei"]


def test_prioritize_events_and_roundups_first():
    urls = [
        "https://sailingsa.co.za/about",
        "https://sailingsa.co.za/sailor/ethan-kruger",
        "https://sailingsa.co.za/sailing-roundup/issues/2026-10-26/",
        "https://sailingsa.co.za/regatta/2026-10-24-vyc-tour-de-vlei",
    ]
    out = prioritize(urls)
    assert "regatta" in out[0]
    assert "sailing-roundup" in out[1]


def test_first_seen_does_not_submit():
    with tempfile.TemporaryDirectory() as td:
        web = Path(td) / "web"
        data = Path(td) / "data"
        web.mkdir()
        _write_child(web, "sitemap-core.xml", ["https://sailingsa.co.za/"])
        payload = run(web_root=web, data_root=data, submit=True)
        assert payload["first_seen"] is True
        assert payload["submitted"] is False
        assert payload["added"] == []
        assert "Indexing API" in payload["note"]


def test_growth_lists_added_urls_without_indexing_api():
    with tempfile.TemporaryDirectory() as td:
        web = Path(td) / "web"
        data = Path(td) / "data"
        web.mkdir()
        data.mkdir()
        _write_child(web, "sitemap-core.xml", ["https://sailingsa.co.za/"])
        run(web_root=web, data_root=data, submit=False)
        _write_child(
            web,
            "sitemap-regattas.xml",
            ["https://sailingsa.co.za/regatta/2026-10-24-vyc-tour-de-vlei"],
        )
        payload = run(web_root=web, data_root=data, submit=False)
        assert payload["added"] == [
            "https://sailingsa.co.za/regatta/2026-10-24-vyc-tour-de-vlei"
        ]
        assert payload["submitted"] is False
        assert "indexing.googleapis.com" not in payload["note"]


if __name__ == "__main__":
    import sys
    from pathlib import Path as P

    sys.path.insert(0, str(P(__file__).resolve().parents[3]))
    test_collect_ignores_child_sitemap_locs()
    test_prioritize_events_and_roundups_first()
    test_first_seen_does_not_submit()
    test_growth_lists_added_urls_without_indexing_api()
    print("ok")
