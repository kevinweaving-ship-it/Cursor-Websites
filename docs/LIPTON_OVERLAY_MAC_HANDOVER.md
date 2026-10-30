# Lipton Event Reels — Mac morning handover

**Updated 10 Sep 2026.** Lipton R2 generic is locked to triangle-1 M2 at video 0:00. Cache tag: **`mmr102`**. PR: https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/66

No clip in the feed = no clip. Do not invent Race 2 start or extra races.

No Whisper/STT on the VM. Do not treat assumed offsets as heard guns unless a video time was given.

---

## Still the issue

None of the Event Reels race clips are unlockable. Remaining work is optional ear-check of stamp-assumed starts/finishes.

---

## Not issues (do not re-do unless ear-check fails)

**Measured** — leave unless live regresses:

- `1014880974840710` R7 Start — `offsetMs +24200` (gun 15:57:01, STT ~1:36.8)
- `2410502969472697` R7 1st top — `offsetMs -88000` (1st M1 16:10:56 ~0:25)
- `2622643364847262` R7 1st downwind — `offsetMs +36000` (Pin 16:22:43, STT ~3:07)
- `1802153794291569` R3 leeward 1 — `offsetMs -252000` (1st FBYC M2 15:30:25 at video **0:37**)
- `1530770848344300` R3 Downwind 2 — `offsetMs +1524000` (HYC L2 M2 16:16:34 at video **0:10**, FBYC 2nd 16:17:05)
- `1384453329808359` Lipton R2 — `offsetMs 0` (triangle 1 **M2** at **0:00**; WYAC passing 13:45:01, LDYC already leading from 13:42:59)

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
| `1079923421076157` | R4 start | gun 13:55:01 ~3:01 |
| `1582165340314238` | R4 1st windward | L1 M1 WBYC 14:15:19 (pack still rounding) |
| `1588170962712352` | Lipton race4 | L1 M3 WBYC 14:34:51 (pack still rounding) |
| `2111285223132517` | R4 2nd Quad | L2 M1 WBYC 15:00:54 (pack still rounding) |
| `1751846282795149` | R4 Finish | WBYC **15:25:32** horn ~1:32 |

If a horn/rounding is **not** at that video time, send the video time — `offsetMs = gpsEvent − (stamp + videoTimeOfEvent)`.

---

## Mac first actions

1. Open `docs/LIPTON_OVERLAY_MAC_HANDOVER.md` (this file).
2. Optional: ear-check stamp-assumed starts/finishes only.
3. Optional: ear-check assumed starts/finishes (R5/R4/R3 start, R4/R2 finish). R7 start needed **+24.2s** after STT — the same trap.
4. Surgical deploy only: overlay JS both paths, race JSON under `/js/`, cache tag in live `api.py`, restart `sailingsa-api`. **Do not overwrite live `api.py` wholesale.**

Live page: https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup
