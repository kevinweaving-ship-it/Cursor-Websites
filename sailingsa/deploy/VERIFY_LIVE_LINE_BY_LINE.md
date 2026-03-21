# Verify live line-by-line

Use this when comparing local vs live so nothing is missed.

## 1. Frontend (what deploy-with-key.sh pushes)

- **Stylesheet:** In `index.html` and `public/index.html`, the main CSS link must be:
  - `href="/css/main.css"` (root-relative). Not `href="css/main.css"`.
- **Site-stats iframe:** In both index files:
  - `src="/site-stats.html"`. Not `src="site-stats.html"`.

## 2. Files that deploy actually updates

- Script zips **`sailingsa/frontend/`** and uploads to server. Server unzips into `/var/www/sailingsa/` (so `index.html`, `css/main.css`, `public/index.html`, etc. land there).
- **api.py is NOT in that zip.** Deploy-with-key.sh only uploads `sailingsa/api/modules/`. To change live api.py you use the separate flow: scp api.py to `/root/incoming/`, then on server `/root/deploy_api.sh` (see SSH_LIVE.md).

## 3. Quick local checks before you push

```bash
grep -n 'href=.*main\.css' sailingsa/frontend/index.html sailingsa/frontend/public/index.html
# Expect: href="/css/main.css"

grep -n 'site-stats\.html' sailingsa/frontend/index.html sailingsa/frontend/public/index.html
# Expect: src="/site-stats.html"
```

## 4. On the server (after you deploy)

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "grep -n 'main\.css\|site-stats' /var/www/sailingsa/index.html /var/www/sailingsa/public/index.html"
```

If you see `css/main.css` or `site-stats.html` without the leading `/`, the wrong version is on live.

## 5. Restart API after any api.py change

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
```

Expect: `active`.
