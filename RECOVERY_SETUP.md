# Hard recovery + off-device backup

## STEP 1 — Git (done)
- Repo initialised in project root. Branch: `main`.
- Confirm: `test -d .git && git branch --show-current` → `main`.

## STEP 2 — Remote backup (you do this once)

**Choose one:** (a) GitHub  (b) GitLab  (c) Bitbucket

**If GitHub:**
1. Create a **private** repo (e.g. `Project6` or `sailingsa-recovery`). Do **not** add README/license (repo empty).
2. In this project root run:
   ```bash
   git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
   git push -u origin main
   git push origin pre_congrats_parity_restored_2026_02_05
   ```
3. Confirm: `git push` succeeds.

**If GitLab/Bitbucket:** Same idea — create private repo, add `origin`, push `main` and the tag.

## STEP 3 — Checkpoint tag (one-command recovery)

Tag: **`pre_congrats_parity_restored_2026_02_05`**

After you push to remote, push the tag:
```bash
git push origin pre_congrats_parity_restored_2026_02_05
```

**Recovery from crash:** Fresh clone then checkout this tag:
```bash
git clone <REPO_URL> <new_folder>
cd <new_folder>
git checkout pre_congrats_parity_restored_2026_02_05
```
You are now at the verified parity state. No IDE needed.

## STEP 4 — Auto-snapshot (no IDE)

Script: **`tools/snapshot.sh`**

- Zips entire project (excludes .git, node_modules, __pycache__, .zip).
- Filename includes timestamp (e.g. `Project 6_snapshot_20260205_140000.zip`).
- Snapshots stored **outside** project: `../snapshots/` (or set `SNAPSHOT_DIR`).

Run from project root or anywhere:
```bash
bash tools/snapshot.sh
```
Or from project root: `bash "$(pwd)/tools/snapshot.sh"`

## STEP 5 — Protection rules (enforced)

- After **every** verified fix: commit **immediately**, push **immediately**.
- No batch commits. One fix = one commit.
- Keeps remote as source of truth and limits loss to one change.

## STEP 6 — Verify recovery

After remote is set and pushed:
```bash
git clone <REPO_URL> /tmp/recovery_test
cd /tmp/recovery_test
git checkout pre_congrats_parity_restored_2026_02_05
# Confirm project loads (e.g. open sailingsa/frontend/index.html or run app).
```

---

**Repo URL:** *(fill after you create the repo and add origin)*  
**Last commit hash:** `git rev-parse HEAD`  
**Tag hash:** `git rev-parse pre_congrats_parity_restored_2026_02_05`

**Recover after a crash:** Clone the repo, then `git checkout pre_congrats_parity_restored_2026_02_05`. That single checkout restores the known-good parity state.
