# Sailfish (旗鱼体育) — patents & software dossier

**Assignee searched:** 深圳旗鱼体育传播有限公司  
**Source:** Google Patents (2026-08-31 crawl)  
**Note:** “Patients” interpreted as **patents**. Soft著 (software copyright registrations) are **not publicly enumerable** without a registration number on copyright.com.cn; none were found via open web indexes under this exact company name.

---

## A. Patent inventory (assignee = 深圳旗鱼体育传播有限公司)

Eight publication numbers found (families collapsed where A→B). English assignee string on Google Patents: **Shenzhen Swordfish Sports Communication Co ltd** (translation of 旗鱼).

| Pub | Type | Title (ZH) | Inventors | Priority | Status (GP) | Link |
|---|---|---|---|---|---|---|
| **CN110750962B** | Invention | 天气数据转换方法和系统 | 刘海岚 | 2019-10-14 | Granted | [GP](https://patents.google.com/patent/CN110750962B/zh) |
| CN110750962A | Invention appl. | same | 刘海岚 | 2019-10-14 | →B | [GP](https://patents.google.com/patent/CN110750962A/zh) |
| **CN110738023B** | Invention | 一种将JSON天气数据转换为JPEG图片的系统及方法 | 刘海岚 | 2019-10-17 | Granted | [GP](https://patents.google.com/patent/CN110738023B/zh) |
| **CN113033968B** | Invention | 一种对帆船比赛中竞赛选手的赛事表现进行评价的方法 | 田维宏, 王腾 | 2021-03-04 | Granted 2022-03-25 | [GP](https://patents.google.com/patent/CN113033968B/zh) |
| CN113033968A | Invention appl. | same | 田维宏, 王腾 | 2021-03-04 | →B | [GP](https://patents.google.com/patent/CN113033968A/zh) |
| **CN113588153A** | Invention appl. | Offshore real-wind remote real-time monitoring system and method（海上真风远程实时监测） | 田维宏 | 2021-04-26 | Published 2021-11-02 (B not found) | [GP](https://patents.google.com/patent/CN113588153A) |
| **CN114690225B** | Invention | 一种运动对象绕过目标的识别方法 | 顾俊 | 2022-03-21 | Granted 2024-07-23 | [GP](https://patents.google.com/patent/CN114690225B/zh) |
| CN114690225A | Invention appl. | same | 顾俊 | 2022-03-21 | →B | [GP](https://patents.google.com/patent/CN114690225A/en) |
| **CN220137400U** | Utility model | 基于GPS的定位设备及系统 | 田维宏 | 2023-04-22 | Granted 2023-12-05 | [GP](https://patents.google.com/patent/CN220137400U/zh) |
| **CN220874872U** | Utility model | GPS定位设备（带防护结构） | 田维宏, 高翔 | 2023-09-15 | Granted 2024-04-30 | [GP](https://patents.google.com/patent/CN220874872U/en) |
| **CN220874741U** | Utility model | 一种定位系统用的信号基站 | 田维宏, 高翔 | 2023-09-22 | Granted 2024-04-30 | [GP](https://patents.google.com/patent/CN220874741U/zh) |

**Not Sailfish (false friends in broader sailing-track searches):**  
- CN103111065B《帆船轨迹记录系统》— assignee **广东省信息工程有限公司** (unrelated).  
- Trademarks / soft著 for **深圳市旗鱼移动科技** (QIYU点餐) and **广州市旗鱼软件科技** — **different companies**, do not conflate.

**People / equity context:** 王祥胜 (spokesperson, ~20% shareholder) — **no patents found under his name** tied to Sailfish. Legal rep **刘海岚** is inventor on weather patents. Core hardware/algorithm inventors in filings: **田维宏**, **王腾**, **顾俊**, **高翔**. Parent shareholder **深圳市海上轻骑帆船运动有限公司** — **0 patents** as assignee in Google Patents.

Machine-readable claim/abstract extracts: `patent_dossier.json`.

---

## B. Patent content summaries

### 1) Weather pipeline (maps / SF-Traj weather layer)

**CN110750962B — GRIB → JSON for web**  
Pull NOAA GRIB, parse bytes → intermediate single-variable files → merge → emit JSON KEY/VALUE for web display (task add / decompose / download / parse). Supports scheduled weather tasks driven by web client time range.

**CN110738023B — JSON weather → JPEG “image container”**  
Encode weather JSON grids into JPEG: header holds lon/lat ranges, dx/dy, nx/ny, surface type, class, length, max/min/mid/delta; body holds offset-delta bytes; optional encryption. Goal: smaller, faster, encryptable weather tiles for transmission/storage (fits SF-Traj “weather visualization” layer).

### 2) Race analytics (ties to race admin / scoring)

**CN113033968B — sailor performance scoring**  
From race-management raw data compute one or more of:

- **航行得分** (sailing): weighted mix of normalized average speed / average effective speed (VMG-like) / distance  
  `s%*100*α + v%*100*β + l%*100*γ` with example weights α=0.2, β=0.4, γ=0.4  
- **起航得分** (start)  
- **换弦得分** (tack/gybe / “换舷”)

Purpose: quantify strengths/weaknesses per race for spectators/analysts. Explicitly reads from **帆船竞赛管理系统** (their race CMS).

### 3) Mark rounding / course geometry

**CN114690225B — detect moving object bypassing a mark**  
GPS on marks; server stores positions; analysis draws an **auxiliary line through the mark** along the angle bisector of adjacent course legs; circular correction region radius R derived from GPS error X, report rate Z, boat speed Y. Covers collinear start–mark–finish, same start/finish, and gate (two marks) cases. Core of automated rounding / protest evidence on traj.

### 4) Hardware — tracker / microwave base (SF-Tracer family)

**CN220137400U — GPS positioning device & system**  
GPS chip + local memory (offline cache) + gyro (attitude/position/drift) + GPRS uplink at configurable rate; optional Bluetooth to headset/watch; alarm key forces **10 Hz** uplink. Matches documented Tracer sensors + SOS + store-and-forward.

**CN220874872U — GPS unit with protective / anti-collision buffer**  
Protective shell + buffer rods/blocks (mechanical ruggedization for on-deck use).

**CN220874741U — signal base station for positioning system**  
Protective ring/shell with L-slot latch, status LEDs, vents — aligns with **microwave** venue base mentioned in Tracer docs (non-GSM path).

### 5) Wind (Windwatcher)

**CN113588153A — offshore real-wind remote real-time monitoring**  
Invention application (田维宏). Full claims page was rate-limited (HTTP 503) during this pass; title/product alignment is clearly **SF-Windwatcher / true-wind remote monitoring**. Re-fetch claims when GP is available.

---

## C. Software product map (deployed / documented)

| Product | Entry | Stack / notes |
|---|---|---|
| Marketing site | `www.saill.cn` | Vue SPA `sf-front-view`, Element UI, Leaflet demos |
| Front CMS API | `/sf-front-api` | Events, news, banners, partners, videos |
| **SF-Traj** web | share links from admin; docs `/docs/match/web/` | Leaflet map, LIVE/REPLAY, ranks, wind compass; renamed from earlier system |
| **赛事零距离** | WeChat mini program | Mobile traj live + replay of Sailfish events |
| Race admin | `/sf-admin` | Vue admin; `/sf-admin/api/admin-api/`; Netty WS; IoTDB |
| Race APP / short links | `/s/raceApp` | Path-based deep link script |
| Cloud H5 | `/sf-cloud-h5/` | Mobile H5 shell |
| Training admin | `/sf-training/login` | Team training traj management |
| Training H5 | docs `train/h5_v1` | Group training instructions |
| Sailing-rules portal | `/sailingrule-ui` + `/sailingrule-api` + `/sailingrule-h5` + `/sailingrule-web` | **RuoYi-Vue-Plus** fork (`sailfish.sailingrule-Vue-Plus`); protest/score/retire; pay at `/sailingrule-web-pay/pay` |
| Public event QR viewer | `/docs/match/qrcode/event.html` | List → level → rounds; Track / Pro charts; states Ready/Racing/Replay |
| **云相册** | product pages | Photo workflow: shoot / edit / key-gated HD publish |
| **3D panorama** | docs `/docs/3d/` | Win10 desktop 3D broadcast client (GTX-class) |
| EOTS / YB | product pages | Offshore Inmarsat + Iridium companion software (pad apps claimed) |
| Device protocol consumer | docs websocket | Token WS; pipe protocol `$$|…|**` |

**Third-party / OSS in stack (observed):** Leaflet, Element UI, Vue, RuoYi-Vue-Plus, IoTDB (admin API names), Baidu maps link, NOAA GRIB (weather patents), xxl-job (rules API banner).

**Software copyrights:** No public soft著 titles located for **深圳旗鱼体育传播有限公司**. Business scope includes software development; registrations may exist but are not scrapable without certificate numbers. Do **not** attribute soft著 from 旗鱼移动 / 广州旗鱼软件.

---

## D. Relevance notes (SailingSA)

- Patented **mark-rounding geometry** + **performance scoring** are the non-obvious software IP; hardware utility models protect Tracer/base packaging.  
- Weather GRIB→JSON→JPEG pipeline explains SF-Traj weather layers.  
- Soft IP moat is mostly product + ops (admin + Traj + mini program), with a thin but real CN patent layer (2019–2024).
