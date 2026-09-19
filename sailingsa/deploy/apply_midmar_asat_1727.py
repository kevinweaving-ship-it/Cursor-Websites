#!/usr/bin/env python3
"""Midmar: date then 'as at 17:27' under event + fleet headers. Freeze DB stamp."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2

API = Path("/var/www/sailingsa/api/api.py")
CC = Path("/var/www/sailingsa/sailingsa/backend/cape_classic_fleet_sheet.py")
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
STAMP = datetime(2026, 9, 19, 17, 27, tzinfo=ZoneInfo("Africa/Johannesburg"))

FLEET_OLD = """    if str(regatta_id or "").strip() == "2026-09-19-hmyc-midmar-cup":
        _fleet_center_inner += (
            '<div class="sailed-line fleet-results-status">Results are Provisional</div>'
            '<div class="sailed-line fleet-results-as-at">19 Sep 2026</div>'
        )
"""
FLEET_NEW = """    if str(regatta_id or "").strip() == "2026-09-19-hmyc-midmar-cup":
        _fleet_center_inner += (
            '<div class="sailed-line fleet-results-status">Results are Provisional</div>'
            '<div class="sailed-line fleet-results-as-at">19 Sep 2026</div>'
            '<div class="sailed-line fleet-results-as-at-time">as at 17:27</div>'
        )  # MIDMAR_ASAT_1727_v1
"""

LIVE_OLD = """    # Official Cape Classic PDF stamp: do not tick wall clock over 17:46 checksum.
    if str(regatta_id or "").strip() == "2026-09-13-zvyc-cape-classic":
        live_ok = False
"""
LIVE_NEW = """    # Official Cape Classic PDF stamp: do not tick wall clock over 17:46 checksum.
    if str(regatta_id or "").strip() == "2026-09-13-zvyc-cape-classic":
        live_ok = False
    if str(regatta_id or "").strip() == "2026-09-19-hmyc-midmar-cup":
        live_ok = False  # MIDMAR_ASAT_1727_v1
"""

CSS_OLD = (
    '    ".header:not(.header--lipton) .status-line--asat,.header:not(.header--lipton) '
    '.regatta-status-as-at-date{white-space:nowrap!important;display:inline!important}"\n'
)
CSS_NEW = (
    '    ".header:not(.header--lipton) .status-line--asat,.header:not(.header--lipton) '
    '.regatta-status-as-at-date{white-space:nowrap!important;display:inline!important}"\n'
    '    ".header .status-line--asat-time,.fleet-results-as-at-time{display:block;'
    'white-space:nowrap;margin-top:0;color:#1a2750}"  # MIDMAR_ASAT_1727_v1\n'
)

CC_OLD = """    # Date + time stay on one line (nbsp between tokens; no wrap on a narrow phone).
    rest = re.sub(r"\\s+", "\\u00a0", rest)
    return (
        f'<div class="status-line">{head}</div>'
        f'<div class="status-line status-line--asat">'
        f'<span class="regatta-status-as-at-date">{rest}</span></div>'
    )
"""
CC_NEW = """    # Date + time stay on one line (nbsp between tokens; no wrap on a narrow phone).
    rest = re.sub(r"\\s+", "\\u00a0", rest)
    if str(regatta_id or "").strip() == "2026-09-19-hmyc-midmar-cup":
        plain_rest = rest.replace("\\u00a0", " ")
        tm = re.search(r"(\\d{1,2}:\\d{2})\\s*$", plain_rest)
        date_part = re.sub(r"\\s+\\d{1,2}:\\d{2}\\s*$", "", plain_rest).strip() or "19 Sep 2026"
        time_part = tm.group(1) if tm else "17:27"
        return (
            f'<div class="status-line">{head}</div>'
            f'<div class="status-line status-line--asat">'
            f'<span class="regatta-status-as-at-date">{date_part}</span></div>'
            f'<div class="status-line status-line--asat-time">as at {time_part}</div>'
        )  # MIDMAR_ASAT_1727_v1
    return (
        f'<div class="status-line">{head}</div>'
        f'<div class="status-line status-line--asat">'
        f'<span class="regatta-status-as-at-date">{rest}</span></div>'
    )
