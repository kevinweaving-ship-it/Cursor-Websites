#!/usr/bin/env python3
"""MP-only sticky condensed score sheet: rank/sail/club-code/helm + Total/Nett."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = """    "@media (max-width:768px) and (orientation:portrait){"
    ".fleet-section .sailed-line{font-size:calc(11px * .75);line-height:1.25}"
    "}"
"""

NEW = """    "@media (max-width:768px) and (orientation:portrait){"
    ".fleet-section .sailed-line{font-size:calc(11px * .75);line-height:1.25}"
    ".fleet-section .table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}"
    ".fleet-section .table-wrapper table.fleet-results-table{"
    "border-collapse:separate;border-spacing:0;"
    "--mp-rank-w:2.25em;--mp-sail-w:3.4em;--mp-club-w:2.7em;--mp-helm-w:4.5em;--mp-tot-w:2.3em;--mp-nett-w:2.3em}"
    ".fleet-section .table-wrapper table.fleet-results-table th.rank-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.rank-col{"
    "position:sticky;left:0;z-index:8;width:var(--mp-rank-w);min-width:var(--mp-rank-w);max-width:var(--mp-rank-w);"
    "background:#fff;box-sizing:border-box}"
    ".fleet-section .table-wrapper table.fleet-results-table thead th.rank-col{z-index:12;background:#e9eefb}"
    ".fleet-section .table-wrapper table.fleet-results-table th.class-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.class-col{position:relative;z-index:1}"
    ".fleet-section .table-wrapper table.fleet-results-table th.sail-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.sail-col{"
    "position:sticky;left:var(--mp-rank-w);z-index:7;width:var(--mp-sail-w);min-width:var(--mp-sail-w);max-width:var(--mp-sail-w);"
    "background:#fff;box-sizing:border-box;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    ".fleet-section .table-wrapper table.fleet-results-table thead th.sail-col{z-index:11;background:#e9eefb}"
    ".fleet-section .table-wrapper table.fleet-results-table th.club-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.club-col{"
    "position:sticky;left:calc(var(--mp-rank-w) + var(--mp-sail-w));z-index:6;"
    "width:var(--mp-club-w);min-width:var(--mp-club-w);max-width:var(--mp-club-w);"
    "background:#fff;box-sizing:border-box;overflow:hidden}"
    ".fleet-section .table-wrapper table.fleet-results-table thead th.club-col{z-index:10;background:#e9eefb}"
    ".fleet-section .table-wrapper table.fleet-results-table td.club-col .rs-club-row-logo-sm,"
    ".fleet-section .table-wrapper table.fleet-results-table td.club-col .rs-club-row-logo,"
    ".fleet-section .table-wrapper table.fleet-results-table td.club-col .rs-club-with-logo > img{"
    "display:none!important}"
    ".fleet-section .table-wrapper table.fleet-results-table th.helm-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.helm-col{"
    "position:sticky;left:calc(var(--mp-rank-w) + var(--mp-sail-w) + var(--mp-club-w));z-index:5;"
    "width:var(--mp-helm-w);min-width:var(--mp-helm-w);max-width:var(--mp-helm-w);"
    "background:#fff;box-sizing:border-box;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
    "box-shadow:2px 0 0 #1d294d}"
    ".fleet-section .table-wrapper table.fleet-results-table thead th.helm-col{z-index:9;background:#e9eefb}"
    ".fleet-section .table-wrapper table.fleet-results-table th.crew-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.crew-col,"
    ".fleet-section .table-wrapper table.fleet-results-table th.race-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.race-col{position:relative;z-index:1}"
    ".fleet-section .table-wrapper table.fleet-results-table th.total-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.total-col{"
    "position:sticky;right:var(--mp-nett-w);z-index:7;width:var(--mp-tot-w);min-width:var(--mp-tot-w);max-width:var(--mp-tot-w);"
    "background:#fff;box-sizing:border-box;box-shadow:-2px 0 0 #1d294d}"
    ".fleet-section .table-wrapper table.fleet-results-table thead th.total-col{z-index:11;background:#e9eefb}"
    ".fleet-section .table-wrapper table.fleet-results-table th.nett-col,"
    ".fleet-section .table-wrapper table.fleet-results-table td.nett-col{"
    "position:sticky;right:0;z-index:8;width:var(--mp-nett-w);min-width:var(--mp-nett-w);max-width:var(--mp-nett-w);"
    "background:#fff;box-sizing:border-box}"
    ".fleet-section .table-wrapper table.fleet-results-table thead th.nett-col{z-index:12;background:#e9eefb}"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-gold > td.rank-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-gold > td.sail-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-gold > td.club-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-gold > td.helm-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-gold > td.total-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-gold > td.nett-col{background:#D4AF37}"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-silver > td.rank-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-silver > td.sail-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-silver > td.club-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-silver > td.helm-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-silver > td.total-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-silver > td.nett-col{background:#D7D7D7}"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-bronze > td.rank-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-bronze > td.sail-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-bronze > td.club-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-bronze > td.helm-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-bronze > td.total-col,"
    ".fleet-section .table-wrapper table.fleet-results-table tr.medal-bronze > td.nett-col{background:#CE8946}"
    "}"
"""


def main() -> None:
    api = API.read_text()
    if "MP_STICKY_SCORE_SHEET_v1" in api:
        print("ALREADY")
        return
    if OLD not in api:
        raise SystemExit("MP_SAILED_BLOCK_MISSING")
    # marker comment inside first new rule for idempotency
    marked = NEW.replace(
        ".fleet-section .table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
        "/* MP_STICKY_SCORE_SHEET_v1 */"
        ".fleet-section .table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
        1,
    )
    api = api.replace(OLD, marked, 1)
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.mp_sticky.{ts}")
    shutil.copy2(API, bak)
    print("BAK", bak)
    API.write_text(api)
    print("MP_STICKY_OK")


if __name__ == "__main__":
    main()
