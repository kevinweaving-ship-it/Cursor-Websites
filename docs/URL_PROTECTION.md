# URL protection — SailingSA live

## Incident (late Aug → early Sep 2026)

While fixing **Lipton / tracking-dev overnight stale pages**, agents repeatedly redeployed:

- Full `sailingsa/frontend` **zip** over `/var/www/sailingsa` (overwrote hub / shared assets)
- A **much smaller** `api.py` (~1.4MB vs ~3.6MB good)

**Result:** public sailor/club/class/regatta/landing URLs looked empty or “old” even when HTTP 200.

**Good restore:** `/root/backup_20260828_081731.tar.gz` (Friday **28 Aug**).

## Rules

### Public production (protected)

Do **not** overwrite without explicit user approval in the same message:

| Path / URL |
|------------|
| `index.html`, `blank.html`, `js/api.js` |
| `api/api.py` |
| `/sailor/*`, `/club/*`, `/class/*`, public `/regatta/*` (no `-dev`) |

### Dev / Lipton sandbox (isolated)

| Allowed | Forbidden |
|---------|-----------|
| `tracking-dev2.html`, `css/tracking-dev2.css`, `css/lipton-dev.css` | `index.html`, `blank.html` |
| `js/tracking-dev2-*.js`, `js/lipton-dev-*` | Full frontend zip extract |
| Dev URLs: `*-dev`, `*-dev2`, `/tracking-dev2` | Default `api.py` deploy |
| `sailingsa/backend/tracking_dev2_sailfish.py` | “Landing fix” scp during Lipton work |

**Deploy:** `bash sailingsa/deploy/deploy-tracking-dev2-live.sh` (allowlist scp only).

Optional API (dangerous): user must approve, then:

```bash
SAILINGSA_ALLOW_API_DEPLOY=1 bash sailingsa/deploy/deploy-tracking-dev2-live.sh
```

Script aborts if local `api.py` is &lt; 80% of live size.

## Agent checklist

1. Is this a **dev URL** task? → allowlist deploy only. Stop.
2. Is this a **public URL** bug? → diagnose layer; do not touch Lipton zip; ask before restore/deploy.
3. Never claim fixed after curling `/` only.
4. Overnight cache on **dev** pages: bump `?v=` / `Cache-Control` on **dev assets only** — do not redeploy the whole site.

## Related

- `.cursor/rules/url-protection-and-dev-isolate.mdc`
- `docs/TRACKING_DEV2.md`
- `AGENTS.md`
