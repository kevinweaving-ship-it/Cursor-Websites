"""Close Dam Bottle on All Regattas listing. Does not change gold api.py."""
from __future__ import annotations

from pathlib import Path

HELPER = """            function _saRegattaListingIsLive(r) {
                if (!r) return false;
                var rid = String(r.regatta_id != null ? r.regatta_id : (r.id || ''));
                if (rid === '2026-10-10-hmyc-dam-bottle-sprints') return false;
                var st = String(r.result_status || r.event_status || '').toLowerCase();
                if (st === 'final' || st === 'completed') return false;
                return !!r.is_live;
            }
            function _sortRegattasNewestFirst(list) {
                return (list || []).slice().sort(function(a, b) {
                    var liveA = _saRegattaListingIsLive(a), liveB = _saRegattaListingIsLive(b);"""

OLD_SORT = """            function _sortRegattasNewestFirst(list) {
                return (list || []).slice().sort(function(a, b) {
                    var liveA = !!a.is_live, liveB = !!b.is_live;"""


def patch_html(path: Path) -> str:
    txt = path.read_text(encoding="utf-8")
    if "_saRegattaListingIsLive" in txt and "2026-10-10-hmyc-dam-bottle-sprints" in txt:
        return "already"
    if OLD_SORT not in txt:
        raise SystemExit(f"listing helper insert failed: {path}")
    txt = txt.replace(OLD_SORT, HELPER, 1)
    txt = txt.replace(
        "var liveN = parents.filter(function(r) { return !!r.is_live; }).length;",
        "var liveN = parents.filter(function(r) { return _saRegattaListingIsLive(r); }).length;",
        1,
    )
    txt = txt.replace(
        "var isLiveWindow = !!r.is_live;",
        "var isLiveWindow = _saRegattaListingIsLive(r);",
        1,
    )
    path.write_text(txt, encoding="utf-8")
    return "applied"


def main() -> None:
    share = Path("/var/www/sailingsa/js/regatta-pdf-share.js")
    t = share.read_text(encoding="utf-8")
    t2 = t
    for old in ("dbs46", "dbs47", "dbs48", "dbs49"):
        t2 = t2.replace(
            f"hmyc-dam-bottle-live-boot.js?v={old}",
            "hmyc-dam-bottle-live-boot.js?v=dbs49",
        )
    if "hmyc-dam-bottle-live-boot.js?v=dbs49" not in t2:
        raise SystemExit("boot cache bust failed")
    share.write_text(t2, encoding="utf-8")
    print("boot query dbs49")
    for html_path in (
        "/var/www/sailingsa/index.html",
        "/var/www/sailingsa/blank.html",
    ):
        print(html_path, patch_html(Path(html_path)))


if __name__ == "__main__":
    main()
