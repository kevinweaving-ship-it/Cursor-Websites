# Lipton Event Reels — Mac morning handover

**Night of 10 Sep 2026.** Cloud/mobile finished GPS+stamp analysis most recent first. Live cache tag after this pass: **`mmr97`**. PR: https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/66

This report lists **only clips that still cannot be synced accurately**. Everything else is either measured (Race 7) or stamp-assumed (ear-check on Mac if you want measured).

No Whisper/STT on the VM. Do not treat assumed offsets as heard guns or “round 1st” calls.

---

## Still the issue (cannot lock accurately)

### Race 4 — no trail / replay (`lipton-dev-trail-r4.json` does not exist)

Cannot tie gun, finish horn, or any rounding to GPS. Overlay will not load boats.

| Clip | Title | Stamp | What Mac must do |
|---|---|---|---|
| `1079923421076157` | Race 4 start | 27 Aug 13:52 | Build R4 trail+replay from Vakaros, then lock **start gun** |
| `1582165340314238` | Race 4 1st windward | 27 Aug 14:16 | Same trail, then lock **1st at M1** from commentary or on-screen |
| `1588170962712352` | Lipton race4 | 27 Aug 14:36 | Same trail; listen for a rounding — title does not name the mark |
| `2111285223132517` | Race 4 2nd Quad | 27 Aug 15:03 | Same trail; listen for which mark |
| `1751846282795149` | Race 4 Finish | 27 Aug 15:24 | Same trail; **finish horn = 1st finish GPS** |

### Race 3 — trail exists, but the named event is not at the stamp

| Clip | Title | Stamp | Why it cannot lock | GPS around the stamp |
|---|---|---|---|---|
| `1802153794291569` | Race 3 leeward 1 | 26 Aug **15:34** | Whole fleet already rounded **M2 by 15:32:19**. 1st M2 was **15:30:25** (3:35 before stamp). Next mark **M3 15:59:28** (25 min later). | If the VOD is long enough, find “rounds” for **M3 ~15:59** and set `offsetMs`. If the clip is only the 15:34 window, there is **no rounding in the video**. |
| `1530770848344300` | Race 3 Downwind 2 | 26 Aug **15:51** | Mid-leg. No mark at open. Next GPS is **L1 M3 HYC 15:59:28** (~**8:28** after stamp). Title says downwind; that leg is the beat to M3. | Play to ~8:28. If 1st rounds there, `offsetMs = 0` and mark `3`. If they say someone rounds earlier, use that boat’s GPS time. |

### Race 2 — generic clip, named moment already over

| Clip | Title | Stamp | Why it cannot lock | GPS around the stamp |
|---|---|---|---|---|
| `1384453329808359` | Lipton R2 | 26 Aug **13:45** | **16/17** already rounded **L1 M2** (1st LDYC **13:42:59**). Only WYAC left (**13:45:01**). Next mark **L1 M3 FBYC 13:49:50** (~4:50). Title does not say which. | Listen: last M2 (WYAC) at open, or 1st M3 at ~4:50. Then set mark + `offsetMs`. |

### No clip / no overlay

| Item | Why |
|---|---|
| Race 2 **start** | Not in the Event Reels feed. No start-gun clip to lock. |
| `983599421402934` Lipton day3 | Day reel, not a race overlay clip. |
| Races 1, 6, 8, 9, 10 | Trails exist under `sailingsa/frontend/js/`, but there are **no Event Reels clips** for them. |
| Race 4 gun / finish GPS | Unknown until R4 trail is built. |

---

## Not issues (do not re-do unless ear-check fails)

**Measured (R7 only)** — leave unless live regresses:

- `1014880974840710` Start — `offsetMs +24200` (gun 15:57:01, STT ~1:36.8)
- `2410502969472697` 1st top — `offsetMs -88000` (1st M1 16:10:56 ~0:25)
- `2622643364847262` 1st downwind — `offsetMs +36000` (Pin 16:22:43, STT ~3:07)

**Stamp-assumed (clock = stamp + videoTime; offset 0 unless noted).** Mac can confirm with one horn / “rounds” call:

| Clip | Title | Assumed lock |
|---|---|---|
| `26023759437321260` | R5 | L3 M1 HYC 16:47:35 ~0:35 |
| `1587763379559775` | Race 5 | L1 M2 HYC 16:02:18, `offsetMs -42000` |
| `4518629078350390` | R5 Start | gun 15:50:01 ~2:01 |
| `825961863876577` | R3 3rd Downwind | pack at L2 M1 (HYC 16:11:09, FBYC 16:11:39) |
| `1813350889838726` | R3 windward 1 | L1 M1 FBYC 15:24:21 ~0:21 |
| `1025386753667866` | R3 start | gun 15:10:01 ~3:01 |
| `940083808452432` | R2 Finish | WBYC **14:44:11** horn ~2:11 |
| `942850414812890` | R2 2nd leeward | L2 M3 LDYC 14:18:12 ~2:12 |
| `3239679922895545` | R2 2nd Lap | L2 M1 LDYC 14:05:37 ~1:37 |

If a horn/rounding is **not** at that video time, send the video time — `offsetMs = gpsEvent − (stamp + videoTimeOfEvent)`.

---

## Mac first actions

1. Open `docs/LIPTON_OVERLAY_MAC_HANDOVER.md` (this file).
2. **Race 4 trail** — highest blocker. Without it, five clips stay dark.
3. Ear-check the three **cannot-lock** clips that already have GPS (R3 leeward 1, R3 Downwind 2, R2 generic). Write `offsetMs` + mark from a real in-video event.
4. Optional: ear-check assumed starts/finishes (R5 start, R3 start, R2 finish). R7 start needed **+24.2s** after STT — the same trap.
5. Surgical deploy only: overlay JS both paths, R3/R4 JSON under `/js/`, cache tag in live `api.py`, restart `sailingsa-api`. **Do not overwrite live `api.py` wholesale.**

Live page: https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
