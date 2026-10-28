# GoWifi website + authentication — REA deploy path

Host: box.gowifi.co.za. User `rea` has **no general root**. Privileged work
goes through `/usr/local/sbin/rea-ops-helper` (ForceCommand / `rea-ops`).

This is the live runbook. Rea can publish the homepage, `/login/`, `/dash/`
assets, and the dedicated `gowifi-auth` service, then roll them back, without
Cursor.

## What you may publish

Stage files as `rea`, then one helper verb:

| Stage (write as rea) | Live |
|---|---|
| `/opt/rea/ops/stage/gowifi-home/index.html` | `https://gowifi.co.za/` → `/home/user-data/www/default/index.html` |
| `/opt/rea/ops/stage/gowifi-web/login/` | `https://gowifi.co.za/login/` → `/home/user-data/www/default/login/` |
| `/opt/rea/ops/stage/gowifi-web/dash/` | `https://gowifi.co.za/dash/` → `/home/user-data/www/default/dash/` |
| `/opt/rea/ops/stage/gowifi-auth/app.py` | `/opt/gowifi-auth/` (`gowifi-auth.service` on `127.0.0.1:8810`) |

Homepage: exactly `index.html`. Rejects symlinks, traversal, and non-HTML.

Login/dash extensions: `.html .css .js .svg .png .jpg .jpeg .webp .ico .woff .woff2 .map`

Auth extensions: `.py .txt .lock .md .json` — never `new-password`, `.env`,
`accounts.json`, `sessions.json`, or any JSON that contains password/secret keys.

## Exact commands

```bash
# --- Homepage (landing + Login popup) ---
# write /opt/rea/ops/stage/gowifi-home/index.html
/opt/rea/ops/bin/rea-ops deploy gowifi-home
# JSON includes backup.backup_id

# --- Login + admin dash static assets ---
# write /opt/rea/ops/stage/gowifi-web/login/...
# write /opt/rea/ops/stage/gowifi-web/dash/...
/opt/rea/ops/bin/rea-ops deploy gowifi-web

# --- Dedicated auth service ---
# write /opt/rea/ops/stage/gowifi-auth/app.py  (and optional locked deps)
/opt/rea/ops/bin/rea-ops deploy gowifi-auth

# --- Rollback (id from the matching deploy JSON) ---
/opt/rea/ops/bin/rea-ops backup gowifi-home
/opt/rea/ops/bin/rea-ops backup gowifi-web
/opt/rea/ops/bin/rea-ops backup gowifi-auth
/opt/rea/ops/bin/rea-ops rollback <backup_id>
# After an auth rollback, restart the unit:
/opt/rea/ops/bin/rea-ops restart gowifi-auth

# --- Health ---
/opt/rea/ops/bin/rea-ops status gowifi-auth
/opt/rea/ops/bin/rea-ops journal gowifi-auth 80
/opt/rea/ops/bin/rea-ops health gowifi-auth
/opt/rea/ops/bin/rea-ops nginx test
/opt/rea/ops/bin/rea-ops nginx reload

# --- Accounts (password is NEVER an argument or log line) ---
# 1. write the password once to this 0600 file, then run account-add.
#    The helper consumes and unlinks the file.
install -m 0600 /dev/null /opt/rea/ops/stage/gowifi-auth/new-password
# put the password in that file with an editor; do not echo it
/opt/rea/ops/bin/rea-ops account-add <username> admin    # or: client
/opt/rea/ops/bin/rea-ops account-list                    # usernames/roles only
/opt/rea/ops/bin/rea-ops account-revoke <username>
```

Same verbs work as `sudo -n /usr/local/sbin/rea-ops-helper …`.

## Auth behaviour (server-side)

- Service: `gowifi-auth` (user `gowifi-auth`, loopback `:8810`)
- Public API: `https://gowifi.co.za/auth/` (`/health` `/csrf` `/login` `/logout` `/whoami`)
- Internal verify: `location = /auth/verify` (nginx `internal`, for a later `auth_request`)
- State: `/var/lib/gowifi-auth/` (hashes + session hashes only)
- Secrets: `/etc/gowifi-auth.env` (root:gowifi-auth 640; Rea cannot read)
- Cookie: `gowifi_session` Secure HttpOnly SameSite=Lax Path=/ Max-Age 180 days
- No inactivity logout. Browser restart stays signed in.
- Logout and `account-revoke` delete server session hashes.
- CSRF: GET `/auth/csrf`, then POST `/auth/login` or `/auth/logout` with `X-CSRF-Token`
- Brute-force: 8 failures / 15 min per IP+user; 30 / 15 min per IP
- Roles: `admin` and `client`. Do not expose accounts.json to clients.

`/dash/` still uses existing Basic auth until the new login is proven. Do not
remove `auth_basic` yet. When it is proven, swap **this dashboard only** to
`auth_request` against `/auth/verify`. `/login/` stays public.

## Acceptance (checked on bootstrap)

- Unauthenticated `/dash/` HTML/API/data remains 401 (Basic auth still on)
- `/login/` is public 200
- Root homepage Login is upper-left and opens the same-page popup (`<dialog>`)
- `gowifi-auth` health 200 on loopback and `/auth/health`
- Login issues a session cookie; `/auth/whoami` works after a new client
- Logout and revoke reject the old cookie
- Helper can restart **only** `gowifi-auth` among new units; WhatsApp / mail / ssh denied
- htpasswd, `local.conf`, `gowifi.co.za.conf`, `/root/secrets` writes remain denied
- Homepage and auth rollback restore the previous files

## Forbidden (already denied)

- Unrestricted root / `exec-b64` / shell as root
- `/home/user-data/www/.gowifi-dash.htpasswd` and `.gowifi-seo.htpasswd`
- `/var/lib/gowifi-auth`, `/etc/gowifi-auth.env`
- `accounts.json` in the webroot, Dolibarr books JSON
- `/etc/nginx/conf.d/local.conf` (Mail-in-a-Box owns it)
- `/home/user-data/www/gowifi.co.za.conf` (extra include; `/login/` and `/auth/` already added)
- `/root/secrets`, `/root/gowifi-upp`, SSL private keys, SSH keys, `.env`
- WhatsApp auth/session, sailingsa-api Gold replace
- Restart of healthy WhatsApp / mail / ssh

Do not move admin htpasswd onto `/login/`. Do not print passwords, session
tokens, or `/etc/gowifi-auth.env` in chat, command arguments, or logs.

## Existing protection preserved

- `rea` sudoers remain `REA_STATUS` / `REA_JOURNAL` / `REA_CTRL` only
- Helper ForceCommand still rejects unknown verbs and secret paths
- MIAB `local.conf` is not patched
- Live files are copied to `/opt/rea/ops/backups/` before replace
- Only `gowifi-auth` was added to helper control; other units unchanged

Billing deploy / rebuild / read-only QB fetch is a separate runbook:
`aerialnet/deploy/GOWIFI_BILLING_DEPLOY.md`.
