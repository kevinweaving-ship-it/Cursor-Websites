# UniFi UDM Pro — own dash, then share

UDM Pro has **its own dash**. Landing (`https://gowifi.co.za/`) and any other
public URL only show what is **selected on that dash**. Nothing is public by
default. Do not invent status. Do not scrape `unifi.ui.com`. Do not mix this
with UISP radios.

Official docs (as at 7 Oct 2026):

- https://help.ui.com/hc/en-us/articles/30076656117655-Getting-Started-with-the-Official-UniFi-API
- https://developer.ui.com/llms.txt
- Site Manager: https://developer.ui.com/site-manager-api/
- Network (local, versioned): https://developer.ui.com/network
- Protect (cameras, only if that app is installed): https://developer.ui.com/protect

## What is live today (proved on the box)

| Surface | What it is | UniFi? |
|---|---|---|
| `https://gowifi.co.za/` | Coming-soon poster + Facebook hit-area. File `/home/user-data/www/default/index.html` dated 22 Sep. | No |
| `https://gowifi.co.za/dash/` | Admin (htpasswd). Network health / Active outages / sectors. | **UISP radios**, not UniFi |
| `/dash/api/sites` + `/dash/api/devices` | nginx → `https://gowifi.uisp.com/nms/api/v2.1/{sites,devices}` | UISP NMS |
| `/root/secrets/` | FNB, Netcash, QBO, Openserve, UPP | **No UniFi key** |
| systemd | `gowifi-fnb-api`, `gowifi-qb-oauth` | No UniFi service |

The box (`102.209.119.186`) is a VPS. It is **not** on the UDM LAN, so
`https://192.168.1.1/proxy/network/...` is not reachable from here unless we
add a LAN collector or use Ubiquiti’s cloud connector.

## Two Ubiquiti products (do not conflate)

**UISP** = WISP radios / sites / CPEs. Already on `/dash/`. Token stays in
`/root/gowifi-dash-uisp-proxy.conf` (server-side only). That is last-mile
wireless.

**UniFi Dream Machine Pro** = UniFi OS console. Gateway + Network app
(switches, APs, VLANs, WAN, clients). Optional apps on the same box: Protect,
Access, Talk, InnerSpace. This is the LAN / premises controller — not the
UISP radio NMS.

A device that is “online” on UISP is not a UniFi client. A UniFi WAN that is
up is not a UISP sector. Landing share lists are chosen per dash.

## Official API layers

All official calls use header `X-API-KEY` (Ubiquiti also accepts `X-API-Key`).
Keys are created once and shown once.

### 1) Site Manager (cloud) — what the VPS can reach

Base: `https://api.ui.com`

Create key: sign in at `unifi.ui.com` → **Settings → API Keys**.

| Method | Path | For the UDM dash |
|---|---|---|
| GET | `/v1/hosts` | Consoles (the UDM Pro is a host) |
| GET | `/v1/hosts/{id}` | That console’s reported state |
| GET | `/v1/sites` | Network sites on those hosts |
| GET | `/v1/devices` | UniFi devices across hosts |
| GET | `/v1/isp-metrics/{5m\|1h}` | WAN / ISP health (5m ≥24h, 1h ≥30d) |
| POST | `/v1/isp-metrics/{type}/query` | Same, filtered |
| GET | `/v1/sd-wan-configs` + `/{id}` + `/{id}/status` | Only if SD-WAN is in use |

Rate limit on v1: 10,000 req/min. `429` + `Retry-After`. Key is **read-only**
at GA; write is rolling out and needs a new key if enabled later.

### 2) Cloud Connector — cloud key, local Network/Protect

Needs console firmware **≥ 5.0.3**. 100 req/min per console. 25s timeout.
10 MB response cap.

```
https://api.ui.com/v1/connector/consoles/{hostId}/proxy/network/integration/v1/...
https://api.ui.com/v1/connector/consoles/{hostId}/proxy/protect/integration/v1/...
```

This is how the box talks to the UDM as if it were on LAN, without opening
443 on the UDM to the internet.

### 3) Local Network Integration API (on the UDM)

Needs UniFi Network **≥ 9.3**. Docs for *this* firmware: UniFi Network →
**Settings → Control Plane → Integrations** (also the local key mint).

On UDM / UDM Pro / UDM SE the path is behind UniFi OS:

```
https://<udm>/proxy/network/integration/v1/...
```

Header `X-API-KEY`. Self-signed cert is normal; verify pin later, do not
ship `verify=false` as policy.

Read endpoints that belong on the **UDM dash** (full picture, still private):

| GET | Returns |
|---|---|
| `/v1/info` | Network app version |
| `/v1/sites` | Sites (`id`, `internalReference`, `name`) |
| `/v1/sites/{siteId}/devices` | Adopted devices: `id`, `mac`, `model`, `name`, `state`, `type` |
| `/v1/sites/{siteId}/devices/{id}` | One device |
| `/v1/sites/{siteId}/devices/{id}/statistics/latest` | Live stats |
| `/v1/sites/{siteId}/clients` | Connected clients (wired / wireless / VPN / Teleport) |
| `/v1/sites/{siteId}/clients/{id}` | One client |
| `/v1/sites/{siteId}/wans` | WAN interfaces |
| `/v1/sites/{siteId}/networks` | LAN / VLAN |
| `/v1/sites/{siteId}/wifi/broadcasts` | SSIDs |
| `/v1/sites/{siteId}/vpn/servers` + `.../site-to-site-tunnels` | VPN |
| `/v1/pending-devices` | Waiting adoption |

