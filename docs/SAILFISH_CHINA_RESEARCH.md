# Sailfish Sports (旗鱼体育) — China platform research

**Status:** scrape / learn-for-later (read-only reconnaissance)  
**Date:** 2026-08-31  
**Root:** https://www.saill.cn/  
**Docs:** https://www.saill.cn/docs/ (VitePress v1.6.4, ZH + EN)

This is **not** SailingSA production code. It captures how the Chinese Sailfish stack is structured (hardware, protocols, backends, product surfaces) for future comparison / integration thinking.

---

## 1. What they are

深圳旗鱼体育传播有限公司 — sailing media + tracking company (est. ~2012/2016). Positioning: water-sports broadcast, inshore/offshore tracking, event ops, training.

**Contact (public docs):**  
- Email: info@saill.cn  
- Tel: +86 (0532) 8563 1190  
- Qingdao + Shenzhen offices  

**ICP:** 粤ICP备18008383号 · Host: Aliyun Qingdao (`47.105.51.191`) · DNS: `ns1/ns2.alidns.com`

---

## 2. Site map (crawl inventory)

### 2.1 Marketing SPA — `sf-front-view`

- Vue SPA shell at `/` (JS required).
- Element UI 2.13, Leaflet, Fancybox, Owl/Swiper.
- Baidu analytics: `hm.js?70f2f50753bd8169ad59e383460ce0c5`
- AES util: `/util/aes.js`
- Client API base: **`/sf-front-api`**

**Vue routes (sample):** `/`, `/home`, `/index`, `/index-en`, `/about`, `/events`, `/events/detail/:eventCd`, `/events/level/:eventCd/:levelCd`, `/news`, `/videos`, `/path_tracking`, `/race_live`, `/product-tracer`, `/product-winds`, `/product-tracking`, `/product-tracking3D`, `/product-training`, `/product-eots`, `/product-yb`, `/product-cloud-album`, `/automatic-buoy`, `/service-*`, `/contact`, FAQ/blog variants (`*-en`).

**Public front API (verified live POST):**

| Endpoint | Notes |
|---|---|
| `POST /sf-front-api/api/event/list` | Paginated events (`eventCd`, dates, address, logo…) — ~87 pages |
| `POST /sf-front-api/api/banner/list` | Banners under `sf-front-api/sfupload/banner/…` |
| `POST /sf-front-api/api/partnerList` | Partners |
| `POST /sf-front-api/api/news/list` | News HTML content |
| `POST /sf-front-api/api/videoList` | Videos |
| `/sf-front-api/api/event/info|img|video|level/…` | Event detail variants (from JS) |
| `/sf-front-api/api/level/race|score/…` | Level race/score |
| `/sf-front-api/api/news/info/…` | News detail |
| `/sf-front-api/api/dataConfigInfo` | Exists; GET → 405 |

Uploads / logos served as `https://www.saill.cn/file/image/…` and `sf-front-api/sfupload/…`.

### 2.2 Technical docs — `/docs` (primary intel)

VitePress site, **45 pages** in `hashmap.json` (ZH + EN mirrors).

| Section | URL | Role |
|---|---|---|
| Home | `/docs/` | Product matrix |
| Devices | `/docs/device/` | Hardware hub |
| **SF-Tracer** | `/docs/device/tracker/1-tracker.html` | Little orange box |
| User manual | `/docs/device/tracker/2-user-manual.html` | Power/SOS/LEDs |
| SIM swap | `/docs/device/tracker/3-sim-card-replacement.html` | SIM |
| Windwatcher | `/docs/device/wind/1-wind.html` | Wind instrument |
| **WebSocket push** | `/docs/device/data/websocket.html` | Live client interface |
| **Comms protocol** | `/docs/device/data/communication-protocol.html` | Device↔server framing |
| Match / race admin | `/docs/match/race/` | Event management ops |
| **SF-Traj** | `/docs/match/web/` | Live tracking UI (QIYU TRAJ) |
| Match APP | `/docs/match/app/` | Mobile app guide |
| QR / public view | match qrcode docs | Spectator H5 |
| Training | `/docs/train/track/` | Training system |
| Training H5 | `train_h5_v1` | Group training H5 |
| 3D panorama | `/docs/3d/` | 3D broadcast client |
| Sailing rules portal help | `/docs/sailingrule/*` | Protest / score / retire flows |

