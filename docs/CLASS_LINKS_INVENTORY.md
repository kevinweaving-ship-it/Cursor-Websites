# Class links inventory – where class names are shown

Every place a **class name** is displayed must be a clickable link to `/class/{class_id}-{slug}` when `class_id` is available.

## Already using classLink / result_class_id (links)

| Location | File | Notes |
|----------|------|--------|
| Regatta result rows (Class column) | index.html, public/index.html | `classCell` with `result_class_id` |
| Regatta result rows (Fleet column) | index.html, public/index.html | `fleetCellHtml` with `result_class_id` |
| Result sheet popup header | index.html, public/index.html | `fleetHeaderHtml` |
| Profile Breakdown by Class (search result) | index.html, public/index.html | `classLink(st.class_id, className)` |
| Profile Main/2nd/… Class chips | index.html, public/index.html | `classLink(cid, cn)` |
| Profile "X Results" section headers | index.html, public/index.html | `classHeaderHtml` |
| Regatta standalone pages | regatta/results.html, regatta/class/class-results.html | `classCell` with `result_class_id` |

## Fixed in this pass (make clickable) ✓

| Location | File | Fix |
|----------|------|-----|
| Profile meta "Classes" line (AGE, CLASSES, PROVINCE…) | index.html, public/index.html | `classesDisplayHtml` → join classLink(classStats[c].class_id, c) |
| Sailor Stats Lite "Breakdown by Class" | index.html, public/index.html | Store class_id in classStats; render with classLink(stats.class_id, className) |
| loadPersonalProfile class boxes (Main Class, 2nd…) | index.html | classIdByClass from results; use classLink in boxes |
| loadPerClassResults "X Results" headers | index.html | classIdByClassPerResults; use classLink in h4 |
| Regatta Fleet column (anchored rows) | regatta/results.html, regatta/class/class-results.html, public copies | fleetCell / fleetCellOpen from first row result_class_id |

## Lower priority / no class_id in payload

| Location | File | Note |
|----------|------|------|
| Search result card "Classes" | index.html | String from API; would need per-class ids in search response |
| Congrats message (className in text) | index.html | Could wrap in link if we pass class_id into template |
| Highlights text "(ClassName)" | index.html | Snippet text; would need class_id in highlight payload |
