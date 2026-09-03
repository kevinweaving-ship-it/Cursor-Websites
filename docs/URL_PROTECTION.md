# URL protection — SailingSA live

## Permanent principle

**New pages and experiments must never wipe or change good URLs we are not working on.**

We will always be adding new pages. Each task may only touch **that** page’s URLs and files. Shared production files (`index.html`, `blank.html`, `js/api.js`, `api/api.py`, public sailor/club/class/regatta) stay locked unless the user explicitly names them in the same message.

## Incident (late Aug → early Sep 2026)

While fixing **Lipton / tracking-dev overnight stale pages**, agents repeatedly redeployed:

- Full `sailingsa/frontend` **zip** over `/var/www/sailingsa` (overwrote hub / shared assets)
- A **much smaller** `api.py` (~1.4MB vs ~3.6MB good)

**Result:** public sailor/club/class/regatta/landing URLs looked empty or “old” even when HTTP 200.

**Good restore:** `/root/backup_20260828_081731.tar.gz` (Friday **28 Aug**).

## Rules

### Public / good URLs (never collateral)

Do **not** overwrite unless the user names that URL or writes `deploy public` / `restore …` / `override lock`:

| Path / URL |
|------------|
| `index.html`, `blank.html`, `js/api.js` |
| `api/api.py` |
| `/sailor/*`, `/club/*`, `/class/*`, public `/regatta/*` (no `-dev`) |

### New page / Lipton / tracking sandbox (isolated)

| Allowed | Forbidden |
|---------|-----------|
| Files unique to the new/dev URL only | `index.html`, `blank.html`, shared `js/api.js` |
| e.g. `tracking-dev2*`, `lipton-dev-*` | Full frontend zip extract |
| Dev URLs: `*-dev`, `*-dev2`, `/tracking-dev2` | Default `api.py` deploy |
| Dedicated backend module if any | “While we’re here” edits to good pages |

**Deploy:** `bash sailingsa/deploy/deploy-tracking-dev2-live.sh` (allowlist scp only).

Optional API (dangerous): user must approve, then:

```bash
SAILINGSA_ALLOW_API_DEPLOY=1 bash sailingsa/deploy/deploy-tracking-dev2-live.sh
```

Script aborts if local `api.py` is &lt; 80% of live size.

## Agent checklist

1. Am I working on a **new/dev URL**? → only those files. Stop. Do not touch good URLs.
2. Is this a **named public URL** bug? → diagnose that layer only; ask before restore/deploy.
3. Never claim fixed after curling `/` only.
4. Overnight cache on **dev** pages: bump `?v=` / `Cache-Control` on **dev assets only** — do not redeploy the whole site.

## Related

- `.cursor/rules/url-protection-and-dev-isolate.mdc`
- `docs/TRACKING_DEV2.md`
- `AGENTS.md`
