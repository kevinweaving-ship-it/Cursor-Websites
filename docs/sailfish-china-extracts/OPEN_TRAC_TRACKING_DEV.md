# open_trac.html — tracking system reverse-engineering (for SailingSA tracking-dev)

**Target URL:**  
https://www.saill.cn/sf-admin/html/race/live/open_trac.html?raceCd=6010fbd608e54ae4aff7d8363f912077  

**Sample race:** 2026 ILCA 6 Youth Europeans — `ILCA6 BoysEMERALD` / rounds `F5` / status `99` (finished → auto-replay)  
**Captured:** 2026-08-31  
**Artifacts:** `docs/sailfish-china-extracts/open_trac/`

This is the public spectator tracking shell (**SF_TrajX** / SF-Traj “X” generation). Use it as the primary reference for a SailingSA live + replay tracking page.

---

## 1. Script imports and bundle names

From `open_trac.html` `<head>`:

| Asset | Role |
|---|---|
| `cdn/sf-traj/vendor/riot.min.js` | Riot.js UI tags (X shell) |
| `cdn/sf-traj/vendor/long.min.js` | 64-bit ints (protobuf timestamps) |
| `cdn/sf-traj/vendor/protobuf.min.js` | Binary sail/track decode |
| `cdn/sf-traj/vendor/echarts.min.js` | Charts (disabled on open_trac) |
| `cdn/sf-traj/vendor/xgplayer/xgplayer.min.js` (+ mp4/hls) | Optional camera/video |
| **`cdn/sf-traj/app/sailing/appX.min.js?v=20260303`** | **Main SF_TrajX app (~378 KB, obfuscated)** |
| `../../../static/config.js` → `/sf-admin/static/config.js` | `window.g.BaseUrl` |

CSS: `xgplayer.min.css`, `loadingX.min.css`, `fontsX.min.css`, `appX.min.css`.

Global entry after load: **`SF_TrajX({...})`** (also referred to in marketing as SF-Traj / 旗鱼轨迹).

Lang pack URL (base64 in page): `//www.saill.cn/cdn/sf-traj/app/sailing/langX/` (files currently 404 from unauthenticated fetch).

---

## 2. raceCd parsing

Query string parsed in inline IIFE:

| Param | Default | Meaning |
|---|---|---|
| **`raceCd`** | `""` | Race UUID (required) |
| `rounds` | `"1"` | Round hint (title uses server `rounds`) |
| `stomp` | base64 → `ws://localhost:8186/websocket?token=sailfish` | Dev STOMP override (prod replaces via race payload) |
| `replayFlag` | `false` | Force replay; sets path end to `replay2/` |

**Live vs replay switch (server-authoritative):**

```text
GET {BaseUrl}/app-api/match/race/getRace?pageName=open_trac&raceCd={raceCd}
if data.status == '99' → replayFlag=true, urlEnd='replay2/'
else default urlEnd='live2/'
```

Documented status used here: **`99` = race finished → replay**. Live races stay on `live2/`.

---

## 3. Config + API routes

### 3.1 `static/config.js`

```js
window.g = {
  BaseUrl: '/sf-admin/api',
  LoginUrl: '/sf-admin/index',
  SubtitleUrl: 'https://www.saill.cn/sf-cloud-subtitle',
  LeaderBoardUrl: 'https://www.saill.cn',
  storeKey: 'SF_CLOUD-',
}
```

### 3.2 Boot APIs (verified)

| Method | Path | Notes |
|---|---|---|
| GET | `/sf-admin/api/app-api/match/race/getRace?pageName=open_trac&raceCd=` | Race meta + `viewConfig` JSON string |
| GET | `/sf-admin/api/app-api/match/race/getRouteInfo?raceCd=` | Course/marks; this sample returned empty `{}` |
| (client) | `{origin}{BaseUrl}/app-api/match/race/live2/` | Live track base; `method: 'getEncryption'` |
| (client) | `{origin}{BaseUrl}/app-api/match/race/replay2/` | Replay track base; same method |

