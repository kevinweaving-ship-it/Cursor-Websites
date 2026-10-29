"""Page Indexing snapshot + family-probe contract. No live network."""

from __future__ import annotations

from sailingsa.tools.gsc_daily.page_indexing import (
    FAMILY_PROBES,
    SNAPSHOT,
    expect_redirect,
    probe_families,
    render_lines,
    snapshot_by_action,
    snapshot_total,
)


def test_snapshot_is_the_pasted_gsc_table():
    by = {row["key"]: row["pages"] for row in SNAPSHOT}
    assert by["page_with_redirect"] == 3795
    assert by["not_found_404"] == 1199
    assert by["crawled_not_indexed"] == 829
    assert by["discovered_not_indexed"] == 104
    assert by["duplicate_no_canonical"] == 408
    assert snapshot_total() == sum(by.values())
    actions = snapshot_by_action()
    assert actions["keep"] > actions["fix"]
    assert actions["wait"] == 829 + 484 + 104


def test_redirect_helper():
    assert expect_redirect({"status": 301, "location": "/sailor/ethan-kruger"}, "/sailor/ethan-kruger")
    assert not expect_redirect({"status": 200, "location": ""}, "/sailor/ethan-kruger")


def test_probe_families_uses_injected_hit():
    def hit(url: str):
        path = url.split("sailingsa.co.za", 1)[-1]
        table = {
            "/sailor/15515": {"status": 301, "location": "/sailor/ethan-kruger", "body": b""},
            "/sailor/ethan-kruger-15515": {"status": 301, "location": "/sailor/ethan-kruger", "body": b""},
            "/class/35-formula-1": {"status": 301, "location": "/class/formula-1", "body": b""},
            "/club/FBYC": {"status": 301, "location": "/club/fbyc", "body": b""},
            "/home": {"status": 301, "location": "/", "body": b""},
            "/regatta": {"status": 301, "location": "/events", "body": b""},
            "/sailor/unknown": {"status": 404, "location": "", "body": b""},
            "/boats": {"status": 200, "location": "", "body": b"<html><title>Boats</title></html>"},
            "/boat/extra-906": {"status": 200, "location": "", "body": b"<html><title>Boat</title></html>"},
            "/admin/": {"status": 403, "location": "", "body": b""},
            "/index.html": {
                "status": 200,
                "location": "",
                "body": b'<link rel="canonical" href="https://sailingsa.co.za">',
            },
            "/temp-landing": {
                "status": 200,
                "location": "",
                "body": b'<link rel="canonical" href="https://sailingsa.co.za">',
            },
            "/class/505": {
                "status": 200,
                "location": "",
                "body": b'<link rel="canonical" href="https://sailingsa.co.za/class/505">',
            },
            "/api/og/sailor/ethan-kruger.png": {"status": 200, "location": "", "body": b"PNG"},
            "/api/club-logo/fbyc": {"status": 200, "location": "", "body": b"PNG"},
            "/club/abyc": {
                "status": 200,
                "location": "",
                "body": b'<link rel="canonical" href="https://sailingsa.co.za/club/abyc">',
            },
        }
        return table.get(path, {"status": 500, "location": "", "body": b""})

    out = probe_families(hit=hit)
    assert out["broken"] == []
    assert "/boats" in out["known_gaps"]
    assert "/boat/extra-906" in out["known_gaps"]
    lines = "\n".join(render_lines(out))
    assert "3795" in lines
    assert "families OK" in lines


def test_every_family_has_a_bucket_in_the_snapshot():
    keys = {row["key"] for row in SNAPSHOT}
    for spec in FAMILY_PROBES:
        assert spec["bucket"] in keys, spec["path"]


if __name__ == "__main__":
    test_snapshot_is_the_pasted_gsc_table()
    test_redirect_helper()
    test_probe_families_uses_injected_hit()
    test_every_family_has_a_bucket_in_the_snapshot()
    print("ok")
