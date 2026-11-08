# Mac cost cut — Codex baseline, OpenCode evaluated

Kevin vibe-codes only. One natural-language workflow. No model picker.
No purchases. No downgrade until a Mac trial passes.
This Cloud Linux pod cannot sign into Codex, buy GLM/MiniMax, or expose a phone-reachable OpenCode host.

## Dashboard (Kevin, 22 Oct 2026) — overflow corrected

Two monthly pools. Reset **3 November**. On-demand **OFF**.

| Pool | Used | Rule |
| --- | --- | --- |
| Cursor Models | **91%** | Composer / Grok (including this phone Cloud **high-fast**). |
| Other Models | **19%** | Catalog third-party at API list price. |

**Overflow (dashboard + Cursor staff, Jul 2026):** when Cursor Models hits 100%, further Composer/Grok usage **rolls into the Other Models quota**. Other Models overflow goes to **on-demand only**. On-demand is OFF, so the hard stop is **after Other Models is also empty**, not at Cursor Models 100%.

Remaining Other Models (~81%) is now the overflow tank for the same expensive Cursor models. It is not spare “cheap GLM room” unless someone picks GLM.

**Mini / My Machines does not cut inference.** Tool calls run on the Mini; the **selected model** still bills Cursor at that model’s rate (Fast and max-context still multiply). Location ≠ cheaper tokens. Cursor CLI on Linux is the same: still Cursor usage.

## Escalation — verified, not promised

| Product | What is verified | What is not |
| --- | --- | --- |
| **Codex desktop “Default”** | Official: Default **combines models and reasoning levels on one slider**. Leave Default; do not pick a named model. Codex **keeps** a model you picked manually. CLI **has no slider**. | No published “hard task → named bigger model” router. Community still asking for that (Sep 2026). |
| **OpenCode stock** | Pin **one** default in `opencode.json`. Phone/Mac browser talks to that server. Keys live on the **server**, so Cursor iPhone custom-key limits do not apply. | `/models` is **manual**. Stock OpenCode does **not** escalate by task difficulty. Plugins that fail over on 429 or by “category” need classification or extra spend — out of spec. |
| **Cursor Auto (individual Ultra)** | Auto still picks a model. Individual plans do **not** get Teams Router Cost/Balance/Intelligence. | Not a verified hard-task escalate. Mini+Auto still bills the routed Cursor model. |
| **GLM / MiniMax alone** | One subscription model. | No difficulty escalate. |

The only **verified** hands-off combine-models path is **Codex desktop Default**. Use that, not CLI-without-Default, if Kevin must not switch models.

## Compare completed-task cost, retries, allowance, phone

Published rates, not Kevin’s invoice. One small Mac edit ≈ 0.05–0.2M tokens (order-of-magnitude).

| | Extra $/mo | $ / completed small task | Retries | Allowance | Phone |
| --- | --- | --- | --- | --- | --- |
| **Codex Default** (ChatGPT Pro, already paid) | **$0** | **$0** extra (uses included). Fast = **2.5×** allowance — leave Standard. | Repo 2-strike. Default may spend more reasoning on the same turn (that is the escalate cost). | ChatGPT Pro weekly; **tier $100/$200/$500 unread**. No 5-hour local cap. **Not measured** against his Ultra-sized month. | ChatGPT iOS **Remote** to the Mac, or Codex Cloud (separate, still ChatGPT allowance). Authenticated. |
| **OpenCode on a server + GLM Coding Plan** | from **$18** Lite (2k/5h, 10k/week). Pro 12k/5h, 60k/week. Max 28k/5h, 140k/week. Exact Pro/Max $ not on the public overview. | **$0** Cursor. GLM credits. Catalog GLM in Cursor is different: **$1.40 / $4.40** per 1M from Other Models. | 2-strike in AGENTS. Stock OpenCode will **retry the same GLM**. No verified escalate. | Lite is likely **too small** for a user at Ultra 91% in three weeks. Pro/Max might cover; **unproven** on his repos. | Browser → `opencode web` with basic auth (or `opencode pair` cookie). Needs a **reachable authenticated host** (Tailscale / SSH tunnel — not a public open port). Separate `--dir` per project. |
| **OpenCode + MiniMax M** | **$22 / $55 / $132** (Go / Explore / Build). Explore is their “daily coding” tier. | MiniMax Flash API list ~**$0.15 / $0.60** per 1M if PAYG; M Plan uses subscription credits. | Same GLM story: one model, no difficulty escalate. | Go = light edits. His volume → Explore+ (**$55+**). | Same browser-to-server path. Cursor iPhone key limit **does not apply**. |
| **Cursor on Mini or Linux CLI** | $0 extra sub | **Same as picker:** Composer $0.50/$2.50; Grok $2/$6; **this run Fast $4/$12**; iOS Cloud = max context (2× / Fast-long 3×). Overflow eats Other Models after Cursor Models 100%. | 2-strike. Auto pick unverified as escalate. | Ultra two pools until 3 Nov, then overflow, then stop (on-demand OFF). | Cursor iOS. **No** custom GLM/MiniMax keys. Still bills the selected model. |