**Verified encrypted endpoints (2026-08-31 browser capture):**

| Path | Role |
|---|---|
| `{live2\|replay2}/getRaceDatas?&raceCd={uuid}&time={ms}` | Bootstrap (LZ `result` → JSON: `teamList`, marks, `viewConfig`) |
| `{live2\|replay2}/getEncryptionReplayData?raceCd=…&matchCd=…&rounds=…&replayFlag=…&timeSpan=6&asTime=…&timestamp=…&nonCache=…` | Track time-series chunks (~666 KB compressed) |
| Headers on encrypted GETs: `oQ: i8/RH`, `TV: gB` | `method: 'getEncryption'` transport |

Plain curl to `live2/` / `replay2/` **directory root** still returns **404** — use the named endpoints above.

**Payload decode + `runtime[]` index map:** **`WS_PAYLOAD_SCHEMA.md`**

Secondary (tenant-gated): `/app-api/match/searoute/get` → “租户的请求未传递”.

### 3.3 `SF_TrajX` init options (open_trac)

```js
SF_TrajX({
  raceCd,
  url: origin + BaseUrl + '/app-api/match/race/' + (replay ? 'replay2/' : 'live2/'),
  method: 'getEncryption',
  lang: '<base64 langX/>',
  replay: replayFlag,
  club: false,
  layout: false,
  camera: true,
  toolShowAll: true,
  toolMeasuring: true,
  charts: false,
  teamList: true,
  route: origin + BaseUrl + '/app-api/match/race/getRouteInfo?raceCd=' + raceCd,
});
```

---

## 4. WebSocket URL construction

1. **Page default (dev):** base64 `stomp` → `ws://localhost:8186/websocket?token=sailfish`  
2. **Prod override:** race/bootstrap payload supplies STOMP endpoint list; client does `new WebSocket(url)` with `binaryType = "arraybuffer"`.  
3. **Legacy/prod pattern seen elsewhere:** `wss://www.saill.cn/sailfish-ntwss?token=sailfish`  
4. Client logs: `mU Socket Opened...` then subscribes by race.

### Topics (from `appX.min.js`)

| Topic pattern | Purpose |
|---|---|
| `/RX/RACE_CONTROL_{raceCd}` | Race state machine (start / clear / time sync / next race) |
| `/RX/SAIL_DATA_P_{raceCd}` | Per-tick sail/boat telemetry (protobuf) |
| `/RX/SAIL_DATA_BATCH_P_`… | Batched sail updates |
| `/RX/BUOY_DATA_{raceCd}` | Mark/buoy position updates |
| `/RX/BEG{raceCd}` | Additional race/entity stream |

`RACE_CONTROL` handler cases observed (obfuscated `JE` codes):

| Code | Behavior (inferred) |
|---|---|
| `0` | Reset all boats + course graphics |
| `10` | Wind / instrument update (`BAm`); refresh marks |
| `an` (hex) | Time sync / seek (`CC` clock) |
| `99` | Next-race handoff (extract next `CL=` raceCd from message) |

Sail payloads decoded with **protobuf** field map (lat/lon, cog/sog, ranks, distances, battery, etc. — field numbers 1…51 in decoder `Nd`).

---

## 5. Leaderboard fields (COG / SOG / VMG / VMC / DTL)

Column model inside `appX` (i18n keys + `Col*` flags from `viewConfig`):

| UI / Col flag | Meaning | Typical unit |
|---|---|---|
| Rank / `ColRanking` | Race order | — |
| Sail No. | Sail number | — |
| Team / short name | Team label + color | — |
| **COG** | Course over ground | ° |
| **SOG** / Max / Ave (`ColMaxSOG`, `ColAveSOG`) | Speed over ground | **kts** (`sogUnit`) |
| **VMG** / Ave (`ColVMG`, `ColAveVMG`) | Velocity made good (windward) | kts |
| **VMC** / Ave (`ColVMC`, `ColAveVMC`) | Velocity made good on course / to mark | kts |
| **DTL** / `ColDTL`, `ColDTLv` | Distance to leader (or to line — DTLv variant) | m / NM |
| **DTF** / `ColDTF` | Distance to finish | m / NM |
| **DTS** / `ColDTS` | Distance to start / next mark (context) | m / NM |
| **RTS** / `ColRTS` | Remaining time / time-to-sail estimate | s |
| Total Dist / Time Cost | Path length / elapsed | — |
| Status | Racing / finished / DNS/DNF-style | — |
| Power | Tracker battery | % |

