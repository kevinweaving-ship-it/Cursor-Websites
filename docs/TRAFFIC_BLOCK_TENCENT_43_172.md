# Tencent 43.172 swarm block (2026-10-22)

**Confirmed:** `43.172.197.x` (and neighbours `.194–.198`) = **AS132203 Tencent Cloud**, Singapore.

## Behaviour
- Many distinct IPs, 1–5 hits each
- Deep links to `/regatta/…` and `/sailor/…` (no home land)
- Spoofed desktop Chrome UAs; sparse/fake `clicked` tokens
- ~290 IPs / ~531 hits in 7 days on `43.172.*`

## Gap
API already had Tencent `43.128.0.0/14` — that does **not** cover `43.172`.

## Block applied (live)
1. **nginx** `deny 43.172.0.0/16` in `/etc/nginx/snippets/sailingsa-swarm-deny.conf`
2. **API** `_KNOWN_SCANNER_NETS` + `_lean_cloud_nets` include `43.172.0.0/16`
3. **Quarantine** ~371 IPs `reason=tencent_43_172_swarm`

Scripts: `sailingsa/deploy/patch_block_tencent_43_172.py`, `_remote_apply_tencent_43_172.py`
