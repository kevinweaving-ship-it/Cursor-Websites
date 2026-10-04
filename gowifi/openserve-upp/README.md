# GoWiFi Openserve UPP mirror

Read-only copy of the GOWIFI (org 955) Openserve UPP profile, orders, and
services. Runs on `box.gowifi.co.za`. Does not place orders or change services.

## Mail

- Public accounts address (old dash domain, keep this): `accounts@go-wifi.co.za`
- Openserve UPP `emailAddress` / `bundleTransactionEmail`: `accounts@go-wifi.co.za`
- Both inboxes get a copy of accounts mail:
  - `kevin@gowifi.co.za`
  - `openserve@gowifi.co.za`
- `accounts@gowifi.co.za` is the same alias (Kevin + Openserve).
- Checksum the two copies:

```bash
python3 /root/gowifi-upp/checksum_accounts_mail.py
```

Mailbox passwords stay in `/root/secrets/openserve-mail.env` (mode 600). Do not commit them.

## Database

SQLite at `/root/gowifi-upp/upp.db`.

```bash
# token from a Johannesburg / box-IP login (24h JWT)
install -m 600 /dev/stdin /root/secrets/upp.token
python3 /root/gowifi-upp/sync.py
```

Cron (every 15 minutes) re-pulls orders and service status while the token is valid.

Tables: `organisations`, `organisation_history`, `users`, `orders`, `services`,
`service_status_history`, `products`, `sync_runs`.

Service `lifecycle` values: `active`, `suspended`, `cancelled`, `unauthorized`, `unknown`.

## Audit page

Compact fibre list at **https://gowifi.co.za/dash/accounts.html** (same dash login).

- Active accounts: client, service number, line status, speed, join date, months as client
- Cancellations list under that
- Suspended / held lines at the bottom

```bash
python3 /root/gowifi-upp/audit_export.py
```

`sync.py` refreshes `/dash/accounts.json` after each pull.
