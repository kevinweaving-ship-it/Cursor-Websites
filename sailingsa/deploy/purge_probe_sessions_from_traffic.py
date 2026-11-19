#!/usr/bin/env python3
import subprocess
import psycopg2
import psycopg2.extras

env = subprocess.check_output(
    ["systemctl", "show", "sailingsa-api", "-p", "Environment", "--value"], text=True
)
db = None
for part in env.split():
    if part.startswith("DATABASE_URL=") or part.startswith("DB_URL="):
        db = part.split("=", 1)[1]
        break
conn = psycopg2.connect(db)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

probe_re = r"(^/wp-|backup|\.zip$|\.sql$|\.bak$|/xmlrpc|/wordpress|/phpmyadmin|\.(zip|sql|bak|tar|gz|rar|7z)$)"

cur.execute(
    """
    SELECT DISTINCT ip_address FROM public.public_sessions
    WHERE COALESCE(last_path, '') ~* %s
    """,
    (probe_re,),
)
ips = [(r["ip_address"] or "").strip() for r in (cur.fetchall() or []) if r.get("ip_address")]
print("probe_ips", len(ips), ips[:15])

cur.execute(
    """
    DELETE FROM public.public_page_hits
    WHERE COALESCE(path, '') ~* %s
    """,
    (probe_re,),
)
print("deleted_hits", cur.rowcount)

cur.execute(
    """
    DELETE FROM public.public_sessions
    WHERE COALESCE(last_path, '') ~* %s
    """,
    (probe_re,),
)
print("deleted_sessions", cur.rowcount)

for ip in ips:
    cur.execute(
        """
        INSERT INTO public.traffic_quarantine_ips
            (ip_address, reason, active, hit_count, first_seen_at, last_seen_at)
        VALUES (%s, 'probe_path', true, 1, NOW(), NOW())
        ON CONFLICT (ip_address) DO UPDATE SET
            active = true,
            reason = 'probe_path',
            hit_count = public.traffic_quarantine_ips.hit_count + 1,
            last_seen_at = NOW()
        """,
        (ip[:80],),
    )
print("quarantined", len(ips))
conn.commit()

# confirm trackable list has zip
import pathlib
src = pathlib.Path("/var/www/sailingsa/api/api.py").read_text(encoding="utf-8")
# find trackable function chunk
i = src.find("def _is_trackable_page_path")
j = src.find("def _admin_current_page_label", i)
chunk = src[i:j]
print("trackable_has_zip", '".zip"' in chunk)
print("probe_has_wp_backup_rule", "path_only.startswith(\"/wp-\")" in chunk or 'path_only.startswith("/wp-")' in src)
print("live_probe_guest_rule", "never Guest / sailor / registered" in src)

cur.execute(
    """
    SELECT COUNT(*)::int AS n FROM public.public_sessions
    WHERE COALESCE(last_path,'') ILIKE %s OR COALESCE(last_path,'') ILIKE %s
    """,
    ("%wp-backup%", "%.zip"),
)
print("remaining_probe_sessions", cur.fetchone()["n"])
cur.close()
conn.close()
