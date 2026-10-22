# Tencent 43.172/15 swarm block (2026-10-22)

**Confirmed:** `43.172.*` and spillover `43.173.*` = **AS132203 Tencent Cloud**, Singapore.

## Behaviour
- Many distinct IPs, 1–5 hits each
- Deep links to `/regatta/…` and `/sailor/…` (no home land)
- Spoofed desktop Chrome UAs; sparse/fake `clicked` / long fake session clocks
- First block was `/16` only — swarm immediately continued on `43.173.*` as fake “guest”

## Gap
API already had Tencent `43.128.0.0/14` — that does **not** cover `43.172`/`43.173`.

## Block applied (live)
1. **iptables** `DROP` `43.172.0.0/15` (covers `.172` + `.173`; persisted)
2. **nginx** `deny 43.172.0.0/15`
3. **API** `_KNOWN_SCANNER_NETS` + `_lean_cloud_nets` include `43.172.0.0/15`
4. **Quarantine** ~1385 IPs; purge `public_sessions` for that range so Live guests clear

Scripts: `sailingsa/deploy/patch_block_tencent_43_172.py`, `_remote_expand_tencent_43_172_15.py`
