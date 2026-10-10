# PRODUCTION OPERATING RULES (MANDATORY)

1. This project runs LIVE on this server.
2. All changes are assumed to affect production.
3. SSH context is persistent and authoritative.
4. NEVER restore from backup unless explicitly instructed. The **only** allowed restore is `/root/backups/API_MASTER_GOLD/api.py` (`docs/API_MASTER_GOLD.md`).
5. NEVER replace live api.py with this GitHub repo’s `api.py` (~1.4MB, old EVENTS/SAILORS club layout).
6. Do not write dated `api.py.*` backups on the box. Master/Gold is the only snapshot.
7. If unsure: read-only first, never edit first.
8. No local assumptions. Confirm working directory before any change.

---

## Force Cursor To Confirm Context

Before ANY edit, Cursor must run:

```bash
pwd
ls -l /var/www/sailingsa/api/api.py
wc -l /var/www/sailingsa/api/api.py
```

If that is not run first → no edit.

This forces awareness.

---

## LIVE EDIT PROTOCOL (Permanent)

Every time before editing `/var/www/sailingsa/api/api.py` on PROD, follow this sequence.

### 1. READ-ONLY FIRST (mandatory)

```bash
pwd
ls -l /var/www/sailingsa/api/api.py
wc -l /var/www/sailingsa/api/api.py
```

**If this is not shown → no edit.**

### 2. SNAPSHOT (mandatory)

Do **not** write dated `api.py.*.bak` next to live or under `/root/backups/api.py.TIMESTAMP`. Those copies became restore bait and were deleted.

The only allowed snapshot/restore is Master/Gold:

```bash
ls -l /root/backups/API_MASTER_GOLD/api.py
sha256sum /root/backups/API_MASTER_GOLD/api.py
# must be 9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b
```

See **`docs/API_MASTER_GOLD.md`**.

### 3. EDIT

```bash
chattr -i /var/www/sailingsa/api/api.py
```

Make change.

Then:

```bash
chattr +i /var/www/sailingsa/api/api.py
systemctl restart sailingsa-api
systemctl is-active sailingsa-api
```

### 4. VERIFY CHANGE (mandatory)

Example:

```bash
sed -n '1350,1375p' /var/www/sailingsa/api/api.py
```

Must show the inserted block (adjust line range to your edit).

**No verification → change invalid.**

---

## Deploy api.py from local (upload) — LOCKED

**Do not upload this GitHub repo’s `api.py`.** Live is Master/Gold only. See **`docs/API_MASTER_GOLD.md`**.

If live is damaged, restore Master/Gold — do not `scp` project-root `api.py` and do not write dated `api.py.*` backups (those became restore bait):

```bash
chattr -i /var/www/sailingsa/api/api.py || true
cp /root/backups/API_MASTER_GOLD/api.py /var/www/sailingsa/api/api.py
chown www-data:www-data /var/www/sailingsa/api/api.py
systemctl restart sailingsa-api
```

**Proof** (must paste outputs):

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "grep -n \"var classesSortKey = 'no'\" /var/www/sailingsa/api/api.py; grep -n \"var classesSortAsc = false\" /var/www/sailingsa/api/api.py; grep -n \"ROW_NUMBER() OVER (ORDER BY sailor_count DESC\" /var/www/sailingsa/api/api.py; ls -l /var/www/sailingsa/api/api.py"
```

**Cache-bust test:** Open `/admin/dashboard?v=classes_no_1` (use a new value each deploy, e.g. `?v=classes_no_2` next time).

---

## Admin dashboard — Dashboard V3 only (mandatory)

**We only work on https://sailingsa.co.za/admin/dashboard-v3.** No other page or route may be changed without the user’s explicit consent.

- **Only in scope:** The page served at `/admin/dashboard-v3` and the code that produces it (e.g. route `admin_dashboard_v3`, and any assets/logic used only by that page).
- **Out of scope unless user agrees:** `/`, `/admin/dashboard`, `/admin/dashboard-v2`, and all other routes and pages.

---

### Alternative: incoming + deploy script (one-time setup then two commands)

**One-time on server** (SSH in, or one-off):

```bash
# Install script (from project root, or copy sailingsa/deploy/deploy_api.sh content to server)
scp -i ~/.ssh/sailingsa_live_key sailingsa/deploy/deploy_api.sh root@102.218.215.253:/root/deploy_api.sh
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 "chmod +x /root/deploy_api.sh && mkdir -p /root/incoming"
```

**Do not** `scp` this repo’s `api.py` to `/root/incoming/` or live. `/root/deploy_api.sh` refuses stale/undersized files. Restore Master/Gold only (`docs/API_MASTER_GOLD.md`).

---

### Manual (no script)

Do **not** copy a laptop/repo `api.py` over live. Restore Master/Gold only. Do not write dated `api.py.backup.*` files next to live.

Back on the **server**:

```bash
# 5. Relock + ownership
chown www-data:www-data /var/www/sailingsa/api/api.py
chattr +i /var/www/sailingsa/api/api.py

# 6. Restart
systemctl restart sailingsa-api

# 7. Confirm
systemctl is-active sailingsa-api
```

Expected: `active`.

---

**No restore unless explicitly authorised.**

---

## Why SSH "Memory Loss" Happens

Cursor doesn't have persistent environmental memory.
Each instruction is treated statelessly.

So unless you anchor it with rules in-repo, it will:

- Assume local is source of truth
- Assume replacing is safe
- Assume restore is neutral

That's default AI behaviour.

You must override it structurally.

---

## The Real Fix

You need a simple mental model:

- **PROD server** is the source of truth.
- **Local** is a draft.
- **Baseline** is reference only.
- **Nothing replaces PROD** without explicit intent.

Once that rule is written inside the repo, Cursor stops improvising.

---

## Parser / class strings (mandatory)

- **Keep exact class string from PDF.** Do not normalize or “fix” class names in the parser. Examples: `RS Tera Sport`, `RS Tera Pro`, `RS Tera Sport Plus` are distinct; preserve exactly as in the source.
- **Never auto-convert these to each other or to a single canonical form:**
  - `ILCA 4`
  - `ILCA 4.7`
  - `Laser 4.7`
  - `Laser Radial` / `ILCA 6`
  - `Laser` / `ILCA 7`
- Any mapping or canonicalisation (e.g. `class_canonical`) must be **deliberate** (explicit mapping table or rule), not a blind replace/normalise step.
