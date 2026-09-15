# Live jobs: do not fill the disk

**Full rule:** [`docs/NO_DISK_FILL_HEADLESS.md`](../../docs/NO_DISK_FILL_HEADLESS.md)

Any new Chrome / scrape / watcher / PDF-print script in this folder must:

- use `ssa_headless_chrome.py` and **delete the folder after every run**
- set HOME **and TMPDIR** inside that folder
- run frequent timers **only while the event is active**

Leaving Chrome leftovers in `/tmp` has already taken the site down twice.
