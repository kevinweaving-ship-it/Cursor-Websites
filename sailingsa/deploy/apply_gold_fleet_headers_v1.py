#!/usr/bin/env python3
"""GOLD fleet headers: DF95 sailed tokens, checksum to_count, no scoring in title."""
from pathlib import Path
import shutil
import time
import psycopg2

API = Path("/var/www/sailingsa/api/api.py")
MARK = "GOLD_FLEET_HEADERS_v1"
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"

DF95_OLD = """    if use_df95_qf_columns:
        dc = int(discard_count or 0)
        q_discards = max(0, dc - 1) if dc > 0 else 0
        f_discards = min(1, dc) if dc > 0 else 0
        sailed_line = (
            f"Results are after {races_sailed} races with {q_discards} Qualifying Discards "
            f"and {f_discards} Finals Discard. Scoring check: Total = sum(Q+F), Nett = Total - Disc."
        )
"""

DF95_NEW = """    # GOLD_FLEET_HEADERS_v1: DF95 Q/F columns stay; sailed line stays gold tokens.
"""

COUNT_OLD = """    to_count = fleet.get("to_count")
    if to_count is None and discard_count is not None:
        to_count = max(0, int(races_sailed) - int(discard_count))
"""

COUNT_NEW = """    to_count = max(0, int(races_sailed) - int(discard_count or 0))
"""

RATING_OLD = """    if rating_system:
        _sailed_parts.append(f"Rating system: {rating_system}")
    _sailed_parts.append(f"Entries: {entries}")
"""

RATING_NEW = """    _sailed_parts.append(f"Entries: {entries}")
"""

RE_OLD = """    r"Scoring(?:\\s+system)?|"
    r"Rating(?:\\s+system)?"
    r")(?:\\s+Fleet)?\\s*$",
"""

RE_NEW = """    r"Scoring(?:\\s+\\S+)*|"
    r"ToD(?:\\s*-\\s*Custom)?|"
    r"Rating(?:\\s+system)?"
    r").*$",
"""

OVERALL_OLD = """    else:
        fleet_header_title = _collapse_duplicate_fleet_word(fleet_header_title)
    _cc_logo = ""
"""

OVERALL_NEW = """    else:
        fleet_header_title = _collapse_duplicate_fleet_word(fleet_header_title)
    _ov_core = re.sub(r"(?i)\\s+fleet$", "", str(fleet_header_title or "")).strip()
    if _ov_core.casefold() in ("overall", "overall results", "all"):
        _ov_names = []
        for _r in (fleet.get("rows") or []):
            _n = str(_r.get("class_name") or _r.get("class_canonical") or "").strip()
            if _n and _n.casefold() not in ("overall", "all", "mixed"):
                _ov_names.append(_n)
        _ov_uniq = {x.casefold(): x for x in _ov_names}
        if len(_ov_uniq) == 1:
            fleet_header_title = _ensure_single_trailing_fleet(next(iter(_ov_uniq.values())))
        elif class_canonical and class_canonical.casefold() not in ("overall", "all", "mixed", ""):
            fleet_header_title = _ensure_single_trailing_fleet(class_canonical)
    _cc_logo = ""
"""


SQLS = [
    """
    UPDATE regatta_blocks SET to_count = GREATEST(0, races_sailed - discard_count)
    WHERE races_sailed > 0 AND to_count IS DISTINCT FROM GREATEST(0, races_sailed - discard_count)
      AND block_id IN (
        '2026-03-30-29er-rsa-nationals:29er',
        '2026-03-08-mbsc-interclub:slow',
        '2025-03-01-zvyc-wc-champs-extra:extra',
        '2023-04-10-msc-dinghy-western-cape-champs:optimist_a',
        '2025-03-01-mykonos-race-mono-all-b-01032025:offshore',
        '2025-03-01-mykonos-race-c31-division-01032025:cape31',
        '2025-03-01-mykonos-race-mono-c-010320225:offshore',
        '2025-03-01-mykonos-race-mono-a-010320225:mono-class-a',
        '2025-10-12-df95-wc-regional-championships:silver',
        '2024-09-24-df95-national-championship:silver-fleet'
      )
    """,
    """
    UPDATE regatta_blocks
    SET races_sailed = 6, to_count = 6, discard_count = 0,
        scoring_system = COALESCE(NULLIF(scoring_system,''), 'Appendix A')
    WHERE block_id = '2024-12-01-tsc-cape-classic:ilca-6' AND races_sailed = 0
    """,
    """
    UPDATE regatta_blocks
    SET block_label_raw = 'Multi', fleet_label = COALESCE(NULLIF(fleet_label,''), 'Multi')
    WHERE block_id = '2025-03-01-mykonos-race-multi-01032025:offshore'
    """,
    """
    UPDATE regatta_blocks
    SET scoring_system = 'Appendix A'
    WHERE (scoring_system IS NULL OR btrim(scoring_system) = '')
      AND regatta_id = '2024-11-06-east-v-west'
    """,
]


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    for i, sql in enumerate(SQLS, 1):
        cur.execute(sql)
        print(f"SQL{i}", cur.rowcount)
    conn.commit()
    cur.close()
    conn.close()

    api = API.read_text()
    if MARK in api and COUNT_NEW in api and DF95_NEW in api:
        print("ALREADY")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.gold_fleet_hdr.{ts}"))
    missing = []
    if DF95_OLD not in api:
        missing.append("DF95")
    if COUNT_OLD not in api:
        missing.append("COUNT")
    if RATING_OLD not in api:
        missing.append("RATING")
    if RE_OLD not in api:
        missing.append("RE")
    if OVERALL_OLD not in api:
        missing.append("OVERALL")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    api = api.replace(DF95_OLD, DF95_NEW, 1)
    api = api.replace(COUNT_OLD, COUNT_NEW, 1)
    api = api.replace(RATING_OLD, RATING_NEW, 1)
    api = api.replace(RE_OLD, RE_NEW, 1)
    api = api.replace(OVERALL_OLD, OVERALL_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK)


if __name__ == "__main__":
    main()
