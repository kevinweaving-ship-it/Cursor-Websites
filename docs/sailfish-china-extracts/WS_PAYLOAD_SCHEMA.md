# Sailfish open_trac — payload schema (HTTP encrypted + WebSocket)

**Scope:** `open_trac.html` / **SF_TrajX** (`appX.min.js?v=20260303`)  
**Sample race:** `6010fbd608e54ae4aff7d8363f912077` — ILCA6 Boys EMERALD F5 — **status `99` (replay)**  
**Captured:** 2026-08-31 (Puppeteer + curl + LZ decode)  
**Companion:** `OPEN_TRAC_TRACKING_DEV.md`, artifacts under `open_trac/`

This doc answers: **what the wire format looks like before/after decode**, how **`runtime[]`** maps to sail telemetry, and what we know about **WebSocket/STOMP** without a live race.

---

## 1. Transport overview

| Mode | When | Primary transport | WebSocket |
|---|---|---|---|
| **Live** | `getRace.status != '99'` | `live2/getRaceDatas` bootstrap + `live2/getEncryptionLiveData?` chunks + WS | Yes — STOMP-like over `wss://…?token=sailfish` |
| **Replay** | `status == '99'` or `replayFlag=true` | `replay2/getRaceDatas` bootstrap + `replay2/getEncryptionReplayData?` chunks | **No** on sample race (0 WS frames in 30s capture) |

Encrypted HTTP uses custom headers ( **`getEncryption`** method):

| Header | Value | Notes |
|---|---|---|
| `oQ` | `i8/RH` | Required on encrypted GETs |
| `TV` | `gB` | Present on bootstrap; omitted on some cache hits (`no-TV`) |
| `tenant-id` | often empty on public `open_trac` | Tenant APIs return “租户的请求未传递” |

---

## 2. HTTP envelope (before decode)

All encrypted race endpoints return the same JSON shell:

```json
{
  "result": "N4I…",
  "success": true,
  "flag": true
}
```

| Field | Type | Meaning |
|---|---|---|
| `result` | string | **LZ-String** payload, URI-encoded component form (`N4I…` prefix) |
| `success` | bool | HTTP-level OK |
| `flag` | bool | App-level OK |

**Decode chain (verified in Node + browser):**

```javascript
const text = LZString.decompressFromEncodedURIComponent(json.result);
const payload = JSON.parse(text);
```

Do **not** use `decompressFromBase64` — it fails on these payloads.

---

## 3. HTTP endpoints (verified)

Base: `https://www.saill.cn/sf-admin/api/app-api/match/race/`

| Step | Replay path | Live path (inferred) |
|---|---|---|
| Race meta | `GET getRace?pageName=open_trac&raceCd=` | same |
| Bootstrap | `GET replay2/getRaceDatas?&raceCd={uuid}&time={ms}` | `GET live2/getRaceDatas?&raceCd={uuid}&time={ms}` |
| Track chunks | `GET replay2/getEncryptionReplayData?raceCd=…&matchCd=…&rounds=…&replayFlag=1&timeSpan=6&asTime=…&timestamp=…&nonCache=false` | `GET live2/getEncryptionReplayData?…` (same param shape in `appX`) |
| Course | `GET getRouteInfo?raceCd=` | same (empty `{}` on sample) |

**Replay chunk request params** (from browser capture + `appX`):

| Param | Example | Role |
|---|---|---|
| `raceCd` | UUID | Race id |
| `matchCd` | `e681cd22…` | Regatta / match id |
| `rounds` | `F5` | Flight / round label |
| `replayFlag` | `1` | Replay mode |
| `timeSpan` | `6` | Chunk width in **minutes** (`viewConfig.timeSpan`) |
| `asTime` | epoch ms | Window anchor |
| `timestamp` | epoch ms | Client cache buster |
| `nonCache` | `false` | Cache control |

First replay chunk (~666 KB compressed) decodes to ~2.4 MB JSON map of time series.

---

## 4. Bootstrap payload (after decode) — `getRaceDatas`

Top-level keys on sample race (56 teams + marks + meta):

| Key group | Examples | Role |
|---|---|---|
| Meta | `status`, `replayFlag`, `matchCd`, `readyTime`, `startTime`, `viewConfig`, `searouteRole` | Race state + UI config |
| `teamList[]` | 56 entries | Sailors: names, sail numbers, `deviceCd`, `teamCd`, **`runtime[]` snapshot** |
| `navigationMark`, `markpositions`, `marktimes`, `worklist` | mark ids / roles | Course geometry + rounding log |
| `windInstrumentList[]` | Wind sensor row | Same `runtime[]` shape as boats |

**No `stomp` field** on finished replay bootstrap — WebSocket config arrives only on **live** races (or page query override).

### 4.1 `teamList[]` row (logical)

