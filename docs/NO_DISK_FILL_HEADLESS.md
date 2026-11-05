# HARD RULE — do not fill the live disk again

**Read this before any new scrape, Chrome, PDF-print, watcher, timer, or “peek at a page” job.**

Live is a **77 GB** VPS. Disk 100% → Postgres recovery → **no logins, site down**. This already happened **twice** (Sep 2026) from headless Chrome leftovers. That is not allowed to happen again.

## What went wrong

Headless Chrome was used to check “is MM live?”. Each check left a full browser folder in `/tmp`. The script never binned it. A 5-second timer made thousands of folders (~42 GB). PDF Chrome had a temp folder but **did not set TMPDIR**, so Chrome still dumped `/tmp/.com.google.Chrome.*`.

A “not live” check does **not** need to keep anything. The check only turns the live card on. Historical Chrome pages have **zero** value.

## Mandatory for NEW code (and edits to old jobs)

1. **Do not** launch Chrome / Chromium / Puppeteer / Playwright / Selenium on live unless there is no other way (prefer Graph/API).
2. **If you must use a headless browser:**
   - Use **`sailingsa/deploy/ssa_headless_chrome.py`**: `make_chrome_run_dir()`, `chrome_env()`, `delete_chrome_run_dir()` in a `finally`.
   - Set **HOME, TMPDIR, TMP, TEMP, XDG_*** inside that folder (the helper does this). Missing TMPDIR **will** leak into `/tmp`.
   - **Bin the folder after every run** — live or not live, success or fail. No historical Chrome profiles.
   - One reused dir is only OK if you still delete cache on a schedule; default is **create → use → delete**.
3. **Do not** poll every few seconds **except while the event is active**. Use an event date window (see `mm_fb_event_window.py`). Past/upcoming = timers **off**.
4. **Do not** write unbounded caches under `/tmp`, `/tmp/.cache`, or Chrome `scoped_dir*`.
5. **Do not** ship a systemd timer that can grow forever (no cap, no delete, no event stop).
6. **Do not** spawn many Chrome processes on this 2-vCPU box. One at a time, flocked.
7. After adding any such job: confirm `df -h /` still has headroom and leftover Chrome dir count is **0**.

Existing live jobs: MM Facebook peek (`mm_fb_fetch_cape.py`) and results PDF (`regatta_stored_pdf.py`). Sweeper: `ssa-chrome-reaper.timer` (every 15 min). **The reaper is a backstop, not permission to leak.**

LibreOffice `--headless` is not Chrome; still do not leave huge convert dirs behind.

## If you are about to add a watcher

Ask: does this need to run when no event is live? If no → **do not enable the timer**.  
Ask: does a “no” result need a file on disk? If no → **delete everything from that check**.
