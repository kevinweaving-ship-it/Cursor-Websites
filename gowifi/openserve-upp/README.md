# GoWiFi Openserve UPP mirror

Read-only copy of the GOWIFI (org 955) Openserve UPP profile, orders, and
services. Runs on `box.gowifi.co.za`. Does not place orders or change services.

## Mail

- Openserve UPP `emailAddress` / `bundleTransactionEmail`: `accounts@gowifi.co.za`
- Openserve UPP user (was obsolete `kevin@go-wifi.co.za`): `kevin@gowifi.co.za`
- Lead / support / sales stay on `kevinweaving@icloud.com`
- `accounts@gowifi.co.za` is an alias (Kevin + Openserve). Both inboxes get a copy:
  - `kevin@gowifi.co.za`
  - `openserve@gowifi.co.za`
- Refresh the UPP token and rewrite those emails if Openserve ever puts `@go-wifi.co.za` back:

```bash
python3 /root/gowifi-upp/upp_emails.py
```
- First-login password change for `kevin@gowifi.co.za` (Openserve requires upper, lower, number, and a symbol). Secrets stay in `/root/secrets/openserve-upp.env`:

```bash
OPENSERVE_UPP_TEMP_PASS='…' OPENSERVE_UPP_NEW_PASS='…' python3 /root/gowifi-upp/upp_set_password.py
```
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

## Clients (simple)

Every GoWiFi URL is **white background, dark-blue text**. No dark/navy page chrome.

Live https://gowifi.co.za only updates after the files are on the box.
`clients.html` 404s and the old dash stays dark blue until this runs:

```bash
# from a host that can SSH to the box (102.209.119.186)
bash gowifi/openserve-upp/deploy-to-box.sh
```

Or on the box itself, after this tree is in `/root/gowifi-upp`:

```bash
bash /root/gowifi-upp/install-on-box.sh
python3 /root/gowifi-upp/audit_export.py
```

**https://gowifi.co.za/dash/clients.html** — simple cards + search.

One card per client, with a search bar: name, address, contact, start date, year/month,
B number if fibre, package, balance / due (7-day grace). Status LED: green active,
red Openserve issue, orange if we suspend. VK Pop incoming fibre is not a client.
Auto-suspend, WhatsApp and reply notes come later (copied to admin).
Addresses, phones and emails come from the QuickBooks `Customers.xls` list.

**https://gowifi.co.za/dash/invoices.html** — all QuickBooks invoices (1 Jan 2020–5 Oct 2026).
Repeating mid-month amounts are monthly line rental. Odd amounts (install /
equipment / fees) are listed as queries so Kevin can send the full invoice PDF.
Do not invent line items. Do not put once-offs on the monthly D/O.

The detailed fibre audit stays at **https://gowifi.co.za/dash/accounts.html**.

## Audit page

Compact fibre list at **https://gowifi.co.za/dash/accounts.html** (same dash login).

- Per line: order → install → activate → (suspend/restore stints) → cancel is complete
- A new house is a new order/install, not a continuation of a cancelled line
- Cancel stories are inferred from orders only: address-error redo (never
  installed, next order is the install), later move (was a live client, then a
  new house), or cease (cancelled, no new order — end of account)
- Never use a previous-ISP / previous-owner circuit date
- Active accounts: client, service number, exclusive line status, speed, join date, months as client
- GoWiFi incoming fibre at **VK Pop** (legal UPP name Kevin Weaving) is **not a
  client**. All info lives on the POP card only — do not duplicate these on the
  Active / Suspended / Cancelled client lists. `B110033875` primary Webstream
  500/250, `B110034814` failover Office Connect 300/150. They are the backhaul
  **cost of wireless**: WiFi client income has to cover them. Same two lines
  also appear on the UISP home / VK Pop site as incoming fibre.
- Cancelled lines (own history) then cancelled orders
- Suspended lines at the bottom: how long, how many stints, own history

```bash
python3 /root/gowifi-upp/audit_export.py
```

`sync.py` refreshes `/dash/accounts.json` after each pull.

## Books (no QuickBooks)

GoWiFi books are three feeds, not a full ledger package:

1. **We invoice / statement** active fibre lines (series continues after QuickBooks 3039)
2. **Netcash** debit-order API (`NIWS_NIF`) — collections and unpaids. Read-only pull via `python3 /root/gowifi-upp/netcash.py pull`. Keys in `/root/secrets/netcash.env` (`NETCASH_USERNAME`, `NETCASH_SERVICE_KEY`). Does not upload debit batches.
3. **FNB** — Own FNB Online login only. GoWiFi is **not** an Online Banking Enterprise user, so Integration Channel (`POST RetrieveRealtimeStatement`) is no use. The box logs in as GoWiFi for `62860060278`, skips Devices when that page shows, opens My bank accounts, reads Available, then Statements. Card on `/dash/clients.html` shows fetch steps next to Bank. New rows allocate who paid. Leftovers sit on Issues. Not QuickBooks.
4. **Openserve invoices** already on the box — fibre cost to match against FNB debits

### Packages (April 2026)

`packages.py` stores the **current Openserve wholesale + GoWiFi retail table**.
GoWiFi is **not VAT registered**: cost = letter × 1.15 (VAT we pay); retail
has no VAT. Live retail on 25/50/100; other speeds including 1000 Mbps use the
50/25 markup then round up to R99. Rows live in SQLite `openserve_wholesale`.

**Each March/April:** watch for the next Openserve increase and WhatsApp a
mailshot to clients before 1 April.

Monthly D/O is the line only. Phillipus May and Phillip De Gruchy are on a
discount. Wireless and EFT clients sit on the same 17th cycle.

QuickBooks / Xero are not required for this. An accountant can take a CSV export at year end.

Old QuickBooks invoice and statement PDFs in `kevin@` / `accounts@` mail are
imported as history. Every statement line already has the invoice number,
what it was for, and the amount — those rows are recreated as full invoices
(bill-to, address, qty/rate, terms). Same-client known packages fill monthly
lines that only say `Invoice No.N`. Click `Invoice No.N` on the statement
to open that invoice. New invoices are one A4 page at `/dash/invoice.html`:
company and client cards, this month’s invoice card, then a statement card
from the last paid-up zero through the current bill and amount due. Date /
Description / Amount / Balance, ageing, closing. The document is an Invoice, not
a Tax Invoice (no VAT number on the old PDFs). FNB `62860060278`. Cancel
QuickBooks once that history is on the box.

Openserve invoice CSVs from `kevin@` / `openserve@` mail (INATS* zip) are
imported into `invoices` / `invoice_lines` for payment reconcile, grouped
per Openserve billing account and per fibre line. Bank proof-of-payment
uploads come later. Extra
charges such as Dynamic IPv4 and ONT bridge show on the line with the date
they were added. Cancelled orders that never reached Accepted are **never
installed** — `dateImplemented` on a cancel is not an install date.
