# WhatsApp alerts — unattended operation

## Problem

Baileys (linked companion device) **requires a phone once** to pair, and can require the phone again if:

- another client uses the **same** companion credentials (`connectionReplaced` / 440), or
- WhatsApp invalidates the companion (`loggedOut` / 401).

Fighting reconnects or auto-wiping `state/auth` makes delivery worse (“Waiting for this message…”, single grey ticks) and is unsafe for a gas / remote phone that nobody is holding.

## Current live policy (Arial + SailingSA PoCs)

On the HostAfrica box (`/opt/arial-whatsapp-poc`, `/opt/sailingsa-whatsapp-poc`):

| Event | Old behaviour (bad for unattended) | New behaviour |
|---|---|---|
| `401 loggedOut` | Rename/wipe `auth`, force QR/pairing loop | **Hold** `REAUTH_REQUIRED`, **keep creds**, no auto re-pair |
| `440 connectionReplaced` | Reconnect every few seconds (fight) | **Hold** `DEGRADED`, retry at most every **30 minutes** |
| New socket | Could overlap previous socket | Close previous socket before `connect()` |

Node security patch remains: both services run **Node 22.23.4** via systemd drop-ins.

**Never** wipe `state/auth` or force pairing unless an operator is at the phone and explicitly asks.

## Why Baileys cannot be “phone-free forever”

It is a **linked device**. Meta can invalidate it; a second copy of the same session will kick the server every ~minute. That is a product limit, not a systemd bug.

## Better system: WhatsApp Cloud API (recommended)

Official **WhatsApp Business Platform / Cloud API** (Meta) — **paid is OK**; goal is **low and predictable** cost for community / box services, not “free at all costs”.

- Server sends with a **permanent access token** + phone number ID  
- **No Baileys**, no linked-device fight, no QR on the gas phone for routine sends  
- Phone is only needed for **one-time** Business / number setup (or number migration)  
- Fits unattended monitoring (disk, Olarm, Tuya, etc.)

### Keep costs down (community boxes)

| Do | Don’t |
|---|---|
| Talk to **Meta Cloud API directly** from the VPS (no BSP / Twillio / chat SaaS markup) | Pay a reseller per message on top of Meta |
| Prefer **utility** templates for alerts (Olarm down, disk, Tuya) | Marketing templates for ops alerts |
| **One** Business number for Arial/ops alerts; reuse existing `/send` callers | Extra WABA numbers “just in case” |
| Dedupe / cooldown in `site_watch` / monitor (already the pattern) | Page every admin on every flap |
| Use the **1 000 free service messages / number / month** when someone has messaged in | Blast free-form outside the 24h window |
| Keep SailingSA **group archive** on Baileys only if still needed; don’t Cloud-API that traffic | Move high-volume chat into Cloud without a need |

Rough order of magnitude for SA recipients: utility/service is on the order of **cents per delivered message** after free tiers; a quiet monitoring number (tens–low hundreds of alerts/month) stays cheap. Confirm live rates in [Meta WhatsApp pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing) when provisioning Billing Hub (card on file so sends don’t stop after the free tier).

### Target shape on this box

```
monitor / site_watch / alert_watcher
        → small local Python sender (no new SaaS)
        → Graph API (Cloud API)
        → few admin recipients
```

Thin adapter behind the existing `POST /send` shape so cron/watchers barely change. **No** paid middleware.

### What to provision (operator, once)

1. Meta Business Manager + WhatsApp Business account (community / org billing)  
2. Cloud API app: **Phone number ID**, **WABA ID**, **permanent token**  
3. Secrets only in e.g. `/etc/sailingsa-whatsapp-cloud.env` (`0600`), not in git  
4. One ops alert number first (Arial/server-monitor). Add a second number only if SailingSA outbound must be separate  
5. Approve a small set of **utility** templates (disk warning, Olarm offline/online, Tuya fail)

### Send path (sketch)

`POST https://graph.facebook.com/v21.0/{phone-number-id}/messages`  
Bearer token; **utility template** for cold alerts; free-form only inside an open customer-care window.

### Cutover (controlled)

1. Cloud sender beside Baileys; flag `USE_CLOUD_API=1` on Arial/ops only  
2. Prove disk + Olarm paths; leave Baileys for inbound archive if still required  
3. Turn off Baileys **send** for ops once Cloud is solid — saves fight risk, not “save Meta fees”  
4. Skip BSP migration tools unless Meta forces number move

## Until Cloud API is live

1. **One** companion only for `076…` / Arial — no WhatsApp Web / second Baileys with copied `auth`  
2. Do not restart PoCs unless needed; do not delete `state/auth`  
3. Health: `GET http://127.0.0.1:8009/health` (Arial), `:8012` (SailingSA) with Bearer token  
4. `DEGRADED` + `connectionReplaced` means another client still owns the session — find and remove that client when someone is next at a phone; do **not** wipe auth from the server  

## Related live paths

| Path | Role |
|---|---|
| `/opt/arial-whatsapp-poc` | Arial alerts + server-monitor WhatsApp send (`:8009`) |
| `/opt/sailingsa-whatsapp-poc` | SailingSA event box (`:8012`) |
| `/usr/local/sbin/sailingsa-server-monitor` | Disk/API health → Arial `/send` |
| `/opt/arial-whatsapp-poc/site_watch.py` | Olarm/Tuya heartbeats (service currently disabled) |
| `/opt/arial-whatsapp-poc/alert_watcher.py` | Arm/disarm alerts (service currently disabled) |
