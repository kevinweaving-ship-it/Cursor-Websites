# Chat handoff: class URLs, Regatta 385 Optimist A/B, race vs family classes

Use this doc when starting a **new chat** to continue work. One agent was crashing; this summarizes what’s done and what’s next.

---

## 1. Class URLs and routing (done)

- **Backend:** `/class/{slug}` route: slug-only (e.g. 420) → resolve class_id, 301 to `/class/{class_id}-{slug}`; canonical `{id}-{slug}` (e.g. 7-420) serves SPA. Route order: `/class/{slug}` registered early (after `/sailor/{slug}`) so it runs before any SPA fallback.
- **API:** GET `/api/class/{class_id}` and HEAD `/api/class/{class_id}` return class data; HEAD added so `curl -sI` returns 200.
- **Nginx:** `location ~ ^/class/` proxies to FastAPI so `/class/420` and `/class/7-420` hit the API.
- **Frontend:** In `index.html` (and `public/index.html`), when path matches `/class/(\d+)-`, we call `/api/class/{id}`, render class page (name, stats, regattas, sailors tables), show `#class-view`, hide landing; no fallback to landing.
- **Deploy:** Frontend and api.py deployed; nginx updated and reloaded.
- **Verify:** `/class/420` → 301, `/class/7-420` → 200 and class data renders.

---

## 2. Regatta 385 Optimist A/B fix (partially done, verification odd)

**Goal:** No results rows for HYC Classic 2026 (regatta 385) with generic Optimist; use Optimist A / Optimist B only.

**Done:**

- Class IDs confirmed: Optimist = 1, Optimist A = 62, Optimist B = 63, Optimist C = 103.
- Two UPDATEs run on production (with `regatta_id = '385-2026-hyc-cape-classic'`):
  - Optimist A: UPDATE 10
  - Optimist B: UPDATE 7

**Issue:** After the UPDATEs, verification

```sql
SELECT c.class_name, COUNT(*) FROM results r JOIN classes c ON c.class_id = r.class_id
WHERE r.regatta_id = '385-2026-hyc-cape-classic' GROUP BY c.class_name
```

still shows **Optimist | 17** and no Optimist A/B. So either:

- `results.regatta_id` for those rows is not `'385-2026-hyc-cape-classic'` (e.g. integer 385 or another string), or
- The JOIN to `regatta_blocks` (e.g. `fleet_label = 'Optimist A'` / `'Optimist B'`) didn’t match the same rows we’re counting.

**Next step for new chat:** On production, run the diagnostic query that groups by `r.regatta_id` and `c.class_name` for Optimist / Optimist A / Optimist B to see which `regatta_id` the 17 rows actually have and whether any show as Optimist A/B. Then either correct the UPDATE WHERE (e.g. `regatta_id` type/value) or run a direct UPDATE on the correct regatta_id/block set.

---

## 3. Classes table: race vs family (done in code; schema already on prod)

**Goal:** Only “race” classes (e.g. Optimist A/B/C, Ilca 4.7/6/7) in results; “family” classes (Optimist, ILCA/Laser) aggregate-only, never in results.

**Schema (production):**

- `classes.is_race_class` (BOOLEAN, default TRUE) and `classes.parent_class_id` (INT NULL) already exist.
- Optimist, Ilca/Laser → `is_race_class = FALSE`.
- Optimist A/B/C, Ilca 4.7/6/7 → `is_race_class = TRUE`.
- Parent links: A/B/C → Optimist; Ilca 4.7/6/7 → Ilca/Laser.

**Ingestion:** In `results_ingestion_common.py`, `require_class_id()` now checks `is_race_class`; if FALSE, logs to `ingestion_issues` and raises (hard fail). If `is_race_class` column is missing, it allows (backward compatible).

**Docs:** `docs/README_RESULTS_INGESTION.md` has a “Race class vs family class rule” section: only `is_race_class = TRUE` in results; family classes must never be stored.

---

## 4. Deploy / scripts

- **Deploy:** `bash sailingsa/deploy/deploy-with-key.sh` (frontend zip + API restart). api.py is uploaded separately (e.g. scp api.py; restart) when backend changes.
- **Nginx class proxy:** `sailingsa/deploy/fix-nginx-class.sh` adds `location ~ ^/class/`; run on server (or via SSH) then reload nginx.
- **DB:** Production Postgres: `psql postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master` (no `!` in password; server = 102.218.215.253, key `~/.ssh/sailingsa_live_key`).
- **Ingestion:** Scripts (e.g. `add_regatta_385_420_fleet.py`) use `results_ingestion_common.require_class_id()`; they run locally against local or remote DB; no deploy of ingestion code to server, only frontend + api.py.

---

## 5. What to do in the new chat

1. **Fix regatta 385:** Run the diagnostic query above, confirm `regatta_id` and block/fleet for the 17 Optimist rows, then correct and re-run the Optimist A/B UPDATEs and re-verify counts.
2. Anything else on class pages, ingestion rules, or deploy can continue from this summary.

---

*Primary deploy/SSH source: `sailingsa/deploy/SSH_LIVE.md`.*
