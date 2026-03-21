# Bio insert — backup and restore (https://sailingsa.co.za/)

**Before changing any HTML or frontend for bio insert, back up the live site so you can restore without breaking the whole site.**

---

**After deploying bio or API changes you must restart the API or the bio will not show:**

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
```

Expected: `active`.

---

## 1. Backup (run before bio insert)

From project root:

```bash
bash sailingsa/deploy/backup-live-frontend-before-bio.sh
```

This will:

- Copy `/var/www/sailingsa` on the server to `/root/backups/sailingsa_frontend_BEFORE_BIO_YYYYMMDD_HHMMSS`
- Write a proof file on the server: `/root/backups/PROOF_sailingsa_frontend_BEFORE_BIO_YYYYMMDD_HHMMSS.txt` (file list + checksums of `index.html`, `about.html`)
- Print the **restore command** so you can run it if needed

**Keep the printed backup path and restore command.**

## 2. Restore (if bio insert breaks the site)

Use the **exact** path printed by the backup script. Example (replace `BACKUP_DIR` with the path from the script output):

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 'rm -rf /var/www/sailingsa/* ; cp -a /root/backups/sailingsa_frontend_BEFORE_BIO_YYYYMMDD_HHMMSS/* /var/www/sailingsa/ ; chown -R www-data:www-data /var/www/sailingsa ; systemctl restart sailingsa-api'
```

**Warning:** `rm -rf /var/www/sailingsa/*` removes everything under the web root. The next `cp -a` restores from the backup. Only run this when you intend to restore that backup.

## 3. Verify after restore

- Open https://sailingsa.co.za/ — homepage should load as before.
- Check https://sailingsa.co.za/about if you use it.

---

## 4. Git rollback (local / repo)

So you can restore or roll back code without losing work:

- **Before making edits:** optional local backup of changed files:
  ```bash
  bash sailingsa/deploy/backup-before-commit.sh
  ```
  Creates `backups/pre_commit_YYYYMMDD_HHMMSS/` with copies of modified files.

- **Discard uncommitted changes** (restore files to last committed state):
  ```bash
  git status
  git restore .                    # all tracked files
  git restore path/to/file.html    # one file
  ```

- **Restore from pre-commit backup** (if you ran backup-before-commit.sh):
  Copy files from `backups/pre_commit_YYYYMMDD_HHMMSS/` back over the working tree.

- **Undo last commit but keep changes:**
  ```bash
  git reset --soft HEAD~1
  ```

- **Undo last commit and discard those changes:**
  ```bash
  git reset --hard HEAD~1
  ```
  Use only when you are sure; changes are gone.

---

## 5. After deploying bio (or api) changes: restart API

Restart is required for bio/API changes to take effect on live:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "systemctl restart sailingsa-api && sleep 2 && systemctl is-active sailingsa-api"
```

Expected: `active`. See **`sailingsa/deploy/SSH_LIVE.md`** for full deploy and restart steps.

---

## Reference

- Server: `102.218.215.253`
- Web root: `/var/www/sailingsa`
- SSH: `ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253`
- Full deploy/SSH: **`sailingsa/deploy/SSH_LIVE.md`**
