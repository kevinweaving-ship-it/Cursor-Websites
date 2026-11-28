# SailingSA signup — easier path (plan and report)

**Status:** Plan only. No live deploy. No merge of existing signup PRs.  
**Date:** 28 Nov 2026 (Africa/Johannesburg)  
**Update:** Box design/code tools + gated teaser (seamless signup, hide profile depth until claim).  
**Live inspected:** HTTPS to `sailingsa.co.za` (this Cloud VM has **no** `~/.ssh/sailingsa_live_key`; SSH to `root@102.218.215.253` returned `Permission denied (publickey,password)`). Readme commands remain the deploy path on the Mac Mini.

---

## What “easier” means

A sailor who already sees their name should get in with **one proof + one password**, on **phone portrait (390×844)**, without searching twice or filling email, WhatsApp, and two passwords after they already proved they own the phone.

**Happy path (claim from search or profile):**

1. Stay on the sailor they recognised — **do not bounce** to a second URL if we can overlay.  
2. **WhatsApp number → Request Code → 4-digit PIN** (existing engine).  
3. **Set password once.**  
4. **Well Done** → that same profile unlocks in place.

Google / Facebook stay one-tap alternatives. Email Confirm stays the slow fallback. No `user_accounts` / session / sailor page until OAuth, WhatsApp PIN, or email Confirm click.

**Why sign up:** logged-out people see a **teaser**, not the full product. Name, club, class chips, last event — yes. Full career, race-by-race, rank cards, media depth — behind Claim. Search and official **regatta sheets** stay public (sport records + SEO). Sailor profile **depth** is the reward.

---

## Verdict from every prior chat, PR, and live check

Live already has a WhatsApp-first splash. Git `main` does not. Easier signup is **not** a greenfield page. It is **collapsing extra steps on the live funnel**, then **capturing that funnel into git** so the next frontend zip cannot wipe it.

| Layer | What is true today |
|---|---|
| **Live `/signup.html`** | 218 350 bytes, last-modified **15 Nov 2026 22:06 UTC**. Full splash: WhatsApp / Google / Facebook / email. `Request Code` exists. WhatsApp labelled **optional** on the long form. |
| **Repo `signup.html`** | **330-byte stub** that meta-refreshes to `/login.html`. Deploying `main` **destroys** live signup. |
| **Live `/login.html`** | 99 931 bytes (15 Nov 2026). Sign in with Google / Facebook / email. WhatsApp **optional**. Empty-field rule is in place (readonly until focus). |
| **Repo `login.html`** | 71 159 bytes. Still **requires** WhatsApp. Google still labelled **(in Development)**. Older Find-profile + required email/password/WhatsApp form. |
| **Live API** | `POST /api/register-account` with email returns **200** `{verification_required: true, via: "link"}` even with a fake `sas_id`. Empty body → 400 password rule. **Does not create a member on first POST.** `/sailor/general-public` → **404**. `/auth/google` and `/auth/facebook` **307** to the real providers. |
| **Repo `api.py`** | `register-account` still **requires sas_id + email + password + WhatsApp**, hashes SHA-256, **inserts `user_accounts` + session immediately**, and Facebook callback still has the **7-column / 6-value `login_method` INSERT** plus `http://192.168.0.130:8081/...`. **Do not deploy repo `api.py` over live.** |
| **`/pop-up`** | Still live (lab, 11 Sep 2026). WhatsApp Step 1 prototype. |
| **`/blank.html`** | **410 Gone** (SOP still names it as the hub URL). |

---

## Source inventory (chats / PRs / code)

### Cloud agents that actually contain signup work

