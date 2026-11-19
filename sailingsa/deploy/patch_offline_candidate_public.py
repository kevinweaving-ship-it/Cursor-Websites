from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-cand-pub-{stamp}"))
text = API.read_text(encoding="utf-8")

old = '''        cur.execute(
            """
            SELECT h.ip_address,
                   MAX(h.occurred_at) AS last_hit,
                   MIN(h.occurred_at) AS first_hit
            FROM public.public_page_hits h
            WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
              AND h.occurred_at > NOW() - make_interval(hours => %s)
              AND h.ip_address <> '102.218.215.253'
            GROUP BY h.ip_address
            HAVING MAX(h.occurred_at) <= NOW() - make_interval(mins => %s)
                OR h.ip_address IN (
                     SELECT ip_address FROM public.traffic_quarantine_ips
                     WHERE COALESCE(active, true) = true
                       AND COALESCE(first_seen_at, last_seen_at) <= NOW() - INTERVAL '60 seconds'
                   )
            ORDER BY MAX(h.occurred_at) DESC
            LIMIT 80
            """,
            (look_h, live_m),
        )
'''
new = '''        # All IPs with hits in lookback; Done vs Live decided later from last *public* trail time
        cur.execute(
            """
            SELECT h.ip_address,
                   MAX(h.occurred_at) AS last_hit,
                   MIN(h.occurred_at) AS first_hit
            FROM public.public_page_hits h
            WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
              AND h.occurred_at > NOW() - make_interval(hours => %s)
              AND h.ip_address <> '102.218.215.253'
            GROUP BY h.ip_address
            ORDER BY MAX(h.occurred_at) DESC
            LIMIT 100
            """,
            (look_h,),
        )
'''
if old not in text:
    raise SystemExit("candidate sql missing")
text = text.replace(old, new, 1)
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK candidates")
