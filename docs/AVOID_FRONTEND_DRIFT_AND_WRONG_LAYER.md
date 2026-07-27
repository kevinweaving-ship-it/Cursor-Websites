# Avoid frontend drift and fixing the wrong layer

**Read this when:** "still broken", "fix local", sailor profile regatta click, "Failed to load regatta data", or any bug that might be backend/DB vs frontend.

## Do NOT do this in future

1. **Do not add local-only frontend changes that diverge from LIVE**
   - Do not change z-index, popup hiding, API_BASE logic, base tags, or error messages in the frontend **unless** the same change is intended for live and you are aligning with a stated requirement.
   - If the user says "fix local" or "match live", **revert** local-only frontend edits so local matches live. Do not add "fixes" that only exist on local.

2. **Do not "fix" the frontend when the failure is backend or data**
   - "Failed to load regatta data" / 404 on `/api/regatta/{id}`: first **diagnose** whether the API is running, whether the SQL returns 200, and whether the regatta_id exists in the DB. Fix the backend (e.g. SQL type mismatch in `api.py`) or data/DB alignment. Do not add parent.API_BASE, base tags, or new error copy in the frontend as the primary fix.
   - If LIVE works with the same frontend code, the problem is **environment or data** (local API, local DB, port, regatta_id in DB). Fix that layer; do not change the frontend to "work around" it.

3. **Match live first**
   - When the user reports that something works on live but not local, compare LIVE vs LOCAL (e.g. `sailingsa/deploy/read-live-index.exp`, diagnosis docs). Identify the **exact** difference. If the fix is "make local match live", revert or align code to live; do not add new local-only logic.

## Do this instead

- **Diagnose before changing:** Confirm which layer is wrong (frontend, API, DB, or data). Use curl for the API, SQL for the DB, and compare with live.
- **One layer at a time:** If the error is backend (500 SQL, 404 regatta not found), fix backend only. Do not touch the frontend "to be safe".
- **Keep frontend aligned with live** unless the user explicitly asks for a new frontend feature or a change that will be deployed to live.

## Reference

- Backend regatta endpoint: `GET /api/regatta/{regatta_id}` in `api.py` (`api_regatta`). SQL type mismatches (e.g. COALESCE timestamp vs text) → fix in `api.py` with casts.
- Local DB may use string `regatta_id` (e.g. `385-2026-hyc-cape-classic`); 404 "Regatta not found" is data/DB alignment, not a frontend bug.
- **`sailingsa/deploy/SSH_LIVE.md`** for deploy and live; **`sailingsa/deploy/DIAGNOSIS_LIVE_VS_LOCAL_REGATTA_CLICK.md`** for the regatta click flow.
