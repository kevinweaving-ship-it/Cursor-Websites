# Fix live (sailingsa.co.za) — do this on the server

**See also:** `SSH_LIVE.md` for full SSH and deploy commands.

**Problem:** `/api/*` and `/auth/*` return HTML instead of hitting the Python API. Nginx is not proxying them to 127.0.0.1:8000.

---

## Step 1: SSH to the server

```bash
ssh root@102.218.215.253
```

(Use your password when prompted.)

---

## Step 2: Check if the API is running

```bash
systemctl status sailingsa-api
# or
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/site-stats
```

- If **200** → API is running; the issue is nginx only.
- If **connection refused** or **000** → start the API:
  ```bash
  systemctl start sailingsa-api
  # or if no systemd service:
  cd /var/www/sailingsa/api && source venv/bin/activate && uvicorn api:app --host 127.0.0.1 --port 8000 &
  ```

---

## Step 3: Fix nginx (add proxy for /api/ and /auth/)

Config file is usually: `/etc/nginx/sites-enabled/timadvisor`

**3a) Backup:**
```bash
sudo cp /etc/nginx/sites-enabled/timadvisor /tmp/timadvisor.bak.$(date +%Y%m%d%H%M)
```

**3b) Edit the file** and find the `server { ... }` block that has `server_name` for sailingsa.co.za. **Before** the line that says `location / {` (or `location / {`), add these two blocks:

```nginx
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location ^~ /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
```

So the order inside the server block is:
1. (other location blocks if any)
2. **location ^~ /api/ { ... }**
3. **location ^~ /auth/ { ... }**
4. **location / {** ... try_files ... **}**

**3c) Test and reload:**
```bash
nginx -t && sudo systemctl reload nginx
```

If `nginx -t` fails, fix the syntax (often a missing `}` or `;`) and try again.

---

## Step 4: Verify

```bash
curl -s -o /dev/null -w "%{http_code}" https://sailingsa.co.za/api/site-stats
```

You should see **200** and the response body should be **JSON** (e.g. `{"active_sailors":...}`), not HTML.

Then in the browser: https://sailingsa.co.za/ — stats, login, and search should work.
