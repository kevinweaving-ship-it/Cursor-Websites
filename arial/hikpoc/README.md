# Voëlklip hikpoc (clips / WA card stills)

Alarm WhatsApp cards and `/voelklip/clip/` replay need the **ring recorder** writing
`/opt/hikpoc/out/ring/{garage,workshop,pool,driveway}/*.mkv`.

Live go2rtc can still show frames while the ring is empty — they are separate
`bridge_cam.py` processes sharing `/opt/hikpoc/.session_cache.json`.

## Failure mode (2026-10-28)

- Hik-Connect returned **401 Unauthorized** to ring `bridge_cam` workers.
- `bridge_cam.py` only re-logged in once (`from_cache`); later 401s looped forever.
- Ring dirs emptied → `/voelklip/hik/clip` → `footage no longer available`.
- WA cards rendered black tiles with **no image** (`card.fetch_snaps` got no stills).

## Fix

1. Clear stale session if stuck: `rm -f /opt/hikpoc/.session_cache.json`
2. `systemctl restart hikpoc-ring`
3. Apply `patch_bridge_cam_401_relogin.py` so every 401 forces `fresh_login`.

Verify:

```bash
ls /opt/hikpoc/out/ring/garage | tail
curl -sS "https://aerialnet.co.za/voelklip/hik/clip?cam=garage&t=$(date +%s)&pre=5&post=5" -o /tmp/t.mp4 -w "%{http_code} %{size_download}\n"
curl -sS "https://aerialnet.co.za/voelklip/hik/snaps.json?max_age=60" | python3 -c 'import sys,json;d=json.load(sys.stdin);print([k for k in d if not str(k).startswith("_")])'
```

Past events during the outage cannot be reconstructed — ring retention only covers
what was recorded.
