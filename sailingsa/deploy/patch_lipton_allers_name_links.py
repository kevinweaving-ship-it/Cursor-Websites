#!/usr/bin/env python3
"""Patch live api.py: Allers NAME: links (no fake SAS IDs) + crew2/crew3 slug resolve.

Run on the live host against /var/www/sailingsa/api/api.py. Never overwrite live api.py
with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_ALLERS_NAME_LINKS_V2"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

HELPER = '''
def _identity_pending_is_confirmed_no_sas(name: str) -> bool:
    """True when identity_pending_sailors.status = admin_confirmed_no_sas (no fake SAS id)."""
    # ''' + MARKER + '''
    nm = (name or "").strip()
    if not nm:
        return False
    key = re.sub(r"\\s+", " ", nm.lower())
    now = time.time()
    cache = globals().setdefault("_IDENTITY_PENDING_CONFIRMED_NO_SAS_CACHE", {"at": 0.0, "names": set()})
    if now - float(cache.get("at") or 0) > 60:
        names = set()
        try:
            if table_exists("identity_pending_sailors"):
                conn = get_db_connection()
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT LOWER(TRIM(normalized_name)) AS n1, LOWER(TRIM(display_name)) AS n2 "
                        "FROM public.identity_pending_sailors "
                        "WHERE status = 'admin_confirmed_no_sas'"
                    )
                    for row in cur.fetchall() or []:
                        vals = row.values() if isinstance(row, dict) else row
                        for v in vals:
                            if v:
                                names.add(re.sub(r"\\s+", " ", str(v).strip().lower()))
                finally:
                    cur.close()
                    try:
                        return_db_connection(conn)
                    except Exception:
                        try:
                            conn.close()
                        except Exception:
                            pass
        except Exception as e:
            print(f"[api] _identity_pending_is_confirmed_no_sas: {e}")
        cache["names"] = names
        cache["at"] = now
    return key in (cache.get("names") or set())


'''

OLD_LINK = '''def _wc_sailor_name_link_html(nm: str, sid, slug) -> str:
    nm = (nm or "").strip()
    if not nm:
        return ""
    matched = sid is not None and str(sid).strip().isdigit()
    # No SAS id still gets a personal /sailor/{first-last} URL (red unmatched).
    if not slug:
        slug = _identity_pending_name_slug(nm)
'''

NEW_LINK = '''def _wc_sailor_name_link_html(nm: str, sid, slug) -> str:
    nm = (nm or "").strip()
    if not nm:
        return ""
    sid_s = str(sid or "").strip()
    matched = sid_s.isdigit() or sid_s.upper().startswith("NAME:")
    if not matched and _identity_pending_is_confirmed_no_sas(nm):
        matched = True
    # No SAS id still gets a personal /sailor/{first-last} URL.
    # admin_confirmed_no_sas (e.g. Allers) uses linked class — not red unmatched.
    if not slug:
        slug = _identity_pending_name_slug(nm)
'''

OLD_CREW = '''                    return nm, "NAME:" + sp
            # Helm/crew in results but no SA ID: try sas_id_personal with first-name variant (Tom<->Thomas)
'''

NEW_CREW = r'''                    return nm, "NAME:" + sp
            cur.execute("""
                SELECT TRIM(crew2_name) AS name
                FROM results
                WHERE crew2_sa_sailing_id IS NULL
                  AND crew2_name IS NOT NULL AND TRIM(crew2_name) != ''
                  AND REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TRIM(REPLACE(REPLACE(crew2_name,'/',' '),'&',' and '))),'[^a-z0-9 ]',' ','g'),'\\s+',' ','g') = ANY(%s)
                LIMIT 1
            """, (norm_candidates,))
            row = cur.fetchone()
            if row and (row.get("name") or "").strip():
                nm = (row.get("name") or "").strip()
                sp = _slug_from_name(nm)
                if nm and sp:
                    return nm, "NAME:" + sp
            cur.execute("""
                SELECT TRIM(crew3_name) AS name
                FROM results
                WHERE crew3_sa_sailing_id IS NULL
                  AND crew3_name IS NOT NULL AND TRIM(crew3_name) != ''
                  AND REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TRIM(REPLACE(REPLACE(crew3_name,'/',' '),'&',' and '))),'[^a-z0-9 ]',' ','g'),'\\s+',' ','g') = ANY(%s)
                LIMIT 1
            """, (norm_candidates,))
            row = cur.fetchone()
            if row and (row.get("name") or "").strip():
                nm = (row.get("name") or "").strip()
                sp = _slug_from_name(nm)
                if nm and sp:
                    return nm, "NAME:" + sp
            # Helm/crew in results but no SA ID: try sas_id_personal with first-name variant (Tom<->Thomas)
'''

OLD_PROFILE = '''                WHERE (
                    (r.helm_sa_sailing_id IS NULL AND TRIM(LOWER(r.helm_name)) = TRIM(LOWER(%s)))
                    OR (r.crew_sa_sailing_id IS NULL AND TRIM(LOWER(r.crew_name)) = TRIM(LOWER(%s)))
                )
                ORDER BY COALESCE(reg.end_date, reg.start_date) DESC NULLS LAST, r.result_id DESC
                LIMIT 1
                """,
                (dn, dn),
'''

NEW_PROFILE = '''                WHERE (
                    (r.helm_sa_sailing_id IS NULL AND TRIM(LOWER(r.helm_name)) = TRIM(LOWER(%s)))
                    OR (r.crew_sa_sailing_id IS NULL AND TRIM(LOWER(r.crew_name)) = TRIM(LOWER(%s)))
                    OR (r.crew2_sa_sailing_id IS NULL AND TRIM(LOWER(r.crew2_name)) = TRIM(LOWER(%s)))
                    OR (r.crew3_sa_sailing_id IS NULL AND TRIM(LOWER(r.crew3_name)) = TRIM(LOWER(%s)))
                )
                ORDER BY COALESCE(reg.end_date, reg.start_date) DESC NULLS LAST, r.result_id DESC
                LIMIT 1
                """,
                (dn, dn, dn, dn),
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already patched:", MARKER)
        return 0
    for label, old in (
        ("link", OLD_LINK),
        ("crew2", OLD_CREW),
        ("profile", OLD_PROFILE),
    ):
        n = text.count(old)
        if n != 1:
            print(f"FAIL {label}: found {n} copies", file=sys.stderr)
            return 1
    if text.count("def _wc_sailor_name_link_html") != 1:
        print("FAIL: _wc_sailor_name_link_html count", file=sys.stderr)
        return 1
    text = text.replace(OLD_LINK, HELPER + NEW_LINK, 1)
    text = text.replace(OLD_CREW, NEW_CREW, 1)
    text = text.replace(OLD_PROFILE, NEW_PROFILE, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", API_PATH, "ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
