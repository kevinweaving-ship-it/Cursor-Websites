# Arial / Olarm — saved digest

Source: [OlarmTech/olarmflowclient-python](https://github.com/OlarmTech/olarmflowclient-python) (PyPI `olarmflowclient` **2.0.1**, Apache-2.0).  
Dev URL on this server: **`/arial`** (later **`https://arial.co.za`** on the same box).

**Do not commit API tokens.** Set `OLARM_API_TOKEN` in a gitignored `.env` (or the live process environment). Tokens are minted at [login.olarm.com](https://login.olarm.com) → API section.

## What Olarm is

Olarm turns existing alarm panels (Paradox, DSC, Texecom, IDS, Honeywell, …) into app-controlled devices. Official Python client is **async** (`aiohttp` + `aiomqtt`).

## HTTP API

| Item | Value |
|------|--------|
| Base | `https://api.olarm.com` |
| Auth | `Authorization: Bearer <token>` |
| Devices list | `GET /api/v4/devices?page=1&pageLength=100&deviceApiAccessOnly=1` |
| One device | `GET /api/v4/devices/{deviceId}?deviceApiAccessOnly=1` |
| Events | `GET /api/v4/devices/{deviceId}/events?limit=&after=` |
| Past actions | `GET /api/v4/devices/{deviceId}/actions` |
| Command | `POST /api/v4/devices/{deviceId}/actions` body `{"actionCmd":"…","actionNum":N}` |
| Prolink command | `POST /api/v4/prolinks/{prolinkId}/actions` same body |

List response top-level: `userId`, `page`, `pageLength`, `pageCount`, `search`, `data[]`.  
`userId` is required later for MQTT (`{userId}-{suffix}` client id).

### Errors (client maps these)

| HTTP | Meaning / exception |
|------|---------------------|
| 401 / `tokenExpired` | Token expired |
| 403 | Unauthorized / `insufficientScope` |
| 404 | Device(s) not found |
| 429 | Rate limited (`Retry-After`) |
| 500 | Server error |
| 502/503/504 | Gateway / unavailable |

Bearer required. Missing token looks like `anon-notoken-…` in `reqId`.

## Commands (`actionCmd`)

| Method | actionCmd | actionNum |
|--------|-----------|-----------|
| Disarm area | `area-disarm` | area 1… |
| Arm area | `area-arm` | area |
| Stay | `area-stay` | area |
| Sleep | `area-sleep` | area |
| Partial arm | `area-part-arm-{part}` | area |
| Custom arm (ONE HUB) | `area-custom-arm-{part}` | area |
| Bypass / unbypass | `zone-bypass` / `zone-unbypass` | zone |
| PGM open/close/pulse | `pgm-open` / `pgm-close` / `pgm-pulse` | pgm |
| Utility key | `ukey-activate` | ukey |
| LINK IO | `link-io-open` / `close` / `pulse` | output + prolink id |
| LINK relay | `link-relay-latch` / `unlatch` / `pulse` | relay + prolink id |
| MAX IO | `max-io-open` / `close` / `pulse` | output |
| Panic | `user-panic` | 0 |

`deviceAlarmTypeActions` on the device says which of these the panel actually supports.

## MQTT (live events)

| Item | Value |
|------|--------|
| Host | `mqtt-pubapi.olarm.com` |
| Port | `443` websockets path `/mqtt` |
| Username | `public-api-user-v1` |
| Password | same access token |
| Topic | `v4/devices/{deviceId}` |

Payload patches may include `deviceState`, `deviceFence`, `deviceLinks`, `deviceIO`, `deviceEvents` (e.g. `eventAction: zone_alarm`). Dev page **polls HTTP**; MQTT is a later step.

## Zone types (`deviceProfile.zonesTypes`)

| Code | Meaning |
|------|---------|
| 0 | N/A |
| 10 | Door |
| 11 | Window |
| 20 | Indoor motion |
| 21 | Outdoor motion |
| 50 | Panic button |
| 51 | Panic zone |
| 90 | Not in use |

## Zone state letters (`deviceState.zones[]`)

Observed / used in the Dev UI:

| Letter | Meaning |
|--------|---------|
| `c` | Closed |
| `a` | Active (open / motion) |
| `b` | Bypassed |
| `al` | Alarm (if present) |

Area strings in `deviceState.areas[]`: `disarm`, `arm`, `stay`, `sleep`, `notready`, plus alarm variants.

## Live account snapshot (sanitized)

Fetched with the operator token against `GET /api/v4/devices` (not stored in git).

- **userId:** `34a72607-53ba-4534-bcd6-c2501fce9681`
- **deviceId:** `d6f25654-5fe8-4a85-a7ba-f8ff1449144a`
- **Name:** Home - Voelklip
- **Type:** `OLARMPRO` / panel `paradox`
- **Serial:** `P2EFHV9K`
- **Status:** `online` (when last polled)
- **Timezone:** `Africa/Harare`
- **Firmware:** `212.152`
- **Areas (2):** Main House, Garage
- **Supported area actions:** `area-disarm`, `area-arm`, `area-stay`, `area-sleep`
- **Zones (labels in use):** Garage PIR, Main Bedroom PIR, Office Stairs PIR, Lounge Stairs PIR, Front Door Mag (type door=10); first four are indoor PIR (20)
- **Power:** `powerAC` / `powerBattery` (`ok` when last polled)
- **Events:** `eventAction` `zone` / `zone_watch`, `eventState` `active`/`closed`/`alert`, `eventNum` = zone index, `eventMsg`, `eventTime` epoch **ms**

## Python client (if we vendor later)

```python
from olarmflowclient import OlarmFlowClient
async with OlarmFlowClient(token) as client:
    devices = await client.get_devices()
    device = await client.get_device(device_id)
    await client.send_device_area_arm(device_id, 1)
    await client.start_mqtt_async(user_id, client_id_suffix="1")
    client.subscribe_to_device(device_id, callback)
```

Arial Dev talks to Olarm over HTTPS from `arial_api.py` so we do not need the package installed on the SailingSA API host.

## Arial users (this app)

Separate from SailingSA `user_accounts`. Stored in `data/arial_users.json` (gitignored). Each person has email/password + a profile (name, phone, notes). Dashboard is shared Olarm devices for now; later bind devices per profile.

## Point `arial.co.za` at this server (later)

See `sailingsa/deploy/ARIAL_DOMAIN.md`. Do not mix that host into the sailingsa.co.za nginx `server_name`.