English mirrors under `/docs/en/…`.

### 2.3 Other product UIs on same host

| Path | Title / stack | Notes |
|---|---|---|
| `/sf-admin/login` | 旗鱼管理系统 | Race + device admin (login required) |
| `/sf-training/login` | Training admin | Documented in train docs |
| `/sailingrule-ui/` | 赛事信息平台系统 | RuoYi-Vue-Plus fork (`sailfish.sailingrule-Vue-Plus`) |
| `/sailingrule-api/` | Backend welcome banner | API base for rules platform |
| `/sailingrule-h5/` | `sr-ui` | Mobile H5 |
| `/sailingrule-web/` | Public web | `?matchId=` |
| `/sailingrule-web-pay/pay` | Payments | Linked from UI JS |
| `/sf-cloud-h5/` | Cloud H5 | Linked from admin |
| `/s/raceApp` | Race app entry | Linked from admin |
| `/cdn/qyh/nb|wf/file_*.html` | Event-specific HTML | nb/wf variants |

**Dead / blocked from this crawl:** `robots.txt` 404, `sitemap.xml` 404, `base.saill.cn:9505` connection refused (legacy asset host still referenced in SPA), `doc./api./live.` subdomains NX/timeout. `https://new.saill.cn/` redirects to www.

---

## 3. Hardware

### 3.1 SF-Tracer「小橙盒」 (inshore tracker)

| Spec | Value |
|---|---|
| Size / weight | 80×40×26 mm · 110 g |
| Battery | 3500 mAh · ~24 h (rate-dependent) |
| Ingress | IP-65 |
| Temp / humidity | −40–80 °C · 5–95% |
| GNSS | GPS + BeiDou (+ Galileo claimed) · ~2.5 m · dual-GPS correction |
| Sample rate | up to **4 Hz**; interval 1 s–arbitrary |
| Network | GSM quad-band 850/900/1800/1900; **microwave** variant available |
| Sensors | gyro, accelerometer, vibration motor |
| Storage | offline store + resume upload |
| LEDs | GPS blue · POWER red · SIGNAL orange |

**Ops:** short-press SOS = power on; long-press 3 s = power off; triple-press SOS = SOS; remote power via admin (disabled after manual power-off). Commands also in protocol (below).

### 3.2 SF-Windwatcher 风力仪

Portable wind / direction / swell sensor for venue met. Works with Tracer.

| Spec | Value |
|---|---|
| Size / weight | 1150×52×140 mm · 1.75 kg |
| Wind | 0–60 m/s · 0–359° |
| GPS | ~2 m · 4 Hz |
| Runtime | ~20 h |
| Materials | polycarbonate shell · carbon mast |

### 3.3 Other hardware / third-party (marketing)

- **Automatic buoy** — RTK, cm-level  
- **YB Tracking** — Iridium offshore  
- **EOTS 天空之眼** — Inmarsat + YB, compressed media/comms for ocean races  
- GoPro integration appears in admin (`/device/gopro/*`)

---

## 4. Device communications protocol (v1.0)

Source: `/docs/device/data/communication-protocol.html`  
Prefer **English** page for MESSAGE TYPE codes (ZH page has copy-paste errors saying type `1` for position/wind).

### 4.1 Uplink frame (device → server / consumer)

```
$$|ACK|VERSION|MESSAGE TYPE|DEVICE ID|MESSAGES NUMBER|MESSAGE 1|…|MESSAGE N|**
```