This sample race has most `Col*` flags **false** in `viewConfig` (minimal public columns); the column *engine* still supports the full set when enabled by ops.

**Older SF-Traj replay UI** (screenshots `screenshot_01`…`05`, path `/sailfish-admin/view/racereplay/live/{id}/{round}/{n}`) shows Ranking board with: Team Name, R, **COG**, **SOG**, **Ave.SOG**, **Max.SOG** — same product family, older Leaflet shell (“QIYU TRAJ”).

---

## 6. Course / mark geometry

From `getRace`:

- `searouteRole`: **`1-1a-4s/4p-1-2-3p`** — mark sequence (`/` = gate).  
- `searouteCd`: course definition id.  
- `getRouteInfo` → empty for this race (marks may arrive only via WS `BUOY_DATA` or encrypted track bootstrap).

UI layers in appX:

- Start line / finish line (`起航线BO/BP`, `终点线BO/BP`)  
- Guide line, buoy marks, work marks  
- **Laylines** — `layline: true`, angle **44.2°** (`laylineAngle`)  
- **Leader line** — `leaderline: true`  
- Reference / ladder lines, target mark highlight  
- Optional jury boats (`showJury`)

---

## 7. Live vs replay switching

| Signal | Effect |
|---|---|
| Query `replayFlag=true` | Force `replay2/` |
| `getRace.status == '99'` | Force replay |
| Else | `live2/` + live WS |
| `viewConfig.replaySpeed` / `maxPlaySpeed` | Replay UI speed (5 … 500) |
| `trackLength: 90` | Trailing track points |
| `trajMode: 2` | Trajectory render mode |
| `buffer: 5000`, `timeout: 15` | Live buffering / stall |

Replay UI (older shell screenshots): timeline, play/pause, speed, leg markers, green **REPLAY** clock.

---

## 8. Boat-follow / leader-follow

From `viewConfig` + appX strings:

- `camera: true`, `cameraRace: true` — race camera / auto-frame  
- `leaderline: true` — graphic to race leader  
- Toolbar: follow boat (target), auto-camera, show-all  
- `scopeRadius: 24` — follow framing radius  
- Ranking row click / checkbox → highlight + optional center on boat (Ctrl/center patterns in older SF-Traj docs)

---

## 9. Wind data source

- Race field `windInstruments`: UUID `9cf6ceca-…` — bound wind sensor set.  
- `windCog` on race can be null; live wind via instruments + WS.  
- UI: `windCompass: true`; settings `settings_wind_sensor_`, layers `layers_wind_mark`, pens `P-windcog` / `P-windsog`.  
- `weather: false` on this race (no weather tile overlay).  
- Toolbar action `toolbar_update_vmg` recomputes VMG series when wind direction known (`calcVMG` / `windSog` / `windCog` in bundle).

---

## 10. Start / recall / finish state

- `readyTime` / `startTime` / `endTime` on race record (epoch ms).  
- `countdown: 300000` (5 min) in viewConfig — pre-start countdown window.  
- `startingAnalysis: true`, `readyShow: 0`.  
- `RACE_CONTROL` drives start/reset; timeline markers in replay UI for start / marks.  
- Explicit “general recall” string not plain-text in obfuscated bundle; expect it as a `RACE_CONTROL` / status enum on sail records (`ColStatus`).  
- `currentStep` / `stepOverFlag` — course leg progress.

---

## 11. Device ↔ sail / team mapping

