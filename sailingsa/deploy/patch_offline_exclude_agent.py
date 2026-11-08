from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-excl-agent-{stamp}"))
text = API.read_text(encoding="utf-8")

needle = '''            trail = _lean_offline_build_trail_from_hits(cur, ip=ip, lookback_hours=look_h)
            if not trail:
                continue
'''
insert = '''            trail = _lean_offline_build_trail_from_hits(cur, ip=ip, lookback_hours=look_h)
            # Any agent/dev junk hit on this IP → never a "valid" Done visitor
            try:
                cur.execute(
                    """
                    SELECT 1 FROM public.public_page_hits
                    WHERE ip_address = %s
                      AND occurred_at > NOW() - make_interval(hours => %s)
                      AND (
                        path LIKE '/workspace%%' OR path = '/workspace'
                        OR path LIKE '/cursor%%' OR path LIKE '/.cursor%%'
                        OR path LIKE '%%clean-trail%%' OR path LIKE '%%local-trail%%'
                      )
                    LIMIT 1
                    """,
                    (ip, look_h),
                )
                if cur.fetchone():
                    continue
            except Exception:
                pass
            if not trail:
                continue
'''
if needle not in text:
    raise SystemExit("needle missing")
text = text.replace(needle, insert, 1)

# Also: for staff still in live window but idle with only public pages — include if last PUBLIC hit outside window
# Change human gate: use last public trail occurred_at not max of all hits (admin keeps staff "live")
old_live = '''            in_live_window = False
            try:
                if la is not None:
                    cur.execute(
                        "SELECT (%s::timestamptz > NOW() - make_interval(mins => %s))",
                        (la, live_m),
                    )
                    rr = cur.fetchone()
                    if rr:
                        in_live_window = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
            except Exception:
                pass
'''
new_live = '''            in_live_window = False
            try:
                # Use last *public* trail time so staff sitting on /admin does not hide their public Done trail forever
                last_pub = None
                if trail:
                    last_pub = trail[-1].get("occurred_at")
                check_at = last_pub or la
                if check_at is not None:
                    cur.execute(
                        "SELECT (%s::timestamptz > NOW() - make_interval(mins => %s))",
                        (check_at, live_m),
                    )
                    rr = cur.fetchone()
                    if rr:
                        in_live_window = bool(rr[0] if not isinstance(rr, dict) else next(iter(rr.values())))
            except Exception:
                pass
'''
if old_live not in text:
    raise SystemExit("live window block missing")
text = text.replace(old_live, new_live, 1)

API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK exclude agent + staff public clock")
