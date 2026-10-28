# GoWifi billing reconciliation — REA deploy path

Host: box.gowifi.co.za. User `rea` has **no general root**. Privileged work
goes through `/usr/local/sbin/rea-ops-helper`.

Rea can deploy billing source, rebuild published dash JSON, roll back, and
run a **read-only** QuickBooks fetch. This does **not** write to QuickBooks,
FNB, or Dolibarr.

## Trees

| Path | Who | What |
|---|---|---|
| `/opt/rea/ops/stage/gowifi-billing/` | rea write | staged `.py` modules |
| `/opt/gowifi-billing/` | helper publish | project-owned non-secret source |
| `/root/gowifi-upp/` | helper publish (allowlisted `.py` only) | live generator used by cron |
| `/home/user-data/www/default/dash/accounts.json` | helper rebuild | published Clients / Accounts / Invoices |
| `/root/gowifi-upp/upp.db` | root only | ledger (Rea cannot read/write) |
| `/root/secrets`, QB tokens | root only | denied |

Allowed module names: `statements.py qb_api.py qb_import.py books.py clients.py billing.py audit_export.py recon.py invoice_list.py ledger.py`

## Exact commands

```bash
# Stage a module, then publish it to the project tree and the live generator
# write /opt/rea/ops/stage/gowifi-billing/statements.py
/opt/rea/ops/bin/rea-ops deploy gowifi-billing

# Rebuild published accounts.json (lock, backup, atomic replace)
/opt/rea/ops/bin/rea-ops rebuild gowifi-billing

# Read-only QuickBooks delta (GET). Never writes to QB.
/opt/rea/ops/bin/rea-ops qb-fetch

# Rollback source or published JSON (id from the deploy/rebuild JSON)
/opt/rea/ops/bin/rea-ops rollback <backup_id>
```

Same verbs work as `sudo -n /usr/local/sbin/rea-ops-helper …`.

## What the rebuild does

One reconciled result drives Clients, Accounts, Invoices, ageing, and
statements. October invoices stay open only when no later payment covers
them. A 5 Oct Netcash batch cannot clear a 17 Oct invoice. EFT payments
already on FNB / QB (for example 19 Oct) clear those invoices once.

Bank allocations (`fnb-alloc`, `netcash-alloc`) are kept across ingest.
QuickBooks Payment `Id` is attached to an existing bank row when one
matches; D/O apply rows are never inserted. Only a post-baseline EFT
with no bank twin is stored once.

Wessels and Paltco stay off the service-client cards (cancellation / offset).
Do not sum those cards against the 25-customer QB ledger.

## Forbidden

- Writing invoices or payments **to** QuickBooks
- Manufacturing receipts from date / amount / name
- Duplicate payment rows (QB `Id` is the identity)
- `/root/gowifi-upp` and `/root/secrets` reads/writes
- htpasswd, `local.conf`, WhatsApp, mail, ssh

## Automatic QB updates

Each `audit_export` / 15-minute UPP sync calls `refresh_delta` after
statement ingest (GET only). Status: `/var/lib/gowifi-billing/qb-sync.json`
(`last_success`, `error`, `writes_to_qb: false`). `books.quickbooks` on
the published JSON is that status object, not `skip`.
