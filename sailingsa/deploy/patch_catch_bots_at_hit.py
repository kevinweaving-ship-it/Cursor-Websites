#!/usr/bin/env python3
"""Quarantine bounce/junk/sterile at hit+leave time so new sessions match manual cleanup."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''def _lean_maybe_quarantine_missed_bot(cur, ip_address: str, current_path: str = "") -> None:
    """Apply the same bounce/junk/sterile rules used in Live cleanup, at hit/leave time.

    Skips IPs that already showed a real multi-page / engaged browse.
    """
    ip = (ip_address or "").strip()[:80]
    if not ip:
        return
    try:
        if _lean_ip_has_human_browse(cur, ip):
            return
    except Exception:
        pass
    path = (current_path or "").split("?", 1)[0].strip() or ""
    try:
        if path and _lean_is_junk_false_path(path):
            _lean_quarantine_ip(cur, ip, "junk_false_path")
            return
    except Exception:
        pass
    trail = []
    try:
        cur.execute(
            """
            SELECT path, dwell_seconds, engagement, left_at
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - INTERVAL '45 minutes'
            ORDER BY occurred_at ASC
            LIMIT 30
            """,
            (ip,),
        )
        for row in cur.fetchall() or []:
            if isinstance(row, dict):
                trail.append(
                    {
                        "path": row.get("path"),
                        "dwell_seconds": row.get("dwell_seconds"),
                        "engagement": row.get("engagement"),
                        "open": row.get("left_at") is None,
                    }
                )
            else:
                trail.append(
                    {
                        "path": row[0],
                        "dwell_seconds": row[1],
                        "engagement": row[2],
                        "open": row[3] is None,
                    }
                )
    except Exception:
        if path:
            trail = [{"path": path, "dwell_seconds": 0, "open": True}]
    if not path and trail:
        path = (trail[-1].get("path") or "") if isinstance(trail[-1], dict) else ""
    try:
        if any(
            _lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "")
            for t in trail
        ):
            _lean_quarantine_ip(cur, ip, "junk_false_path")
            return
        if _lean_sterile_short_trail_bot(trail, path, ip):
            reason = (
                "cloud_sterile_short"
                if _lean_ip_is_cloud_datacenter(ip)
                else "sterile_single_page"
            )
            _lean_quarantine_ip(cur, ip, reason)
            return
        if _lean_bounce_home_bot(trail, path):
            _lean_quarantine_ip(cur, ip, "bounce_home_no_engage")
            return
    except Exception:
        pass


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-catch-hit-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_maybe_quarantine_missed_bot" not in text:
        anchor = text.find("def _lean_bounce_home_bot")
        if anchor < 0:
            raise SystemExit("bounce helper missing")
        text = text[:anchor] + HELPER + text[anchor:]

    # After new URL stay insert
    old_ins = '''    cur.execute(
        """
        INSERT INTO public.public_page_hits
            (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
        VALUES (%s, %s, %s, NOW(), NULL, NULL)
        """,
        (vid, ip, p),
    )
    return True
'''
    new_ins = '''    cur.execute(
        """
        INSERT INTO public.public_page_hits
            (visitor_id, ip_address, path, occurred_at, left_at, dwell_seconds)
        VALUES (%s, %s, %s, NOW(), NULL, NULL)
        """,
        (vid, ip, p),
    )
    try:
        _lean_maybe_quarantine_missed_bot(cur, ip, p)
    except Exception:
        pass
    return True
'''
    if old_ins not in text:
        raise SystemExit("record_url_stay insert block not found")
    if "_lean_maybe_quarantine_missed_bot(cur, ip, p)" not in text:
        text = text.replace(old_ins, new_ins, 1)
        print("hooked record_url_stay_hit")
    else:
        print("record hook already present")

    # End of close open hit
    old_close_end = '''                    WHERE ip_address = %s AND left_at IS NULL
                    """,
                    (at, at, ip),
                )
    except Exception:
        pass


