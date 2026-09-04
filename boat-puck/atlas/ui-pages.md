# Boat Atlas — UI pages (4.2" RLCD 300×400)

Portrait **300×400** mono (ST7305). Design for **sun + big digits**, not dense dashboards.

## Layout rules

- One job per page; max **2 primary metrics** + 1 status line.  
- Primary digit height target: **≥48–72 px** (stretch toward Atlas’s “huge digit” feel).  
- Top status strip (always): **FIX · LoRa · Batt · Race state**.  
- No colour dependency — use invert / bar / LED for alerts (OCS = full invert + LED red).  
- Prototype on Waveshare board with **LVGL**.

---

## v1 pages (must ship)

| # | Page | Shows | Atlas 2 equivalent |
|---|------|-------|---------------------|
| 1 | **Start** | Countdown · DTL · TTL/burn | Distance/time-to-line + timer |
| 2 | **Speed** | SOG · heading · heel | Velocity / heading / heel |
| 3 | **Line** | DTL big · bow offset hint | Start line focus |
| 4 | **Race** | OCS/clear · gun sync · FIX quality | RaceSense sailor status |
| 5 | **Shift** | Heading vs mean · shift ° | Shift tracking |
| 6 | **Timer** | Countdown only (class-simple) | Countdown |

## v1.1 pages

| # | Page | Notes |
|---|------|-------|
| 7 | **VMG** | Needs wind later or app-set TWD |
| 8 | **Strip** | Mini history of heading/SOG (mono bars) |
| 9 | **Setup** | Bow offset, boat ID, LED mode (or BLE app only) |

## Always-on LED modes (mirror Atlas LED array lite)

| Mode | Behaviour |
|------|-----------|
| Timer | Flash/count toward gun |
| DTL | Colour/pace by distance bands |
| Heel | Warn past threshold |
| OCS | Solid alert until clear |
| Off | — |

---

## Start page wire (ASCII)

```
┌──────────────────── 300 ────────────────────┐
│ FIX● LoRa●  85%   SYNC●            status   │
│                                             │
│              3:42                           │  countdown
│                                             │
│         DTL  12.4 m                         │  primary
│         TTL   0:08                          │  secondary
│                                             │
│  [A page]  [B gun]  [C mark]                │
└─────────────────────────────── 400 ─────────┘
```

OCS: invert whole content area + LED; show **OCS** until Race Control / geometry clears.
