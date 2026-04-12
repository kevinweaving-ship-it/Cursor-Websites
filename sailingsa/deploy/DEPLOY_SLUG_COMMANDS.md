# Deploy slug/redirect to live — exact commands

Run from **project root** (`Project 6`). Server: **102.218.215.253**, user **root**, web root **/var/www/sailingsa**, API dir **/var/www/sailingsa/api**.

---

## 1) Build frontend zip (local)

```bash
cd "$(git rev-parse --show-toplevel)"
cd sailingsa/frontend
zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak" -x "*.md"
cd ../..
```

---

## 2) Backup + deploy frontend (on server via SSH)

Use SSH key so Cursor/scripts can run without password. Key: `~/.ssh/sailingsa_live_key`.

```bash
SERVER=102.218.215.253
WEB_ROOT=/var/www/sailingsa
KEY=~/.ssh/sailingsa_live_key

# Upload zip
scp -i $KEY -o StrictHostKeyChecking=no sailingsa-frontend.zip root@${SERVER}:/tmp/

# Backup web root, extract, chown
ssh -i $KEY root@${SERVER} "B=\$(date +%Y%m%d_%H%M%S); sudo cp -a ${WEB_ROOT} ${WEB_ROOT}.backup.\$B && echo Backup: ${WEB_ROOT}.backup.\$B; cd ${WEB_ROOT} && unzip -o /tmp/sailingsa-frontend.zip && rm -f /tmp/sailingsa-frontend.zip && chown -R www-data:www-data ${WEB_ROOT}"
```

---

## 3) Backup + deploy backend (on server via SSH)

```bash
SERVER=102.218.215.253
API_DIR=/var/www/sailingsa/api
KEY=~/.ssh/sailingsa_live_key

# Backup current api.py on server
ssh -i $KEY root@${SERVER} "cp ${API_DIR}/api.py ${API_DIR}/api.py.backup.\$(date +%Y%m%d_%H%M%S)"

# Upload api.py from project root
scp -i $KEY -o StrictHostKeyChecking=no api.py root@${SERVER}:${API_DIR}/

# On server: add STATIC_DIR to service, reload, restart
ssh -i $KEY root@${SERVER} "grep -q STATIC_DIR /etc/systemd/system/sailingsa-api.service || (sed -i '/WorkingDirectory=/a Environment=\"STATIC_DIR=/var/www/sailingsa\"' /etc/systemd/system/sailingsa-api.service); systemctl daemon-reload && systemctl restart sailingsa-api && sleep 2 && systemctl status sailingsa-api --no-pager | head -12"
```

---

## 4) Nginx: proxy /, /index.html, /about, /sailor/ to API

On server, edit the sailingsa site config (e.g. `/etc/nginx/sites-enabled/timadvisor`). Add these `location` blocks **before** any existing `location /` or `location /api/`:

```nginx
    location = / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /index.html {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location ~ ^/sailor/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /about {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
```

Or run: `expect sailingsa/deploy/fix-nginx-about.exp` to add `/about` automatically.

Then:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "nginx -t && systemctl reload nginx"
```

---

## 5) Verify (run locally)

```bash
# 301 from ?sas_id= to /sailor/<slug>
curl -sI "https://sailingsa.co.za/index.html?sas_id=18020"
# Expect: 301, Location: https://sailingsa.co.za/sailor/ben-henshilwood (or canonical slug)

curl -sI "https://sailingsa.co.za/index.html?sas_id=16401"
# Expect: 301, Location: https://sailingsa.co.za/sailor/<slug>

# /sailor/<slug> returns 200 and HTML
curl -sI "https://sailingsa.co.za/sailor/ben-henshilwood"
# Expect: 200

# Resolve endpoint
curl -s "https://sailingsa.co.za/api/sailor/resolve?sas_id=18020"
# Expect: JSON with slug, canonical_url
```

---

## One-shot (SSH key — recommended)

From project root:

```bash
bash sailingsa/deploy/deploy-with-key.sh
```

Uses `~/.ssh/sailingsa_live_key`; no password. Builds zip, uploads, extracts, chown, restarts sailingsa-api.

**Alternative (expect + password):** `expect sailingsa/deploy/push-to-cloud-expect.exp`. See **SSH_LIVE.md** for full SSH/deploy docs. Add nginx location blocks (step 4) and `location = /about` once (or run `expect sailingsa/deploy/fix-nginx-about.exp`).
