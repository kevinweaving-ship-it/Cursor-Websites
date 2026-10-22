# Cursor credit burn — what to change

Agents cannot change your plan, model picker, or API keys. Do this on the Mac / dashboard.

**Usage (dollar amounts):** [cursor.com/dashboard/spending](https://cursor.com/dashboard/spending) (legacy Pro/Ultra) or [grok.com/dashboard](https://grok.com/dashboard) (X Subscription). This repo has no billing API.

**This Cloud run’s model:** `cursor-grok-4.6-high-fast` (mobile). That is the expensive default.

## Settings that actually move the bill

1. **Model picker** (biggest lever after plan): Cursor Settings → Models → **Auto** or **Composer 2.5**. Turn off Fast / high effort. Do not pick Grok 4.6 High Fast, Grok 4.7 high, Claude Opus, or Thinking.
2. **Downgrade Ultra → Pro:** [cursor.com/dashboard/billing](https://cursor.com/dashboard/billing). Upgrades are immediate; **downgrades apply at period end**. Legacy Ultra is $200/mo; legacy Pro is $20/mo. Pro still includes Cloud Agents — you must stop launching them or Pro will overage.
3. **Other AI keys (BYOK):** Settings → Models → paste OpenAI / Anthropic / Google / Azure / Bedrock key → Save. On individual plans those requests **do not** draw Cursor included usage; the provider bills you. [Help](https://cursor.com/help/models-and-usage/api-keys). Tab still uses Cursor’s pool.
4. **Cap overages:** Spending tab → disable on-demand or set a monthly spend limit. Otherwise Pro + Cloud + high-fast still invoices at API rates.
5. **Mobile:** do not start Cloud Agents. Use This Mac, Composer, Auto. Close other agent chats first.

## What was eating Cloud usage (281 agents, this environment)

| Slice | Count | Share | Note |
| --- | --- | --- | --- |
| Internal subagents | 227 | 81% | Browser audits, summarize/extract chats — hidden multiplier |
| Mobile Cloud | 30 | 11% | 21 of 30 on `cursor-grok-4.6-high-fast` |
| Desktop Cloud | 22 | 8% | `grok-4.7` (10) and `cursor-grok-4.6-high` (9) |
| Web Cloud | 2 | 1% | `cursor-grok-4.5-high-fast` |
| Claude Opus Thinking | 2 | — | Violates the existing user credit rule |

Last 14 days: 52 Cloud runs, 12 mobile (11 high-fast), 7 desktop (`grok-4.7`), 33 internal. Several user threads stayed open 4–50 days (every follow-up reloads a huge context).

Counts are Cloud Agents only. Desktop Composer / Tab / on-demand $ are only on the Spending tab.

## Existing rules (gap)

- User rule **CREDIT / USAGE BURN** already says cheap models, no Max, no Cloud — Cloud/Mobile still launch `high-fast`.
- `AGENTS.md` points at `.cursor/rules/task-splitting-and-resources.mdc`, but **`.cursor/` was gitignored**, so Cloud agents never saw those files.
- Draft PR #219 (`credits-self-check-monitor`) is a 7k-line email-dispute script, not a burn cut.

## Repo rules this change adds

- `.cursor/rules/credit-burn.mdc` (always apply)
- `.cursor/rules/task-splitting-and-resources.mdc` (always apply)
- `AGENTS.md` short credit section
- `.gitignore` exception so `.cursor/rules/` is committed