**Cursor CLI on Linux** is not a cheaper host. It still draws Cursor Models / overflow Other Models.

**Desktop/server agents** (OpenCode, Codex CLI on a box) are **not** blocked by Cursor iPhone custom-key rules. That only helps if a **non-Cursor** key already exists. None purchased this turn.

**REA** (already on GoWifi box `102.209.119.186`, `/opt/rea`, user `rea`, v6.4.0): stdio MCP, no public port. Cheap path = **`audit_*` only**. `analyze_*` dumps 4–50MB and burns the parent model. Do not install extras. Cloud cannot register Mac MCP (Darwin script). OpenCode/Codex on a box can call the same SSH stdio MCP; still bounded to audit_*.

## One recommended setup (no purchase)

**Cheapest setup that is actually available and verified for “no model switching”:**

1. **Mac daily:** ChatGPT **desktop Codex**, picker left on **Default**, Standard speed. Existing ChatGPT Pro. SSH/deploy stay on This Mac (`deploy-with-key.sh`).
2. **Phone after hours:** ChatGPT iOS → **Remote** to that Mac Codex session (same Default). Not Cursor Cloud. Not Mini-as-a-discount (Mini still bills a Cursor model).
3. **Cursor:** leave running only if needed for Tab / rare native. Do not start Cloud. On-demand stays OFF so overflow cannot become an invoice after Other Models empties.
4. **OpenCode+GLM/MiniMax:** evaluated, **not bought**. Config template is in `opencode/`. I cannot finish a live server until Kevin authenticates a **purchase** (GLM/MiniMax key) and a reachable host. Lite GLM is unlikely to cover his month; do not buy on hope.
5. **Downgrade Ultra → Pro $20:** not yet. Pro still has iOS / Auto / My Machines / Remote Control; those still bill the selected Cursor model. Phone after Pro = Codex Remote first, Cursor Mini+Auto only if Codex is down.

**Why this covers the month better than staying on Cursor Ultra:** every Mac Grok/Composer turn now overflows toward the remaining 81% Other Models. Moving Mac work to already-paid Codex **stops that overflow**. Whether ChatGPT Pro fully replaces Ultra-sized volume is **unproven** until `/status` on the Mac. If a week of Codex Default shows the ChatGPT bar slamming, the next cheapest *candidate* is OpenCode+GLM **Pro** (not Lite) — still a purchase, still no verified difficulty escalate.

**Do not** use OpenCode with a ChatGPT/Codex provider hoping to save money — that is the same ChatGPT allowance plus another UI.

## Trial (Codex Default, unsupervised by this Cloud agent)

On This Mac, ChatGPT desktop Codex:

1. Darwin. Signed into ChatGPT. Picker = **Default**. `/status` shows Pro.
2. `bash sailingsa/deploy/codex-mac-trial-gate.sh` — SSH + `blank.html` 200. No deploy.
3. One already-authorised task in that chat. Live deploy only if that message asked.
4. Two strikes then stop. No picker. No Cursor Cloud.

Pass = gate green + task done. Then Kevin may click Ultra → Pro.

## What this Cloud session did vs could not

**Did:** correct overflow + Mini billing; verify Codex Default vs OpenCode stock escalate; write this compare; pin OpenCode template (no keys); keep 2-strike in `AGENTS.md`.

**Could not:** ChatGPT login, `/status`, GLM/MiniMax purchase, start `opencode web` on a phone-reachable host, register REA on Darwin, deploy live.