| MESSAGE TYPE | Meaning |
|---|---|
| 0 | Server / CMD |
| 1 | Heartbeat |
| 2 | Position |
| 3 | Wind |

**Heartbeat:** `BATTERY|STATUS`  
**Position:** `SAMPLE TIME|LONGITUDE|LATITUDE|ALTITUDE|SPEED|HEADING|BATTERY|STATUS|SOS`  
**Wind:** `SAMPLE TIME|LON|LAT|ALT|SPEED|HEADING|VOLTAGE|TWD|TWS`  

Units: lat/lon decimal degrees; speed m/s; heading 0–360° (N=0, CW); SOS 0/1; STATUS `2` = charging.

Example position:

```
$$|1|1|2|2463|1|1772009017000|120.371522|36.1087272|41.0|0.01|339.0|100||2|**
```

### 4.2 Downlink commands (server → device)

```
$$|COMMAND|DEVICE ID|##
```

Device IDs comma-separated.

| CMD | Action |
|---|---|
| 33 | Restart |
| 35 | Remote power off |
| 36 | Remote power on (not after manual off) |
| 90 | Clear SOS |

Example: `$$|36|2248,2249|##`

---

## 5. WebSocket live-data interface

Source: `/docs/device/data/websocket.html`

- Auth: query `token` (issued by Sailfish — contact required)  
- URL pattern (placeholder): `ws://domain?token=…`  
- Payload: **same framing as device protocol**  
- Keepalive: client sends `'\x0A'` (LF) every **10 seconds**

Admin-side separate Netty WS:

- Device online WS URL from API: `GET …/device/all/getNettyWebsocketUrl`  
- Infra test socket UI defaults to: `ws(s)://…/sf-admin/api/websocket/message?userId=`

---

## 6. Backend / system architecture (inferred)

```
SF-Tracer / Windwatcher / buoy / YB
        │  GSM / microwave / satellite
        ▼
 Device ingest + command channel (Netty WebSocket; pipe protocol $$|…|**)
        │
        ├─► IoTDB (time-series GPS / wind)  ← admin APIs *FromIotDb / saveToIotDB
        │
        ├─► Race / match domain (sf-admin, /sf-admin/api/admin-api/)
        │       match / race / searoute / teams / wind instruments / work ships
        │
        ├─► SF-Traj web map (live + replay)  ← “旗鱼轨迹 / QIYU TRAJ”
        │
        ├─► Training system (/sf-training)
        │
        ├─► Marketing CMS (/sf-front-api)
        │
        └─► Sailing-rules platform (RuoYi-Vue-Plus: /sailingrule-api + ui/h5/web)
```

### 6.1 Admin API surface (unauthenticated paths mined from SPA)

Base: **`/sf-admin/api/admin-api/`** (auth required in practice).

**Device domain highlights:**

- `/device/all/*` — inventory, online status, detail, heading/avg-time mods, **`getNettyWebsocketUrl`**
- `/device/device/*` — tags, share, naming
- `/device/device-command/sendCommand` — remote CMD path
- `/device/device-gps-data/*` + `findLastPositionFromIotDb`, `getLastValueFromIotDb`
- `/device/device-wind-data/*` + `calculateTrueWind`, `saveToIotDB`
- `/device/device-sim/*` — SIM lifecycle / expiry stats
- `/device/device-virtual/*` — virtual devices
- `/device/device-shipping/*`, `/device/device-life/*` — logistics / lifecycle
- `/device/traffic-log/*` — cellular plans / flow
- `/device/gopro/*`, transform-company leasing APIs

**Match / race domain highlights:**

- `/match/match/*`, `/match/match-level/*`, `/match/match-level-team/*`, `/match/match-device-pool/*`
- `/match/race/*` — create/start/ready/finish/replay/view-config/rank lock…
- `/match/race-searoute/*`, `/match/race-team/*`, `/match/race-wind-instrument/*`, `/match/race-work-ship/*`
- `/match/race-report/*`, `/match/race-trac-ext/*` (trajectory extensions / scores)
- `/match/race-simulate/sendGPS` — GPS simulation for tests
- National sync: `matchDataToNationalServer`, sync statistics

