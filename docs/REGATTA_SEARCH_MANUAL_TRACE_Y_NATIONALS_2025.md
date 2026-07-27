# Regatta Search – Manual Trace: "Y nationals 2025"

## How the backend runs this search

1. **Parse query**  
   `_parse_search_terms_and_year("Y nationals 2025")`  
   - Words: `["Y", "nationals", "2025"]`  
   - `"2025"` is 4 digits and 20xx → **year = 2025**, not a search term  
   - **Terms used for matching:** `["Y", "nationals"]`

2. **Year filter**  
   Only regattas where `start_date`, `end_date`, or `year` is **2025** are considered.

3. **Term matching (AND between terms)**  
   A regatta is returned if **either**:
   - **Path A (results):** It has at least one **result row** where **both** terms match (each term can match any of: class, sail_number, boat_name, club fields, event_name, host_club_name), **or**
   - **Path B (name fallback):** Its **event_name** or **host_club_name** matches **both** terms (substring `LIKE %term%`).

4. **How each term is matched**  
   - **"y"** (stored as lowercase): `LIKE %y%` → any text containing the letter **y**.  
   - **"nationals"**: `LIKE %nationals%` → any text containing the word **nationals**.

So for a regatta to qualify it must be in **2025** and have at least one of:
- A result row where something contains **"y"** and something contains **"nationals"**, or  
- A regatta name/host that contains **"y"** and **"nationals"**.

---

## Why each of the 14 results qualifies

| # | Regatta | Why it qualifies |
|---|---------|------------------|
| 1 | **SA Youth Nationals Dec 2025** | **2025** ✓. **"y"** ✓ (in "**Y**outh" and "National**s**"). **"nationals"** ✓ in event_name. Strong match. |
| 2 | **Stadt 23 Nationals Results** | **2025** ✓. **"y"** ✓: the word "National**s**" contains the letter **y**. **"nationals"** ✓ in event_name. So both terms match on the same regatta/result row. |
| 3 | **Hobie16 Nationals** | **2025** ✓. **"y"** ✓: "Hob**y**" contains **y**. **"nationals"** ✓ in event_name. |
| 4 | **Dart 18 Nationals** | **2025** ✓. **"y"** ✓: "National**s**" contains **y**. **"nationals"** ✓ in event_name. |
| 5 | **L26 Nationals Results** | **2025** ✓. **"y"** ✓: "National**s**" contains **y**. **"nationals"** ✓ in event_name. |
| 6 | **J22 Nationals Results** | **2025** ✓. **"y"** ✓: "National**s**" contains **y**. **"nationals"** ✓ in event_name. |
| 7 | **29er Nationals Results** | **2025** ✓. **"y"** ✓: "29**er**" has no **y**, but "National**s**" does. **"nationals"** ✓ in event_name. |
| 8 | **Hobie Tiger Nationals Final Results** | **2025** ✓. **"y"** ✓: "Hob**y**" or "Tiger" (no y) – "National**s**" has **y**. **"nationals"** ✓ in event_name. |
| 9 | **SA Sailing Youth Nationals - Dabchick ... - 2024** | **2025** ✓ from date filter? No – event is 2024. So this qualifies because **year filter** is applied to regatta dates; if this regatta’s `start_date`/`end_date`/`year` is 2025 it’s in; otherwise it’s 2024 and would only appear if the year filter allows 2024. *If it appears in a "2025" search, then either the regatta has a 2025 date in the DB or the frontend is not sending the year.* **"y"** ✓ (Youth / Nationals). **"nationals"** ✓. |
| 10–14 | **SA Sailing Youth Nationals - ILCA 4 ...**, **Youth Nationals 2024 - 2024** (×3), **SA Sailing Youth Nationals - Optimist A ...** | Same idea: **"y"** from "Youth" or "National**s**"; **"nationals"** in event name. If they appear under a 2025 search, then either they have a 2025 date stored or the year filter is not applied for that request. |

---

## Main takeaway

- **"Y"** is treated as the **letter y**, not the word "Youth".
- So **any** regatta whose name (or a result row) contains the letter **y** and the word **nationals** qualifies.
- The word **"Nationals"** itself contains the letter **y** → every regatta with "Nationals" in the name automatically satisfies the **"y"** term. That’s why you see "Stadt 23 Nationals", "Hobie16 Nationals", "Dart 18 Nationals", etc., even when you meant **Youth** nationals.

So the 14 results qualify because:

1. **Year:** All are 2025 (or, for 2024 events, only if the year filter is not applied for that run).
2. **Term "y":** Matched by the **y** in "National**s**" (and in "**Y**outh" where present).
3. **Term "nationals":** Matched by the word "Nationals" in the regatta name (or in a result row’s event_name / host_club_name).

If the goal is to restrict to **Youth** nationals only, the search logic would need to treat **"Y"** as an abbreviation for **"Youth"** (e.g. term expansion or alias) so that "Y nationals 2025" only matches when "youth" (or "y") appears in the right place, and not just any "y" inside "Nationals".
