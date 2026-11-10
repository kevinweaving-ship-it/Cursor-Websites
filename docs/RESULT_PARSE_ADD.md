# Result Parse - Add

**Named agent / trigger:** say **"Result Parse - Add"** when passing partial or full regatta results from iPhone App → Cursor.

Gold-standard example (Aug 2026): **2026 ILCA KZN Regional Championships**  
Live URL: https://sailingsa.co.za/regatta/2026-08-10-ilca-kzn-regional-championships

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| `sailingsa/deploy/create_*_stub.py` | Master header / nav (locked) |
| `sailingsa/deploy/pass_*_*.py` | `class-results.html` / `results.html` iframe sheets (locked unless `override lock`) |
| `sailingsa/deploy/result_parse_common.py` | Replacing live `api.py` with workspace copy (~26k vs ~64k lines) |
| Live DB pass via SSH (`SSH_LIVE.md`) | Inventing fleets/classes not on the sheet |
| Header icons merge (`wc_regatta_header_icons.json`) | |

**Related docs:** `docs/RESULTS_PASSING_WORKFLOW.md`, `docs/RESULTS_CHECKSUM_RULES.md`, `docs/RESULTS_HTML_STATUS_LINE_RULE.md`, `docs/SAS_ID_RESULTS_NAME_MATCH.md`, `sailingsa/deploy/SSH_LIVE.md`

---

## Inputs (from user / sheet)

Collect before coding:

1. **Regatta** — name, dates, host club code, status line (`Provisional`/`Final` + **as at** date/time)
2. **Source** — PDF/Revolutionise URL or pasted Sailwave table
3. **Per fleet** — class as sailed, Sailed/Discards/To count/Entries/Scoring
4. **Column order** — note if non-standard (e.g. Rank \| Sail No \| Club \| Name \| Category \| Gender \| R1… \| Total \| Nett)
5. **Header icons** — class logo left, host club logo right (if specified)
6. **Partial OK** — one fleet at a time; re-run pass replaces that block only

---

## Step-by-step (agent checklist)

### 1. Stub regatta

Create `sailingsa/deploy/create_YYYY_<slug>_stub.py`:

- `REGATTA_ID` = `YYYY-MM-DD-<event-slug>` (match live URL slug)
- `event_name` without leading year in title
- `result_status`, `as_at_time`, `host_club_id`, `source_url`
- **Merge** header icons JSON — never replace whole `data/wc_regatta_header_icons.json` with one key

Template: `create_2026_ilca_kzn_regionals_stub.py`

### 2. Pass script (fleet data)

Create `sailingsa/deploy/pass_YYYY_<slug>_<fleet>.py`:

- Import shared helpers from `result_parse_common.py`
- Fleet dict per class: `class_original`, `class_canonical`, `block_slug`, `entries`, `discards`, `races`, `rows`
- Row tuple: `(rank, sail, club, name, category, gender, [r1..rn], total, nett)`
- `NAME_ALIASES` only for sheet typos → known SAS spelling

Template: `pass_2026_ilca_kzn_ilca4_ilca7.py`

### 3. Class mapping (validated names only)

| Sheet | `class_canonical` | Never use |
|-------|-------------------|-----------|
| ILCA 4 / Ilca 4 | `Ilca 4.7` | `Ilca 4`, family `Ilca/Laser` |
| ILCA 6 | `Ilca 6` | |
| ILCA 7 | `Ilca 7` | |

**Fleet = class as sailed:** `fleet_label` = `class_canonical`

### 4. Score encoding & checksum (mandatory before insert)

Use `result_parse_common.checksum_row()` — abort pass if any row fails.

| Rule | Example |
|------|---------|
| Penalty = entries + 1 | 12 entries → `"13.0 DNC"`; 10 entries → `"11.0 OCS"` |
| Discarded penalty | `"(13.0 DNC)"` |
| Numeric scores | `"5.0"` not `"5"` |
| One discard | worst (highest) score dropped |
| Total / Nett | must match sheet exactly |

```python
from result_parse_common import checksum_row, encode_score
chk = checksum_row(["1.0", "(3.0)", "2.0"], entries=10, total="6.0", nett="3.0")
assert chk["ok"]
```

### 5. Sailor names (SAS truth)

