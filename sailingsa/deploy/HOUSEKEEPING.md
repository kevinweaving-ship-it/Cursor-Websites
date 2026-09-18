# SailingSA permanent housekeeping

Infrastructure only. **No** `api.py`, DB pool, SQL, nginx, frontend, or application changes.

## Install (live)

```bash
scp -i ~/.ssh/sailingsa_live_key -r sailingsa/deploy/sailingsa-housekeeping.py \
  sailingsa/deploy/sailingsa-housekeeping.wrapper \
  sailingsa/deploy/housekeeping-keep.list \
  sailingsa/deploy/install-housekeeping.sh \
  sailingsa/deploy/cron.d-sailingsa-housekeeping \
  sailingsa/deploy/journald-sailingsa-retention.conf \
  sailingsa/deploy/logrotate-rsyslog-sailingsa \
  sailingsa/deploy/logrotate-sailingsa-housekeeping \
  root@102.218.215.253:/root/incoming/housekeeping/

ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'python3 /root/incoming/housekeeping/sailingsa-housekeeping.py --dry-run'

# Review: ZERO deletes of media / PDFs / telemetry / PG / source / KEEP rollbacks.
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'bash /root/incoming/housekeeping/install-housekeeping.sh && /usr/local/sbin/sailingsa-housekeeping --apply'
```

## Commands

| Command | Effect |
|---|---|
| `sailingsa-housekeeping --dry-run` | Report exactly what **would** be removed. Default if neither flag is passed. |
| `sailingsa-housekeeping --apply` | Perform only approved safe-retention cleanup. Logs every deletion and before/after disk. |

Lock: `/var/lock/sailingsa-housekeeping.lock` (flock; overlapping runs exit).  
Log: `/var/log/sailingsa-housekeeping.log`  
KEEP list: `/etc/sailingsa/housekeeping-keep.list`  
Schedule: `/etc/cron.d/sailingsa_housekeeping` — `15 4 * * *` `--apply`

## Retention

| Class | Rule |
|---|---|
| Full backups (`/root/backup_YYYYMMDD_HHMMSS.tar.gz` **and** size ≥ 1 GB) | Keep latest **3** tar-valid. Delete older only after newer retained backups exist **and** are tar-valid. |
| Scoped / tiny `backup_*.tar.gz` | **Report only.** Not full backups. |
| `api.py.YYYYMMDD_HHMMSS[.bak]` in `/var/www/sailingsa/api/` and `/root/backups/` | Keep latest **10** per directory. |
| Named / ambiguous `api.py.bak*` | **Report only.** |
| Releases in `/root/releases/` | KEEP/known-good retained forever. Ordinary intermediate expire after **14 days**. |
| KEEP / known-good / `BEFORE_BIO` / keep-list paths | **Never** auto-deleted. |

## Temporary / debug (48 hours)

Eligible only under `/tmp` (plus disposable `/root/__pycache__` and `/tmp/**/__pycache__`):

- `/tmp/ssa_*`
- stress-test / matrix output
- diagnostic JSON/JSONL
- temporary patches matching `ssa_*.patch` / `cursor_diag_*`

**Never expired:** `*.env`, cookies, secrets, keys, PDFs, media.

## Logs

- journald: `SystemMaxUse=500M`, `SystemKeepFree=1G`, `MaxRetentionSec=14day`  
  (`/etc/systemd/journald.conf.d/sailingsa-retention.conf`)
- rsyslog: daily + `maxsize 100M`, rotate 14. **Does not `rm` the active syslog.**  
  Original saved as `/etc/logrotate.d/rsyslog.pre-housekeeping`.

## Disk bands

| Use | Band | Cleanup |
|---|---|---|
| < 75% | OK | Safe-retention rules only |
| 75–84% | WARNING | Same safe-retention rules only |
| ≥ 85% | CRITICAL | Same safe-retention rules only |

**Never** auto-delete production/user data to recover space.

## Absolute protected data

Automated housekeeping never deletes these by age or size:

- `/media`, `/media/og`, frontend media/uploads
- PDFs, event/result documents
- Lipton telemetry/archive (`/root/lipton-vakaros-archive`)
- Postgres data (`/var/lib/postgresql`)
- Production source (`/var/www/sailingsa`) except timestamped `api.py.*.bak` via the bak rule
- `.env` / credentials / SSH
- Explicit KEEP / known-good / rollback files

Unknown or ambiguous files = **REPORT, DO NOT DELETE**.

## Process audit (report only)

Each run reports SailingSA listening ports, uvicorn processes, restore/test units, zombies, and processes running from `/tmp` or backup/release paths.

- **Do not** automatically kill an unknown production process.
- **8002 / `sailingsa-admin-api`:** report only; leave running until separately decided.
- **8001 / `sailingsa-api-restore`:** must stay disabled.

## Cursor production rule

Every production task that creates backups, releases, temporary files, diagnostic processes, or test services **owns those artifacts** and must clean them up when the task finishes.

End-of-task report:

1. Temporary files removed
2. Temporary processes/services stopped
3. Backups intentionally retained
4. Disk utilisation
5. Unexpected leftovers

Do **not** create a repeated full ~11 GB backup for every surgical change. Use a scoped `api.py` snapshot unless a full backup is genuinely required.

Mark anything that must survive housekeeping as KEEP (filename or `/etc/sailingsa/housekeeping-keep.list`).
