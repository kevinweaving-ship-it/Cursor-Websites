# Mac vibe setup — Codex daily, Cursor Pro after trial

Kevin vibe-codes only. He does not classify tasks or switch models.
Ultra $200 is not the target. No downgrade until the trial on **This Mac** passes.

**This Cloud Linux pod cannot run the Mac steps.** A Darwin/Mini session executes them.

## Dashboard (Kevin, 22 Oct 2026)

These are **two pools**, not shares of one bill:

| Pool | Used | Meaning |
| --- | --- | --- |
| Cursor Models | **91%** | Grok / Composer / this phone Cloud high-fast path. Almost empty. |
| Other Models | **19%** | Catalog Claude / GLM / GPT. Mostly unused. |
| Reset | **3 November** | Both pools refill with the billing cycle. |
| On-demand | **OFF** | When Cursor Models hits 100%, Cursor Agent **stops** until reset. No overage invoice. |

Staying on Ultra does not add pool. It keeps a $200 line while the 91% pool dies.

## One recommended setup

**Daily Mac:** ChatGPT Codex signed into the existing ChatGPT Pro subscription (desktop app or `codex` CLI in the repo). Default model. Standard speed. No Fast / Ultrafast.

**After-hours phone:** Cursor iOS → My Machines → Kevin - Mac Mini → **Auto**. Rare. On-demand stays OFF.

**After trial:** Ultra → **legacy Pro $20**. Do not click until the trial on Mac passes.

Do **not** buy GLM Coding Plan or MiniMax M Plan. Do **not** Override OpenAI Base URL.

## Compare (why Codex)

| | Codex (ChatGPT Pro, already paid) | GLM Coding Plan | MiniMax M Plan | Catalog GLM 5.3 in Cursor |
| --- | --- | --- | --- | --- |
| Extra monthly | **$0** | from **$18** (Lite) | **$22 / $55 / $132** (Go / Explore / Build) | $0 extra sub; draws **Other Models** at $1.40 / $4.40 per 1M |
| Kevin picks models? | No. Stay on default. | One GLM model; no auto-escalate | One Flash model; no auto-escalate | Yes — forbidden |
| Hard tasks | Codex raises its own reasoning | Same GLM | Same MiniMax | Kevin would tap High/Max |
| SSH / deploy | Mac host; `deploy-with-key.sh` | Only if wired into an extra agent | Custom Cursor URL (global; can break other keys) | Cursor Other Models; still Ultra burn |
| iPhone | Codex Remote (optional). Cursor Pro covers occasional Mini+Auto | No Cursor iPhone custom key | No | Manual Cloud pick; max context |
| Fits “no classify” | **Yes** | Weak | Weak | No |

Catalog GLM would spend the leftover 81% Other Models and still require a picker. After Pro, that pool shrinks. Rejected.

## Pro still covers phone / Mini

Verified against Cursor docs (legacy Pro):

| Need | Pro? | Note |
| --- | --- | --- |
| Cursor iOS | Yes | Legacy Pro, Pro+, Ultra |
| Cloud Agents | Yes | Smaller **Cursor Models** pool than Ultra |
| Auto | Yes | Start does not have Auto; Pro does |
| My Machines (Mini worker) | Yes | Tool calls on Mini; **model loop still bills Cursor** |
| Remote Control | Yes | Legacy Pro with Cloud Agents; Cursor ≥ 3.9.8 |
| Custom MiniMax/GLM from iPhone | **No** | Desktop Chat only on any plan |
| Fast / high-fast Cloud | Works, **do not use** | Would empty Pro in days |

Phone rule after downgrade: Mini + Auto only. Never Cloud. Never Fast. On-demand OFF.

## Monthly cost

**Now (trial, no downgrade):** Ultra **$200** + existing ChatGPT Pro (**$100 / $200 / $500**, tier not in the dashboard text) + **$0** GLM + **$0** MiniMax.

**After trial passes:** legacy Pro **$20** + same ChatGPT Pro. Save **$180 / month** vs Ultra. No new SKUs.

ChatGPT Pro: no 5-hour local cap; weekly limits apply; Fast = **2.5×** included usage — leave Standard. Do not buy extra ChatGPT credits for the trial.

## Limits the setup enforces

- Codex: default model, Standard speed, **2 strikes** then stop (this repo `AGENTS.md`).
- Cursor: on-demand **OFF** (already). After Pro, Auto only on Mini.
- No Cursor Cloud for SailingSA. No parallel subagents.
- Deploy only with `bash sailingsa/deploy/deploy-with-key.sh` when the user asked for live in that message.

## Trial (Codex alone — this Ultra Cloud agent does not supervise)

On **This Mac**, Codex does the gate, then one already-authorised live change:

1. `uname` is Darwin.
2. `codex` is signed into **ChatGPT** (not an API key). `/status` shows Pro.
3. `bash sailingsa/deploy/codex-mac-trial-gate.sh` — SSH key works; `https://sailingsa.co.za/blank.html` returns 200.
4. One change Kevin already authorised in that Mac chat. Codex edits, deploys with `deploy-with-key.sh` if live was requested, checks the live URL.
5. Same fix fails twice → stop. No model picker. No Cursor Cloud. No this agent.

Pass = gate green + that task finished + live URL matches. Then Kevin may click Ultra → Pro at [cursor.com/dashboard/billing](https://cursor.com/dashboard/billing) (takes effect at period end).

## Reversible

Repo files: `AGENTS.md`, `.cursor/rules/credit-burn.mdc`, this doc, `sailingsa/deploy/codex-mac-trial-gate.sh`. Revert the PR to undo.

Mac-only (not done from Cloud): Codex ChatGPT login, Cursor leftover chats closed. No GLM/MiniMax keys to remove if we never add them.