| Field | Example | Notes |
|---|---|---|
| `teamName` | `GAITANOS Paris` | Display name |
| `sailNo` | `CYP 1` | Sail number |
| `deviceCd` | `F1025` | SF-Tracer device id |
| `teamCd` | UUID | Primary map key in replay chunks |
| `nationality`, `raceTeamColor`, `model` | … | UI |
| `runtime[]` | 51-slot sparse array | **Latest tick** at bootstrap time |

### 4.2 `runtime[]` slot map (0-based, verified)

Shared by bootstrap snapshots, replay chunk ticks, and (after WS decode) live sail updates.

| Index | Protobuf field | Type | Sample | Semantics |
|---:|---:|---|---|---|
| 3 | 4 | string | UUID / `1a` / `起航线A` | **Entity id** — `teamCd`, mark role, or instrument id |
| 4 | 5 | string | `B` | **Status** letter (bootstrap only; racing/finished/DNS-style) |
| 10 | 11 | string | `0.97736` | **SOG** (kts on this race — `viewConfig.sogUnit`) |
| 16 | 17 | string | `242.0` | **COG** (degrees) |
| 17 | 18 | double | `40.57052667` | **Latitude** |
| 18 | 19 | double | `22.92888167` | **Longitude** |
| 19 | 20 | int | `61` | **Power / battery** (%) |
| 22 | 23 | long | `1784378280000` | **Sample time** (epoch ms) |
| 32 | 33 | int | `0`, `1`, `2` | **Rank** (changes during race) |

Other indices (VMG, VMC, DTL, DTF, DTS, RTS, total distance, etc.) are supported by the **`Nd()` protobuf decoder** and leaderboard columns but were **empty** in this public replay chunk — likely computed client-side or present only on live WS ticks with full tenant columns enabled.

Array length: **51 slots** (protobuf fields 1–51).

---

## 5. Replay chunk payload (after decode) — `getEncryptionReplayData`

Decoded shape: **flat object** keyed by entity id:

```text
{
  "1": [ tick, tick, … ],           // race-level series (360 pts)
  "2": [ tick, tick, … ],           // race-level series (360 pts)
  "{teamCd}": [ tick, … ],          // one array per boat (~250–360 ticks per 6-min chunk)
  "1a", "3p", "4s", "4p": [ … ],    // mark / gate roles from searouteRole
  "起航线A", "起航线B", "终点线A", "终点线B": [ … ],
  "{windInstrumentCd}": [ … ]
}
```

Each **tick** is a sparse **51-element array** (same indices as §4.2). Example first tick for team `f0ae4260…`:

```json
["","","","f0ae426023554becbb405a4e73c0a527","","","","","","","0.97736","","","","","242.0","40.57052667","22.92888167","61","","","1784378280000","","","","","","","","","","0.0"]
```

Chunk cadence: client polls every **`timeSpan` minutes** (6 on sample) while replay plays.

Sample artifact: `open_trac/replay_chunk0.decoded.sample.json` (one team × 3 ticks + meta keys).

---

## 6. WebSocket (captured 2026-09-01)

**Production URL verified** from `live2/getRaceDatas` bootstrap (`stomp` field, base64):

```text
wss://www.saill.cn/sailfish-ntwss?token=sailfish
```

(`replay2/getRaceDatas` omits `stomp` on finished races; use `live2/` bootstrap or force live client mode.)

Artifact: **`open_trac/ws_handshake_sample.json`**

### 6.1 Handshake + subscribe (captured frames)

| # | Dir | Payload |
|---:|---|---|
| 1 | ← server | `{"v":"CONNECTED","k":"CMD"}` |
| 2 | → client | `{"subscribe":"/topic/SAIL_DATA_BATCH_P_{raceCd}"}` |
| 3 | → client | `{"subscribe":"/topic/BUOY_DATA_{raceCd}"}` |
| 4 | → client | `{"subscribe":"/topic/RACE_CONTROL_{raceCd}"}` |
| 5 | ← server | `{"v":"SUBSCRIBE#/topic/SAIL_DATA_BATCH_P_{raceCd}","k":"CMD"}` |
| 6 | ← server | `{"v":"SUBSCRIBE#/topic/BUOY_DATA_{raceCd}","k":"CMD"}` |
| 7 | ← server | `{"v":"SUBSCRIBE#/topic/RACE_CONTROL_{raceCd}","k":"CMD"}` |
| 8 | → client | `\n` (keepalive) |
| 9 | ← server | `\n` (keepalive ack) |

**Wire topics** use `/topic/…` prefix. **`appX` internal handlers** map to `/RX/…` after decode (e.g. `/RX/SAIL_DATA_P_{raceCd}`).

Client sets `binaryType = "arraybuffer"` for protobuf sail batches.

### 6.2 Topics (wire vs internal)