def '''
    # find unique - the function after close
    i = text.find("def _close_open_public_page_hit")
    if i < 0:
        raise SystemExit("close fn missing")
    # next def after close
    j = text.find("\ndef ", i + 10)
    close_fn = text[i:j]
    if "_lean_maybe_quarantine_missed_bot" not in close_fn:
        # replace trailing except pass before next def
        if close_fn.rstrip().endswith("pass"):
            # insert before final except's end
            patched = close_fn.rstrip() + "\n    try:\n        if ip:\n            _lean_maybe_quarantine_missed_bot(cur, ip)\n    except Exception:\n        pass\n\n\n"
            text = text[:i] + patched + text[j:]
            print("hooked close_open_public_page_hit")
        else:
            # insert before last except pass
            marker = "    except Exception:\n        pass\n"
            last = close_fn.rfind(marker)
            if last < 0:
                raise SystemExit("close end marker missing")
            close_fn2 = (
                close_fn[: last + len(marker)]
                + "    try:\n        if ip:\n            _lean_maybe_quarantine_missed_bot(cur, ip)\n    except Exception:\n        pass\n\n"
            )
            text = text[:i] + close_fn2 + text[j:]
            print("hooked close via marker")
    else:
        print("close hook already present")

    # After idle finalize — quarantine bounce homes that just got dwell closed
    old_fin = '''        return int(cur.rowcount or 0)
    except Exception:
        return 0


def _lean_parse_engage_tokens'''
    new_fin = '''        n = int(cur.rowcount or 0)
        if n:
            try:
                cur.execute(
                    """
                    SELECT DISTINCT h.ip_address
                    FROM public.public_page_hits h
                    JOIN public.public_sessions s ON s.ip_address = h.ip_address
                    WHERE h.left_at IS NOT NULL
                      AND h.left_at > NOW() - INTERVAL '10 minutes'
                      AND s.last_activity < NOW() - make_interval(secs => %s)
                    LIMIT 80
                    """,
                    (idle,),
                )
                for row in cur.fetchall() or []:
                    ipx = row[0] if not isinstance(row, dict) else row.get("ip_address")
                    if ipx:
                        _lean_maybe_quarantine_missed_bot(cur, str(ipx))
            except Exception:
                pass
        return n
    except Exception:
        return 0


def _lean_parse_engage_tokens'''
    if old_fin not in text:
        # try without following def name exact
        if "def _lean_parse_engage_tokens" in text and "_finalize_idle_open_page_hits" in text:
            old_fin2 = '''        return int(cur.rowcount or 0)
    except Exception:
        return 0
'''
            # only replace first occurrence inside finalize — find finalize then replace once in that region
            fi = text.find("def _finalize_idle_open_page_hits")
            fj = text.find("\ndef ", fi + 10)
            region = text[fi:fj]
            if "_lean_maybe_quarantine_missed_bot" in region:
                print("finalize hook already present")
            elif old_fin2 in region:
                region2 = region.replace(
                    old_fin2,
                    '''        n = int(cur.rowcount or 0)
        if n:
            try:
                cur.execute(
                    """
                    SELECT DISTINCT ip_address FROM public.public_page_hits
                    WHERE left_at IS NOT NULL
                      AND left_at > NOW() - INTERVAL '15 minutes'
                      AND ip_address IS NOT NULL AND TRIM(ip_address) <> ''
                    LIMIT 80
                    """
                )
                for row in cur.fetchall() or []:
                    ipx = row[0] if not isinstance(row, dict) else row.get("ip_address")
                    if ipx:
                        _lean_maybe_quarantine_missed_bot(cur, str(ipx))
            except Exception:
                pass
        return n
    except Exception:
        return 0
''',
                    1,
                )
                text = text[:fi] + region2 + text[fj:]
                print("hooked finalize_idle")
            else:
                print("WARN finalize region unexpected")
                print(repr(region[-400:]))
        else:
            raise SystemExit("finalize block not found")
    else:
        text = text.replace(old_fin, new_fin, 1)
        print("hooked finalize exact")

    # Offline: quarantine when bounce/junk detected
    old_off = '''                ):
                    is_bot = True
                else:
                    # cloud single-page no engage → bot
'''
    new_off = '''                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_maybe_quarantine_missed_bot(cur, ip, path)
                        except Exception:
                            pass
                else:
                    # cloud single-page no engage → bot
'''
    # only in offline section - first occurrence after bounce_home in offline
    bi = text.find("or _lean_bounce_home_bot(trail, path)")
    if bi >= 0:
        chunk = text[bi : bi + 500]
        if old_off in chunk:
            text = text[:bi] + chunk.replace(old_off, new_off, 1) + text[bi + 500 :]
            print("offline quarantine on bot")
        elif "_lean_maybe_quarantine_missed_bot(cur, ip, path)" in chunk:
            print("offline q already")
        else:
            # wider
            chunk = text[bi : bi + 900]
            if old_off in chunk:
                text = text[:bi] + chunk.replace(old_off, new_off, 1) + text[bi + len(chunk) :]
                print("offline quarantine on bot (wide)")
            else:
                print("WARN offline is_bot block", repr(chunk[:400]))

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK catch-at-hit (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
