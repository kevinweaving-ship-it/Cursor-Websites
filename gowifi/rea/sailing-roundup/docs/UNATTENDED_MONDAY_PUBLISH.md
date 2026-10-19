# Unattended Monday weekend roundup

Generation stays on GoWifi (`/opt/rea/work/sailing-roundup`). Publication is
authenticated, issue-scoped rsync onto SailingSA
`/var/www/sailingsa/sailing-roundup/issues/YYYY-MM-DD/` only. No SailingSA SPA,
API, nginx, database, or other site files are modified.

## Schedule

- Timer: `sailing-roundup.timer` — `OnCalendar=Mon *-*-* 06:00:00` (host timezone
  Africa/Johannesburg), `Persistent=true`.
- Service: `sailing-roundup.service` as user `rea`.
- Issue date: current Monday in `Africa/Johannesburg` via `safe_publish.py --monday`.
- Overlap: `flock` on `data/monday.lock`; a second start exits 0.
- Retry: three attempts, 90s apart, for generate, publish, and public-URL verify.
- Last good: local `backups/` + `data/last-success.json`; remote
  `/var/www/sailingsa/sailing-roundup/.last-good/issues/YYYY-MM-DD/`.
- Alerts: `/usr/sbin/sendmail` to `ROUNDUP_ALERT_TO` (default `root`) on
  generate, publish, or URL-verify failure.

## Duplicate publishers

The only enabled timer is GoWifi `sailing-roundup.timer`. The SailingSA-local
copy at `/opt/sailing-roundup` is disabled and masked so it cannot publish.

## Publish path

1. `app/safe_publish.py` builds in `.builds/`, validates unique events, accepted
   sources, citation-backed paragraphs, podium-only tables, unique photo hashes,
   HTML and PDF, then atomically replaces only that issue.
2. `deploy/publish-to-sailingsa.sh <public> <issue>` stages the one issue on
   SailingSA, validates HTML/JSON/PDF, keeps last-good, then directory-renames
   into `issues/<issue>/`. Landing files (`index.html`, `latest.json`,
   `feed.json`, `cards.json`) are overwritten without `--delete` of other issues.
3. `run-monday.sh` curls
   `https://sailingsa.co.za/sailing-roundup/issues/<issue>/` plus `issue.json`
   and `edition.pdf` and checks the rebuilt HTML.

SSH: `rea` uses `/opt/rea/.ssh/id_rea_publish` → `root@102.218.215.253`
(`Host sailingsa-publish` in `/opt/rea/.ssh/config`).

## Reference weekend

`2026-09-28` (26–27 Sep) remains the audit edition. Build with
`ROUNDUP_MODE=test-weekend` or `python3 app/safe_publish.py --test-weekend`.
Production `data/roundup.env` must be `ROUNDUP_MODE=due`.

## Manual involvement

None for the weekly cycle. Failures mail `root` and leave the last good edition
in place. Re-run: `systemctl start sailing-roundup.service` on GoWifi.
