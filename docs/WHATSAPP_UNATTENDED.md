# WhatsApp alerts — unattended, **free only**

**Constraint:** community / box services — **no paid WhatsApp** (no Cloud API billing, no BSP, no Twilio, no chat SaaS). Stay on the existing Baileys PoCs.

## Problem

Baileys is a **linked companion device**. It is free, but:

- another client with the **same** companion creds causes `connectionReplaced` (440) and breaks delivery (“Waiting for this message…”, grey ticks);
- wiping `state/auth` forces phone pairing — unacceptable for an unattended gas phone.

Official Meta Cloud API is **out of scope** here (paid / Billing Hub).

## Where alarm stack runs

**Canonical host for Hansekop + Voëlklip (HOME):** gowifi / aerial — `box.gowifi.co.za` / `aerialnet.co.za` (`102.209.119.186`).

| Function | Aerial (gowifi) | Sailingsa live |
|---|---|---|
| Olarm keypad APIs | `aerialnet-hansekop-api` `:8003`, `aerialnet-voelklip-api` `:8004` | **disabled** (`arial-api`, `arial-voelklip`) |
| Tuya meter / lights | `tuya-sharing`, `tuya-home-api` | **disabled** |
| WhatsApp (GoWifi `27762639937`) | `arial-whatsapp-poc` + watcher + site-watch | **disabled** (must stay off) |
| Cameras live + ring + clips | `hikpoc-go2rtc`, `hikpoc-ring`, `hikpoc-warm` under `/opt/hikpoc` | **disabled** |
| UI + data store | `/home/user-data/www/aerialnet.co.za/`, `/var/www/aerialnet/data/` (keypad logs, weather sqlite, windguru, energy) | `/voelklip/` redirects → aerialnet |
| SailingSA event WhatsApp | — | `sailingsa-whatsapp-poc` (separate number) |
| Stanford / Bing Olarm | not yet migrated | `arial-stanford`, `arial-bing` still here |

### Public Voëlklip URLs (aerialnet only)

| Purpose | URL |
|---|---|
| Keypad / HOME | `https://aerialnet.co.za/voelklip/` |
| Clip Replay / LIVE | `https://aerialnet.co.za/voelklip/clip/` |
| snaps / warm / clip API | `https://aerialnet.co.za/voelklip/hik/…` → local `:8444` |
| Live go2rtc | `https://aerialnet.co.za/voelklip/cam/…` → local `:8443` |

`sites.json` on gowifi: `voelklip.clip_page` / `voelklip.snaps` must be those aerialnet URLs.

## Live policy (Baileys PoCs)

| Event | Policy |
|---|---|
| `401 loggedOut` | **Hold** `REAUTH_REQUIRED`, **keep** `state/auth` — never auto-wipe / auto-pair |
| `440 connectionReplaced` | **Hold** `DEGRADED`, retry at most every **30 minutes** — do not fight; stop the other box |
| New socket | Close previous socket before `connect()` |
| Node | Current LTS via systemd drop-ins (security) |

**Never** delete `state/auth` or force pairing unless someone is at the phone **and** explicitly asks.

## Free unattended design

```
monitor / site_watch / alert_watcher
        → existing localhost POST /send (Baileys on gowifi)
        → few admin recipients
```

### Rules

1. **One companion only** for GoWifi/Arial — runs on **gowifi only**.
2. Gas phone stays powered as the primary; server is the only linked device.
3. On `connectionReplaced`: find the other client; do **not** wipe server auth.
4. Keep cooldowns / dedupe so the free session is not hammered.

## Ops checks

1. GoWifi WA health: `/opt/arial-whatsapp-poc/state/health.json` → `state: UP`.
2. Cameras: `systemctl is-active hikpoc-go2rtc hikpoc-ring hikpoc-warm`; `curl -sk https://aerialnet.co.za/voelklip/hik/snaps.json` after `/warm`.
3. Keep sailingsa `arial-whatsapp-*`, `hikpoc-*`, `arial-voelklip`, `arial-api`, Hansekop `tuya-*` **disabled**.
