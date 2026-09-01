# When to capture live WebSocket telemetry (Sailfish)

**Status:** waiting on an actively racing `open_trac` event  
**Last checked:** 2026-09-01

Live sail/buoy/control **telemetry** on `wss://www.saill.cn/sailfish-ntwss?token=sailfish` only flows while a race is **in progress** and publishing. Handshake + subscribe ACKs are already captured in `open_trac/ws_handshake_sample.json`.

---

## What we checked (2026-09-01)

| Source | Result |
|---|---|
| `POST /sf-front-api/api/event/list` (pages 1–5) | **Stale** — every page returns the same 2019 Hainan regatta block; **0 future events** |
| `POST /sf-front-api/api/news/list` | **Stale** — newest items ~2020 |
| Known sample race `6010fbd6…` (ILCA6 Youth Europeans) | `getRace.status = 99` (finished); ran **2026-07-18** |
| China Sailing listing (Quanzhou U-series, Aug 2026, Sailfish轨迹费) | Event window **2026-08-19 – 24** — already past as of Sep 2026 |

**Conclusion:** Sailfish’s **public marketing API is not a reliable schedule feed**. Use **China Sailing** + procurement notices instead (see watchlist below).

---

## China regatta watchlist (web check 2026-09-01)

Monitor [chinasailing.org.cn/wap/matchs/getList](https://www.chinasailing.org.cn/wap/matchs/getList) during racing days. **Sailfish likely?** = explicit 旗鱼 contract/payment in notice, or Sailfish won轨迹技术服务 bid.

| Dates | Event | Location | Sailfish likely? | Notes |
|---|---|---|---|---|
| **22–28 Sep 2026** | [全国帆船冠军赛 ILCA4 & 青年 ILCA6](https://www.chinasailing.org.cn/match/410) | 宁波 | **Maybe** | 2025 same event had real-time轨迹直播 (QR scan); vendor not named. **Nearest upcoming dinghy target.** |
| **1–6 Oct 2026** | [全国青少年帆船联赛总决赛](https://npo093864.npoall.com/news/itemid-299276.html) | 秦皇岛蔚蓝海岸 | **High** | Sailfish **won** [2026全国青少年帆船联赛分站赛轨迹技术服务](https://bbda.com/bidDetail/6ce8c9f276206f59d625a8107d6d5ac958d2cef9e2d712975bfe003ea42e0168.html) bid (厦门文旅环东). |
| **9–15 Oct 2026** | [全国翻波板锦标赛暨青年帆板冠军赛](https://www.chinasailing.org.cn/match/411) | 四川雅安汉源 | Low | Windsurf/wing; different device stack |
| **12–18 Oct 2026** | [全国帆船锦标赛 49er/49erFX/Nacra17](https://www.chinasailing.org.cn/match/412) | 宁波象山亚帆中心 | **Maybe** | Major Olympic-class nationals; often tracked but no Sailfish name in notice yet |
| **17–19 Oct 2026** | [China Coast Regatta](https://www.chinacoastraceweek.com/about-ccr) | 香港 RHKYC | Low | Offshore IRC; different org |
| **14–18 Nov 2026** | [第十八届中国杯](http://chncup.com/info-detail/id-199.html) | 深圳大鹏 | Unknown | 纵横四海承办; may use different tracking vendor |

**Confirmed Sailfish (already past):**

- **19–24 Aug 2026** — U系列体校联赛泉州站 — notice requires **轨迹服务费** to 深圳旗鱼体育传播有限公司 ([match/409](https://www.chinasailing.org.cn/match/409))
- **Jul 2026** — ILCA6 Youth Europeans — our `open_trac` sample race (replay only now)

**How to confirm day-of:** search notice PDF for `旗鱼` / `轨迹服务费` / `深圳旗鱼体育`; or watch for `open_trac.html?raceCd=` links on WeChat/赛事零距离 during racing hours (typically **10:00–17:00 CST**).

---

## How to know when to capture next

1. **Direct `open_trac` share link** during a regatta (best signal)  
   `https://www.saill.cn/sf-admin/html/race/live/open_trac.html?raceCd={uuid}`  
   Capture when `getRace.status != '99'` and boats are on the course.

2. **赛事零距离 WeChat mini program** — Sailfish’s live ops surface; often where share links originate.

3. **China Sailing / regatta notices** — search for **旗鱼轨迹** or **轨迹服务费** (e.g. [chinasailing.org.cn](https://www.chinasailing.org.cn) match pages). Payment to 深圳旗鱼体育传播有限公司 = likely SF-Tracer tracking.

4. **Sailfish contact** (public docs): info@saill.cn · +86 (0532) 8563 1190 — only if you need tenant/demo access.

5. **Re-check annually** — scrape `sf-front-api` again in case they fix the event list; compare `beginDate`/`endDate` to `Date.now()`.

---

## Capture checklist (when live)

1. Open share URL in browser or run Puppeteer CDP capture (`ws` + `Network.webSocketFrame*`).
2. Confirm `live2/getRaceDatas` bootstrap includes `stomp` (base64 → `sailfish-ntwss`).
3. Record first ~20 frames **after** subscribe ACKs on:
   - `/topic/SAIL_DATA_BATCH_P_{raceCd}`
   - `/topic/RACE_CONTROL_{raceCd}`
   - `/topic/BUOY_DATA_{raceCd}`
4. Decode protobuf sail batches via `Nd()` map in `WS_PAYLOAD_SCHEMA.md`.
5. Append samples to `open_trac/` and update `WS_PAYLOAD_SCHEMA.md` §6.6.

---

## Still open after live capture

- Protobuf telemetry frame hex + decoded `runtime[]` tick
- `RACE_CONTROL` JSON bodies (`JE`, `H0`, wind updates)
- `BUOY_DATA` mark rounding payloads
- VMG/DTL columns if ops enable `Col*` flags on that event
