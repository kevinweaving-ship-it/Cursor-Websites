# API Master / Gold — the only live api.py

**Created:** 2026-10-10

Live club pages (pennant, Founded, weather, camera — e.g. `/club/hyc`) are served by the **production** `api.py` on the box, not by this GitHub repo.

This repo’s `api.py` (~1.4MB) is an old copy. Deploying it overwrites gold and brings back the 4–5 month EVENTS / SAILORS club layout.

## The only allowed file

| | |
|---|---|
| Live | `/var/www/sailingsa/api/api.py` |
| Master/Gold | `/root/backups/API_MASTER_GOLD/api.py` |
| Alias | `/root/backups/api.py.MASTER_GOLD` |
| sha256 | `9c1eea9a2bebfd02125c8eb5c133b776fd0cf06ca67e066a09a293f77857d32b` |
| Bytes | `3953427` |

There is **no** other restore. Dated `api.py.bak`, `/root/incoming/api.py`, GitHub `main`, and `api/api.py` are not options. Those copies were deleted from the live box (532 files) so they cannot be used again.

## Restore (only this)

```bash
chattr -i /var/www/sailingsa/api/api.py || true
cp /root/backups/API_MASTER_GOLD/api.py /var/www/sailingsa/api/api.py
chown www-data:www-data /var/www/sailingsa/api/api.py
systemctl restart sailingsa-api
```

## Hard lock

- Server: `/root/deploy_api.sh` and `/root/deploy_api_verified.sh` refuse any incoming file that is not this exact hash (or is under 3 900 000 bytes). A fake 3.9MB file is also refused.
- Repo: `sailingsa/deploy/refuse_stale_local_api.sh` — every deploy script that used to `scp` this repo’s `api.py` must call it first.
- Do **not** `scp` this repo’s `api.py` onto live. Do **not** create dated `api.py.*` backups next to live (those became restore bait).

## HMYC / Dev work

Dev URLs must be a **new file or thin route** added beside gold. Never replace `/var/www/sailingsa/api/api.py` with this repo.
