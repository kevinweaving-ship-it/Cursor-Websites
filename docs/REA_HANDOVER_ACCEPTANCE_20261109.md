# ACCEPTANCE — REA both-box ordinary-work rights + Cupido Oct correction
Verified: Monday 9 November 2026 (Africa/Johannesburg). Evidence as UID 996 `rea` unless noted.

## Anti-brick / recovery (both boxes)
- VERIFIED: `gold_lock=true`, `general_root_shell=false`
- VERIFIED: `bash` / `exec-b64` / `admin` denied (`denied_unrestricted_shell`)
- VERIFIED: protected units include postgresql, sailingsa-api, nginx, sshd, openai-rea-tunnel, WhatsApp POCs
- VERIFIED: postgresql `can_control=false` / `can_stop=false` on SailingSA
- Backups of helpers: `/root/backups/rea-ops-handover-20261109T110752Z/` and `/root/backups/rea-ops-handover-20261109T111203Z/`

## GoWifi — capabilities as `rea`
| Capability | Verb | Result |
|---|---|---|
| QuickBooks read | `rea-admin gowifi -- qb-fetch` | VERIFIED ok, writes_to_qb=false |
| QuickBooks customer | `rea-admin gowifi -- qb-customer cupido` | VERIFIED |
| QuickBooks write (named) | `rea-admin gowifi -- qb-correct cupido-oct-2026 apply` | VERIFIED |
| Email read (IMAP) | `mail-probe` | VERIFIED openserve@gowifi.co.za INBOX |
| Email send (locked) | `mail-send-probe` | VERIFIED sendmail to same mailbox only |
| GitHub read | `github-status` / `gh status` | VERIFIED HTTPS ls-remote |
| GitHub write | SSH deploy key | **FAILED** — Permission denied (publickey) |
| Database | `rea-ops db-query "select 1 as ok"` | VERIFIED |
| Services | `status nginx`, `preflight gowifi-auth` | VERIFIED |
| Deploy/backup | `backup gowifi-auth` | VERIFIED backup_id created |
| Nginx | `nginx test` | VERIFIED syntax ok |

## SailingSA — capabilities as `rea` via `sailingsa-ops`
| Capability | Verb | Result |
|---|---|---|
| Services | `status sailingsa-api` | VERIFIED active |
| Control gate | `can-control sailingsa-api` | VERIFIED can_control=true, no restart |
| DB | `db-query 'select 1 as ok'` | VERIFIED |
| Nginx | `nginx test` | VERIFIED |
| Backup | `backup sailingsa-ops-stage` | VERIFIED |
| Preflight | `preflight sailingsa-api` | VERIFIED |
| GitHub status | `gh status` | VERIFIED key exists |
| GitHub write | deploy key | **FAILED** — same class of failure; write deploy key not authorized |

## Cupido October correction (authorized write)
- Before: Balance R2477; open invoices 3150(R759)+3137(R959)=R1718; payment 2457 + JE 2473 (R759 float)
- Applied as `rea`: DELETE payment 2457 then DELETE journalentry 2473
- After (independent `qb-customer cupido`): Balance **R2477.0**; open **3125(R759)+3150(R759)+3137(R959)=R2477.0**
- Evidence: `/opt/rea/ops/audit/cupido-oct-correct-20261109.json` (`ok=true`, `post_errors=[]`)

## Remaining failure
1. **GitHub write from either box** — REA ed25519 deploy keys exist but GitHub rejects SSH auth (`Permission denied (publickey)`). HTTPS read works. Add write deploy keys (or enable ChatGPT GitHub connector) for:
   - GoWifi: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIZUbaqtPqcweuv3PR+IO5t+XJH0A8DKpNl81OIhSkNP rea-ops-github@gowifi`
   - SailingSA: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKKpToPKDJLUM1HQ810tF6iPgduZEU4CbvutALEQQf6b rea-ops-github@sailingsa`

## Toolchain note
Section 6 lightweight tool installs (rg/ruff/etc.) were not the blocking path for the rights + Cupido task; ordinary-work verbs above are live. Toolchain pin/ACCEPTANCE rows for those CLIs remain deferred if not already present under `/opt/rea/tools/`.
