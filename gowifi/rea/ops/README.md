# REA ops helpers (managed copy)

Live installs:

- GoWifi helper: `/usr/local/sbin/rea-ops-helper` (ForceCommand from `rea` via localhost SSH)
- GoWifi CLI: `/opt/rea/ops/bin/rea-admin`, `/opt/rea/ops/bin/rea-ops`
- Cupido named correction: `/opt/rea/ops/bin/qb_cupido_oct_correct.py`
- SailingSA entry: SSH `sailingsa-ops` → `/opt/rea-ops/bin/ops-agent` → local sudo helper

Ordinary-work verbs added for GoWifi (still no unrestricted root):

- `qb-fetch`, `qb-customer <key>`, `qb-correct cupido-oct-2026 plan|apply`
- `mail-probe`, `mail-send-probe` (recipient locked to accounts mailbox)
- `github-status`
- existing: `account-*`, `rebuild gowifi-billing`, deploy/backup/nginx/status/…

Gold lock and protected units remain. See `docs/REA_HANDOVER_ACCEPTANCE_20261109.md`.
