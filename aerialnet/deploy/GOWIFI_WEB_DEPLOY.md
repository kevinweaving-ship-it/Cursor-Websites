# GoWifi login + admin-dashboard — REA deploy path

Host: box.gowifi.co.za. User `rea` has **no general root**. Privileged work goes through
`/usr/local/sbin/rea-ops-helper` (ForceCommand / `rea-ops`).

## What you may publish

Stage files, then one helper verb:

| Stage (write as rea) | Live |
|---|---|
| `/opt/rea/ops/stage/gowifi-web/login/` | `https://gowifi.co.za/login/` → `/home/user-data/www/default/login/` |
| `/opt/rea/ops/stage/gowifi-web/dash/` | `https://gowifi.co.za/dash/` → `/home/user-data/www/default/dash/` |

Allowed extensions only: `.html .css .js .svg .png .jpg .jpeg .webp .ico .woff .woff2 .map`

## Exact commands

```bash
# 1. Write staged files (rea can write these paths)
#    /opt/rea/ops/stage/gowifi-web/login/index.html
#    /opt/rea/ops/stage/gowifi-web/dash/index.html   (and other dash html/js/css)

# 2. Deploy (backs up live dash+login, copies allowlisted files, nginx -t && reload)
/opt/rea/ops/bin/rea-ops deploy gowifi-web

# 3. Or via helper (same verb)
sudo -n /usr/local/sbin/rea-ops-helper deploy gowifi-web
```

Rollback:

```bash
/opt/rea/ops/bin/rea-ops backup gowifi-web          # extra snapshot if needed
/opt/rea/ops/bin/rea-ops rollback <backup_id>       # id from deploy JSON
```

nginx only:

```bash
/opt/rea/ops/bin/rea-ops nginx test
/opt/rea/ops/bin/rea-ops nginx reload
```

## Forbidden (already denied)

- Unrestricted root / `exec-b64` / shell as root
- `/home/user-data/www/.gowifi-dash.htpasswd` and `.gowifi-seo.htpasswd`
- `accounts.json`, Dolibarr books JSON
- `/etc/nginx/conf.d/local.conf` (Mail-in-a-Box owns it)
- `/home/user-data/www/gowifi.co.za.conf` (extra include; login location already added)
- `/root/secrets`, `/root/gowifi-upp`, SSL private keys, SSH keys, `.env`
- WhatsApp auth/session, sailingsa-api Gold replace
- Restart of healthy WhatsApp / mail / ssh

`/dash/` stays behind existing basic-auth. `/login/` is public client login (no htpasswd).
Do not move admin htpasswd onto `/login/`.

## Services

No new units. Deploy may `nginx -t` then `reload nginx` only. Do not restart nginx.
Do not restart `gowifi-*-api`, Dolibarr, or WhatsApp for this work.

## Existing protection preserved

- `rea` sudoers remain `REA_STATUS` / `REA_JOURNAL` / `REA_CTRL` only
- Helper ForceCommand still rejects unknown verbs and secret paths
- MIAB `local.conf` is not patched
- Live files are copied to `/opt/rea/ops/backups/` before replace
