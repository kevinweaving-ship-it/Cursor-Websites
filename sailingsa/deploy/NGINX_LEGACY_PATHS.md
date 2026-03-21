# Nginx: legacy path redirects (sailingsa.co.za)

Apply these in the **sailingsa.co.za** server block. Place the block **above** the sailor/class/regatta proxy blocks.

## Snippet to add

```nginx
# normalize legacy paths
location = /index.html {
    return 301 https://sailingsa.co.za/;
}

location = /home {
    return 301 https://sailingsa.co.za/;
}

location = /home/ {
    return 301 https://sailingsa.co.za/;
}
```

Reference full block: `sailingsa/deploy/nginx-timadvisor-patched.conf` (SailingSA server block).

---

## On the server

1. **Edit** the nginx site config that contains the sailingsa.co.za server block (e.g. `/etc/nginx/sites-available/...` or the file that’s symlinked in `sites-enabled`).

2. **Test config**
   ```bash
   sudo nginx -t
   ```
   You must see:
   ```
   syntax is ok
   test is successful
   ```

3. **Reload nginx**
   ```bash
   sudo systemctl reload nginx
   ```

4. **Verify redirects**
   ```bash
   curl -I https://sailingsa.co.za/index.html
   curl -I https://sailingsa.co.za/home
   ```
   Expected:
   ```
   HTTP/1.1 301
   Location: https://sailingsa.co.za/
   ```
