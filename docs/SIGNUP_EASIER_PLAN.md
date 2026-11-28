# SailingSA signup — easier path (plan and report)

**Status:** Plan only. No live deploy. No merge of existing signup PRs.  
**Date:** 28 Nov 2026 (Africa/Johannesburg)  
**Update:** Box design/code tools + gated teaser + mimic Facebook / YouTube (screen-by-screen, planning only).  
**Live inspected:** HTTPS + SSH to `root@102.218.215.253` (`SSH_LIVE.md` password path). Stats from live `traffic_funnel_events`, `public_page_hits`, `user_accounts`.

---

## Plain English (read this first)

This is a **plan**. Nothing on the live site changes until you say go.

**How it works today**

1. You search, see your name, tap Claim / Sign up.  
2. The site **leaves that page** and opens a different Sign up page.  
3. It asks you to **search for yourself again**.  
4. You confirm “this is me”.  
5. You pick WhatsApp / Google / Facebook / email **again**.  
6. You fill a long form (email, password, password again, WhatsApp).  
7. It then asks if you are registered with SA Sailing — even after you just claimed a sailor.  
8. Sometimes you search a third time.

That is why it feels hard. The buttons exist. The path is too long and it forgets who you already picked.

**What we plan instead — one box, two doors**

Same pop-up everywhere. Same buttons: WhatsApp, Google, Facebook, email. Header layout does **not** change; the existing “Sign In / Sign Up” button just opens this box.

**Door 1 — you already found yourself** (Claim on a sailor)

Box pops up **on that sailor**. It already knows who you are. It does **not** ask “is this you?”. Three steps: prove it (WhatsApp code or Google/Facebook) → one password → that profile unlocks.

**Door 2 — you tapped Sign Up in the header** (you have not picked a sailor)

Same box. Same prove + one password. Then **one** search that works like the homepage sailor search — because names clash.

Type `Tim` or `Thomas Henshaw` and you get a **list**. Keep typing to shrink it. Each row shows enough to tell them apart: full name, club, class, last event (youth vs dad, which club). Tap the right one. That tap **is** the choice — no extra “is this you?” after.

Same list on the **homepage search** before Claim: if two Henshaws come up, you pick one there, then Claim is Door 1 on that person. We do not invent a second search.

Or skip and link a sailor later.

**After you have an account — Sign In** (same box, other tab)

You are not creating anything. WhatsApp code **or** Google/Facebook **or** email + the password you already chose. No search. No “is this you?”. No new password. You are in. If you claimed a sailor, that profile is yours; if not, you land on the site logged in.

Today’s login page mixes Sign In **and** a full Register / Find Profile on the same screen. That mix goes away: Sign In is only for people who already signed up. Sign Up is the other tab of the same box.

**What you see before vs after sign-up (reason to bother)**

Like YouTube: you can watch without an account; like/subscribe needs sign-in.

- **Not signed in:** name, club, last event. Race result pages for events stay public.  
- **Signed in:** full career, rankings, media.

**What actually changes (when we build it)**

| Today | After |
|---|---|
| Claim sends you to another page | Box on the same sailor |
| Header Sign In / Sign Up dumps you on a mixed login+register page | Same box, two tabs: Sign in / Sign up |
| Search for yourself twice, then “is this you?” | Claim on a sailor you already opened: no search, no “is this you?”. If many Tims / father-and-son: **one** list (homepage or header box) with club, class, last event; keep typing to narrow; tap the right row |
| Login page also has Find Profile + Register | Login is only “I already have an account” |
| Long form after you already proved the phone | One password when new; existing password when returning |
| “Are you SAS registered?” after you claimed | That question gone |
| Full sailor profile visible logged out | Preview only until they sign up |

**What makes it easier:** fewer pages, fewer questions, no repeating work you already did.

Email sign-up stays the slow path (wait for a link). WhatsApp or Google/Facebook is the fast path. We are **not** merging old signup pull requests and **not** overwriting the live server from git.