**Admin UI modules (webpack views):** tag/wind/buoy lists, buoy-control, race-control, mobile-control, device GPS/wind/air data, SIM, virtual devices, GoPro, traffic logs, ocean chat/logbook, race kernel / traj browsing logs.

### 6.2 SF-Traj (旗鱼轨迹 / “QIYU TRAJ”)

Documented as **SF-Traj** (system rename noted in marketing JS). Web map product:

- Leaflet-class UX: info panel, live rank board, timeline, wind compass, eagle-eye, measure tools  
- Metrics: COG, SOG, Ave/Max SOG, VMG, VMC, DTL, DTF, DTS, RTS, sail no., leg analysis  
- Layers: vector/satellite/weather viz, chart, day/night, grid, marks, work boats, wind instruments  
- Modes: **LIVE** vs **REPLAY**; shareable public race links from admin  

### 6.2b Install / spectators / training / “profiles”

Full write-up: **`docs/sailfish-china-extracts/INSTALL_SPECTATOR_TRAINING_UX.md`**.

- **Install:** SOS short=on / long 3s=off / triple=SOS; remote power via admin (disabled after manual off); SIM swap with 4 screws; serial on unit, QR on back.  
- **Race equipment bind:** event device pool → import teams as Sail No. + Team Name + Device No. → assign mark/wind devices → share traj link → formal replay.  
- **Spectators:** QR event viewer (Ready/Racing/Replay + Track/Pro); SF-Traj web; 赛事零距离 mini program.  
- **“Sailor profile”:** thin — race team row + training H5 My (avatar/nickname, bound/followed teams, personal history). No SailingSA-style public career page.  
- **Training:** `/sf-training` daily tracks (auto end midnight); H5 scan device QR to join (Manager/Coach/Team); demo `demo1`/`123456` in docs.  
- **Equipment substitution** in sailingrule = sails/mast/hull paperwork, not GPS binding.

### 6.3 Sailing rules / event info platform

- Fork of **RuoYi-Vue-Plus** (`https://gitee.com/dromara/RuoYi-Vue-Plus`)  
- API prefix `/sailingrule-api`  
- Features from docs: protest, score inquiry, retirement, equipment replacement, beginner guide  
- Also references `xxl-job-admin` (scheduled jobs)

### 6.4 3D panorama client

Windows desktop-class viewer (docs: Win10, i5, 16 GB, GTX 1060). Consumes traj data for 1:1 3D broadcast (terrain tiers, sea modes, wind, marks, boats).

---

## 7. Relevance to SailingSA (notes only)

| Sailfish | SailingSA analogue / gap |
|---|---|
| Hardware GPS boxes + protocol | No first-party tracker hardware today |
| SF-Traj live map + replay | Different product surface; worth studying UX metrics (VMG/VMC/DTL…) |
| Race admin (start/recall/finish + device pool) | Stronger ops-time race control loop |
| IoTDB time-series | Potential model for high-rate track storage |
| Dual public CMS API vs ops admin API | Clean split marketing vs race kernel |
| Sailing-rules protest/score portal | Separate product line |

**Do not** treat scraped admin API paths as free-to-call; they need auth tokens. Public protocol docs + marketing APIs are the durable references.

---

## 8. Key URLs (bookmark)

- https://www.saill.cn/  
- https://www.saill.cn/docs/  
- https://www.saill.cn/docs/device/tracker/1-tracker.html  
- https://www.saill.cn/docs/device/data/websocket.html  
- https://www.saill.cn/docs/en/device/data/communication-protocol.html  
- https://www.saill.cn/docs/match/web/  
- https://www.saill.cn/docs/match/race/  
- https://www.saill.cn/docs/train/track/  
- https://www.saill.cn/sf-admin/login  
- https://www.saill.cn/sf-training/login  
- https://www.saill.cn/sailingrule-ui/  

