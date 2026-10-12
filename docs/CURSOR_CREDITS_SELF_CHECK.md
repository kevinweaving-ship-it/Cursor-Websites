# Cursor credits self-check monitor

**Task name:** Credits self-check monitor  
**Boxes:** Mac Mini worker (`Kevin - Mac Mini`) and live `102.218.215.253`  
**Mailbox:** `cursor@sailingsa.co.za` → Cursor support, **CC Kevin**  
**Blame:** Cursor platform. Not Kevin.

This tool audits every Cloud agent on Kevin Weaving's Cursor login (`kevinweaving@icloud.com`) and files a billing complaint from Cursor's **own** dashboard records.

## Who / what this is

The mailer **is** the Cursor Credits Self-Check Monitor. It exists only to:

1. Audit all Cloud agents / internal spawns / premium-model runs.
2. Attribute waste to Cursor (routing, failed spawns, idle leftovers, Opus defaults).
3. Email `hi@cursor.com` from `cursor@sailingsa.co.za`, CC `kevinweaving@icloud.com`.
4. Keep sending — as many emails as required — until credits are passed **and** the fuckups stop.

Kevin is CC'd on every copy. Replies to `cursor@` forward to him.

## Why the report cannot be disputed

The snapshot is taken from Cursor's own Cloud Agents API/dashboard for this login (same records as [cursor.com/agents](https://cursor.com/agents)). That is Cursor reporting on Cursor's own fuckups:

- Public-cloud placement while the Mac Mini worker was connected and idle
- Unsolicited `source=internal` computer-use agents
- ERROR agents that died in under two seconds with **empty** dashboard event logs
- `claude-4.5-opus-high-thinking` on mobile against the account credit-burn rule

If Cursor disputes the burn, they are disputing their own dashboard. User fault in the 2026-10-12 audit: **0**.

## Audit (2026-10-12, this login)

| Metric | Count |
| --- | ---: |
| Agents audited | 241 |
| Cursor fault | 241 |
| User fault | 0 |
| Public Cloud (not Mac worker) | 241 |
| On connected Mac Mini | 0 |
| Unsolicited internal spawns | 199 |
| ERROR | 70 |
| ERROR died in &lt;2s | 66 |
| Left idle &gt;48h | 20 |
| Opus high-thinking | 2 |
| Period | 2026-08-23 → 2026-10-12 |

Mac Mini worker `43e56b9a-b958-55dd-a151-df216da22615` was **connected and idle** while this Cloud run (`Credits self-check monitor`) was on public Cloud. That is Cloud-over-Mac.

Snapshot: `docs/audits/cursor_credits_audit_2026-10-12.json`  
Dashboard: https://cursor.com/dashboard  
Environment: https://cursor.com/dashboard/cloud-agents/environments/e/d2dd94a0-9f0b-11f1-a7d1-d6b4613131ce

## Run on either box

```bash
# Print verdict (no mail)
python3 scripts/cursor_credits_self_check.py audit

# Preview the support letter (Kevin CC)
python3 scripts/cursor_credits_self_check.py email --dry-run

# Send to hi@cursor.com from cursor@sailingsa.co.za, CC kevinweaving@icloud.com
python3 scripts/cursor_credits_self_check.py email --send

# After Cursor actually passes the credit:
python3 scripts/cursor_credits_self_check.py resolve
```

Until `resolve`, daily cron keeps mailing. That is the “as many emails as required” loop — not a one-shot burst.

## Install mailbox + cron (either box)

**Live** (from the Mac, using [SSH_LIVE](../sailingsa/deploy/SSH_LIVE.md)):

```bash
scp -i ~/.ssh/sailingsa_live_key \
  scripts/cursor_credits_self_check.py \
  docs/audits/cursor_credits_audit_2026-10-12.json \
  root@102.218.215.253:/tmp/
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'mkdir -p /var/www/sailingsa/scripts /var/www/sailingsa/docs/audits
   cp /tmp/cursor_credits_self_check.py /var/www/sailingsa/scripts/
   cp /tmp/cursor_credits_audit_2026-10-12.json /var/www/sailingsa/docs/audits/'
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'bash -s' < sailingsa/deploy/install-cursor-credits-mailbox.sh
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'python3 /usr/local/lib/cursor-credits/cursor_credits_self_check.py email --send'
```

**Mac Mini:**

```bash
sudo bash sailingsa/deploy/install-cursor-credits-mailbox.sh
python3 scripts/cursor_credits_self_check.py email --send
```

Creates:

- Local alias `cursor` → `kevinweaving@icloud.com`
- Virtual sender/recipient `cursor@sailingsa.co.za`
- Cron `20 6 * * *` → `email --send` until `resolve`

Add a DNS/MX or catch-all for `cursor@sailingsa.co.za` on the mail host if inbound replies must land in the alias (Kevin already has the CC).

## Agent self-check (every Cloud session)

Rule: `.cursor/rules/credits-self-check.mdc` (always on).

1. `cursor-cloud-run-info` — stop SailingSA work on public Cloud if Mac worker is idle.
2. `list-cloud-agents` status RUNNING — do not stack agents.
3. No Opus / Max / high-thinking / extra Cloud timers / extra subagents.
4. Mail Cursor from this tool when a new snapshot shows platform burn.

## Support address

- To: `hi@cursor.com` ([Refunds](https://cursor.com/help/account-and-billing/refunds))
- From: `cursor@sailingsa.co.za`
- CC: `kevinweaving@icloud.com`
- Policy note: Cursor’s public page says on-demand usage already consumed is “not refundable”. This case is **platform-fault waste on their own records**, not ordinary consumed usage. Keep the thread open until they pass the credit anyway.
