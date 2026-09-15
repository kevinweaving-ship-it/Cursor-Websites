#!/usr/bin/env python3
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")

OLD = """    if place and not is_lipton:
        # GOLD: Venue only if different from host (Vulcan: Hout Bay Yacht Club == HBYC).
        _p = re.sub(r"\\s+", " ", str(place)).strip().casefold()
        _host_bits = set()
        try:
            _ab = (_wc_regatta_host_club_abbrev_for_regatta(regatta_id) or "").strip()
            if _ab:
                _host_bits.add(_ab.casefold())
            _hid = _regatta_host_club_id(regatta_id)
            if _hid and table_exists("clubs"):
                _conn = get_db_connection()
                _cur = _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                try:
                    _cur.execute(
                        "SELECT NULLIF(btrim(CAST(club_fullname AS text)), '') AS n, "
                        "NULLIF(btrim(CAST(club_abbrev AS text)), '') AS a "
                        "FROM clubs WHERE club_id = %s LIMIT 1",
                        (int(_hid),),
                    )
                    _row = _cur.fetchone() or {}
                    if _row.get("n"):
                        _host_bits.add(str(_row["n"]).strip().casefold())
                    if _row.get("a"):
                        _host_bits.add(str(_row["a"]).strip().casefold())
                finally:
                    _cur.close()
                    return_db_connection(_conn)
        except Exception:
            pass
        if _p in _host_bits:
            place = ""
            if not co_host:
                return ""
"""

NEW = """    if place and not is_lipton:
        # GOLD: Venue only if different from host (compare regattas.host_club_name).
        _p = re.sub(r"[^a-z0-9]+", " ", str(place).lower()).strip()
        _host_bits = set()
        try:
            _conn = get_db_connection()
            _cur = _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                _cur.execute(
                    "SELECT NULLIF(btrim(CAST(host_club_name AS text)), '') AS n, "
                    "NULLIF(btrim(CAST(host_club_code AS text)), '') AS a "
                    "FROM public.regattas WHERE regatta_id = %s LIMIT 1",
                    (str(regatta_id),),
                )
                _row = _cur.fetchone() or {}
                if _row.get("n"):
                    _host_bits.add(re.sub(r"[^a-z0-9]+", " ", str(_row["n"]).lower()).strip())
                if _row.get("a"):
                    _host_bits.add(str(_row["a"]).strip().lower())
            finally:
                _cur.close()
                return_db_connection(_conn)
        except Exception:
            pass
        if _p and any(_p == h or (_p in h) or (h in _p) for h in _host_bits if h and len(h) >= 3):
            place = ""
            if not co_host:
                return ""
"""


def main() -> None:
    text = API.read_text()
    if "compare regattas.host_club_name" in text:
        print("ALREADY")
        return
    if OLD not in text:
        raise SystemExit("BLOCK_MISSING")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name(f"api.py.bak.hide_dup_venue_v2.{ts}")
    shutil.copy2(API, bak)
    API.write_text(text.replace(OLD, NEW, 1))
    print("BACKUP", bak, "PATCHED")


if __name__ == "__main__":
    main()
