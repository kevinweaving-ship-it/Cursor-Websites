# WhatsApp alerts — unattended, **free only**

**Constraint:** community / box services — **no paid WhatsApp** (no Cloud API billing, no BSP, no Twilio, no chat SaaS). Stay on the existing Baileys PoCs on the VPS.

## Problem

Baileys is a **linked companion device**. It is free, but:

- another client with the **same** companion creds causes `connectionReplaced` (440) and breaks delivery (“Waiting for this message…”, grey ticks);
- wiping `state/auth` forces phone pairing — unacceptable for an unattended gas phone.

Official Meta Cloud API is **out of scope** here (paid / Billing Hub).

## Live policy (Arial + SailingSA PoCs)

On the HostAfrica box (`/opt/arial-whatsapp-poc`, `/opt/sailingsa-whatsapp-poc`):

| Event | Policy |
|---|---|
| `401 loggedOut` | **Hold** `REAUTH_REQUIRED`, **keep** `state/auth` — never auto-wipe / auto-pair |
| `440 connectionReplaced` | **Hold** `DEGRADED`, retry at most every **30 minutes** — do not fight |
| New socket | Close previous socket before `connect()` |
| Node | **22.23.4** via systemd drop-ins (security) |

**Never** delete `state/auth` or force pairing unless someone is at the phone **and** explicitly asks.

## Free unattended design (what we keep)

```
monitor / site_watch / alert_watcher
        → existing localhost POST /send (Baileys)
        → few admin recipients
```

No new vendors. No Graph API tokens. No monthly WhatsApp invoice.

### Rules that keep it free and stable

1. **One companion only** for the Arial ops number — no WhatsApp Web, no second Baileys, no copied `auth` on a Mac/laptop.  
2. Gas phone stays powered / on WhatsApp as the **primary**; server is the only linked device.  
3. When health is `DEGRADED` + `connectionReplaced`: find the other client (phone → Linked devices); do **not** wipe server auth.  
4. Optional **free** non-WhatsApp backup for “WA down” only (e.g. email via existing Postfix on the box, or a local log + dashboard flag) — still no paid SMS/WA.  
5. Keep cooldowns / dedupe in monitors so the free session is not hammered.

### Honesty limit

Free WhatsApp **outbound** without Meta’s paid API means Baileys (or similar unofficial linked-device). Meta can still invalidate a companion; recovery then needs a one-time phone action. The harden above makes that rare and stops the server from making it worse.

## Until the conflict client is gone

1. Do not restart PoCs unless needed; do not delete `state/auth`.  
2. Health: `GET http://127.0.0.1:8009/health` (Arial), `:8012` (SailingSA) with Bearer token.  
3. `DEGRADED` = another linked client still owns the session — remove it on the phone when next possible; server will retry on the 30‑minute timer.  
4. `arial-site-watch` / `arial-whatsapp-watcher` stay off until WA is stably `UP` (avoid sending into a broken session).

## Related live paths

| Path | Role |
|---|---|
| `/opt/arial-whatsapp-poc` | Arial alerts + server-monitor WhatsApp send (`:8009`) |
| `/opt/sailingsa-whatsapp-poc` | SailingSA event box (`:8012`) |
| `/usr/local/sbin/sailingsa-server-monitor` | Disk/API health → Arial `/send` |
| `/opt/arial-whatsapp-poc/site_watch.py` | Olarm/Tuya heartbeats (service currently disabled) |
| `/opt/arial-whatsapp-poc/alert_watcher.py` | Arm/disarm alerts (service currently disabled) |
