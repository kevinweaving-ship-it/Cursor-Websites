# WhatsApp alerts — unattended, **free only**

**Constraint:** community / box services — **no paid WhatsApp** (no Cloud API billing, no BSP, no Twilio, no chat SaaS). Stay on the existing Baileys PoCs.

## Problem

Baileys is a **linked companion device**. It is free, but:

- another client with the **same** companion creds causes `connectionReplaced` (440) and breaks delivery (“Waiting for this message…”, grey ticks);
- wiping `state/auth` forces phone pairing — unacceptable for an unattended gas phone.

Official Meta Cloud API is **out of scope** here (paid / Billing Hub).

## Where it runs (split by number)

| Number / role | Box | Path | Notes |
|---|---|---|---|
| **GoWifi / Arial ops** (`27762639937`) | **gowifi / aerial** `box.gowifi.co.za` (`102.209.119.186`) | `/opt/arial-whatsapp-poc` | **Only** place this companion may run. Services: `arial-whatsapp-poc`, `arial-whatsapp-watcher`, `arial-site-watch`. |
| **SailingSA events** | HostAfrica live `102.218.215.253` | `/opt/sailingsa-whatsapp-poc` | Separate number; keep on sailingsa. |

On HostAfrica, **`arial-whatsapp-poc` / watcher / site-watch stay disabled** so they cannot steal the GoWifi session (`connectionReplaced`).

## Voëlklip alarm video (Replay / LIVE)

Public URLs are on **aerialnet** (gowifi nginx), not `sailingsa.co.za`:

| Purpose | URL |
|---|---|
| Keypad / HOME | `https://aerialnet.co.za/voelklip/` |
| Clip Replay / LIVE page | `https://aerialnet.co.za/voelklip/clip/` |
| snaps / warm / clip API | `https://aerialnet.co.za/voelklip/hik/…` → proxies sailingsa hikpoc `:8444` |
| Live go2rtc | `https://aerialnet.co.za/voelklip/cam/…` → proxies sailingsa go2rtc `:8443` |

`sites.json` on the gowifi box (`voelklip.clip_page` / `voelklip.snaps`) must use the aerialnet URLs above so WhatsApp arming messages link correctly.

Old `https://sailingsa.co.za/voelklip/…` UI paths redirect to aerialnet when nginx redirects are installed on live.

## Live policy (Baileys PoCs)

| Event | Policy |
|---|---|
| `401 loggedOut` | **Hold** `REAUTH_REQUIRED`, **keep** `state/auth` — never auto-wipe / auto-pair |
| `440 connectionReplaced` | **Hold** `DEGRADED`, retry at most every **30 minutes** — do not fight; stop the other box |
| New socket | Close previous socket before `connect()` |
| Node | Current LTS via systemd drop-ins (security) |

**Never** delete `state/auth` or force pairing unless someone is at the phone **and** explicitly asks.

## Free unattended design (what we keep)

```
monitor / site_watch / alert_watcher
        → existing localhost POST /send (Baileys)
        → few admin recipients
```

No new vendors. No Graph API tokens. No monthly WhatsApp invoice.

### Rules that keep it free and stable

1. **One companion only** for the Arial/GoWifi ops number — runs on **gowifi only**. No WhatsApp Web, no second Baileys on sailingsa, no copied `auth` on a Mac/laptop.
2. Gas phone stays powered / on WhatsApp as the **primary**; server is the only linked device.
3. When health is `DEGRADED` + `connectionReplaced`: find the other client (phone → Linked devices, or a second VPS service); do **not** wipe server auth.
4. Optional **free** non-WhatsApp backup for “WA down” only (e.g. email via existing Postfix on the box, or a local log + dashboard flag) — still no paid SMS/WA.
5. Keep cooldowns / dedupe in monitors so the free session is not hammered.

### Honesty limit

Free WhatsApp **outbound** without Meta’s paid API means Baileys (or similar unofficial linked-device). Meta can still invalidate a companion; recovery then needs a one-time phone action. The harden above makes that rare and stops the server from making it worse.

## Ops checks

1. Do not restart PoCs unless needed; do not delete `state/auth`.
2. GoWifi Arial health: on gowifi, `GET http://127.0.0.1:8009/health` (or local health.json under `/opt/arial-whatsapp-poc/state/`).
3. SailingSA health: on live, `:8012` with Bearer token.
4. `DEGRADED` = another linked client still owns the session — remove it; server retries on the timer.
5. Keep sailingsa `arial-whatsapp-*` **disabled**; enable watcher/site-watch only on gowifi when WA is `UP`.

## Related paths

| Path | Role |
|---|---|
| gowifi `/opt/arial-whatsapp-poc` | GoWifi/Arial alerts (`alert_watcher`, `site_watch`, Baileys send) |
| live `/opt/sailingsa-whatsapp-poc` | SailingSA event box only |
| gowifi `/home/user-data/www/aerialnet.co.za/voelklip/` | Keypad + clip UI |
| gowifi `aerialnet.co.za.conf` | `/api/voelklip/`, `/voelklip/hik/`, `/voelklip/cam/` |
| live `/opt/hikpoc` | Camera ring / warm / go2rtc backends (proxied via aerialnet until full migrate) |
