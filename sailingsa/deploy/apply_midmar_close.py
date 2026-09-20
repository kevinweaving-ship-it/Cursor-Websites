#!/usr/bin/env python3
"""Close Midmar: Final as at 18:00 SAST 20 Sep 2026. No score changes. WA cutoff after 18:00."""
from __future__ import annotations

import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

RID = "2026-09-19-hmyc-midmar-cup"
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
SAST = ZoneInfo("Africa/Johannesburg")
STAMP = datetime(2026, 9, 20, 18, 0, tzinfo=SAST)
INGEST = Path("/opt/arial-whatsapp-poc/event_whatsapp_ingest.py")
CC = Path("/var/www/sailingsa/sailingsa/backend/cape_classic_fleet_sheet.py")
MARK = "MIDMAR_CLOSE_1800_v1"

INGEST_OLD = '''def maybe_post_midmar_mm_clip(o: dict) -> None:
    """Copy a Midmar group photo/video onto the event MM card."""
    kind = o.get("kind") or ""
    if kind not in ("photo", "video"):
        return
'''

INGEST_NEW = '''def maybe_post_midmar_mm_clip(o: dict) -> None:
    """Copy a Midmar group photo/video onto the event MM card."""
    # Event closed 20 Sep 2026 18:00 SAST — ignore further Midmar media. ''' + MARK + '''
    from datetime import datetime as _dt, timezone as _tz
    from zoneinfo import ZoneInfo as _ZI
    _cutoff = _dt(2026, 9, 20, 18, 0, tzinfo=_ZI("Africa/Johannesburg"))
    if _dt.now(_ZI("Africa/Johannesburg")) > _cutoff:
        return
    _occ = o.get("occurred_at") or o.get("t")
    try:
        _ms = int(_occ)
        if _ms < 10**12:
            _ms *= 1000
        if _dt.fromtimestamp(_ms / 1000, tz=_tz.utc).astimezone(_ZI("Africa/Johannesburg")) > _cutoff:
            return
    except Exception:
        pass
    kind = o.get("kind") or ""
    if kind not in ("photo", "video"):
        return
'''

CC_OLD = '        date_part = re.sub(r"\\s+\\d{1,2}:\\d{2}\\s*$", "", plain_rest).strip() or "19 Sep 2026"\n        time_part = tm.group(1) if tm else "17:27"\n'
CC_NEW = '        date_part = re.sub(r"\\s+\\d{1,2}:\\d{2}\\s*$", "", plain_rest).strip() or "20 Sep 2026"\n        time_part = tm.group(1) if tm else "18:00"  # ' + MARK + "\n"


def score_fingerprint(cur) -> list:
    cur.execute(
        """
        SELECT helm_name, sail_number, race_scores
        FROM results WHERE regatta_id=%s ORDER BY helm_name, sail_number
        """,
        (RID,),
    )
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def stamp_db() -> list:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    before = score_fingerprint(cur)
    cur.execute(
        "UPDATE regattas SET as_at_time=%s, result_status='Final' WHERE regatta_id=%s",
        (STAMP, RID),
    )
    cur.execute(
        "UPDATE results SET as_at_time=%s WHERE regatta_id=%s",
        (STAMP, RID),
    )
    conn.commit()
    cur.execute("SELECT as_at_time, result_status FROM regattas WHERE regatta_id=%s", (RID,))
    print("REGATTA", cur.fetchone())
    cur.execute(
        "SELECT count(*), min(as_at_time), max(as_at_time) FROM results WHERE regatta_id=%s",
        (RID,),
    )
    print("RESULTS_ASAT", cur.fetchone())
    after = score_fingerprint(cur)
    if after != before:
        raise SystemExit("REFUSE scores changed")
    print("SCORES_UNCHANGED", len(after))
    cur.close()
    conn.close()
    return after


def patch_cc() -> None:
    text = CC.read_text()
    if MARK in text and "20 Sep 2026" in text and 'else "18:00"' in text:
        print("CC_ALREADY")
        return
    n = text.count(CC_OLD)
    if n != 1:
        raise SystemExit("ANCHOR_CC_" + str(n))
    CC.write_text(text.replace(CC_OLD, CC_NEW, 1))
    print("CC_OK")


def patch_ingest() -> None:
    text = INGEST.read_text()
    if MARK in text:
        print("INGEST_ALREADY")
        return
    n = text.count(INGEST_OLD)
    if n != 1:
        raise SystemExit("ANCHOR_INGEST_" + str(n))
    INGEST.write_text(text.replace(INGEST_OLD, INGEST_NEW, 1))
    print("INGEST_OK")


def restart_wa() -> None:
    subprocess.check_call(["systemctl", "restart", "arial-whatsapp-poc"])
    for i in range(20):
        time.sleep(2)
        st = subprocess.check_output(
            ["systemctl", "is-active", "arial-whatsapp-poc"], text=True
        ).strip()
        print("WA", i, st)
        if st == "active":
            return
    raise SystemExit("REFUSE whatsapp poc not active")


def verify_public() -> None:
    req = urllib.request.Request(
        "https://sailingsa.co.za/regatta/2026-09-19-hmyc-midmar-cup",
        headers={"Cache-Control": "no-cache", "User-Agent": "midmar-close"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    print(
        "PUBLIC",
        "Final",
        html.count("Results are Final"),
        "Prov",
        html.count("Results are Provisional"),
        "18:00",
        html.count("as at 18:00"),
        "17:27",
        html.count("as at 17:27"),
        "20 Sep",
        html.count("20 Sep"),
        "19 Sep",
        html.count("19 Sep"),
    )
    if html.count("Results are Final") < 1 or html.count("as at 18:00") < 1:
        raise SystemExit("REFUSE public not Final as at 18:00")
    if "Results are Provisional" in html or "as at 17:27" in html:
        raise SystemExit("REFUSE public still provisional/17:27")


def main() -> None:
    stamp_db()
    patch_cc()
    subprocess.check_call(["python3", "-m", "py_compile", str(CC)])
    print("CC_COMPILE_OK")
    patch_ingest()
    subprocess.check_call(["python3", "-m", "py_compile", str(INGEST)])
    print("INGEST_COMPILE_OK")
    subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
    time.sleep(5)
    print("API_SVC", subprocess.check_output(["systemctl", "is-active", "sailingsa-api"], text=True).strip())
    restart_wa()
    verify_public()
    print("DONE", MARK)


if __name__ == "__main__":
    main()
