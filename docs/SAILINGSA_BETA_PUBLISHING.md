# SailingSA.co.za Beta publishing

**Single reference for pushing the Beta (and later versions) to the cloud server.**

---

## Goals

- Publish Beta (and future versions) to https://sailingsa.co.za
- **Production domain only:** Beta V1 must be served on the real domain. No temporary subdomains, IP URLs, or alternate test URLs. Testers use the real public URL so Google can index immediately, SEO signals accrue to the correct domain, and feedback reflects real-world behaviour (search, sharing, previews).
- **Never brick the server**: backup first, rollback possible, no destructive changes
- **Push newer versions** anytime using the same process
- **Do not affect**: database, server config (e.g. `.env`), or existing HTML/data except where we intentionally replace frontend/backend code

---

## Golden rules (never break)

| Rule | Why |
|------|-----|
| **Always backup on server before deploy** | So we can restore if something goes wrong. |
| **Deploy from a git tag** | Reproducible; we can redeploy or rollback the same version. |
| **No destructive database changes** | Beta/V1 deploys are code-only. DB changes only via additive migrations. |
| **Do not edit code on the server** | All changes come from this repo; deploy by replacing files. |
| **Do not overwrite server `.env`** | Credentials and config live on the server; we never replace them with project defaults. |
| **Full replace frontend/backend, not partial** | Prevents mixed old/new code and broken state. |

---

## What gets deployed (and what does not)

| Deploy | What we update | What we do not touch |
|--------|----------------|----------------------|
| **Frontend** | All files under web root (e.g. `index.html`, assets, css, js) — full replace from zip. | Server `.env`, nginx config, DB. |
| **Backend (Node)** | `server.js`, `package.json`, `package-lock.json`, `routes/`. Install deps on server with `npm ci` / `npm install --production`. | `node_modules` (reinstall on server). Server `.env`. |
| **Python API** (if used) | `api.py`, `requirements.txt`. On server: venv, `pip install -r requirements.txt`, restart. | Server `.env`, database data. |
| **Database** | Only if you run an **additive** migration script (new tables/columns/indexes). | No DROP, no DELETE of data, no destructive migrations. |

So: **HTML pages and app code are updated by deploy; database and server config are preserved unless you explicitly run a safe migration or change config.**

---

## Versioning and tags

- **Beta:** tag format `prod_beta_YYYY_MM_DD` (e.g. `prod_beta_2026_02_06`).
- **V1 (later):** tag format `prod_v1_YYYY_MM_DD`.
- Create the tag **before** deploying. Never deploy from untagged or uncommitted state.

```bash
# Create tag (from project root, on the commit you want to deploy)
git tag prod_beta_2026_02_07
git push origin prod_beta_2026_02_07   # if using remote
```

---

## Exact deployment steps (every time)

Use this for **first Beta** and for **every newer version** (only the tag name and zip contents change).

### Pre-requisites (local)

1. Code is committed and the tag you want is created and (if applicable) pushed.
2. Checkout that tag and confirm clean state:
   ```bash
   git fetch --tags
   git checkout prod_beta_2026_02_07   # or your tag
   git status   # should be clean (or deploy from a machine that has only this tag checked out)
   ```

### Step A — Build package (local, from project root)

3. **Frontend zip (full replace):**
   ```bash
   cd sailingsa/frontend
   zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak"
   cd ../..
   ```
   Output: `sailingsa-frontend.zip` at project root.

4. **Backend (Node)** — have these ready to upload or pull from git at the same tag:
   - `sailingsa/backend/server.js`
   - `sailingsa/backend/package.json`, `sailingsa/backend/package-lock.json`
   - `sailingsa/backend/routes/` (all files)
   - Do **not** upload local `node_modules`; install on server with `npm ci` or `npm install --production`.

5. **Python API** (if production uses it): have `api.py` and `requirements.txt` from project root (same tag).

### Step B — On the server (sailingsa.co.za)

6. **Backup current live state (mandatory):**
   - Copy current web root to a dated backup, e.g.:
     ```bash
     sudo cp -a /var/www/sailingsa.co.za /var/www/sailingsa.co.za.backup.$(date +%Y%m%d)
     ```
   - If you use git on the server, note current tag/commit: `git describe --tags` or `git rev-parse HEAD`.

7. **Deploy frontend (full replace):**
   - Upload `sailingsa-frontend.zip` to the server.
   - Extract to the web root **replacing** existing frontend files (e.g. into `/var/www/sailingsa.co.za/` or whatever nginx serves for `/`).
   - Example:
     ```bash
     cd /var/www/sailingsa.co.za
     unzip -o /path/to/sailingsa-frontend.zip
     ```
   - Do **not** do partial file copies; replace the full frontend tree so we don’t leave old files behind.