---

## 9. Crawl method / limits

- Fetched root SPA bundles + full VitePress `hashmap.json` (45 pages) + SSR HTML for tech sections.  
- Mined `/sf-admin` webpack chunks for REST paths (no authenticated session).  
- Hit live `/sf-front-api` list endpoints.  
- Did **not** obtain production WebSocket host/token, Netty WS URL, or IoTDB credentials (gated).  
- Some ZH protocol docs have incorrect MESSAGE TYPE numbers; use EN.

## 11. open_trac live/replay tracking (tracking-dev)

Primary public tracker page reverse-engineered for SailingSA tracking-dev reuse:

- URL pattern: `/sf-admin/html/race/live/open_trac.html?raceCd={uuid}`
- Stack: **SF_TrajX** (`appX.min.js`) + riot + protobuf + echarts + xgplayer
- Boot: `getRace?pageName=open_trac` → status `99` forces `replay2/` else `live2/` + `getEncryption`
- Leaderboard metrics: COG, SOG, VMG, VMC, DTL/DTF/DTS, RTS, ranking
- WS topics: `/RX/RACE_CONTROL_*`, `/RX/SAIL_DATA_P_*`, `/RX/BUOY_DATA_*`
- Full notes: **`docs/sailfish-china-extracts/OPEN_TRAC_TRACKING_DEV.md`**
- Sample artifacts: `docs/sailfish-china-extracts/open_trac/`

**Next scrape steps (when useful):** authenticate demo tenant if Sailfish provides one; capture live `getNettyWebsocketUrl` host; record one LIVE race share URL end-to-end; map SF-Traj tile/API calls in browser DevTools; re-fetch CN113588153A full claims when Google Patents is available; confirm soft著 via CN copyright certificate numbers if Sailfish shares them.

---

## 10. Patents & software (follow-up dig)

Full dossier: **`docs/sailfish-china-extracts/PATENTS_AND_SOFTWARE.md`** (+ `patent_dossier.json`).

### Patents (assignee 深圳旗鱼体育传播有限公司)

**Count reconciliation** (see `PATENT_COUNT_RECONCILIATION.md`): **8 families / 12 CN pubs**. “10+ patents” = counting every A/B/U publication. Company site itself only advertises **2 invention patents + 23 soft copyrights**.

| Family | Topic | Status |
|---|---|---|
| CN110738023A/B | JSON weather → JPEG | Granted (ZL201910989617.3) — software method |
| CN110750962A/B | GRIB → JSON weather | Granted (ZL201910975113.6) — software method |
| CN113033968A/B | Race performance scores (sail/start/tack) | Granted — software method |
| CN114690225A/B | Mark-rounding detection | Granted — software method |
| CN113588153A | Marine true-wind / Windwatcher | Application only |
| CN220137400U / CN220874872U / CN220874741U | GPS tracker, protective shell, signal base | Utility models granted |

Soft著: **23 claimed** on saill.cn; certificate titles not public. No patents under 王祥胜 / 海上轻骑.

### Software surfaces (beyond §2)

- **赛事零距离** WeChat mini program (mobile SF-Traj)  
- **Sailfish-App** `/sf-cloud-h5/` — uni-app race ops client (`__UNI__BB85F3F`): devices (Tracer/wind/auto-buoy), GoPro, match control, check-in, start/course/全召; talks to `/sf-admin/api/admin-api/`  
- `/sf-training`, `/s/raceApp`  
- 云相册, 3D panorama desktop, EOTS/YB companion apps  
- Sailing-rules stack = RuoYi-Vue-Plus fork  

**HNTE:** GR202444208141 (Shenzhen 2024 batch). Soft著 titles still not public (23 claimed). See `DIG_CONTINUATION.md`.
