# Sailfish — install manuals, equipment integration, spectators, “sailor profiles”, training

**Source:** public VitePress docs under `https://www.saill.cn/docs/` (+ EN mirrors), scraped 2026-08-31.  
**Purpose:** how hardware binds into race/training ops, how spectators watch, and what exists instead of rich sailor CRM profiles.

---

## 1. Install / device manuals (SF-Tracer 小橙盒)

Docs: `/docs/device/tracker/2-user-manual.html`, `/docs/device/tracker/3-sim-card-replacement.html`  
Local mirrors: `sf-tracer-manual.md`, `/tmp/sailfish_ux/md_js/en_device_tracker_*`.

### Power / SOS

| Action | Effect |
|---|---|
| Short press SOS | Power on |
| Long press SOS ~3 s | Power off (release after lights flash) |
| Triple-press SOS | Start SOS; triple again to cancel |
| Admin remote on/off | Via 旗鱼后台 (`/sf-admin`) |
| **Manual power-off** | **Disables remote power** until unit is turned on locally again |

### LEDs

| Light | Color | Meaning |
|---|---|---|
| GPS (left) | Blue | Steady = fix; flash = no fix |
| Power (middle) | Red | Steady = charging; off = not charging / full |
| Signal (right) | Orange | Steady = connected to server; fast flash = lost |

Combined: slow GPS+signal flash ≈ SOS sending; signal on + GPS/power off ≈ sleep.

### SIM swap (field install)

1. Power off.  
2. Remove 4 corner screws → back cover → battery (gentle on thin battery lead).  
3. Slide SIM tray toward head; swap nano/appropriate SIM; reseat.  
4. Reassemble battery → cover → screws.  
5. FAQ: won’t boot → check battery + SIM seated; no network → SIM must be **activated with balance**.

### Physical identity used in software

- Device serial / device number is printed on the unit (SOS-button side in race flows; **QR on the back** for training H5 scan-join).  
- Binding model is **device No. ↔ team / sail number / mark role** in race or training admin — not a deep personal athlete CRM profile.

---

## 2. Equipment integration (race ops)

### 2.1 GPS trackers + marks + wind (regatta admin)

Doc: `/docs/match/race/` (EN: `en_match_race_index`).

**Prep materials:** sailing instructions, Excel for team check-in, **equipment serial number table** for trackers.

**Event wizard (5 steps):**

1. **Event info** — name, logo, dates, country/city/venue, map center (affects traj initial view).  
2. **Courses** — e.g. `I2` with path `1-4s/4p-1-2-3p` (`/` = gate, `-` = marks; Start/Finish not in string).  
3. **Devices** — paste event device pool (incl. backups), one number per line.  
4. **Classes** — class name, planned race count.  
5. **Teams** — **Import Team** template: **Sail Number + Team Name + Device Number** (+ nationality). Batch update later for icons/country/Ext1/Ext2.

**Per-race setup:**

- Assign **mark devices**: Start Boat / Start Pin / Finish Boat / Finish Pin / numbered marks (gate s/p). Type = Device + device No. from pre-built Excel map.  
- Confirm team device numbers/colors for that race.  
- Optional **anemometer** (Windwatcher) by device No.  
- Ops: Start Sailing (course + start-line open time) → General Recall → Finish Sailing (auto-create next race e.g. R2) → generate **Formal replay** (smooths Informal/live gaps).

**Sharing tracks:** local “open track” tab is login-gated for outsiders; use **More → Share Track Link** for public/shareable SF-Traj URLs.

### 2.2 Sailfish-App / race APP (ops on water)

Docs: `/docs/match/app/`; product surface `/sf-cloud-h5/` (uni-app).

Roles: organizers / refs / teams. Modules include event/race management, **remote smart-device control**, real-time monitoring, check-in/withdrawal, start/course/全召, GoPro, auto-buoy (from earlier dig). Talks to authenticated `/sf-admin/api/admin-api/`.

### 2.3 “Equipment substitution” ≠ tracker binding

Doc: `/docs/sailingrule/5-equipment-replacement.html` (rules portal).

Athletes apply to replace **sails / mast / hull** etc. by searching **sail number or name**, then Old/New equipment + reason + photos. Officials approve. This is class-rules compliance — **not** GPS tracker assignment.

---

## 3. How spectators interact

Three public-facing layers:

### 3.1 QR / event viewer H5

Doc: `/docs/match/qrcode_event` (EN: `en_match_qrcode_event`).

- Client gets a **dedicated QR** → events list (name, start/end, venue).  
- Drill: **Event → Level → Rounds**.  
- Round statuses: **Ready** | **Racing** | **Replay**.  
- **Track** button: live traj when Ready/Racing; replay when finished.  
- Some events expose **Pro** advanced analysis charts.  
- Share: copy browser URL.  
- Mobile companion also marketed as WeChat mini program **赛事零距离**.

### 3.2 SF-Traj web (旗鱼轨迹 / QIYU TRAJ)

Doc: `/docs/match/web/`.

Layout: map + (A) race info + leaderboard, (B) playback bar, (C) eagle eye + wind compass + toolbar.

