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

Service `lifecycle` / `exclusive_status` is one bucket only: `active`,
`suspended`, `cancelled`, or `unknown`. A line is never both active and
suspended. Access status wins over partner `IspActive` only while GoWiFi
still owns the circuit. Holding pool / `WS TELKOM` / validator "holding
pool" / `circuitAdmin=Disconnected` on an unowned circuit is a **cease**
(cancelled), not a credit suspend — Openserve often leaves
`accessStatus=Suspended` on those. Empty/unowned circuits with a cancelled
order are cancelled. Each service number keeps its own suspend → restore
stint history in `service_events`.

## Audit page

Compact fibre list at **https://gowifi.co.za/dash/accounts.html** (same dash login).

- Per line: order → install → activate → (suspend/restore stints) → cancel is complete
- A new house is a new order/install, not a continuation of a cancelled line
- Cancel stories are inferred from orders only: address-error redo (never
  installed, next order is the install), later move (was a live client, then a
  new house), or cease (cancelled, no new order — end of account)
- Never use a previous-ISP / previous-owner circuit date
- Active accounts: client, service number, exclusive line status, speed, join date, months as client
- GoWiFi incoming fibre at **VK Pop** (legal UPP name Kevin Weaving) is labelled as the
  POP, not a residential client: `B110033875` primary 500, `B110034814` failover 300.
  Same two lines also appear on the UISP home / VK Pop site as incoming fibre.
- Cancelled lines (own history) then cancelled orders
- Suspended lines at the bottom: how long, how many stints, own history

```bash
python3 /root/gowifi-upp/audit_export.py
```

`sync.py` refreshes `/dash/accounts.json` after each pull.

## Books (no QuickBooks)

GoWiFi books are three feeds, not a full ledger package:

1. **We invoice / statement** active fibre lines (series continues after QuickBooks 3039)
2. **Netcash** debit-order API (`NIWS_NIF`) — collections and unpaids
3. **FNB daily CSV** — scheduled “ACCOUNT TRANSACTION HISTORY” to `accounts@go-wifi.co.za`
4. **Openserve invoices** already on the box — fibre cost to match against FNB debits

QuickBooks / Xero are not required for this. An accountant can take a CSV export at year end.

Openserve invoice CSVs from `kevin@` / `openserve@` mail (INATS* zip) are
imported into `invoices` / `invoice_lines` for payment reconcile, grouped
per Openserve billing account and per fibre line. Bank proof-of-payment
uploads come later. Extra
charges such as Dynamic IPv4 and ONT bridge show on the line with the date
they were added. Cancelled orders that never reached Accepted are **never
installed** — `dateImplemented` on a cancel is not an install date.