**Why they start and then click away** (live DB, 28 Nov 2026 SAST)

Source: `traffic_funnel_events` + `/traffic/api/claim-attempts` on the box. Probe POSTs without a real step are ignored; **real attempts are stored**.

**All time (people, not page hits)**

| | n |
|---|---|
| Opened claim/signup | **80** |
| Searched for a sailor | 14 |
| Opened the long form | 38 |
| Submitted | 29 |
| Finished | **29** |
| Failed (error) | 10 |
| **Left without finishing** | **51** (~64% of people who opened) |

Event counts: Claim button seen 286 → signup page 253 → sailor already chosen 67 → form started 50 → submitted 43 → completed 31. Claim **click** only recorded 3 times (most people never get a tracked click; they hop to the page).

**Last 30 days:** 26 opened, **5 finished**, 2 failed, **20 left** (~77%). Signup page hits: 13 visits / 5 visitors. Accounts created: 13 (some not via this funnel). **Last 7 days: 9 signup page loads, 2 sailor-chosen, 0 new accounts.** Last event 25 Nov 2026 14:21 SAST — loaded signup, walked away.

**Why (from stored fail reasons + drop steps):**

| Where they bail | Evidence | Fix |
|---|---|---|
| Open page, never pick a sailor | 253 page loads vs 67 preselected | Pop-up on the sailor they already had; skip Find Profile |
| Claim click almost untracked | 3 clicks vs 286 impressions | Stay on the sailor; don’t hop |
| Long form | 67 chosen → 50 form → 43 submit | One password after WhatsApp/Google |
| **Email/phone already registered — sign in instead** | 5 fails in 30 days (only fail reason this month) | Same box, Sign In tab — don’t make them start Sign Up |
| Form incomplete | 10 all-time | Fewer fields |
| **INSERT has more target columns than expressions** (`login_method`) | 2 real fail events | Live Facebook/session insert bug — **do not copy repo `api.py`**; fix live only with backup |
| “Do this later” SAS quiz | Page copy after “account is ready” | Drop quiz on Claim |
| Full profile already visible | 20 of 26 left in 30 days with no error | Teaser: hide career/ranks/media |

| Where they bail | Why | Fix in this plan |
|---|---|---|
| Claim → new Sign up page | They lose the sailor they were looking at. Easy to hit Back. | Pop-up on that sailor |
| Find Your Profile again | They already picked someone. Feels like a dead end. | Skip if we already know who |
| Two Henshaws / lots of Tims | List is not enough to tell them apart, or they get an extra “is this you?” | One list with club, class, last event; tap = choice |
| Long form (email, two passwords, rules) | After they already proved the phone. | One password |
| Email “we sent a link” | They leave for inbox and never come back. | WhatsApp code / Google is the fast path; email labelled slow |
| “Are you registered with SAS?” **after** “Your account is ready” | They think they are done. Three buttons include **“I’m not sure — do this later”** and **“I can’t find my profile — do this later”**. That is an official exit. | Drop this quiz on Claim |
| “Profile link needs checking” / email support | Feels broken. They leave. | Do not send Claim traffic here |
| Login-required **Back to Page** | They only wanted results. Full profile is already visible, so no reason to finish. | Teaser: hide career/ranks/media until they are in |
| Password / WhatsApp / email / date-of-birth errors | Form fights them (`validation_error` in the code). | Fewer fields, so fewer errors |

On the **Mac Mini** (Step 0): re-pull `/traffic` claim-attempts after backup. Do **not** turn extra tracking on as a surprise live change.

---

**How we will not break it (when you say go — Mac Mini, not this Cloud machine)**