| Area | Spectator affordances |
|---|---|
| Leaderboard | Rank, COG, SOG, Ave/Max SOG, VMG, VMC, DTL, DTF, distance, sail no., Ext1/Ext2; filter by name/sail; select/highlight boats |
| Playback | Play/pause, speed ±, scrub timeline, mark rounding ticks, LIVE (blue) vs REPLAY (green) |
| Map tools | Layers (vector/sat/weather/chart/grid/marks/work boats/wind), measure, follow boat / follow leader, auto race view |
| Wind | Compass + speed; click rotates map into wind |

### 3.3 Marketing CMS events

`/events` SPA + `/sf-front-api` event/level/race/score endpoints — editorial event pages, not the live ops map.

---

## 4. “Sailor profiles” — what actually exists

Sailfish does **not** ship a public sailor profile product comparable to SailingSA (career history, media tab, rankings identity page). Closest constructs:

| Surface | Identity fields | Persistence |
|---|---|---|
| **Race team row** | Sail No., Team Name, Nat., Device No., track icon/color, Ext1/Ext2 | Per event/class; import Excel |
| **Training team/mark** | Name, Device No., icon, color; optional mid-day **Device Usage Record** for swaps | Per training track / group |
| **Training H5 “My”** | Avatar, nickname, password; **bound** vs **followed** teams; personal training history when join type = **Personal** | User account scoped |
| **Sailingrule athlete search** | Class, division, sail no., boat name, first/last, phone, email | Event registration for protest / retire / equipment / scores |

**Join types (training H5 scan):** Personal (logged-in athlete history) | Team (guest / scan for others) | Mark (start/finish boat/pin / named mark — race-oriented).

Binding is operational (**who carries which box today**), not a lifelong sailor CRM.

---

## 5. Training — examples / flows

### 5.1 Web admin — `/sf-training`

Doc: `/docs/train/track/`.

1. Login → pick **group** (club/squad) if multi-group.  
2. Training → Track List → **Add** daily track (default “In progress”).  
3. Team&Mark → Add: **team name + device No.** (from physical unit); or Import Team; marks for start/finish boat/pin.  
4. Open track name → live map of all teams.  
5. End of day: devices off ashore; system **auto-ends at midnight** (end = last point, or 23:59:59 if never off). Manual **End** optional.  
6. Mid-day device swap: **Device Usage Record** timestamps which box a team used when.  
7. Types: routine daily training vs intra-group race; sports type switches units on the map.

### 5.2 Training H5 (mobile)

Doc: `train_h5_v1` / EN `en_train_h5_v1`.

**Roles:** Manager (full) | Coach (create/manage activities, guide) | Team (view, scan-join, own traj).

**Athlete loop:**

1. Scan **team QR** → home.  
2. Center **Scan** → camera reads **QR on device back** → join dialog (Personal / Team / Mark).  
3. Live map: positions, colors, battery, speed (kn), heading, max speed, distance (NM), duration; refresh ~10 s.  
4. History: filter by date; avg/max speed, mileage; permanent traj storage (per docs).  
5. Stats after end: planar distance, duration, max speed, max 2 s, best 100/250/500 m / 1 km.  
6. Manager/coach: workbench, invite QR + invitation code, device management, video management (needs Sailfish video app).

**Demo credentials (published in docs; may rotate):** username `demo1` / password `123456` (manager/coach sandbox).

---

## 6. End-to-end mental model

```
Physical SF-Tracer (serial + back QR + SIM)
        │
        ├─► Race admin device pool ──► team SailNo↔Device ──► marks/wind
        │         │
        │         ├─► Share Track Link ──► SF-Traj LIVE/REPLAY (spectators)
        │         ├─► QR event viewer / 赛事零距离
        │         └─► Sailfish-App (ops: start/recall/devices)
        │
        ├─► Training admin (device No. on team) ──► daily track map
        │         └─► Training H5 scan-join + My history (thin “profile”)
        │
        └─► Sailingrule portal (athlete by sail/name) ──► protest / equipment / scores
              (boat equipment, not GPS)
```

---

## 7. SailingSA comparison (notes only)

| Sailfish | Implication for learning |
|---|---|
| Device-centric identity | Sailor page is not the hub; **sail number + tracker serial** is |
| Spectator = traj product | Rich metrics board (VMG/VMC/DTL…) worth studying separately from results sheets |
| Training H5 “My” | Lightweight account + followed teams — not rankings/media career |
| Equipment substitution portal | Parallel to protest/score; orthogonal to tracking hardware |
| Formal vs Informal replay | Explicit post-race data cleanup step before public polish |

---

## 8. Source URLs

- https://www.saill.cn/docs/device/tracker/2-user-manual.html  
- https://www.saill.cn/docs/device/tracker/3-sim-card-replacement.html  
- https://www.saill.cn/docs/match/race/  
- https://www.saill.cn/docs/match/web/  
- https://www.saill.cn/docs/match/app/  
- https://www.saill.cn/docs/en/match/qrcode_event.html (path may vary; see hashmap)  
- https://www.saill.cn/docs/train/track/  
- https://www.saill.cn/docs/en/train/h5_v1.html (or ZH `train_h5_v1`)  
- https://www.saill.cn/docs/sailingrule/5-equipment-replacement.html  
- https://www.saill.cn/sf-training/login  
