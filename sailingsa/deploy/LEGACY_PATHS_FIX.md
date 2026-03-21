# Legacy Paths Fix — Until Done, Cloud ≠ Mac

## 1. Delete legacy directories on server

```bash
rm -rf /var/www/sailingsa/sailingsa
rm -rf /var/www/sailingsa/frontend
```

## 2. Remove nginx alias for legacy paths

Edit nginx site config, **delete** any block like:

```nginx
location /sailingsa/frontend/ {
    alias /var/www/sailingsa/frontend/;
}
```

Or any `/sailingsa/` alias at all.

## 3. Reload nginx

```bash
nginx -t && systemctl reload nginx
```

## 4. Verify (proof)

**Must be 404:**
- https://sailingsa.co.za/sailingsa/frontend/login.html
- https://sailingsa.co.za/sailingsa/frontend/index.html

**Must be 200:**
- https://sailingsa.co.za/
- https://sailingsa.co.za/login.html
- https://sailingsa.co.za/sailor.html?sa_id=21172

## Final sanity check

```bash
grep -R "/sailingsa/frontend" -n /var/www/sailingsa
```

→ Should return **nothing**.

---

**Bottom line:** Until legacy paths return 404, the app will not behave like the Mac version. Once they do, the problem disappears completely.