- **Backup first.** Run `sailingsa/deploy/pre-change-backup.sh` so live is in `/root/backup_TIMESTAMP.tar.gz`. Confirm the file exists before any edit. Restore = put that tarball back.  
- **Do not touch** the header, nav, or page layout. Same cards, same colours, same compact phone look. Clone the existing Claim pop-up. No new look.  
- **Do not overwrite** live `api.py` from git. Do not merge old signup PRs. Copy **live** signup/login into git first so we do not wipe what already works.  
- **Use the tools on the box:** Graphify, REA, Chromium screenshots at phone size (390×844), MotionSites only for small spacing, Stitch only if it is actually signed in. Screenshot after each step. Two identical visual fails → stop.  
- **No resistance:** Claim = pop-up, prove, one password, done. Header Sign Up = same box. Many Tims / father-son = one list, tap the right row. Sign In = same box, no new form. No second search. No “is this you?” after they already picked. No SAS quiz after claim.

First real build (when you say go): backup, then Claim pop-up stays on the sailor, no “is this you?”, no second search. Header Sign In / Sign Up then uses that **same** box.

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

**Seamless (today is the opposite):** `#state-login-required` already sits on the sailor, then **Sign In** goes to `/login.html` and **Sign Up** goes to `/signup.html` (see `showLoginRequiredPopup` in `index.html`). That bounce is the leak. Keep the same popup shell; swap those two buttons for Screens A–C **in the overlay**. Header **Sign Up** can still open `/signup.html` for cold traffic. Do not add a fourth URL. Do not send claim traffic through Find Your Profile.

**Screen A — proof (390×844, compact card, existing tokens)**  
If `sas_id` is in the query: show that sailor’s name + last classes, then:

- Sign up with **WhatsApp** (primary)  
- Sign up with **Google**  
- Sign up with **Facebook**  
- Sign up with **email** (secondary copy: “we’ll email a Confirm link”)

If no `sas_id`: same buttons, then **one** sailor search (same cards as the homepage). Type to filter. Rows show name, club, class, last event so father/son and many Tims can be told apart. Tapping a row is the choice. Not two searches. Not a second “is this you?”.

**Screen B — WhatsApp PIN** (only if they picked WhatsApp)  
Number → Request Code → 4 digits. Same branded WA message already specified in the Sep thread.

**Screen C — password once**  
One password field (keep the 7-character / capital / number / special rules). No confirm field after PIN or OAuth. Email optional (“so we can recover this login”). WhatsApp already known.

Then Well Done (≤5s) → `returnTo` or that sailor profile.

**Skip automatically when `sas_id` is present:** Find Your Profile, SAS membership question, second search, relationship form (unless they tap “this is my child”).

