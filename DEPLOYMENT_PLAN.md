# DEPLOYMENT PLAN — SAILINGSA.CO.ZA

Controlled beta → V1 production. **Do not deploy until explicitly instructed.**

---

## CORE RULES (NON-NEGOTIABLE)

1. Local project is the **single source of truth**.
2. Production (https://sailingsa.co.za/) is updated **only via full deploys**.
3. **No manual edits on the server.**
4. Every deploy **must be tagged in git**.
5. Database changes must be **additive and migration-based**.
6. **Rollback** must always be possible via git tag.

---

## VERSIONING

| Type   | Tag format              | When created   |
|--------|--------------------------|----------------|
| Beta   | `prod_beta_YYYY_MM_DD`   | Before deploy  |
| V1     | `prod_v1_YYYY_MM_DD`    | Before deploy  |

Tags must exist **before** deployment.

---

## 1. BETA BASE (CONFIRMED)

**Tag used as Beta base:** `pre_congrats_parity_restored_2026_02_05`  
**Commit:** `bb3b25d4bc6e9b5a03072ba0127dc78cd2b55f44`

**Beta deploy tag (create before Friday):** `prod_beta_2026_02_06`  
— Points to the same verified parity state (see below). Created so it exists before deployment.

This is the current verified parity state: sailor search, regatta results, login/logout, province badge, class/fleet results flow.

---

## 2. PROJECT PREPARED FOR PROD_BETA

- **Beta tag created:** `prod_beta_2026_02_06` (points to parity commit `bb3b25d`).
- To deploy beta: checkout `prod_beta_2026_02_06` (or `pre_congrats_parity_restored_2026_02_05`), then follow EXACT DEPLOYMENT STEPS below.

---

## 3. EXACT DEPLOYMENT STEPS (NO ASSUMPTIONS)

**Pre-requisites (local):**

1. Ensure you are on the correct tag:
   ```bash
   git fetch --tags
   git checkout prod_beta_2026_02_06
   ```
2. Confirm no uncommitted changes: `git status` must be clean (or deploy from a machine that has only this tag checked out).

**Step A — Build / package from project root**

3. **Frontend package (full replace):**
   ```bash
   cd sailingsa/frontend
   zip -r ../../sailingsa-frontend.zip . -x "*.DS_Store" -x "__MACOSX" -x "*.BU_*" -x "*.bu_*" -x "*.bak"
   cd ../..
   ```
   Output: `sailingsa-frontend.zip` at project root.

4. **Backend (Node) — list of files/dirs to deploy:**
   - `sailingsa/backend/server.js` (or entry point used in production)
   - `sailingsa/backend/package.json`, `sailingsa/backend/package-lock.json`
   - `sailingsa/backend/routes/` (all files)
   - No `node_modules` from local: install on server with `npm ci` or `npm install --production`.

5. **Backend (Python API) — if production uses `api.py`:**
   - Deploy: `api.py`, `requirements.txt` from project root.
   - On server: create venv, `pip install -r requirements.txt`, run with uvicorn as per current production (e.g. port 8081/8082).

**Step B — On server (https://sailingsa.co.za)**

6. **Backup current live state** (paths depend on your server; adjust names):
   - Backup current web root (e.g. copy to `/var/www/sailingsa.co.za.backup.YYYYMMDD`).
   - Note current git tag/commit if deployed from git: `git describe --tags` or equivalent.

7. **Full replace frontend:**
   - Upload `sailingsa-frontend.zip` to server.
   - Extract to web root **replacing** existing frontend files (e.g. extract to `/var/www/sailingsa.co.za/` or the directory nginx serves for `/`).
   - Do **not** do partial file uploads; replace the entire frontend tree.

8. **Full replace backend (Node):**
   - Upload or pull the backend files listed in step 4 (or deploy from git at `prod_beta_2026_02_06`).
   - On server: `cd <backend_dir> && npm ci` (or `npm install --production`).
   - Restart Node service (e.g. `pm2 restart sailingsa-backend` or systemd equivalent).

9. **Full replace Python API (if used):**
   - Upload `api.py` and `requirements.txt` (or pull from git at tag).
   - On server: venv, `pip install -r requirements.txt`, restart API (e.g. systemd or pm2).

10. **No database changes for beta** unless you have an additive migration script; run only additive migrations if any.

**Step C — Post-deploy verification**

11. Verify in browser (https://sailingsa.co.za/):
    - [ ] Homepage loads
    - [ ] Sailor search
    - [ ] Regatta results
    - [ ] Login / logout
    - [ ] Province badge
    - [ ] Class/Fleet results flow

12. Record deploy in git (if not already):
    - Tag `prod_beta_2026_02_06` must already exist and point to the deployed commit.
    - Optional: add a one-line note in a deploy log (e.g. `DEPLOYS.md`: "2026-02-06 beta: prod_beta_2026_02_06").

---

## 4. ROLLBACK

If beta fails:

1. Checkout previous known-good tag (e.g. last prod tag before beta, or `pre_congrats_parity_restored_2026_02_05`).
2. Repeat the same EXACT DEPLOYMENT STEPS (A–C) using that tag’s tree.
3. No destructive DB changes: rollback is code-only.

---

## 5. BLOCKERS FOR FRIDAY LUNCHTIME BETA

- **Server access:** You need SSH (or equivalent) and correct paths for web root, Node app, and Python API on the host that serves sailingsa.co.za.
- **Env/credentials:** Production `.env` (or equivalent) for Node backend and Python API must be set (DB, OAuth, CORS, etc.); see `sailingsa/backend/DEPLOYMENT_CREDENTIALS.md` and `deploy/prod/.env.example`.
- **Tag on remote:** If you use a remote (e.g. GitHub), push tags so the server can pull: `git push origin prod_beta_2026_02_06`.
- **No re-architect / no auth or route renames:** Plan assumes current stack (frontend + Node backend + optional Python API); no changes to auth flows or route names for beta.

---

## 6. DELTA: BETA → V1 (AFTER BETA VALIDATION)

To be agreed after beta:

- **Content/features:** List missing or incomplete features from beta; implement and test locally.
- **DB:** Any new tables/columns/indexes must be additive and migration-based; no destructive changes.
- **Tag:** Create `prod_v1_YYYY_MM_DD` from the commit that will be deployed for V1 (tag before deploy).
- **Deploy:** Same EXACT DEPLOYMENT STEPS as above, using `prod_v1_YYYY_MM_DD`.
- **Footer / “Beta” marker:** Remove or update to “V1” when going production.

---

## 7. DO NOT (FOR BETA AND V1)

- Re-architect.
- Change auth flows.
- Rename routes.
- Touch production data destructively.

---

**WAIT:** Do **not** deploy until explicitly instructed. This plan only prepares and documents the process.
