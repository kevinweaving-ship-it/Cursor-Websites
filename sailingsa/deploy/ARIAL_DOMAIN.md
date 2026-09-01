# arial.co.za on the SailingSA server (later)

Dev UI is **`https://sailingsa.co.za/arial`** until DNS + TLS for `arial.co.za` exist. Same machine: `102.218.215.253`.

## 1) DNS (registrar for arial.co.za)

Create:

| Type | Name | Value |
|------|------|--------|
| A | `@` (arial.co.za) | `102.218.215.253` |
| A | `www` | `102.218.215.253` |

Wait until `dig +short arial.co.za` returns that IP before Certbot.

## 2) Nginx (own server blocks — do not add to sailingsa `server_name`)

Copy `sailingsa/deploy/nginx-arial.conf` onto the box (e.g. `/etc/nginx/sites-available/arial`), `ln -s` into `sites-enabled`, then HTTP-only first so Certbot can answer.

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253
nginx -t && systemctl reload nginx
certbot --nginx -d arial.co.za -d www.arial.co.za
nginx -t && systemctl reload nginx
```

Same pattern as `timadvisor.co.za` in `nginx-timadvisor-patched.conf`.

## 3) App + token

- Frontend: `/var/www/sailingsa/arial/` (from deploy zip `arial/` folder).
- API: process already on `127.0.0.1:8000`; nginx proxies `/api/arial/` there.
- Copy **`arial_api.py`** next to live `api.py` (`/var/www/sailingsa/api/arial_api.py`) whenever `api.py` is deployed.
- Set **`OLARM_API_TOKEN`** on the API service (never in git). Restart `sailingsa-api`.

Until this is done, use **`https://sailingsa.co.za/arial`**.
