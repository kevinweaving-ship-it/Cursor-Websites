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

None for the weekly cycle. Failures mail `kevin@aerialnet.co.za` (root@box
bounces on this host) and leave the last good edition in place. Re-run:
`systemctl start sailing-roundup.service` on GoWifi.

## Proved cycle — 19 October 2026 SAST

Backup first: `/opt/rea/work/sailing-roundup-backup-20261019-111926.tgz`
(sha256 `f472cf7370d7f6dd5e6608f019eaa3cc3ae5d0be66860dd39c598a3fec71b1e7`).
Installed REA commit `fb9b551069a209dfcae9b6b8134afdce26db66bb` into the
existing project; issues/public/data/.venv kept.

Authenticated publish: `rea` key `/opt/rea/.ssh/id_rea_publish` →
`root@102.218.215.253`. SailingSA `sailing-roundup.timer` is **masked**.

### Reference issue 2026-09-28

`run-monday.sh` with `ROUNDUP_MODE=test-weekend` at 11:25:10 SAST:
generate ok (4 reports, 1 unique photograph) → issue-scoped publish →
`https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/` HTTP 200.

Live hashes match GoWifi rebuild:

| file | sha256 prefix |
| --- | --- |
| index.html | `627bbb478f9002e6` |
| issue.json | `0c017dcbab828949` |
| edition.pdf | `0f5d624badf3cc23` |
| media/2026-09-25-tsc-420-nationals.jpg | `c90991a59e878c66` |

Content checks on that URL: Timothy Weaving and Hayden Miller are the
under-17 champions (NovaNews caption + body cite [2]); helm/crew cells are
people, not school names; four podium tables of three rows; JPEG photograph
is unique and is the U17 pair with the 420 trophy; no Wikimedia.

### Production Monday 2026-10-19

`ROUNDUP_MODE=due` (current Monday in Africa/Johannesburg). Same script at
11:29:29 SAST rebuilt `2026-10-19`, published only that issue, verified
`https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/` (HTML/JSON/PDF
200; hashes `128507b6c5859f4c` / `c6f4dd75f9302076` / `cba87686000a14c0`).
09-28 hashes unchanged. 10-05 and 10-12 left in place.

### Controls

- Timer next: Mon 2026-10-26 06:00 SAST (`Africa/Johannesburg`).
- Overlap: second `run-monday.sh` while lock held printed `skip` and exited 0.
- Retry: three attempts, 90s apart (generate / publish / verify).
- Last good: local `backups/` + `data/last-success.json`; remote
  `.last-good/issues/`.
- Alert path: sendmail to `kevin@aerialnet.co.za` stored in INBOX
  (`status=sent`, msgid `20261019093317.A002610D2EB`).
