# Mailbox — investigation@sailingsa.co.za

**Purpose:** outbound address for French / Greek / Polish record requests. Drafts: [`REQUESTS.md`](REQUESTS.md).

## Access path (do not invent a block)

Per **`docs/CURSOR_RESULTS_BACKFILL_CURRENT.md`**, **`sailingsa/deploy/SSH_LIVE.md`**, **`docs/REA_CHATGPT_ACCESS.md`**, **`gowifi/rea/ops/README.md`**:

- Both boxes are reachable through **REA on GoWifi** (`/opt/rea/ops/bin/rea-admin …`, `ops_*`, `capture_process_scenario`) and through **`~/.ssh/sailingsa_live_key` on the Mac Mini**.
- Do **not** diagnose access from a Cloud Linux pod alone. Missing tools in one Cursor runtime ≠ absent server access.
- Mail for the estate lives on **GoWifi Mail-in-a-Box**: `box.gowifi.co.za` (`102.209.119.186`). Web admin: https://box.gowifi.co.za/admin
- REA ops config allow-reads include `/home/user-data/www` on GoWifi. Mail-in-a-Box **mail data** remains a deliberate deny for unrestricted dump (`docs/REA_CHATGPT_ACCESS.md`); creating a user is a normal MiaB admin / root mail action, not a dump of mailboxes.

## DNS fact (checked 21 Nov 2026)

| Record | `sailingsa.co.za` |
| --- | --- |
| A | `102.218.215.253` (SailingSA web) |
| MX | **none** right now |
| NS | GoDaddy `ns77` / `ns78.domaincontrol.com` |
| GoWifi mail MX | `gowifi.co.za` → `10 box.gowifi.co.za.` |

Until MX points at `box.gowifi.co.za`, new `@sailingsa.co.za` users on MiaB will not receive external mail reliably.

## Create the user (Mac or REA-capable session)

```bash
# 1) Confirm Mac / REA session has the key
ls -la ~/.ssh/sailingsa_live_key

# 2) Reach GoWifi (documented host)
ssh -i ~/.ssh/sailingsa_live_key root@102.209.119.186 'hostname; which mailinabox >/dev/null; ls /home/user-data/mail/mailboxes 2>/dev/null | head'

# 3) Add domain if missing, then user (MiaB management API — admin login from Mac secrets, never commit)
curl -sS -u "$MIAB_ADMIN:$MIAB_PASS" \
  https://box.gowifi.co.za/admin/mail/domains
curl -sS -u "$MIAB_ADMIN:$MIAB_PASS" \
  -d 'email=investigation@sailingsa.co.za&password='"$NEW_PASS" \
  https://box.gowifi.co.za/admin/mail/users/add

# Or UI: https://box.gowifi.co.za/admin → Mail → Users → Add investigation@sailingsa.co.za
```

Then GoDaddy DNS for `sailingsa.co.za` (copy exact lines from MiaB DNS checklist):

| Type | Name | Value |
| --- | --- | --- |
| MX | `@` | `box.gowifi.co.za` priority **10** |
| TXT SPF / DKIM / DMARC | as MiaB prints | — |

```bash
dig +short MX sailingsa.co.za
# expect: 10 box.gowifi.co.za.
```

Webmail: https://box.gowifi.co.za/mail — user `investigation@sailingsa.co.za`.

## Status this Cloud Agent run (tool binding only)

This chat is a **Cloud Linux** agent. Observed here:

- REA MCP tools (`capture_process_scenario`, `ops_*`) are **not bound** in the tool list
- `CreateAgent` / `Task` `self_hosted_worker` placement is **not available** (Task only accepts `same_machine` | `new_cloud_vm`)
- Mac Mini worker **`43e56b9a-b958-55dd-a151-df216da22615`** is **connected, approved, idle**
- Pod has **no** `~/.ssh/sailingsa_live_key`

That is a **runtime binding gap**. It is **not** “SSH is blocked” and not “boxes have no email.” Fix: open/continue this task on the **Mac Mini worker**, or bind the **REA** connector so `rea-admin` / MiaB admin can run.

After create: send letters in [`REQUESTS.md`](REQUESTS.md); update this file’s status line to **mailbox live**.
