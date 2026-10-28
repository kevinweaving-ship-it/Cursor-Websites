# Aerialnet keypad (Hansekop + Voëlklip)

Alarm / Olarm / Tuya / keypad WhatsApp live on the GoWifi / Aerialnet box only.

| Old Sailing URL | Now |
|---|---|
| https://sailingsa.co.za/arial/ | 302 → https://aerialnet.co.za/hansekop/ |
| https://sailingsa.co.za/voelklip/ | 302 → https://aerialnet.co.za/voelklip/ |
| https://sailingsa.co.za/stanford/ | 410 (not moved) |
| https://sailingsa.co.za/bing/ | 410 (not moved) |

Sailing WhatsApp is **SailingSA + Tim Advisor only** (`sailingsa-whatsapp-poc` + event ingest). Alarm number and keypad APIs are masked on Sailing.

Hansekop Olarm + Tuya run on the GoWifi box (`:8003`, `tuya-sharing` `:8007`). Keypad nginx lives in Mail-in-a-Box’s extra file `/home/user-data/www/aerialnet.co.za.conf` (same pattern as `gowifi.co.za.conf`). Mail owns `local.conf` and may rewrite it; it **includes** the extra file, so keypad APIs survive a mail rebuild. Do not patch `local.conf`. Alarm WhatsApp (Baileys) is a **linked device** on the same business number as the phone (accept the box once on the phone). Sends return as soon as WhatsApp accepts them; they do not wait for “delivered” before the next recipient. Poll is 2s. The keypad WhatsApp tab reads `/var/www/aerialnet/data/whatsapp_log.jsonl` (wapoc must be able to write that file).

Voëlklip home cams may still stream from Sailing (`sailingsa.co.za:8443` / `:8444`) until hikpoc is copied.

The Aerialnet landing header has **User Login**, which opens the Hansekop keypad (`/hansekop/`).

## Deploy

From a host that can SSH to `box.gowifi.co.za` (`102.209.119.186`):

```bash
GOWIFI_SSH_KEY=~/.ssh/your_key bash aerialnet/deploy/deploy-to-gowifi-box.sh
```

On the box, tokens live in `/etc/aerialnet-olarm.env` and `/etc/aerialnet-tuya.env` (copied from Sailing when reachable; never commit them).

GoWifi **homepage**, **client login**, **admin /dash**, and **gowifi-auth** publish for REA: `aerialnet/deploy/GOWIFI_WEB_DEPLOY.md` (live copy `/opt/rea/ops/GOWIFI_WEB_DEPLOY.md`). Verbs: `rea-ops deploy gowifi-home`, `gowifi-web`, `gowifi-auth`.

GoWifi **billing reconciliation** (Clients / Accounts / Invoices, read-only QuickBooks delta): `aerialnet/deploy/GOWIFI_BILLING_DEPLOY.md` (live copy `/opt/rea/ops/GOWIFI_BILLING_DEPLOY.md`). Verbs: `rea-ops deploy gowifi-billing`, `rebuild gowifi-billing`, `qb-fetch`, `rollback <backup_id>`. Does not write to QuickBooks.