Write endpoints exist (adopt, restart, block client, create SSID, firewall).
**Never** expose those on landing or any public URL. Dash may use them later
only if asked.

Official Network list: https://developer.ui.com/network/v10.6.106/llms.txt
(current published Network version when this was written).

### 4) Local cookie login (legacy, unofficial)

Only if the Network app is older than the Integration API.

```
POST https://<udm>/api/auth/login     {"username","password","remember":true}
GET  https://<udm>/proxy/network/api/s/{site}/stat/health
GET  https://<udm>/proxy/network/api/s/{site}/stat/sta
GET  https://<udm>/proxy/network/api/s/{site}/stat/device
POST https://<udm>/api/auth/logout
```

Cookie + `X-CSRF-Token`. Works, but it is a session, not an app key. Prefer
the official key. Same rule as FNB: do not keep extra logins hanging.

### 5) Protect (optional)

Only if Protect is installed on this UDM. Local prefix
`/proxy/protect/integration/v1/`. Cameras, snapshots, sensors. A snapshot is
**not** public unless selected on the UDM dash.

## How this maps to “own dash, then share”

Same shape as UISP on `/dash/` and FNB on the box: **server holds the secret,
dash is htpasswd, public URLs read a share file**.

```
unifi.ui.com API key  (or local key via Connector)
        │
        ▼
box  /root/secrets/unifi.env          ← not in git
        │
        ▼
UDM dash  /dash/unifi.html            ← htpasswd, full truth
        │
        │  Kevin ticks what to share
        ▼
share table / JSON                    ← allow-list only
        │
        ├── https://gowifi.co.za/          landing
        └── other public URLs
```

Rules:

1. UDM dash shows **table truth from UniFi**. Offline is offline. Online is
   online. Leftover scores / stale “degraded” do not invent an outage
   (same lesson as UISP `outageScore` on green-dot radios).
2. Landing and other URLs read **only the share allow-list**. Empty share =
   nothing from UniFi on that URL.
3. Browser never sees `X-API-KEY`. nginx or a small box service injects it,
   same as `/root/gowifi-dash-uisp-proxy.conf` does for UISP.
4. Do not write UniFi numbers onto the coming-soon poster until a share row
   exists.

### Share rows (when we build it)

One row per thing Kevin ticks. Suggested columns — not created yet:

- `kind` — `wan` / `device` / `ssid` / `client_count` / `isp` / `protect_cam`
- `unifi_id` — host / site / device / interface id from the API
- `label` — public name (may differ from UniFi name)
- `fields` — allow-list: e.g. `state`, `uptime`, `count` — never a raw dump
- `urls` — `landing` and/or other public paths
- `enabled` — on/off

Public JSON is a projection of those rows. No MAC, no client IP, no hostname
of a home device, no camera still, unless that field is ticked.

### Safe vs never (until ticked)

**Usually safe to offer on the dash as a share candidate**

- WAN up / down (from `/v1/sites/{id}/wans` + ISP metrics)
- UDM / AP / switch `state` (from devices list)
- Count of APs online vs adopted
- Aggregate client count (not the client list)
- ISP latency / uptime from `/v1/isp-metrics/5m`

**Stay on the UDM dash unless explicitly shared**

- Client list (name, MAC, IP, hostname)
- SSIDs that are staff / IoT
- VPN users
- Firewall / VLAN layout
- Protect snapshots / live views
- Pending adoption
- Firmware versions, WAN public IP

**Never on a public URL**

- API key, cookies, CSRF
- Restart / block / adopt / voucher create
- Full device dump

## Probe (do not run until a key is in `/root/secrets/unifi.env`)

```bash
# key from unifi.ui.com → Settings → API Keys
set -a; . /root/secrets/unifi.env; set +a   # UNIFI_API_KEY=...
curl -sS -H "X-API-KEY: $UNIFI_API_KEY" -H "Accept: application/json" \
  https://api.ui.com/v1/hosts
```

`401` = bad/missing key. `200` + hosts = we can build the dash from real
data. Then Connector:

```bash
curl -sS -H "X-API-KEY: $UNIFI_API_KEY" -H "Accept: application/json" \
  "https://api.ui.com/v1/connector/consoles/${HOST_ID}/proxy/network/integration/v1/sites"
```

No key on the box today, so there is **no live UniFi status to publish**.

## Build order (do not skip)

1. Kevin pastes a Site Manager API key into `/root/secrets/unifi.env` (mode 600).
2. Probe `/v1/hosts` — prove the UDM Pro is on that UI account.
3. Build **UDM dash** (`/dash/unifi.html`) — hosts, sites, devices, WAN,
   client counts. Same white / dark-blue dash language as the rest of `/dash/`.
4. Share picker on that dash. Write share JSON.
5. Landing / other URLs read share JSON only.

Do not start the landing UniFi widgets before step 4. Do not cron until asked.
Do not change UISP `/dash/api/sites|devices`.