- Race bootstrap ideally includes team list + device binding (open_trac enables `teamList: true`).  
- appX fields: `deviceCd`, `sailNo`, `teamShortName`, `teamCd`, model/icon, country flag class.  
- `getRace.deviceCdList` was **null** on this public call — mapping likely inside encrypted `live2`/`replay2` payload or a follow-up API not exposed without tenant.  
- Operational model (from earlier admin docs): **device serial ↔ sail number / team** at race import time.

---

## 12. Formulas (ranking, VMG, VMC, DTL) — best current read

Exact source formulas are minified; inferred from column names + sailing practice + `toolbar_update_vmg`:

| Metric | Likely definition |
|---|---|
| **SOG** | GPS speed over ground |
| **COG** | GPS course over ground |
| **VMG** | `SOG * cos(twa)` with TWA from wind instrument vs COG (windward component) |
| **VMC** | Speed component toward next mark / course axis (VMG-on-course) |
| **DTL** | Distance behind leader along course or to mark (leaderline / rank order) |
| **DTF** | Remaining distance to finish along course |
| **DTS** | Distance to start line or to next mark (context-dependent) |
| **RTS** | Time estimate from DTF / VMC or similar |
| **Ranking** | `orderType: 1` in viewConfig — server or client order; `lockRank` field exists on race |

Treat server-provided rank/DTL as authoritative when present in protobuf sail ticks; client recomputes VMG chart series when wind updates.

---

## 13. Visible mobile / UI components

open_trac flags: `layout: false` (compact), `mobiAutoLoads: false`, viewport `user-scalable=no`, WeChat share hooks.

**Chrome-visible structure (SF-Traj family, from screenshots + appX):**

1. **Map canvas** — boats, tracks, marks, laylines, start/finish  
2. **Ranking / team list** — filter, columns, row select  
3. **Wind compass**  
4. **Mini-map / eagle eye** (older shell)  
5. **Right toolbar** — zoom, layers, follow, measure, settings, fullscreen  
6. **Replay bar** — play, speed, timeline, REPLAY clock  
7. **Race header** — match name, round, class, time  
8. Optional **camera/video** (xgplayer; `camera: true`)  
9. Settings panels — layline angle, wind sensor, racer show-all wind, tiles  

Related but **not** open_trac: `/sailfish-admin/view/racereplay/live/{levelOrRaceId}/{round}/{n}` (QIYU TRAJ Leaflet classic).

---

## 14. What to copy into SailingSA tracking-dev

Priority borrow list:

1. **Single race page** keyed by `raceCd` with auto live/replay from status.  
2. **Leaderboard columns:** Rank, Sail#, Team, COG, SOG, VMG, VMC, DTL, DTF, Status — toggleable.  
3. **Map tools:** follow boat, follow leader line, laylines (±α), measure, wind compass.  
4. **Replay:** scrub timeline, speed, track length, formal vs live buffer.  
5. **Course overlay:** start/finish line pair, gate marks `4s/4p`, leg sequence string.  
6. **Transport split:** REST race meta + binary/WS tick stream (don’t poll full tracks).  
7. **Mobile-first shell** with team list drawer + bottom transport bar.

Do **not** copy: encrypted `getEncryption` opacity, Baidu-oriented tile stack, WeChat-only share, tenant header quirks — replace with our auth and OSM/vector tiles.

---

## 15. Open gaps

- Exact `getEncryption` HTTP shape (path/query/body) — needs browser Network tab.  
- Prod WSS host + token for this race.  
- Full protobuf `.proto` field names.  
- Non-empty `getRouteInfo` example.  
- Screenshots of **this** open_trac race (existing webp set is classic SF-Traj Hainan replay).

---

## 16. Local artifact index

| File | Content |
|---|---|
| `open_trac/open_trac.html` | Page source |
| `open_trac/inline.js` | Boot / raceCd / SF_TrajX options |
| `open_trac/config.js` | `window.g` |
| `open_trac/getRace.pretty.json` | Sample race API |
| `open_trac/viewConfig.json` | Parsed view flags |
| `open_trac/screenshot_01…05_*.webp` | Classic SF-Traj replay UI |
| `open_trac/screenshot_06…11_*.webp` | Dead marketing paths (404) |