8. **Deploy backend (Node):**
   - Upload or pull the backend files from the same tag.
   - On server: `cd <backend_dir> && npm ci` (or `npm install --production`).
   - Restart the Node service: e.g. `pm2 restart sailingsa-backend` or `sudo systemctl restart sailingsa-backend`.

9. **Deploy Python API** (if used):
   - Upload `api.py` and `requirements.txt` (or pull from git at same tag).
   - On server: activate venv, `pip install -r requirements.txt`, restart the API (systemd or pm2).
   - **Do not** overwrite the server’s `.env` with a project `.env.example`.

10. **Database:** For Beta/V1, do **not** run any migration unless you have an agreed additive script. No destructive changes.

10b. **Fix robots.txt + sitemap.xml routing (nginx) — required for SEO**

   If nginx uses `try_files $uri /index.html;`, requests to `/robots.txt` and `/sitemap.xml` can fall through to `index.html` (wrong content and wrong Content-Type). Google will treat robots as invalid and delay indexing.

   Add these **exact-match** location blocks **before** the main `location /` block in your sailingsa nginx config (e.g. `/etc/nginx/sites-available/sailingsa.co.za` or equivalent). Rules: blocks must appear before `location /`; no fallback to SPA routing; missing files must return 404, not HTML.

   ```nginx
   location = /robots.txt {
       default_type text/plain;
       try_files $uri =404;
   }
   location = /sitemap.xml {
       default_type application/xml;
       try_files $uri =404;
   }
   ```

   `root` inherits from the server block. Ensure `index.html`, `robots.txt`, and `sitemap.xml` are at the web root. Then: `nginx -t && sudo systemctl reload nginx`.

10c. **Path alias (if needed):** Production serves from `/`. If old links use `/sailingsa/frontend/`, add this **before** `location /`:

   ```nginx
   location /sailingsa/frontend/ {
       alias /var/www/sailingsa/;
   }
   ```

   See `sailingsa/deploy/nginx-alias-sailingsa-frontend.conf`. The frontend now uses root paths (`/index.html`, `/login.html`); this alias keeps legacy links working.

### Step C — Post-deploy verification

