#!/usr/bin/env python3
"""Export regatta 385 table data only. No HTML. Uses live-compatible column lists."""
import os, json
import psycopg2

def sql_val(v):
    if v is None:
        return 'NULL'
    if isinstance(v, dict):
        return "'" + json.dumps(v).replace("'", "''") + "'::jsonb"
    return psycopg2.extensions.adapt(v).getquoted().decode()

DB = os.getenv('DATABASE_URL', 'postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master')
REG = '385-2026-hyc-cape-classic'
out = os.path.join(os.path.dirname(__file__), 'regatta_385_sync.sql')

# Live schema column lists (no id)
REGATTAS_COLS = 'regatta_id,regatta_number,event_name,year,regatta_type,host_club_id,host_club_code,host_club_name,province_code,province_name,start_date,end_date,result_status,fleet_classes,source_url,local_file_path,file_type,doc_hash,import_status,best_method,name_check_local_vs_source,correct_url_source_match_name,relevant_data_to_columns,raw_data_length,scoring_system,scoring_mode,created_at,updated_at,as_at_time,source_platform'.split(',')

conn = psycopg2.connect(DB)
cur = conn.cursor()
lines = ["BEGIN;", "DELETE FROM results WHERE regatta_id = '%s';" % REG, "DELETE FROM regatta_blocks WHERE regatta_id = '%s';" % REG, "DELETE FROM regattas WHERE regatta_id = '%s';" % REG]

cur.execute("SELECT " + ",".join(REGATTAS_COLS) + " FROM regattas WHERE regatta_id = %s", (REG,))
r = cur.fetchone()
if r:
    vals = [sql_val(v) for v in r]
    lines.append("INSERT INTO regattas (" + ",".join(REGATTAS_COLS) + ") VALUES (" + ",".join(vals) + ");")

cur.execute("SELECT * FROM regatta_blocks WHERE regatta_id = %s", (REG,))
brows = cur.fetchall()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='regatta_blocks' ORDER BY ordinal_position")
bcols_all = [x[0] for x in cur.fetchall()]
bcols = [c for c in bcols_all if c != 'id']
for row in brows:
    vals = [sql_val(row[bcols_all.index(c)]) for c in bcols]
    lines.append("INSERT INTO regatta_blocks (" + ",".join(bcols) + ") VALUES (" + ",".join(vals) + ");")

cur.execute("SELECT * FROM results WHERE regatta_id = %s ORDER BY block_id, rank", (REG,))
rrows = cur.fetchall()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='results' ORDER BY ordinal_position")
rcols_all = [x[0] for x in cur.fetchall()]
rcols = [c for c in rcols_all if c != 'id']
for row in rrows:
    row = dict(zip(rcols_all, row))
    # Result 4563: Sail 1311 Optimist B 7th = Mason Guthrie, NO SAS ID (never Gordon 5820).
    if row.get('result_id') == 4563:
        row['helm_name'] = 'Mason Guthrie'
        row['helm_sa_sailing_id'] = None
        row['class_canonical'] = 'Optimist'
        row['class_original'] = 'Optimist'
        row['fleet_label'] = 'Optimist B'
    vals = [sql_val(row[c]) for c in rcols]
    lines.append("INSERT INTO results (" + ",".join(rcols) + ") VALUES (" + ",".join(vals) + ");")

lines.append("COMMIT;")
cur.close()
conn.close()

with open(out, 'w') as f:
    f.write("\n".join(lines))
print("Wrote", out, "- regattas:", 1 if r else 0, "blocks:", len(brows), "results:", len(rrows))
