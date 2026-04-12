# Congratulations Message — How It Works

This doc describes how the **Congratulations** (and related) messages work so you can recreate or change the behaviour later.

**Example output:**  
*Congratulations 🎉 on your **1st Place** 🥇 in **Optimist A** at **SA Youth Nationals Dec 2025** - Hermanus Yacht Club (HYC)*

---

## 1. Where it lives

| What | Where |
|------|--------|
| HTML container | `sailingsa/frontend/index.html` — `#congratulations-section` inside `#sailor-view` (signed-in view) |
| Logic | Same file — function `loadCongratulations(sasId)` (~lines 3095–3255) |
| Trigger | Called from `updatePageContent()` when the user is signed in and has a SAS ID (~line 3012) |

---

## 2. When it runs

1. User is **signed in** and has a **SAS ID** in session.
2. `updatePageContent()` runs (e.g. after login or page load).
3. It calls `await loadCongratulations(sasId)`.
4. `loadCongratulations` fetches the sailor’s results, picks the **most recent regatta** (see below), then fills `#congratulations-section` or hides it.

So: **only for signed-in users**, and only after the “sailor view” is shown.

---

## 3. Data source

- **API:** `GET ${API_BASE}/api/member/${sasId}/results`
- **Backend:** `api.py` — route `GET /api/member/{sa_id}/results` (e.g. ~line 666).
- **Response shape:** `{ results: [ ... ] }` where each item has at least:
  - `event_name` — regatta name
  - `rank` — number or string (e.g. 1, "1", "2")
  - `class_canonical` / `class_original` — class name
  - `club` — club code (e.g. HYC)
  - `club_fullname` — full club name (e.g. Hermanus Yacht Club)
  - `start_date` / `end_date` — for sorting
  - `entries` — fleet size (for “top 50%” logic)
  - `is_series` or regatta_number / event_name used to detect series

---

## 4. How the “current” result is chosen

1. **Filter out series**  
   Drops rows where:  
   `is_series === true` or `regatta_number === 'S'` or `event_name` contains "Series" and "> Overall".

2. **Sort by date**  
   By `end_date` (fallback `start_date`) **descending** — most recent first.

3. **Take the first**  
   The congratulations message is built from this single “most recent regatta” result.

So the message is always for the **most recent non-series regatta** in the member results.

---

## 5. Message rules (placement → text)

From that one result we derive:

- **Rank:** parsed from `rank` (number or leading digits of string).
- **Position text:** 1st, 2nd, 3rd, 4th, … (function `getPositionText(rank)` in the same block).
- **Placement category:**
  - **Podium:** rank 1–3 → “Congratulations 🎉” + medal (🥇🥈🥉).
  - **Top 50%:** rank 4 up to `ceil(entries/2)` → “Well Done 👏”.
  - **Bottom 50%:** below that → “Keep Sailing ⛵”.

**Podium line (what you asked about):**  
*“Congratulations 🎉 on your **&lt;position&gt; Place** &lt;medal&gt; in **&lt;class&gt;** at **&lt;regatta&gt;** - &lt;club display&gt;”*

Club display: `"Club Full Name (Code)"` if `club_fullname` exists, else just `club` (code).

---

## 6. HTML structure (after JS runs)

The script sets `#congratulations-section` innerHTML to a single block, e.g.:

```html
<div style="display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem;">
  <h2 style="...">Congratulations <span>🎉</span></h2>
  <span style="...">on your <strong>1st Place</strong> 🥇 in <strong>Optimist A</strong> at <strong>SA Youth Nationals Dec 2025</strong> - Hermanus Yacht Club (HYC)</span>
</div>
```

If there’s no valid result to show, the section is hidden: `congratsSection.style.display = 'none'`.

---

## 7. Quick reference for reuse

- **Container ID:** `congratulations-section`
- **Function:** `loadCongratulations(sasId)` (global on `window`)
- **API:** `GET /api/member/{sasId}/results` → use `results[]`, filter non-series, sort by `end_date` desc, take first.
- **Fields used:** `rank`, `event_name`, `class_canonical` or `class_original`, `club`, `club_fullname`, `entries`, `start_date`, `end_date`, and series detection.
- **Podium format:**  
  `Congratulations 🎉 on your X Place [medal] in Class at Regatta - Club (Code)`  
  with 1st→🥇, 2nd→🥈, 3rd→🥉.

Store this README with the frontend so you can reopen the code later and recreate or adjust the behaviour without guessing.
