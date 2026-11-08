# Real visitors ▶ sticky across poll updates

**Live:** `patch_real_visitors_toggle_sticky.py`

While any Real visitors (or FB/bots) trail is open, skip full table rebuild on the 3s poll unless the list fingerprint changed. Preserves scroll. Removed one-time wipe of `off:` open keys on page load.

Hard-refresh `/traffic`, open a ▶ trail — it stays open while you read it.