11. **Smoke tests (mandatory):** In the browser (https://sailingsa.co.za/):
    - [ ] Landing page loads (desktop + mobile)
    - [ ] Sailor profile (at least 2 different sailors)
    - [ ] Results — Lite results page
    - [ ] Results — Full results page
    - [ ] News feed
    - [ ] Search
    - [ ] Zero console errors
    - [ ] Zero 404s on internal links

12. **SEO verification (hard requirement):**
    - [ ] `view-source:https://sailingsa.co.za/` shows real HTML: `<title>`, `<meta name="description">`, `<h1>` present (not empty shells)
    - [ ] `/robots.txt` returns crawler rules (text/plain), not HTML
    - [ ] `/sitemap.xml` returns valid XML (application/xml)

12b. **Sailor profile URLs (for Google and direct access):**
    - **Canonical URL:** `https://sailingsa.co.za/sailor/<slug>` (e.g. `/sailor/cordelia-dagnall`). Use this in sitemaps and links.
    - **Legacy / typo:** `/sailing/<slug>` 301-redirects to `/sailor/<slug>`, so both work.
    - For Google to **crawl** the profile and **present that URL in search** so sailors can open their profile directly, two things must be true: (1) the URL returns the profile page (SPA loads and resolves the slug), and (2) the **production database** contains that sailor in `sas_id_personal`. If production DB is missing the sailor, `/api/sailor/resolve?slug=...` returns "Sailor not found" and the profile will not load. So: sync or populate production DB for sailors you want indexable and shareable.

13. Record the deploy (e.g. in a `DEPLOYS.md` or runbook): tag name and date.

---

## Pushing a newer version (same process)

- Create a **new tag** from the commit you want (e.g. `prod_beta_2026_02_14`).
- Follow the **exact same steps** above:
  - Checkout that tag locally.
  - Build a new `sailingsa-frontend.zip` from that tag.
  - On server: **backup** → replace frontend → replace backend → reinstall Node deps → restart Node (and Python API if used).
- Database and server `.env` are **not** touched by this; you keep pushing newer code without affecting data or config.

---

## Rollback (if something goes wrong)

1. On the server, restore the backup of the web root (and backend dir if you backed it up):
   ```bash
   sudo rm -rf /var/www/sailingsa.co.za
   sudo cp -a /var/www/sailingsa.co.za.backup.YYYYMMDD /var/www/sailingsa.co.za
   ```
2. Restart services (Node, and Python API if used).
3. Optionally, from your machine: checkout the **previous** tag, rebuild the zip, and redeploy using the same steps (so the server matches a known good tag).

No database restore is needed for code-only rollbacks.

---

## Server config we do not replace

- **Environment variables** (`.env` or systemd/PM2 env): DB URLs, OAuth credentials, API keys, CORS, etc. Set once on the server and leave alone during code deploys.
- **Nginx** (or other reverse proxy) config.
- **SSL** certificates and Certbot config.
- **Database** contents; only additive migrations if agreed.

See also: `sailingsa/backend/DEPLOYMENT_CREDENTIALS.md` for OAuth and env setup on the live server.

---

## Quick reference

| Action | Command / note |
|--------|-----------------|
| Create deploy tag | `git tag prod_beta_YYYY_MM_DD` then `git push origin prod_beta_YYYY_MM_DD` |
| Build frontend zip | `cd sailingsa/frontend && zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak"` |
| On server: backup | `sudo cp -a /var/www/sailingsa.co.za /var/www/sailingsa.co.za.backup.$(date +%Y%m%d)` |
| On server: Node | `cd <backend> && npm ci && pm2 restart sailingsa-backend` (or systemctl) |
| **Site stats / API** | Nginx must have `location /api/ { proxy_pass http://127.0.0.1:8000; ... }` so `/api/site-stats` hits the Python API (DB). See `sailingsa/deploy/nginx-proxy-sailor-routes.conf`. |
| Rollback | Restore from `sailingsa.co.za.backup.YYYYMMDD` and restart services |

---

## Local vs Live – do not assume they are identical

| | Local | Live |
|---|--------|------|
| **API host** | Same origin (e.g. `http://192.168.0.130:8081`) | Same origin (`https://sailingsa.co.za`) – **no** localhost or local ports |
| **Routing** | Requests go straight to uvicorn | Nginx **must** proxy `/api/` and `/auth/` to backend (e.g. `http://127.0.0.1:8000`) |
| **Frontend** | Must use `window.location.origin` only; no hardcoded `:8080`, `:8081`, `192.168`, `localhost` |

**Repo state:** Frontend uses `window.location.origin` (and production fallback `https://sailingsa.co.za` where needed). No local IP or port refs in `sailingsa/frontend` HTML/JS.

**Live verification:** After deploy, on https://sailingsa.co.za open DevTools → Network; reload; confirm every request is to `https://sailingsa.co.za/...` (no 192.168 or localhost). If any request goes to local IP/port, the **deployed** frontend is stale or wrong – redeploy from this repo.

---

## Correct order to fix redirects and resolve (sailor URLs)

If `index.html?sas_id=...` returns 200 instead of 301, or resolve returns "Sailor not found", fix in **this order**. Do not touch frontend or redeploy randomly.

### Step 1 — Confirm API version on server

On the server:

```bash
grep sailing_to_sailor_redirect /var/www/sailingsa/api/api.py
```

If nothing prints → **api.py is not deployed**. Deploy the repo’s `api.py` and restart the API.

```bash
systemctl status sailingsa-api
```

Ensure the service is running and using the correct working directory.

### Step 2 — Confirm API redirect works directly (bypass nginx)

On the server:

```bash
curl -sI 'http://127.0.0.1:8000/index.html?sas_id=18020'
```

- **301** → backend is correct; nginx is not proxying (fix Step 3).
- **200** → backend not updated or route order wrong; fix API deploy first.

### Step 3 — Fix nginx (critical)

Inside the **sailingsa** server block (e.g. in `sites-enabled/timadvisor`), these `location` blocks **must** appear **above** any `location /` (or `location / { try_files ... }`):

```nginx
location = / {
    proxy_pass http://127.0.0.1:8000;
}
location = /index.html {
    proxy_pass http://127.0.0.1:8000;
}
location ~ ^/sailor/ {
    proxy_pass http://127.0.0.1:8000;
}
location ~ ^/sailing/ {
    proxy_pass http://127.0.0.1:8000;
}
```

Then:

```bash
nginx -t
sudo systemctl reload nginx
```

See **sailingsa/deploy/nginx-proxy-sailor-routes.conf** for the same snippet.

### Step 4 — Fix production database

Resolve fails with `{"error":"Sailor not found"}` because the **production** DB does not contain that sailor (e.g. `sas_id=18020`). The API uses `sas_id_personal` (or whatever `DB_URL` / `DATABASE_URL` points at).

- Check which DB production uses:  
  `cat /etc/systemd/system/sailingsa-api.service` (look for `Environment=DB_URL=...` or `DATABASE_URL=...`) or check `/var/www/sailingsa/api/.env`.
- If production is pointing at an empty or different DB, either point it at the full DB or import/sync the data. Do not change frontend or redeploy blindly.

**Reality:** Even with nginx and API correct, profiles will fail until production DB has the sailors.

**Production DB — verified (live server):**

- **Config:** `cat /etc/systemd/system/sailingsa-api.service` → `DB_URL` / `DATABASE_URL` = `postgresql://sailors_user:***@localhost:5432/sailors_master`
- **Table:** `sas_id_personal` (used by `/api/sailor/resolve` and redirect logic)
- **Row count:** ~28,217 rows (DB is not empty)
- **Sailor 18020:** Not present in production `sas_id_personal`. That is why resolve returns `{"error":"Sailor not found"}` and why redirect cannot produce a slug for that ID. Until that sailor (and any others you need) exist in production, SEO/indexing and direct profile links for them will fail regardless of routing.

---

## Related docs

- **DEPLOYMENT_PLAN.md** (project root) — Same flow in more detail; Beta/V1 rules and blockers.
- **sailingsa/deploy/push-live.sh** — Builds the frontend zip only (manual upload).
- **sailingsa/deploy/push-to-cloud.sh** — Automated: build zip → backup → SCP → extract (requires SSH to server). Run from project root: `./sailingsa/deploy/push-to-cloud.sh`. Override server: `SAILINGSA_SERVER=102.218.215.253 SAILINGSA_WEB_ROOT=/var/www/sailingsa ./sailingsa/deploy/push-to-cloud.sh`.
- **sailingsa/backend/DEPLOYMENT_CREDENTIALS.md** — Google OAuth and env for live server.
- **deploy/prod/.env.example** — Example env vars only; do not overwrite server `.env` with this.

---

## Live server: debug /sailor/{slug} 404 (route order)

**LIVE ONLY. Do not test locally. Do not edit nginx or DB.**

If `https://sailingsa.co.za/sailor/ben-henshilwood` returns 404, confirm the running API and route order on the server.

### 1) Confirm the running API file has the handler

```bash
grep -n "serve_sailor_spa" /var/www/sailingsa/api/api.py
```

You should see line numbers where `serve_sailor_spa` is defined and used.

### 2) Confirm the route is in the file

```bash
grep -n '@app.get("/sailor/{slug}")' /var/www/sailingsa/api/api.py
```

You should see a line (e.g. `470:...`) with that route.

### 3) Print the route table from the running app

From the API directory on the server (so `api` is importable):

```bash
cd /var/www/sailingsa/api
python3 -c "
from api import app
for r in app.routes:
    print(r.path)
"
```

**You must see `/sailor/{slug}` in the output.**

- If it does **not** appear → wrong file deployed or app not restarted after deploy. Deploy current `api.py` and run `sudo systemctl restart sailingsa-api`.
- If it **does** appear → route order in the file is correct; then either the request is not reaching FastAPI (e.g. nginx serving 404 for `/sailor/...`) or another process is serving the app.

### Correct order in api.py (no code change if already like this)

- `app = FastAPI()` then redirect middleware, then explicit routes: `/`, `/index.html`, **`/sailor/{slug}`**, `/regatta/{slug}`, `/sailing/{slug}`, then all `/api/...` and other routes, then **last**: `app.mount("/", StaticFiles(...), name="static")`.
- **StaticFiles must be the last thing registered.** In the repo, `/sailor/{slug}` is at ~line 470 and `app.mount` is at ~line 8870.

---

## Summary

- **How:** Tag → build frontend zip (+ have backend files at same tag) → on server: backup → full replace frontend → replace backend → `npm ci` + restart.
- **Never brick:** Always backup before deploy; rollback by restoring backup and restarting services; no destructive DB changes.
- **Newer versions:** Same process with a new tag and new zip; database and server config stay unchanged.
- **Database / HTML:** DB and server config are left alone; only code (HTML/JS/CSS and backend) is updated by the deploy.

### If timadvisor.co.za still shows redirect (Safari cache)

The server serves TimAdvisor; a **cached 301** in Safari can make it keep redirecting to sailingsa.

1. **Bypass cache:** Open **https://www.timadvisor.co.za/?t=1** (query string often bypasses cached redirect).
2. **Clear site data in Safari:** Safari → Settings → Privacy → Manage Website Data → search “timadvisor” → Remove.
3. **Or empty caches:** If you have the Develop menu: Develop → Empty Caches, then reload timadvisor.co.za.
