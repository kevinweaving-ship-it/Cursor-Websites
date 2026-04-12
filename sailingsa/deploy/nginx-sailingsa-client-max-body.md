# Nginx: allow large Breaking News image uploads

Default nginx `client_max_body_size` is **1m**, which returns **413** before the API can resize photos.

**Live site file:** `/etc/nginx/sites-available/sailingsa` (symlinked from `sites-enabled/sailingsa`).

Inside the `location ^~ /api/ {` block, add:

```nginx
        client_max_body_size 100m;
```

Then:

```bash
nginx -t && systemctl reload nginx
```

The API endpoint `POST /api/super-admin/regatta/{id}/breaking-news-image` accepts up to **80MB** raw and compresses server-side; nginx must allow the request body through.
