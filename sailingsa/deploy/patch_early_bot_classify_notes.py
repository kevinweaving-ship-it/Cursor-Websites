"""Early bot classify — Live is engaged-only; sterile bots quarantined in ~12s.

Live 2026-08-15 on api.py via patch_early_bot_classify.py

Rules:
- Live Guest list: must have scroll/click (no grace flash)
- After open hit with no engage: daemon one-shot sleeps 12s, then if still no
  engage and short trail (≤5 pages) → quarantine no_engage_sterile
- Leave without engage → same classify
- Crawler-cloud IPs: quarantine on touch, skip public session (no live cost)
- Quarantined IPs: further touches ignored for public trail

Does not re-enable lean traffic BG loop / presence middleware BG.
"""