| Agent | What it settled |
|---|---|
| [Sign up functionality](https://cursor.com/agents/bc-14853ecc-50f3-4117-b1b1-af62e77f92ab) | Longest thread. “SignUp Fix”, WhatsApp Request Code, `/pop-up`, landing claim card, one popup per orange arrow. Live-ahead of git. |
| [Sialingsa user authentication](https://cursor.com/agents/bc-01a168c6-8c28-744e-8f2a-764c89744ca5) | Fake **General public** member created without proof. Policy: only OAuth / WhatsApp PIN / email Confirm. Live cleanup + PR **#255**. |
| [Check login fields empty](https://cursor.com/agents/bc-5b64ed7b-801c-5bcd-8295-03da8b30aaec) | Login/signup/verify-link/logout empty-fields **PASS** on live (Oct 2026). Browser autofill ≠ site prefill. |
| [Audit homepage/login transcripts](https://cursor.com/agents/bc-4b9a1f53-5ce6-5271-a9b0-5514f2b7fb55) | Distilled avoid-rules: no PUB_ pages, no Cloud overwrite of live `api.py`, empty login inputs. |
| [Map auth and club perms](https://cursor.com/agents/bc-3c955b39-289f-5c23-9d45-de88734b9ff9) | Inventory only. `POST /auth/register` missing. No `club_admin` role. |
| [OpenWA gateway evaluation](https://cursor.com/agents/bc-01a22176-179d-701a-a90c-7fe16deff764) | **Do not replace** Baileys PoC. WhatsApp PIN delivery stays on current engine. |
| [Read-only WhatsApp box audit](https://cursor.com/agents/bc-103452c4-1eb9-5051-93a4-c26edbba9807) | Cloud had no SSH key — same as this run. PIN health still Mac/REA. |
| Summarize signup chats / claim-popup testers | Empty or ERROR transcripts — no extra findings. |

### Open PRs — **do not merge as the easier-signup fix**

| PR | Title | Why it stays parked |
|---|---|---|
| [#253](https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/253) | signup/login identity repairs **(do not merge)** | Explicit: live `/var/www/sailingsa/api/api.py` is source of truth. Repo `api.py` is the thin clone. |
| [#255](https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/255) | email Confirm before create | Behaviour is **already live** (`via: "link"`). PR is apply-scripts + `auth_identity.py`, not the UX collapse. |
| [#71](https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/71) | 360px claim popup + WA PIN | Draft, Sep 2026. Live signup of 15 Nov is newer. |
| [#83](https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/83) | Cape Classic entries + WhatsApp-first | Mixed with event-entry data. Do not merge for signup. |
| [#101](https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/101) | One standard Claim popup | Draft. Landing claim chips vs popup. Live may already differ. |
| [#11](https://github.com/kevinweaving-ship-it/Cursor-Websites/pull/11) | Auth-funnel human pattern | Traffic classification, not the form. |

Cherry-pick **behaviour**, not those branches, onto a fresh capture of **live files**.

### Standing product rules (already decided)

- No user / session / claim until **Google/Facebook OAuth**, **WhatsApp PIN consumed**, or **email Confirm click**.  
- `PUB_` / “General public” sailor pages **404**.  
- Login fields load **empty**.  
- Verify-link: scanner-safe preview; Confirm required; `returnTo` allowlist.  
- Compact MP-first. Clone the working card. Do not invent a cinematic login.  
- Header / gold header **locked**.  
- Never clobber live `api.py` from git.

---

## Why signup still feels hard (live, 28 Nov 2026)

Live splash is already WhatsApp-first. Friction is **step count and duplicate work**, not missing buttons.

Current live chain can be:

1. Splash (WhatsApp / Google / Facebook / email)  
2. **Find Your Profile** (name and surname only — no SAS ID on that field)  
3. **Confirm Your Profile** (This is me / child / family)  
4. Method again (WhatsApp Request Code, Google, Facebook, email)  
5. **Complete Your Registration** (email *, password *, confirm *, WhatsApp optional)  
6. **“Are you registered with SA Sailing (SAS)?”** even after “Your account is ready”  
7. Search **again** / “Profile link needs checking” / email support  

If they arrived from search with `?sas_id=`, they should skip 2, 6 and 7.

Other live issues that make it feel harder than it is:

- **Two search UIs** (Find Your Profile vs SAS membership search).  
- **Email Confirm** is the default `register-account` path (`via: "link"`). Inbox delay vs WhatsApp PIN. Choosing “email” is the slow road; the splash does not make that obvious enough.  
- **Password confirm + four complexity lines** after PIN/OAuth already proved the person.  
- **Child/family relationship form** sits on the main path (“This is my child”) instead of an advanced option.  
- **Cinematic Trae boat images** (`coresg-normal.trae.ai/api/ide/v1/text_to_image?...`) on the splash — large, external, not a SailingSA asset. Conflicts with compact MP-first and “no invented media”.  
- **Apple button CSS** on splash with no working Apple login.  
- **`/pop-up` lab** still public; **`/blank.html` 410** so old QA URLs 404/410.  
- **Repo vs live landmine:** any agent that deploys `main` `signup.html` would send everyone to the old login register flow.

Repo-only bugs that must **not** be copied to live: required WhatsApp, Google “in Development”, Facebook callback LAN IP, session INSERT missing `login_method`.

---

## Target funnel (one page, three screens)

**Seamless (best practice from our own claim popup + LinkedIn/Strava-style teaser):** run Screens A–C **on the page they were already looking at** (landing search, `/sailor/…`). Header **Sign Up** can still open `/signup.html` for cold traffic. Do not add a fourth URL. Do not send claim traffic through Find Your Profile.

**Screen A — proof (390×844, compact card, existing tokens)**  
If `sas_id` is in the query: show that sailor’s name + last classes, then:

- Sign up with **WhatsApp** (primary)  
- Sign up with **Google**  
- Sign up with **Facebook**  
- Sign up with **email** (secondary copy: “we’ll email a Confirm link”)

If no `sas_id`: same buttons, then **one** name/SAS-ID search (not two).

**Screen B — WhatsApp PIN** (only if they picked WhatsApp)  
Number → Request Code → 4 digits. Same branded WA message already specified in the Sep thread.

**Screen C — password once**  
One password field (keep the 7-character / capital / number / special rules). No confirm field after PIN or OAuth. Email optional (“so we can recover this login”). WhatsApp already known.

Then Well Done (≤5s) → `returnTo` or that sailor profile.

**Skip automatically when `sas_id` is present:** Find Your Profile, SAS membership question, second search, relationship form (unless they tap “this is my child”).

**Do not create** a member, session, or public sailor until PIN / OAuth / Confirm. Keep live `via: "link"` behaviour for email. WhatsApp path must consume the PIN **before** insert (policy from #255, already the rule).

---

## Sequenced work (do in this order)

Each step is one Mac session. Gold lock + `SSH_LIVE.md`. Snapshot live files before any copy. **Use the tools already on the boxes** — do not skip them because this Cloud VM cannot SSH.

### Step 0 — Capture live + inventory box tools (no behaviour change)

On the **Mac Mini** (keys live there), not Cloud:

```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 \
  'wc -c /var/www/sailingsa/signup.html /var/www/sailingsa/login.html \
   /var/www/sailingsa/api/api.py; \
   ls -l /opt/sailingsa-whatsapp-poc /etc/systemd/system/sailingsa-whatsapp-poc.service 2>/dev/null; \
   systemctl is-active sailingsa-whatsapp-poc sailingsa-api; \
   command -v graphify graphifyy stitch chromium; \
   /opt/rea/ops/bin/rea-admin sailingsa -- capabilities 2>/dev/null | head'
```

Then:

1. Copy **live** `signup.html` and `login.html` into git so `main` stops being a stub.  
2. Diff live `register-account` / verify-link / WhatsApp PIN vs repo; **do not replace live `api.py`**.  
3. **Graphify** (PR #302/#303, `ops_run` only — never `ops_jobs`):  
   `graphify query "register-account claim-status signup.html"` on the Mac extract, and on box graphs under `/var/www/sailingsa/graphify-out` if present.  
4. **REA**: `rea-admin sailingsa -- capabilities`; WhatsApp unit status; Chromium `capture_browser_scenario` at **390×844** on live `/signup.html?signup=1`.  
5. **MotionSites skill** (already in repo, PR #293 merged): study **2–3 compact patterns only** — `ai-workflow.md` (LogIn / UserPlus control size), `securify-hero.md` (trust density), `email-landing-page.md` (field spacing). Steal **px / gap / radius**, not cinematic video heroes or 72px type.  
6. **Google Stitch**: on Mac run `stitch status --json`. If `authenticated: true`, ask for a **compact 390×844 claim overlay** using `docs/design_system.md` tokens. If false, record auth required and continue with live splash + skill examples. Never invent Stitch output. Never apply generated CSS onto live without Plan → diff → MP screenshot.  
7. Close or label #253/#71/#83/#101 as superseded-by-live.

### Step 1 — Deep-link skip (biggest ease win, frontend only)

`/signup.html?sas_id=…&signup=1` must open Screen A on **that sailor**, not “Find Your Profile”.  
Claim CTAs in `index.html` already pass `sas_id` (`sailor-claim-cta`, `claimSignupHref`). Wire the live splash to honour it.

Accept: one MP screenshot of a known unclaimed sailor (e.g. previous Sean Kavanagh test pattern) going splash → WhatsApp fields without a search box.

### Step 2 — WhatsApp path skips the long form

After PIN consumed: Screen C only (password). No email required. No SAS “are you registered?” when `sas_id` already claimed in this session.  
Needs a **read-only** check that `sailingsa-whatsapp-poc` is active (Step 0). If PIN send is down, show that error — do not silently fall back to creating a user.

### Step 3 — Drop the post-account SAS quiz for claim traffic

The block `#sailorChoice` / “Are you registered with SA Sailing” is extra work after “Your account is ready”. Keep it **only** for people who signed up with Google/Facebook/email and have **no** `sas_id`. Claim-from-search never sees it.

### Step 4 — Compact the splash (visual, MP first, using installed design tools)

- Design **390×844**. Body 14–16px, slim buttons, no full-width giant CTAs.  
- Remove Trae `text_to_image` backgrounds; use existing SailingSA wordmark / live logo path only.  
- Hide Apple until there is a real Apple login.  
- Clone the working live splash **and** the existing `#state-login-required` / claim popup — same card shell, not a new look.  
- MotionSites: micro-patterns only (see Step 0). Stitch mock if authenticated. Graphify to list every `showLoginRequiredPopup` / `claimSignupHref` call site so we do not miss a surface.  
- Screenshot MP, then ML, then desktop (REA Chromium or Cursor Browser). Two identical visual failures → stop and diagnose.

### Step 4b — Teaser the product (reason to sign up)

Logged-out **sailor profile** is a preview, not the full app. Align with copy we already ship: *“Claim your profile or register to … see more detailed information (SSA ranks, results, and full sailor data).”*

| Logged out (teaser) | After claim / sign-in |
|---|---|
| Name, club, class chips, last event title | Full career, race-by-race, rank cards, media depth |
| SAS ID stays hidden (`PUBLIC_SAS_ID_PAUSE`) | Own SAS ID on their session |
| Claim / Sign up CTA on the same card | Unlocked profile in place |

**Keep public:** search, club/class pages, **regatta result sheets** (official sport records, SEO). Do not 404 `/sailor/…` pages. Do not hide junior-safe public results off the event URL. Personal PII (phone, email, WhatsApp) never appears logged-out (`docs/goals.md` / POPIA).

This is a **product gate**, not a privacy workaround. `README_SAILOR_PROFILE_SYSTEM.md` says competition results are public — that stays true on **regatta pages**. The **profile depth** is what we hold back.

### Step 5 — Align login.html leftovers

Live login still has Find Profile + Complete Registration. Point “1st time / Sign up” at `/signup.html` and leave login as **sign-in + forgot password** only. Stops two different register forms.

### Step 6 — Retire labs

`/pop-up` → redirect to `/signup.html`. Do not revive `/blank.html` for signup QA; use `/signup.html?sas_id=…` and `/login.html`. Update SOP mentions of blank hub if hub work still needs a URL.

### Step 7 — Verify (no merge-as-deploy)

- Email `register-account` still returns `via: "link"` and creates **no** row until Confirm.  
- `/sailor/general-public` still 404.  
- Login fields empty on hard reload.  
- Google/Facebook still 307 to providers (Kevin completes the human OAuth screens).  
- Claim with `sas_id` never hits Find Your Profile.  
- `node scripts/check_website_workflow.cjs` on the branch.  
- Live smoke only **after** Mac deploy of **those two HTML files**, never a wholesale `api.py` git push.

---

## Out of scope (do not mix in)

- Club-admin login / event-entry POST (not implemented; `register-account` is user signup, not a regatta entry).  
- Replacing WhatsApp with OpenWA / Cloud API.  
- Merging #253 or copying repo `api.py` to `/var/www/sailingsa/api/api.py`.  
- Header / gold-header / `enforceHeader` edits.  
- Cinematic MotionSites rebuild of the login card (72–96px type, video heroes).  
- Paywalling official **regatta HTML/PDF sheets**.

---

## Tools this run actually used

| Tool | State |
|---|---|
| GitHub PRs / issues (`kevinweaving-ship-it/Cursor-Websites`) | **verified working** |
| Cloud-agent transcripts (signup / auth / WA) | **verified working** (two “summarize” chats empty) |
| Live HTTPS (`signup.html`, `login.html`, `/pop-up`, APIs, OAuth starts) | **verified working** |
| SSH `root@102.218.215.253` from this Cloud VM | **failed** — no `sailingsa_live_key` (`Permission denied`). Use Mac Mini + `sailingsa/deploy/SSH_LIVE.md`. |
| MotionSites **skill** (repo, PR #293) | **configured** — use for 2–3 compact examples on Mac; premium MCP **auth required** on this Cloud VM |
| Google Stitch CLI | **configured** in `.cursor/mcp.json`; GoWifi 8 Nov 2026 probe was unauthenticated. Re-check on Mac (`stitch status --json`) |
| Graphify | **repo extract + rules** (PR #302 open). Live box graphs **unverified** from Cloud (PR #303 not deployed from Cloud). Use on Mac via `ops_run` |
| REA `rea-admin` / Chromium | **installed on boxes**; **not exposed** in this Cloud session. Mac Mini is the runtime |
| Codex / OpenCode | Mac Codex Default (PR #252). Not this Cloud agent |
| Box MCP | **not used** (“boxes” = SSH servers) |

---

## First implementation step (when you say go)

**Step 0 + Step 1 only on the Mac Mini:** inventory Graphify / REA / Stitch / WhatsApp on the box, snapshot live `signup.html` / `login.html`, then make claim traffic (`?sas_id=`) skip Find Your Profile and stay on WhatsApp-first Screen A (overlay if possible). No `api.py` copy. No PR merges. Teaser (Step 4b) is the step after the funnel is three screens.
