# Nginx Auth Proxy — Final Fix (Manual Steps)

**Target file:** `/etc/nginx/sites-enabled/timadvisor`  
**Target block:** `server { ... }` for sailingsa.co.za

---

## 1. Remove any existing `/auth/` block

Delete these if present:
```
location /auth/
location /auth
location ^~ /auth/
```

## 2. Add this block ABOVE `location /`

```
    location ^~ /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
```

## 3. Ensure `/api/` matches this format

```
    location ^~ /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
```

## 4. Order: these come BEFORE `location /`

```
location / {
    try_files $uri $uri/ /index.html;
}
```

## 5. Reload nginx

```bash
nginx -t && systemctl reload nginx
```

## 6. Verify (MUST NOT RETURN 405)

```bash
curl -i -X POST https://sailingsa.co.za/auth/login \
  -H "Content-Type: application/json" \
  -d '{"provider":"username","username":"21172","password":"test"}'
```

Expected: **200** (valid) or **401** (invalid) — NOT 405.

---

## After api.py Facebook fix

```bash
systemctl restart sailingsa-api
```
