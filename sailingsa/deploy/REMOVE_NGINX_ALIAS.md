# STEP 5: Remove nginx /sailingsa/frontend/ alias

For the hard-fail test to pass, `/sailingsa/frontend/login.html` must return **404**.

If nginx has this block, **remove it**:

```nginx
location /sailingsa/frontend/ {
    alias /var/www/sailingsa/;
}
```

Then: `nginx -t && sudo systemctl reload nginx`

After removal: `/login.html` → 200, `/sailingsa/frontend/login.html` → 404