Use `lookup_sailor()` from `result_parse_common.py`:

1. Match `sas_id_personal` by sail number (`primary_sailno`) when not `TBA`
2. Else match by name (+ aliases for sheet typos)
3. **Store helm_name** = `first_name + last_name` only — ignore `second_name` and `full_name` (often `Surname, First Middle`)
4. **Format:** capitals on first name and surname; particles lowercase (`Kees van Welie`, `Mike Tainton`)
5. Set `helm_sa_sailing_id` when matched
6. Print **UNMATCHED** list for user (Temp ID / alias / SAS scrape)

If SAS row has wrong lowercase (`mike`/`tainton`), **fix source table** for future:

```sql
UPDATE sas_id_personal
SET first_name = 'Mike', last_name = 'Tainton', full_name = 'Mike Tainton', updated_at = NOW()
WHERE sa_sailing_id::text = '29252';
```

See `docs/SAS_ID_RESULTS_NAME_MATCH.md` for bulk name sync migration.

### 6. Run locally (optional) then live

```bash
# Local / dev DB
export DATABASE_URL='postgresql://...'
python3 sailingsa/deploy/pass_YYYY_<slug>_<fleet>.py
```

**Live (SSH — agent must run, not “on your Mac”):**

```bash
sshpass -p '…' scp sailingsa/deploy/pass_*.py sailingsa/deploy/create_*.py \
  root@102.218.215.253:/tmp/kzn_pass/sailingsa/deploy/

ssh root@102.218.215.253 \
  "cd /tmp/kzn_pass && DATABASE_URL='postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master' \
   /var/www/sailingsa/api/venv/bin/python3 sailingsa/deploy/pass_YYYY_<slug>_<fleet>.py"
```

Password / key: `sailingsa/deploy/SSH_LIVE.md`

### 7. Verify

```bash
curl -sI https://sailingsa.co.za/regatta/<regatta_id>   # expect 200
```

DB spot-check:

```sql
SELECT rank, sail_number, helm_name, helm_sa_sailing_id, class_canonical
FROM results WHERE regatta_id = '<regatta_id>' ORDER BY block_id, rank;
```

Confirm status line on page: `Results are Provisional as at DD Month YYYY at HH:MM` (**as at**, not as of).

---

## Partial passes (iPhone → Cursor)

User may paste **one fleet** or a few rows. Agent should:

1. Add/update rows in the pass script for that fleet only
2. Re-run pass (deletes + reinserts that `block_id` only)
3. Leave other fleets untouched
4. Report checksum failures immediately with row name + expected vs computed

---

## File layout (copy for next regatta)

```
sailingsa/deploy/
  result_parse_common.py              # shared — do not duplicate
  create_2026_ilca_kzn_regionals_stub.py
  pass_2026_ilca_kzn_ilca4_ilca7.py
  header_icons_2026_08_10_ilca_kzn_regional_championships.json
```

New regatta: copy stub + pass pattern; change constants and `rows` data only.

---

## Do-not-repeat (live incident)

- **Never** `scp` workspace `api.py` over live `/var/www/sailingsa/api/api.py` (different sizes; caused outage).
- Patch live API surgically if display columns need changing (Category/Gender order).
- **Always merge** `wc_regatta_header_icons.json`; backup before change (`pre-change-backup.sh`).

---

## Quick reference — KZN 2026 constants

| Field | Value |
|-------|-------|
| regatta_id | `2026-08-10-ilca-kzn-regional-championships` |
| Host | PYC |
| Status | Provisional as at 10 August 2026 at 17:25 |
| PDF | https://cdn.revolutionise.com.au/site/ltjdspwjl1li4gni.pdf |
| Fleets | Ilca 4.7 ×12, Ilca 6 ×10, Ilca 7 ×10 |
| Penalties | ILCA4: 13.0; ILCA6/7: 11.0 |

---

## Agent invocation (mobile handoff)

```
Result Parse - Add
Regatta: <name>
URL/slug: <if known>
Source: <PDF or pasted table>
Fleet(s): <class + rows or “partial fleet X only”>
Host/status/icons: <PYC, Provisional, ILCA left / PYC right, etc.>
```

Agent reads this doc + runs checklist; no need to re-derive rules from chat history.