**Do not create** a member, session, or public sailor until PIN / OAuth / Confirm. Keep live `via: "link"` behaviour for email. WhatsApp path must consume the PIN **before** insert (policy from #255, already the rule).

---

## Mimic popular platforms (planning — steal behaviour, not brands)

Live scrape of Facebook / YouTube was **not** run this Cloud turn: Context.dev is at **0 credits** (refill 3 Dec 2026 SAST). Patterns below are the stable 2024–2026 product model plus our own claim popup / Dockside / Strava-style teaser research already in this repo. **On Mac Mini (Step 0)** screenshot those apps at **390×844** with Chromium/REA and copy **px, overlay height, button stack** — never logos, copy, or a cinematic rebuild.

| Platform | How signup actually works | What we copy |
|---|---|---|
| **Facebook / Instagram** | “Continue with” Google, or **phone + code**. Overlay on the feed. Like / comment / save hit a sheet. Account exists after the code. | WhatsApp PIN = their SMS OTP. Overlay on sailor/search. Do not bounce to a 7-step `/signup.html` for claim traffic. |
| **YouTube** | **Watch first.** Sign in (Google one-tap) only for like, subscribe, comment, save. Sign in **is** sign up. Video stays under the sheet. | Logged-out sailor **teaser** stays visible. Claim unlocks ranks / career / media — not the whole site. One “Continue” language, not Register vs Login as two products. |
| **WhatsApp / Telegram** | Phone + code **is** the account. No email, no “confirm password”, no membership quiz. | After PIN: Screen C password once. Skip Find Profile, SAS quiz, second search when `sas_id` is known. |
| **Strava / LinkedIn** | Headline profile is public (name, club/company, last activity). Kudos, full analysis, network depth gated. | Name, club, class chips, last event public. Race-by-race, SSA ranks, media depth behind claim. |
| **Google identity** | One field at a time: who → proof → password. Never dump the whole form. | Screen A buttons → B PIN → C password. Child/family is an advanced tap, not the main path. |

**Intuitive (not a new site):**

1. **Stay in context** — sheet on the sailor they recognised (YouTube watch page). Header Sign Up still opens `/signup.html` for cold traffic.  
2. **Continue with…** — WhatsApp primary, Google, Facebook; email labelled as the slow Confirm-link path. Hide Apple until it works.  
3. **Gate actions, not discovery** — search, club/class, **regatta sheets** stay public (YouTube lets you watch). Profile **depth** is the subscribe/like equivalent.  
4. **One identity** — they already picked the sailor; do not ask name again.  
5. **Sign in = sign up** — login.html becomes sign-in + forgot password only (Step 5). Same overlay can say “Continue” for both.  
6. **Proof before member** — still no `user_accounts` until PIN / OAuth / Confirm (stricter than Facebook’s instant cookie; we keep that on purpose).

Do **not** clone Facebook’s dark sheet or YouTube’s grey modal CSS. Clone **our** `#state-login-required` / claim popup density (14–16px, 44×44 taps, existing tokens).

### Screen-by-screen mimic (planning)

Checked 28 Nov 2026 (SAST) from public help pages, not a live app scrape (Context.dev still 0 credits). Mac Step 0 still screenshots the real apps at 390×844.

**Facebook (mobile, [help](https://www.facebook.com/help/mobile-basic/188157731232424) / [wikiHow Mar 2025](https://www.wikihow.com/Sign-Up-for-Facebook)):** one field per screen → phone is the default identifier (email is a switch at the bottom) → password → SMS code → extras (photo, find friends) are **Skip**. We **do not** copy DOB, gender, or find-friends. For claim traffic we already have the name, so we skip Facebook’s name step too.

**YouTube ([Why sign in](https://support.google.com/youtube/answer/9879569)):** public watch works signed out; the reminder is **dismissable**. Like / Subscribe / Comment / Save opens Sign in. Sign in **is** a Google account — there is no separate YouTube register. Age-restricted is the only hard wall.

| Their moment | SailingSA equivalent |
|---|---|
| YouTube: video plays signed out | Search + sailor **teaser** (name, club, last event) |
| YouTube: dismiss “Sign in?” and keep watching | Existing **Back to Page** on `#state-login-required` |
| YouTube: Like / Subscribe | SSA ranks, career table, Media/Activity depth |
| Facebook: phone field, then SMS code | WhatsApp number → Request Code → 4-digit PIN |
| Facebook: email is a switch, not the default | Email labelled “we’ll send a Confirm link” |
| Facebook: Skip photo / friends | No SAS quiz, no child/family, no second search on claim |
| YouTube: Sign in = Create account | One overlay: **Continue with WhatsApp / Google / Facebook** |
| Instagram / TikTok: sheet on the action | Overlay on the sailor they tapped — no hop to `/signup.html` |

**Do not mimic:** Facebook’s cold-start name + DOB + gender stack (that is *more* fields than we have today). Apple Sign in until it actually works. A YouTube-grey or Facebook-blue restyle of our card.

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

0. Box stats already pulled 28 Nov 2026 (this section). Re-check `/traffic` claim-attempts after backup.  
1. Copy **live** `signup.html` and `login.html` into git so `main` stops being a stub.  
2. Diff live `register-account` / verify-link / WhatsApp PIN vs repo; **do not replace live `api.py`**.  
3. **Graphify** (PR #302/#303, `ops_run` only — never `ops_jobs`):  
   `graphify query "register-account claim-status signup.html"` on the Mac extract, and on box graphs under `/var/www/sailingsa/graphify-out` if present.  
4. **REA**: `rea-admin sailingsa -- capabilities`; WhatsApp unit status; Chromium `capture_browser_scenario` at **390×844** on live `/signup.html?signup=1`.  
5. **MotionSites skill** (already in repo, PR #293 merged): study **2–3 compact patterns only** — `ai-workflow.md` (LogIn / UserPlus control size), `securify-hero.md` (trust density), `email-landing-page.md` (field spacing). Steal **px / gap / radius**, not cinematic video heroes or 72px type.  
6. **Google Stitch**: on Mac run `stitch status --json`. If `authenticated: true`, ask for a **compact 390×844 claim overlay** using `docs/design_system.md` tokens. If false, record auth required and continue with live splash + skill examples. Never invent Stitch output. Never apply generated CSS onto live without Plan → diff → MP screenshot.  
7. Close or label #253/#71/#83/#101 as superseded-by-live.  
8. **Platform screenshots (Mac Chromium, 390×844):** Facebook Continue-with sheet, YouTube “Sign in to like/subscribe”, WhatsApp Web phone+code, Strava logged-out athlete. Steal overlay height and button order only. Store under `shots/signup-platforms/` on the Mac; do not commit third-party UI into git.

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

Tapping a gated block opens the **same overlay** (Screens A–C), not `/login.html`. After proof, the tab they were on unlocks in place.

| Surface | Logged out (teaser) | After claim / sign-in |
|---|---|---|
| Profile header | Name, club, class chips, photo if we have one | Same + own SAS ID on their session |
| Last event | **One** event title | Full **Regattas Sailed** table |
| SSA / SSL rank cards | Hidden or “Claim to see ranks” placeholder | Rank, points, audit popup |
| Race-by-race / career | Hidden | Full history |
| Media tab | Count or first card only, rest gated | Full mentions |
| Activity tab | Gated | Unlocked |
| SAS ID | Hidden (`PUBLIC_SAS_ID_PAUSE`) | Own ID only |
| CTA | Claim / Continue on the same card | Gone — they are in |

**Keep public (not a paywall of the sport):** search, club/class pages, official **regatta HTML/PDF sheets**. Do not 404 `/sailor/…`. Do not hide junior-safe public results off the event URL. Phone / email / WhatsApp never appear logged-out (`docs/goals.md` / POPIA).

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
| SSH `root@102.218.215.253` | **working** (`SSH_LIVE.md` password path). Funnel + account stats read from live DB. |
| MotionSites **skill** (repo, PR #293) | **configured** — use for 2–3 compact examples on Mac; premium MCP **auth required** on this Cloud VM |
| Google Stitch CLI | **configured** in `.cursor/mcp.json`; GoWifi 8 Nov 2026 probe was unauthenticated. Re-check on Mac (`stitch status --json`) |
| Graphify | **repo extract + rules** (PR #302 open). Live box graphs **unverified** from Cloud (PR #303 not deployed from Cloud). Use on Mac via `ops_run` |
| REA `rea-admin` / Chromium | **installed on boxes**; **not exposed** in this Cloud session. Mac Mini is the runtime |
| Codex / OpenCode | Mac Codex Default (PR #252). Not this Cloud agent |
| Box MCP | **not used** (“boxes” = SSH servers) |
| Context.dev live web search | **USAGE_EXCEEDED** this turn (0 credits). Auth valid. Refill **3 Dec 2026 ~10:01 SAST** (~300 credits) or [Developer $20 / 10k credits](https://context.dev/u/120_abdW4TedsjN2cg1dg_7mC_HS). Do not retry until then. Platform mimic uses known patterns + Mac screenshots in Step 0. |

---

## First implementation step (when you say go)

**Step 0 + Step 1 only on the Mac Mini:** inventory Graphify / REA / Stitch / WhatsApp on the box, snapshot live `signup.html` / `login.html`, then make claim traffic (`?sas_id=`) skip Find Your Profile and stay on WhatsApp-first Screen A **inside the existing login-required overlay** (do not bounce to `/signup.html`). No `api.py` copy. No PR merges. Teaser (Step 4b) is the step after that overlay is three screens.
