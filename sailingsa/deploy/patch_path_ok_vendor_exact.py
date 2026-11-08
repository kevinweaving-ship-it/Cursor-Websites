import os, sys
sys.path.insert(0, "/var/www/sailingsa/api")
os.chdir("/var/www/sailingsa/api")
os.environ["DB_URL"] = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
import api as A
import psycopg2.extras
conn = A.get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM public.traffic_quarantine_ips WHERE ip_address IN ('54.221.146.249','34.62.7.178','20.104.85.180')")
print("Q rows", cur.fetchall())
# force quarantine again
for ip,r in [("54.221.146.249","cloud_bot"),("20.104.85.180","probe_path"),("34.62.7.178","agent_junk_path")]:
    A._lean_quarantine_ip(cur, ip, r)
conn.commit()
cur.execute("SELECT * FROM public.traffic_quarantine_ips WHERE ip_address IN ('54.221.146.249','34.62.7.178','20.104.85.180')")
print("Q after", cur.fetchall())
unified = A._lean_traffic_unified_sql("24 hours")
cur.execute("SELECT COUNT(*) hits, COUNT(DISTINCT visitor_key) vis FROM ("+unified+") x")
print("unified", cur.fetchone())
A.return_db_connection(conn)

# Also patch path_ok for /vendor exact and common probe singles
from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone
API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-vendor-{stamp}"))
t = API.read_text()
# add to NOT IN list in path_ok
needle = "'/graphql', '/v1/graphql', '/class', '/club'"
if "'/vendor'" not in t[t.find("def _lean_traffic_path_ok_sql"):t.find("def _lean_traffic_path_ok_sql")+2500]:
    # path_ok uses NOT IN list from earlier patch - find it
    pass
# Add AND clauses
old = "      AND {col} NOT LIKE '/vendor/{pct}'"
new = "      AND {col} NOT LIKE '/vendor/{pct}'\n      AND {col} <> '/vendor'\n      AND {col} <> '/events'"
# /events might be real page on sailingsa - check. User site may have /events. Don't block /events globally - quarantine IP is enough.
new = "      AND {col} NOT LIKE '/vendor/{pct}'\n      AND {col} <> '/vendor'"
if old in t:
    t = t.replace(old, new, 1)
    API.write_text(t)
    py_compile.compile(str(API), doraise=True)
    print("path_ok vendor exact")
else:
    print("vendor like missing")
