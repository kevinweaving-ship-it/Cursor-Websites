# Event Interest — controlled deploy (Stages 1–3)

**Do not run against production until integration checks in this doc pass.**

## What ships

| Stage | Artifact | Effect |
|---|---|---|
| 1 | `event_class_interest.sql` (+ rollback) | Interest tables + history immutability |
| 2 | `sailingsa/backend/event_interest.py` + `api.py` registration | `/api/events/.../interest*` |
| 3 | `css/event-interest.css`, `js/event-interest.js` + blank.html patch | Upcoming card UI |

## Preconditions (blockers if unmet)

1. SSH to live available (`~/.ssh/sailingsa_live_key` or `SSHPASS`).
2. Live Upcoming cards can be given correct `data-event-id` = `public.events.event_id`.
3. Each of those events has rows in `public.event_edition_classes` (class picker FK). Empty edition → popup shows “not configured”; interest cannot be saved.
4. Stage 1/2/3 + this deploy branch reviewed; backup taken via `pre-change-backup.sh`.

## Order (one controlled pass)

### A. Backup
```bash
bash sailingsa/deploy/pre-change-backup.sh
```

### B. Database (Stage 1)
```bash
# On live, with production DSN — apply once
psql "$DB_URL" -v ON_ERROR_STOP=1 -f sailingsa/deploy/event_class_interest.sql
```
Rollback if needed:
```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 -f sailingsa/deploy/event_class_interest_rollback.sql
```

### C. Seed / verify edition classes
```bash
# Read-only check — must return ≥1 class per upcoming event_id
psql "$DB_URL" -c "
  SELECT event_id, count(*) AS classes
  FROM public.event_edition_classes
  WHERE event_id IN (168679, 246456, 248485, 45)
  GROUP BY 1 ORDER BY 1;"
```
If any event is missing, **stop** and load edition classes before continuing (do not invent classes).

### D. Code (API + frontend assets)
```bash
# Prefer verified api deploy + frontend zip from SSH_LIVE.md
bash sailingsa/deploy/deploy-with-key.sh
# Ensure these land on the web root / API path:
#   /var/www/sailingsa/api/api.py  (with register_event_interest_routes)
#   /var/www/sailingsa/api/sailingsa/backend/event_interest*.py
#   /var/www/sailingsa/css/event-interest.css
#   /var/www/sailingsa/js/event-interest.js
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  "systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
```

### E. Landing patch (blank.html only — do not overwrite hub from repo index.html)
Repo `index.html` does **not** currently contain Upcoming cards. Live hub is `blank.html`.
```bash
python3 sailingsa/deploy/patch_blank_event_interest.py --file /path/to/blank.html --write
# Or on live after scp of the patcher:
ssh … 'python3 /tmp/patch_blank_event_interest.py --file /var/www/sailingsa/blank.html --write'
```

Default slot → event_id map (verify on prod before write):
| slot | event_id | title (live) |
|---|---|---|
| 1 | 168679 | 2026 EC Dinghy Regionals |
| 2 | 246456 | Flying fifteen & Soling Nationals |
| 3 | 248485 | TSC Cape Classic |
| 4 | 45 | 2026 USSA Sailing Championships |

### F. Smoke tests
```bash
bash sailingsa/deploy/smoke_event_interest.sh https://sailingsa.co.za
```

### G. Rollback
1. Landing: restore `blank.html.bak_*` created by the patcher.
2. Frontend assets: remove or revert `css/event-interest.css` / `js/event-interest.js` references (patcher `--revert`).
3. API: redeploy previous `api.py` / backend without `register_event_interest_routes`; `systemctl restart sailingsa-api`.
4. DB (only if needed): `event_class_interest_rollback.sql` (drops interest tables only).

## Local integration checks (must pass before live)

```bash
export EVENT_INTEREST_VALIDATE_DSN='postgresql://…@127.0.0.1:5432/…'
python3 sailingsa/deploy/validate_event_class_interest_schema.py
python3 sailingsa/deploy/test_event_interest_api.py
python3 sailingsa/deploy/smoke_event_interest_integration.py
```