"""


def patch_api() -> None:
    text = API.read_text()
    if "MIDMAR_ASAT_1727_v1" in text and "fleet-results-as-at-time" in text:
        print("API_ALREADY")
        return
    for label, old, new in (
        ("FLEET", FLEET_OLD, FLEET_NEW),
        ("LIVE", LIVE_OLD, LIVE_NEW),
        ("CSS", CSS_OLD, CSS_NEW),
    ):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"ANCHOR_{label}_{n}")
        text = text.replace(old, new, 1)
        print("PATCH", label)
    API.write_text(text)
    print("API_OK")


def patch_cc() -> None:
    text = CC.read_text()
    if "MIDMAR_ASAT_1727_v1" in text:
        print("CC_ALREADY")
        return
    # File uses real unicode / raw newlines, not escaped in the source.
    old = """    # Date + time stay on one line (nbsp between tokens; no wrap on a narrow phone).
    rest = re.sub(r"\\s+", "\\u00a0", rest)
    return (
        f'<div class="status-line">{head}</div>'
        f'<div class="status-line status-line--asat">'
        f'<span class="regatta-status-as-at-date">{rest}</span></div>'
    )
"""
    # Match the live file as written (single-backslash regex in source).
    old = (
        "    # Date + time stay on one line (nbsp between tokens; no wrap on a narrow phone).\n"
        '    rest = re.sub(r"\\s+", "\\u00a0", rest)\n'
        "    return (\n"
        "        f'<div class=\"status-line\">{head}</div>'\n"
        "        f'<div class=\"status-line status-line--asat\">'\n"
        "        f'<span class=\"regatta-status-as-at-date\">{rest}</span></div>'\n"
        "    )\n"
    )
    new = (
        "    # Date + time stay on one line (nbsp between tokens; no wrap on a narrow phone).\n"
        '    rest = re.sub(r"\\s+", "\\u00a0", rest)\n'
        '    if str(regatta_id or "").strip() == "2026-09-19-hmyc-midmar-cup":\n'
        '        plain_rest = rest.replace("\\u00a0", " ")\n'
        '        tm = re.search(r"(\\d{1,2}:\\d{2})\\s*$", plain_rest)\n'
        '        date_part = re.sub(r"\\s+\\d{1,2}:\\d{2}\\s*$", "", plain_rest).strip() or "19 Sep 2026"\n'
        '        time_part = tm.group(1) if tm else "17:27"\n'
        "        return (\n"
        "            f'<div class=\"status-line\">{head}</div>'\n"
        "            f'<div class=\"status-line status-line--asat\">'\n"
        "            f'<span class=\"regatta-status-as-at-date\">{date_part}</span></div>'\n"
        "            f'<div class=\"status-line status-line--asat-time\">as at {time_part}</div>'\n"
        "        )  # MIDMAR_ASAT_1727_v1\n"
        "    return (\n"
        "        f'<div class=\"status-line\">{head}</div>'\n"
        "        f'<div class=\"status-line status-line--asat\">'\n"
        "        f'<span class=\"regatta-status-as-at-date\">{rest}</span></div>'\n"
        "    )\n"
    )
    n = text.count(old)
    if n != 1:
        raise SystemExit("ANCHOR_CC_" + str(n))
    CC.write_text(text.replace(old, new, 1))
    print("CC_OK")


def stamp_db() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        "UPDATE regattas SET as_at_time=%s, result_status='Provisional' WHERE regatta_id=%s",
        (STAMP, RID),
    )
    cur.execute("UPDATE results SET as_at_time=%s WHERE regatta_id=%s", (STAMP, RID))
    conn.commit()
    cur.execute("SELECT as_at_time, result_status FROM regattas WHERE regatta_id=%s", (RID,))
    print("DB", cur.fetchone())
    cur.close()
    conn.close()


def main() -> None:
    stamp_db()
    patch_cc()
    patch_api()


if __name__ == "__main__":
    main()
