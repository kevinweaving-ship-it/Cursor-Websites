# Recovery system — output (strict)

## OUTPUT REQUIRED

- **Repo URL:** Not set — create a private repo (GitHub/GitLab/Bitbucket), then run the commands in `RECOVERY_SETUP.md` (add origin, push main, push tag). Put the URL here after.
- **Last commit hash:** `f30111fec8a3c19861ad8ffcaef62237203dc0d5`
- **Tag hash:** `bb3b25d4bc6e9b5a03072ba0127dc78cd2b55f44`
- **Snapshot script exists:** Yes — `tools/snapshot.sh`

## How to recover after a crash (max 5 lines)

1. Create a private remote repo if you haven’t yet; add it as `origin` and push (see `RECOVERY_SETUP.md`).
2. On any machine: `git clone <REPO_URL> <folder>` then `cd <folder>`.
3. Restore the known-good state: `git checkout pre_congrats_parity_restored_2026_02_05`.
4. That single checkout gives you the verified parity state; no IDE required.
5. Optional: run `bash tools/snapshot.sh` from project root for a timestamped zip in `../snapshots/`.