| Wire subscribe path | Internal handler (`appX`) | Payload |
|---|---|---|
| `/topic/RACE_CONTROL_{raceCd}` | `/RX/RACE_CONTROL_{raceCd}` | JSON — race control codes (§6.3) |
| `/topic/SAIL_DATA_BATCH_P_{raceCd}` | `/RX/SAIL_DATA_P_{raceCd}` / `/RX/BEG{raceCd}` | Binary protobuf → `Nd()` → `runtime[]` |
| `/topic/BUOY_DATA_{raceCd}` | `/RX/BUOY_DATA_{raceCd}` | JSON mark arrays (§6.4) |

### 6.3 `RACE_CONTROL` message schema (after JSON decode)

| Field | Type | Code `JE` | Behaviour |
|---|---|---|---|
| `JE` | number | `0` | Reset all boats + course graphics |
| `JE` | number | `10` | Wind update — `BAm` wind instrument payload; refresh marks |
| `JE` | number | `0xan` (hex) | Clock sync — seek replay/live clock to `CC` |
| `JE` | number | `99` | Next race — extract next `raceCd` from `9B` (`CL=…`) |
| `H0` | number | * | Event timestamp (ms) |
| `BAm` | object | 10 | Wind instrument data |
| `CC` | number | 0xan | Target clock value |

### 6.4 `BUOY_DATA` message schema

After `N_.TS()` decode:

| Field | Role |
|---|---|
| `D1` | Array of mark ticks (each tick uses `runtime[]` shape) |
| `pointIndex` | Course point index (+2 used for timeline seek) |
| `H0` | Timestamp ms |

### 6.5 `SAIL_DATA_P` — protobuf → `Nd()` field map

Wire: **binary protobuf** (first byte stripped before decode in handler). Decoder fills 51-element array; field number `N` → index `N-1`.

| Field # | Wire type | Index | Likely metric |
|---:|---|---:|---|
| 1 | double | 0 | (reserved / aux) |
| 2–3 | varint | 1–2 | flags / counters |
| 8 | double | 7 | aux numeric |
| 10 | int64 | 9 | long timestamp fragment |
| 11–14 | string | 10–13 | **SOG** and related strings at 11→10 |
| 16 | double | 15 | aux |
| 17 | string (2 dp) | 16 | **COG** |
| 18–19 | double | 17–18 | **lat / lng** |
| 20–21 | varint | 19–20 | **power**, status codes |
| 22 | double | 21 | aux |
| 23–24 | int64 | 22–23 | **sample time** at 23→22 |
| 32 | varint | 31 | counter |
| 33 | string | 32 | text aux |
| 33 | varint | 32 | **rank** (observed at index 32 in replay) |
| 38 | int64 | 37 | long aux |
| 51 | hex string | 50 | device / id hex |

Exact VMG/VMC/DTL/DTF/DTS/RTS indices are computed in leaderboard layer when `Col*` flags enabled — not populated in minimal public replay extract.

### 6.6 Telemetry frames (still needs active race)

Handshake + subscribe ACKs captured on finished ILCA6 race — **0 telemetry payloads** (server only returns CONNECTED/SUBSCRIBE acks + `\n`). During an active regatta, expect after frame 9:

```text
← binary or JSON sail batch (protobuf → runtime[] ticks)
← JSON RACE_CONTROL { JE, H0, … }
← JSON BUOY_DATA { D1, pointIndex, H0 }
```

Re-capture with a live `open_trac` URL when `getRace.status != 99`.

---

## 7. Device protocol alignment (SF-Tracer docs)

Public **Device Interface Protocol** (`protocol-en.md`) position message maps cleanly onto `runtime[]`:

| Protocol field | runtime index |
|---|---|
| SAMPLE TIME | 22 |
| LONGITUDE | 18 |
| LATITUDE | 17 |
| SPEED (m/s on device; converted to kts in UI) | 10 |
| HEADING | 16 |
| BATTERY | 19 |

WebSocket push format in docs equals device protocol; SF_TrajX adds protobuf wrapping + race-side derived metrics (rank, DTL, VMG, …).

---

## 8. Artifacts in repo

| File | Content |
|---|---|
| `open_trac/getRace.pretty.json` | Race meta + `viewConfig` |
| `open_trac/replay_chunk0.decoded.sample.json` | Decoded chunk excerpt |
| `open_trac/http_capture_urls.json` | Saill API URLs from Puppeteer run |
| `open_trac/ws_handshake_sample.json` | Prod WSS URL + first 9 frames (CONNECTED/subscribe) |
| `OPEN_TRAC_TRACKING_DEV.md` | Full UX / feature reverse-engineering |

---

## 9. Open items

| Item | Blocker |
|---|---|
| First **telemetry** WS frames (protobuf sail tick, RACE_CONTROL JSON body) | **Active regatta** — see **`LIVE_WS_CAPTURE_WHEN.md`** (public `sf-front-api` event list checked 2026-09-01: stale, no future dates) |
| Full VMG/DTL/… index map on live ticks | Need live race with `ColVMG`/`ColDTL` enabled |
