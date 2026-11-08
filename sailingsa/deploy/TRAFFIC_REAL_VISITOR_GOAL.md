# Traffic end-state (product)

## Real visitors (primary)
- **All** real visitors since reset — none hidden if they scrolled/clicked
- Full page trail per visitor (sailors, clubs, events, regattas, boats, home…)
- Staff included when they engage (labelled Staff)
- Live strip: engaged only

## Facebook share crawls (secondary)
- Separate section: confirmation that Meta fetched a URL you posted
- Not counted as real visitors

## Other bots
- Collapsed / ignore — quarantine once, no further resource cost

## Reset
- Watermark: `/var/tmp/sailingsa_traffic_real_since`
- Rewrite that file (ISO timestamptz) and restart API to reset the real list window

## Live evaluate flow (30s)

1. **New visitor** → appears on Live (evaluating)
2. **Scroll/click** → confirmed real → stays on Live until done → Real visitors list (full trail)
3. **Idle 30s, no scroll/click** → **bot final** → quarantine (`bot_final_idle_30s`) → ignore (no more resources)
4. Crawler-cloud / Meta ranges → quarantine immediately (never Live as visitor)
