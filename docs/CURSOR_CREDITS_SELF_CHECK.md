# Cursor credits self-check monitor

**Task name:** Credits self-check monitor  
**Box:** live `102.218.215.253` (SSH_LIVE). No Mac. Auto-install + auto-send.  
**Mailbox:** `cursor@sailingsa.co.za` → Cursor support, **CC Kevin**  
**Blame:** Cursor platform. Not Kevin.

This tool audits every Cloud agent on Kevin Weaving's Cursor login (`kevinweaving@icloud.com`) and files a billing complaint from Cursor's **own** dashboard records.

## Who / what this is

The mailer **is** the Cursor Credits Self-Check Monitor. It exists only to:

1. Audit all Cloud agents / internal spawns / premium-model runs.
2. Attribute waste to Cursor (routing, failed spawns, idle leftovers, Opus defaults).
3. Email `hi@cursor.com` from `cursor@sailingsa.co.za`, **CC `kevinweaving@icloud.com`** — one email per billing month.
4. Wait after filing. Auto-reply only if they reject that month. Do not daily-blast.

Kevin is CC'd on every letter (`msg["Cc"] = kevinweaving@icloud.com`). Apple HCM2 may bounce the iCloud inbox from this VPS; the Cc header still goes to Cursor, and a sent `.eml` is kept on the box.

## Why the report cannot be disputed

The snapshot is taken from Cursor's own Cloud Agents API/dashboard for this login (same records as [cursor.com/agents](https://cursor.com/agents)). That is Cursor reporting on Cursor's own fuckups:

- Public-cloud placement while the Mac Mini worker was connected and idle
- Unsolicited `source=internal` computer-use agents
- ERROR agents that died in under two seconds with **empty** dashboard event logs
- `claude-4.5-opus-high-thinking` on mobile against the account credit-burn rule

If Cursor disputes the burn, they are disputing their own dashboard. User fault in the 2026-10-12 audit: **0**.

## Next fuckup report (not mailed yet)

Queued on this same monitor `bc-01a13244-d4f6-71ba-9fed-f8ab7d7305e1` (public Cloud, Mac idle):

- Required **Cc kevinweaving@icloud.com** was omitted on the August and September `hi@` letters.
- Follow-up burned more Cloud instead of a one-line answer.
- This run is itself Cloud-over-Mac. That is why Kevin needs this tool. It has to stop.

Do not send a new ticket for this. Attach it to the next rejection reply or the next monthly letter.

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

## Auto on live (no Mac)

```bash
python3 sailingsa/deploy/deploy-cursor-credits-live.py
```

That SSHs the live box (SSH_LIVE.md) and installs `cursor@sailingsa.co.za`. There is **no daily outbound cron**. One email per billing month; inbound pipe replies only on rejection.

## One email per month

Each billing month is its own letter and its own ticket. Do not copy October onto August/September.

| Month | Agents in export | Action |
| --- | ---: | --- |
| June 2026 | 0 | No email — cannot invent a refund |
| July 2026 | 0 | No email — cannot invent a refund |
| August 2026 | 53 (from 23 Aug) | Own email — partial month |
| September 2026 | 165 | Own email |
| October 2026 | 23 (since reset) | Already on **T-H16750** — wait |

```bash
# Upload mailer, then file each pending month (skips empty + already-filed)
python3 sailingsa/deploy/deploy-cursor-credits-live.py send-months \
  2026-06 2026-07 2026-08 2026-09 2026-10
```

## Manual on the live box only

```bash
# Print verdict + per-month split (no mail)
python3 sailingsa/scripts/cursor_credits_self_check.py audit

# Preview one month
python3 sailingsa/scripts/cursor_credits_self_check.py email --month 2026-08 --dry-run

# Send that month only from cursor@sailingsa.co.za
python3 sailingsa/scripts/cursor_credits_self_check.py email --month 2026-08 --send

# After Cursor actually passes the credit:
python3 sailingsa/scripts/cursor_credits_self_check.py resolve
```

Default `email --send` (no `--month`) waits if October is already filed on T-H16750.

Every mail includes the full account identity block (login, user id, environment ids, worker/machine ids, repo, dashboard URLs) so Cursor cannot confuse this with another customer.

## Auto-dispute every support reply

Inbound to `cursor@sailingsa.co.za` is piped to:

```bash
python3 sailingsa/scripts/cursor_credits_self_check.py dispute --inbound FILE --send
```

If From is Cursor support (`hi@cursor.com` / `@cursor.com` / `@anysphere.com`):

- **Credit confirmed** (and no refusal language) → mark resolved, stop mailing.
- **Anything else** (policy paste, “on-demand not refundable”, “user launched it”, “not eligible”, “cancel instead”) → **auto-reject** in a reply-all with Kevin CC’d. Point-by-point proof from Cursor’s own dashboard. Same account identity block. Same audit attachment.

Manual test:

```bash
python3 sailingsa/scripts/cursor_credits_self_check.py dispute \
  --inbound docs/audits/cursor_support_refusal_sample.eml --dry-run
```

## Install mailbox + cron (either box)

**Live** (from the Mac, using [SSH_LIVE](../sailingsa/deploy/SSH_LIVE.md)):

```bash
scp -i ~/.ssh/sailingsa_live_key \
  sailingsa/scripts/cursor_credits_self_check.py \
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
python3 sailingsa/scripts/cursor_credits_self_check.py email --send
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
