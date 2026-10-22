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

Official **WhatsApp Business Platform / Cloud API** (Meta):

- Server sends with a **permanent access token** + phone number ID
- **No Baileys**, no linked-device fight, no QR on the gas phone for routine sends
- Phone is only needed for **one-time** Business / number setup (or number migration)
- Fits unattended monitoring (disk, Olarm, Tuya, etc.)

### Target shape on this box

```
monitor / site_watch / alert_watcher
        → small local sender (Python)
        → Graph API messages endpoint
        → recipients (Kevin, …)
```

Keep the existing `POST /send` control shape if useful: implement a thin adapter that speaks Cloud API underneath so cron and watchers need minimal changes.

### What to provision (operator, once)

1. Meta Business Manager + WhatsApp Business account  
2. Cloud API app: **Phone number ID**, **WhatsApp Business Account ID**, **permanent token**  
3. Store secrets only in something like `/etc/sailingsa-whatsapp-cloud.env` (mode `0600`), not in git  
4. Register / migrate the alert numbers you care about (Arial monitoring vs SailingSA event box can be separate WABAs or the same)

### Send path (sketch)

`POST https://graph.facebook.com/v21.0/{phone-number-id}/messages`  
with Bearer token; template messages for outside the 24h session window, plain text inside it.

### Cutover (controlled)

1. Implement Cloud sender beside Baileys; feature-flag per channel (`USE_CLOUD_API=1`)  
2. Dual-run: Cloud for new alerts, Baileys read-only or off  
3. Disable `arial-whatsapp-poc` / Baileys send once Cloud is proven  
4. Leave Baileys only if you still need inbound group archive (or replace that later)

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
