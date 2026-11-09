# Club Event + Calendar + Duty Roster + Messaging — unified plan

**Status:** Plan only. Do not code or deploy until this document is approved.

**Date:** 14 October 2026.

**Scope:** Every SailingSA club (`GET /api/clubs` = **85** clubs). **HYC is the first test case**, not a Hermanus-only product. Do not implement the HYC PDF path in isolation.

**Depends on (do not replace):**

- `docs/CLUB_PAGE_EVENT_WIZARD_PLAN.md` — officer home is `/club/{abbrev}`
- `docs/HYC_CALENDAR_CLUB_PAGE_PLAN.md` — first-club checklist, SAS match, no auto-`regattas` for training / external / duty
- `docs/CLUB_EVENT_SELF_SERVICE_PLAN.md` — Phases 1–5 already live (permissions, claim/create, entries, ingest, publish)

**Ask:** Approve the **consolidated phases in §8** (events, calendars, duties, §6B matching, messaging, WhatsApp, `/club-manage` retirement, Super Admin on every club page) before any implementation.

---

## Verdict

Build **one multi-club system** on the tables and pages that already publish. Do not buy Spond/TeamSnap, do not stand up a second app, and do not treat `@sailingsa.co.za` as working mail.

```
SAS scrape ──► public.events ──► Claim SAS Event (any host, no new slug)
                     │
Club officer ──► club_season_items (every club_id)
                     ├─ kind=race     → optional events + regattas (Activate / Add)
                     ├─ kind=training / informal / cruise / ops → calendar only
                     ├─ kind=external → link to other-host events row
                     └─ kind=duty     → club_duty_assignments (not an event)

calendar names ──► match sas_id_personal + sailor profiles (confidence score)
                     ├─ unique SAS-ID / unique name → provisional assignment link
                     ├─ ambiguous name → officer confirm
                     └─ club unknown → propose roster club (HYC on the test case);
                        never overwrite an existing affiliation; keep calendar evidence

club_duty_assignments ──► notifications (in-app, always)
                       ├─ optional WhatsApp Cloud API (opt-in, reply 1 / 2)
                       └─ optional email later (only after real MX)

sailor personal calendar ──► signed ICS feed of my events + my duties
club admin board ──► who acknowledged / needs remind / no response
```

**Event management lives on `/club/{abbrev}` only.** Super Admin has the full wizard on **every** club page (all 85). Club admin/manager: their assigned club only. Sailors and visitors: public controls only.

**Retire `/club-manage` after the club-page wizard is verified.** Keep the Phase 1–5 APIs; do not duplicate a second UI. Redirect: Super Admin → `/clubs`; club officer → their `/club/{abbrev}`; others → login or public `/clubs`.

**§6B (name → sailor + club proposal) is in scope for Phase B**, not a side doc.

Visitors keep today’s club page. Header / nav stay locked (no new header bell unless separately authorised).

**WhatsApp today is a login identifier, not a messenger.** Messaging must be new, opt-in, and POPIA-safe.

**`@sailingsa.co.za` is not email-hosted.** Public DNS (14 Oct 2026): GoDaddy NS, **no MX**, **no SPF**, Google Search Console TXT only, DMARC `rua=dmarc_rua@onsecureserver.net`. In-app notifications are the real inbox. Human mailboxes (Kevin@…) are a separate hosting purchase, not this product.

---

## 1. Existing functionality (audit)

### 1.1 User accounts and identity — **reuse**

| Piece | What exists | Use for this system |
| --- | --- | --- |
| `user_accounts` | `sas_id`, `login_method` (`email` / `whatsapp` / `sas_id` / Facebook), `provider_id`, `email`, `password_hash`, `profile_picture_path`, live `role` + `admin_club_id` | Auth. WhatsApp **login** number is `provider_id` when `login_method='whatsapp'` (10 digits, leading 0). **Not** a messaging consent. |
| `user_sessions` | Cookie `session` | Gate all writes |
| `GET /auth/session` | `sas_id`, `role`, `is_super_admin`, `admin_club_id`, `is_club_admin`, name | Already returns club fields in git |
| `GET /api/club/me` | `admin_club_id`, `club_abbrev`, `is_super_admin` | Officer gate. Super Admin does **not** need `admin_club_id`; they manage via the URL club. |
| `sas_id_personal` | Name, `club_1`…`club_5`, `primary_club`, `email`, `phone_primary` / `phone_secondary`, `parent_guardian_id` | Resolve who a duty name is; junior → parent for WhatsApp. Club fields are **read for “already affiliated”** — never overwritten by a roster guess. |
| Live roles | sailor ~69, super_admin 13, HMYC `club_manager` (98), ZVYC `club_admin` (3) | **HYC has no officer yet** — prerequisite for the test case |
| `POST /auth/login`, `POST /api/register-account` | WhatsApp number required at register | Source of digits; still need opt-in |

**Do not reuse as ACL:** `sas_id_personal.commodore` / `club_secretary` / `communication_preferences_1`–`4` (documented **empty**). `member_roles` + `roles` are SA **qualifications** (Instructor, Judge) via `GET /api/member/{sa_id}/roles` — display only, not duty roster.

### 1.8 Who may manage (ACL — all phases)

| Actor | Where they manage | What they see on `/club/{abbrev}` |
| --- | --- | --- |
| **`super_admin`** | **Any** of the 85 club pages. Full Event Management wizard, duty board, §6B confirm/propose, publish. Not limited by `admin_club_id`. | Admin chips + wizard + duty board on that page |
| **`club_admin` / `club_manager`** | Only `admin_club_id` == this page’s club | Same admin chrome on **their** page; other clubs stay public |
| **`sailor`** (logged in, not an officer of this club) | Own ack / snooze / ICS / notifications | Public page + “My duties” if assigned here |
| **Visitor** (anon) | Nothing | Today’s public club page only |

Writes take the **page club** from `/club/{abbrev}` (or `?club=` on APIs). Super Admin: allow if `is_super_admin`. Officer: allow if `admin_club_id` equals that club. Never show typed club IDs; Super Admin picks a club by opening `/club/hyc`, `/club/zvyc`, … from `/clubs`.

`GET /api/club/me/events` stays host-scoped to the **page** club (Super Admin included). Do not dump all 85 calendars into one response.

### 1.2 Profile icons — **reuse display, do not invent a chat face**

| Path | Role |
| --- | --- |
| `js/session.js` `sailingBuildSailorAvatarCandidates` | Personal avatar → SAS-id file → `default-youth.png` (ages 9–18) |
| `assets/personal-avatars/{id}-{slug}.png`, `assets/avatars/{sas_id}.png` | Header + sailor identity |
| Facebook download | `assets/profile_pics/fb_{id}.jpg` → `user_accounts.profile_picture_path` |
| Locked header | `.admin-v10-second-header` / `blank-landing-header.js` — **do not add a notification bell here** |

Duty / acknowledge UI uses existing avatars on **club-page cards** and the **sailor profile**, not a new header widget.

### 1.3 Messaging and notifications — **almost nothing**

| What people might think exists | Reality |
| --- | --- |
| In-app inbox / DMs | **None** (repo search: no `inbox`, `user_messages`, push, FCM, OneSignal) |
| Product notifications | Docs only (scrape-complete, media-delete). No sailor/club notify table |
| Email send | `api.py` media-delete: `smtplib` to `ADMIN_EMAIL` via `SMTP_HOST=localhost:25`, `MAIL_FROM=noreply@sailingsa.co.za`, **errors swallowed** |
| `api/app.py` | **Dead stub**: MySQL + Gmail SMTP. Not the live app. Ignore |
| `@sailingsa.co.za` hosting | **No MX.** Mail to that domain is not delivered. Not an internal messenger |

### 1.4 WhatsApp — **login only**

| Exists | Does not exist |
| --- | --- |
| Register / login with 10-digit ZA number | Cloud API / BSP credentials |
| Admin list `whatsapp_provider_id` (derived from `provider_id`) | Webhook, templates, outbound send |
| `user_accounts` has **no** `whatsapp` column | Opt-in, E.164, STOP, delivery log |

No WhatsApp / REA / GoWifi messaging MCP or code is connected in this environment. Cursor REA research used the live codebase + public Meta/SA pricing docs (official `developers.facebook.com/docs/whatsapp/pricing` returned 403 from this host).

### 1.5 Events and club pages — **reuse as the calendar spine**

| Exists | Gap |
| --- | --- |
| `events` (1 302 live) + SAS scrape | Host-scoped lists hide other clubs’ nationals |
| `GET /api/events`, `/club/{abbrev}` Upcoming / Past / Other | Live `/club/hyc` is `.sa-home-regatta-card` lists, not the git carousel |
| `POST /api/club/events/{id}/claim` | **Always** inserts `regattas` if `regatta_id` is null |
| `POST /api/club/events` | **Always** inserts `events` **and** `regattas` |
| `GET /api/club/me/events` | `WHERE host_club_id = session` only |
| Keyword match ~`api.py` 27224 | Good enough for Claim; needs a **public match API** |
| `events.category` (National / Regional / Training / Dinghy Event / …) | Preserve. Do not invent Duty/Informal as SAS types |
| `hide_result_types` Meeting / Training | Extend **tick hide**, not category enum |
| Phases 1–5 (fleets, SAS-ID entries, Sailwave, Provisional/Final) | Only after a race has a slug |

### 1.6 Duty, personal calendar, ICS — **missing**

No roster table, no assignment status, no ICS/webcal route, no reminder job. HYC PDF columns (Duty Officer, Bridge, Rescue, Galley) have nowhere to live. Cron **pattern** exists (daily SAS scrape, weekly accreditation) and should host reminder ticks.

### 1.7 Jobs / cron — **reuse the runner, not the jobs**

`sailingsa/deploy/run-daily-events-scrape.sh`, weekly accreditation sync, standings queue. Add `run-duty-reminders.sh` the same way. Do not add Celery/Redis for v1.

---

## 2. WhatsApp Business API (Cursor REA)

### 2.1 What the Cloud API can do (needed here)

| Capability | Fit |
| --- | --- |
| **Utility template** (pre-approved) | Only legal way to **start** a duty reminder after 24h silence |
| **Quick-reply buttons** on a template | Better than raw “reply 1 or 2”; webhook still receives a button payload |
| **Inbound webhook** (`messages` + `statuses`) | Parse `1` / `2` / button title → acknowledge or snooze |
| **24-hour customer-service window** | Opens on **their** inbound (including button tap). Then free-form / interactive replies allowed |
| **Interactive buttons / lists** inside the window | Confirmation “Acknowledged — Sat 10 Oct, Bridge” |
| Groups / broadcast lists | **Out of scope.** One-to-one only |
| WhatsApp personal / “Business App” (green tick phone) | **Cannot** do reliable 1/2 webhooks. Need Cloud API (or a BSP in front of it) |

User-requested **1 = Acknowledge, 2 = Remind me again** works as:

1. Template body includes the two options.
2. Optional quick-reply buttons with the same meaning (payload `ACK` / `SNOOZE`).
3. Webhook accepts `1`, `one`, `ack`, button `ACK` → acknowledged; `2`, `snooze`, `remind` → snooze (default +24h, cap 1 snooze before race morning).
4. Anything else → one service reply with the same two choices (counts toward the 1 000 free service messages).

A **business-initiated** reminder after the window closes **must** be a template, not free-form “1 or 2”.

### 2.2 Integration options (pick one)

| Option | Pros | Cons | Recommendation |
| --- | --- | --- | --- |
| **A. Meta Cloud API direct** (Graph + webhook on live FastAPI) | Meta list rates; one WABA; we own templates | App review, business verification, display-name, payment method | **v1** |
| **B. BSP** (Twilio / MessageBird / 360dialog / Africa’s Talking) | Faster onboarding, SA support | Markup on every message; extra vendor | Only if verification stalls |
| **C. WhatsApp Business App + shared club phones** | Already how clubs work | No webhook, no ack log, POPIA chaos | **Reject** |
| **D. Per-club WABA numbers** | Club brand | 85 verifications + 85×1 000 free-tier accounting | **Reject** for v1 |

**v1: one SailingSA WABA** (`SailingSA` or `SailingSA Clubs`), one number, messages clearly “{HYC} duty: …”. Club name is in the template variable, not a second number.

### 2.3 Costs (Meta list rates, SA recipients, from 1 Oct 2026)

Official Meta pricing page was not fetchable here (403). Cross-checked SA write-ups dated Sep–Oct 2026 (AmbitX, Whautomate, A2Z, Brunel, Sleekflow):

| Category | USD / delivered | ~ZAR @ 16.5 | Use |
| --- | --- | --- | --- |
| Utility template | **0.0095** | ~R0.16 | Duty reminder, “remind again” |
| Service (free-form in 24h window) | **0.0095** after **1 000 free / number / month** | ~R0.16 | “Thanks, you’re on Bridge” |
| Authentication | 0.0095 | ~R0.16 | Not needed for duty |
| Marketing | 0.0379 | ~R0.63 | **Do not use** for duty (policy + cost) |

Inbound user messages are free. Unused free service units do not roll over. A payment method is required or sends stop after the free tier.

**HYC test-case envelope (order-of-magnitude):**

- ~20 duty weekends × 4 slots × 1 reminder ≈ 80 utility ≈ **$0.76 / season**
- + optional T-24h second ping for non-responders ≈ another 40–80
- Ack confirmations as service replies: HYC fits inside 1 000 free/month

**If all 85 clubs adopted HYC-like volume:** ~7 000 utility/month ≈ **$66** (~R1 100) + service overages if confirmations are chatty. Design confirmations to be **one short service reply** or none (in-app is enough).

**Do not** classify duty reminders as Marketing. Meta can disable the WABA.

### 2.4 Compliance

- POPIA: store `whatsapp_opt_in_at`, source (`registration_prompt` / `club_invite`), and allow STOP.
- Juniors: send to `parent_guardian_id`’s number when age &lt; 18, never to the junior’s login WhatsApp without guardian opt-in.
- Do not message a `provider_id` just because they logged in with it.
- Template review: one `duty_reminder` UTILITY with variables `{{club}}`, `{{role}}`, `{{when}}`, `{{event}}`.

---

## 3. Internal messaging vs `@sailingsa.co.za` email

| Question | Answer |
| --- | --- |
| Can we use `@sailingsa.co.za` as the product inbox? | **No.** No MX. Messages would bounce. |
| Is localhost SMTP production email? | **No.** Media-delete mail is best-effort and silent on failure. |
| Should we host human mailboxes in this project? | **Separate ops ticket.** Zoho Mail (free ≤5 / ~R15–19 pp/mo) or Google Workspace (~R135 pp/mo excl VAT) after adding MX + SPF + DKIM. DMARC already exists (GoDaddy). |
| Should duty mail come from `noreply@sailingsa.co.za`? | Only after a **transactional** provider on a subdomain (`notify.sailingsa.co.za`) so personal inboxes can be added later without mixing. Resend / Postmark / SES. Not Phase 1. |
| What is the product inbox? | **`notifications` table** + club admin board + sailor “My duties” card. Same record fans out to WhatsApp/email. |

**Rule:** In-app is source of truth. WhatsApp is an opt-in channel. Email is a later channel. Never “send email” as the only ack path.

---

## 4. Proven alternatives (why not buy)

| Product | What it solves | Why not as SoT |
| --- | --- | --- |
| WhatsApp group + PDF calendar | What HYC does today | No ack, no SAS match, no results URL |
| Google / Apple Calendar | Personal subscribe | No duty status; use as **ICS output** |
| Spond | Free team duties + push | No SAS events, no `/regatta/{slug}`, another login |
| TeamSnap | Rosters | Paid, US, no SAS |
| Revolutionise | Some SAS events already | External IDs only; not club duty |
| Club-only spreadsheet | Fast for one club | Breaks the 85-club rule |

**Reuse SailingSA for identity, events, results, club pages. Add roster + notify. Export ICS. Optionally speak WhatsApp.**

---

## 5. Recommended architecture (all clubs)

### 5.1 Principles

1. **`club_id` on every new row.** HYC is `WHERE club_id = :hyc`, not a Hermanus schema.
2. **Two layers stay two layers.** SAS/club race → `events` ± `regattas`. Training / external / duty / informal never auto-insert `regattas`.
3. **One season item per weekend cell.** Extra-info fleets are suggestions. Duty names are assignments, not titles.
4. **Named people, not typed SAS IDs in the UI.** Dropdown = scored matches (`sas_id_personal` + profiles + results at this club). IDs stay in JS. Unique SAS-ID / unique high-score name may be **provisionally** linked; ambiguous names wait for the officer. Never overwrite `primary_club` / `club_*`. Calendar raw names stay as evidence.
5. **Claim before create.** Match API across **all** `events`, then Claim / Activate / Add.
6. **Header locked.** Admin board is a `.card` on `/club/{abbrev}`. Sailor view is a `.card` on the sailor profile (and optionally “My duties” on the same club page when logged in as a member).
7. **Live `api.py` (~83k) is the patch target.** Never overwrite with git ~28k.

### 5.2 New tables (additive, nullable FKs)

Do not overload `events.organiser` or `communication_preferences_*`.

```
club_season_items
  item_id          bigserial PK
  club_id          int NOT NULL REFERENCES clubs
  title            text NOT NULL
  start_date       date NOT NULL
  end_date         date
  kind             text NOT NULL
                   -- race | training | external | duty | informal | cruise | ops
  category         text          -- copy of events.category when linked; else club pick
  event_id         int           -- Claim / Activate link; null for club-only
  extra_info       text          -- PDF “A&B racing, 29er” / series hint
  notes            text
  created_by_sas_id text
  created_at       timestamptz

  UNIQUE (club_id, start_date, title)   -- match-check helper, not a UX id

club_duty_roles
  role_id          serial PK
  club_id          int NOT NULL REFERENCES clubs
  role_name        text NOT NULL        -- “Duty Officer”, “Bridge”, …
  sort_order       int
  UNIQUE (club_id, role_name)

club_duty_assignments
  assignment_id    bigserial PK
  item_id          bigint NOT NULL REFERENCES club_season_items
  role_id          int NOT NULL REFERENCES club_duty_roles
  raw_name         text                 -- calendar spelling, always kept
  sas_id           text                 -- null until linked (provisional or confirmed)
  link_status      text                 -- unmatched | provisional | confirmed | rejected
  status           text NOT NULL DEFAULT 'unassigned'
                   -- unassigned | pending | acknowledged | snoozed | declined | no_response
  remind_at        timestamptz
  acknowledged_at  timestamptz
  snooze_count     int DEFAULT 0
  UNIQUE (item_id, role_id)             -- one person per role per weekend (v1)

calendar_person_mentions          -- provenance; never UPDATE in place, append
  mention_id       bigserial PK
  club_id          int NOT NULL REFERENCES clubs
  item_id          bigint REFERENCES club_season_items
  assignment_id    bigint REFERENCES club_duty_assignments
  raw_name         text NOT NULL        -- “Graig Girdlestone”, “Helen”
  role_name        text
  calendar_date    date
  source           text NOT NULL        -- 'club_calendar' | 'officer_typed' | 'import'
  source_ref       text                 -- e.g. HYC Calendar 2026_7, row/weekend
  created_at       timestamptz

calendar_person_matches           -- scored candidates; one mention → many rows
  match_id         bigserial PK
  mention_id       bigint NOT NULL REFERENCES calendar_person_mentions
  sas_id           text                 -- null if no person yet
  display_name     text
  score            numeric(4,3)
  method           text                 -- sas_id_exact | name_unique | name_fuzzy
                                        -- | name_alias | results_club | rejected
  rank             int
  decision         text                 -- candidate | provisional | confirmed | rejected
  decided_by_sas_id text
  decided_at       timestamptz
  notes            text

club_affiliation_proposals        -- only when sailor club is unknown
  proposal_id      bigserial PK
  sas_id           text NOT NULL
  proposed_club_id int NOT NULL REFERENCES clubs
  mention_id       bigint REFERENCES calendar_person_mentions
  status           text NOT NULL DEFAULT 'proposed'
                   -- proposed | accepted | declined
  decided_by_sas_id text
  decided_at       timestamptz
  -- UNIQUE (sas_id, proposed_club_id) WHERE status = 'proposed'

notifications
  notification_id  bigserial PK
  sas_id           text NOT NULL
  club_id          int NOT NULL
  assignment_id    bigint
  item_id          bigint
  kind             text NOT NULL        -- duty_reminder | duty_ack | event_claim …
  title            text NOT NULL
  body             text
  read_at          timestamptz
  created_at       timestamptz

notification_deliveries
  delivery_id      bigserial PK
  notification_id  bigint NOT NULL
  channel          text NOT NULL        -- inapp | whatsapp | email
  provider_message_id text
  status           text                 -- queued | sent | delivered | failed | replied
  payload          jsonb
  created_at       timestamptz

whatsapp_opt_ins
  sas_id           text PRIMARY KEY
  e164             text NOT NULL        -- +2782…
  opted_in_at      timestamptz NOT NULL
  source           text
  stopped_at       timestamptz

calendar_feed_tokens
  token            text PRIMARY KEY     -- unguessable
  sas_id           text NOT NULL
  club_id          int                  -- null = all my clubs
  created_at       timestamptz
```

**Seed `club_duty_roles` per club on first use**, not globally: HYC gets Duty Officer / Bridge / Rescue / Galley. Another club may only want Race Officer / Beach. Super-admin can copy a template; never hardcode HYC names in API.py.

**`events` / `regattas` changes (flags only):**

| Column / behaviour | Why |
| --- | --- |
| `POST …/claim` `create_regatta` default **false**; true only for Activate on `kind=race` | Stops training/external minting slugs |
| `POST …/claim` `assign_host` default **false** for Claim SAS Event | Stops stealing ZVYC / LDYC hosts |
| `POST /api/club/events` `create_regatta` default **false** | Club-only calendar rows |
| Optional `events.club_kind` | Only if we skip `club_season_items` — **don’t**. Season items are the overlay |

### 5.3 APIs (all `admin_club_id == :club` unless noted)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/club/events/match?name=&start=&end=` | All-`events` token + ±3-day match. Returns name, dates, category, **host display name**, `event_id`, `regatta_id` |
| POST | `/api/club/season-items` | Add club-only or linked item. `create_regatta` only if `kind=race` and officer confirms |
| POST | `/api/club/events/{id}/claim` | Existing; add flags above |
| GET | `/api/club/{abbrev}/season` | Public: race/training/external cards already on the page + (members only) duty strip |
| GET/PUT | `/api/club/{abbrev}/duty-roles` | Club catalog |
| GET/POST/PATCH | `/api/club/{abbrev}/duties` | Assign / status. Admin sees counts: acknowledged / snoozed / pending / unassigned. POST body is a **name** (or chosen SAS from the picker), never a typed raw id field. |
| GET | `/api/club/{abbrev}/people/match?name=` | Score `sas_id_personal` + profiles + results. Returns ranked candidates + club-known / club-unknown. |
| POST | `/api/club/{abbrev}/people/choose` | Officer confirms a candidate (`mention_id`, `sas_id`). Writes match decision + optional affiliation proposal. |
| POST | `/api/club/{abbrev}/people/propose-club` | Accept/decline `club_affiliation_proposals` only. Never PATCHes `sas_id_personal` unless accepted **and** all club slots were empty. |
| POST | `/api/club/{abbrev}/duties/{id}/remind` | Queue reminder now |
| GET | `/api/me/duties` | Logged-in sailor: my slots + status |
| POST | `/api/me/duties/{id}/ack` | In-app 1 |
| POST | `/api/me/duties/{id}/snooze` | In-app 2 |
| GET | `/api/me/notifications` | In-app inbox |
| GET | `/cal/{token}.ics` | Personal calendar (events + duties). No session cookie (token is the secret) |
| GET | `/api/whatsapp/webhook` + POST | Meta verify + inbound 1/2 |
| POST | `/api/me/whatsapp/opt-in` | Store E.164 + consent |

Reuse unchanged: `/api/club/me`, fleet/entry/ingest/publish, `/api/events`, public club HTML. Super Admin is allowed on every write when `is_super_admin`; club officers only when session club equals the path club.

### 5.0 Retire `/club-manage` (after verify — do not duplicate)

Live `GET /club-manage` (~20355) and `/club-manage-preview` (~20556) are **not** the officer home. After Phase A is verified on at least two club pages as Super Admin (`/club/hyc` and `/club/zvyc`):

| URL | After retirement |
| --- | --- |
| `GET /club-manage` | 302: Super Admin → **`/clubs`**; `club_admin` / `club_manager` → **`/club/{their-abbrev}`**; sailor → `/clubs`; anon → `/login.html?returnTo=/club-manage` (then the same redirect) |
| `GET /club-manage-preview` | Same 302 (do not keep a second UI) |
| `POST /api/club/events`, `…/claim`, fleets, entries, ingest, publish | **Keep.** Club-page JS calls these. No parallel “manage” API set |

Do **not** retire the routes until the club-page wizard has completed Claim, Activate, and Add (no-regatta informal) as Super Admin on two clubs. Bookmark `/club-manage` must not 404.

### 5.4 UI slots (every `/club/{abbrev}`)

Same chrome as the club-page wizard plan, mapped to **live** cards (`.sa-home-regatta-actions`, Upcoming heading). HYC PDF is how we **test** the slots, not a second layout.

| Who | Slot | Control |
| --- | --- | --- |
| Super Admin (any club) or officer of **this** club | Upcoming heading | **Add New Event** |
| Same | Card actions | **Claim SAS Event** / **Activate Club Event** / **Manage** |
| Same | New `.card` below Upcoming, above Past/Sailors | Wizard (after a choice) **or** Duty board |
| Same | Duty board table | Role, **calendar name**, suggested sailor (named dropdown), match confidence, status pill, Remind |
| Same | Unmatched names | “Needs confirmation” + **Propose {club} as club** only when affiliation is empty |
| Logged-in sailor assigned here (not necessarily officer) | “My duties” `.card` | Weekend, role, Acknowledge / Remind me again |
| Visitor / other sailors | Unchanged Upcoming / Past / Other / Sailors | Public only |

Wizard steps for `kind=race` stay Details → Fleets → Registration → Entries → Upload → Publish. Other kinds stop after Details (and duty assignments).

### 5.5 Reminder state machine

```
unassigned
   → admin assigns sas_id → pending, remind_at = T-72h (club default)
        → sailor/WhatsApp 1 → acknowledged
        → sailor/WhatsApp 2 → snoozed, remind_at += 24h, snooze_count++
        → cron at remind_at → send notification + optional WhatsApp template → still pending
        → T-0 with no ack → no_response (admin filter)
```

Admin filters: **Acknowledged** / **Needs reminding** (snoozed or remind due) / **No response** / **Unassigned**.

### 5.6 Personal calendar

`GET /cal/{token}.ics` includes:

- Season items where I am assigned, or `kind=race` at my clubs I opted to follow
- Claimed external events I starred (v2)
- Timed as all-day (clubs do not have start_time on most rows)

Subscribe in Google / Apple. One token per sailor; rotate on logout-all. This is the “personal calendar” — do not build a full-month JS calendar in v1.

---

## 6. Intelligent SAS matching (all clubs)

Reuse the existing token/keyword helper. New match API is host-agnostic.

| Result | Officer action | `regattas` |
| --- | --- | --- |
| Same host as this club, no slug, `kind` would be race | **Activate Club Event** | Yes, if confirmed |
| Other host / Unassigned SAS row | **Claim SAS Event** | No (link `event_id` only) |
| No row | **Add New Event** | Only if `kind=race` |
| Training / informal / cruise / ops | Add season item | No |
| Duty names | Assignment rows | No |

HYC 2026/27 fixtures (full table in `docs/HYC_CALENDAR_CLUB_PAGE_PLAN.md`) become **seed data for the HYC test case**, loaded by the officer through the same wizard every other club will use. No `if club == HYC` branches.

Date mismatches (PDF 29er Nats in March vs SAS April; Agulhas April vs October; missing TWK Classic) stay **officer picks the SAS row**.

---

## 6B. Calendar names → sailor profiles and club proposals (all 85 clubs)

Duty and season cells carry **people’s names**, not SAS IDs (HYC PDF: “Peter du Preez”, “Kevin Weaving”, “Graig Girdlestone”). Match those strings to existing sailors. The **roster club** (HYC on the first test case, ZVYC/TSC/… on every other club page) may be **proposed** only when the sailor has **no** club on file. Same tables and routes for all 85 clubs. No `if club == HYC`.

### What we match against (reuse)

| Source | Use |
| --- | --- |
| `sas_id_personal` (`first_name`, `last_name`, `full_name`, `sa_sailing_id`) | Canonical person |
| Sailor profiles (`GET /api/member/{sa_id}`, public `/sailor/{slug}`) | Same identity; show avatar + known club in the picker |
| `results` helm/crew at this `club_id` | “Helen at HYC” rule already in `docs/README_SAS_ID_MATCHING_LOGIC.md` |
| `name_alias`, `sailor_helm_aliases` | Nicknames / spelling (Pete/Peter, Deverson/Deversen) |
| Existing fuzzy scorer | `docs/README_SAS_ID_MATCHING.md`: trigram + surname + nickname + **club bonus 0.12**. Auto-apply today is score ≥ 0.90 and margin ≥ 0.06 (`fuzzy_auto`) |
| `GET /api/match/review/{regatta_id}` / `POST /api/match/choose` | Pattern only — new routes are club-scoped, not result-row-scoped |

Do **not** reuse sail-number or family ±10 rules here (no sail on a duty cell). Do **not** write `results.helm_sa_sailing_id` from a duty match.

### Confidence and what may be automatic

| Tier | How we know | Assignment `sas_id` | Club affiliation |
| --- | --- | --- | --- |
| **A — Exact unique SAS-ID** | Calendar/import string is digits that equal exactly one `sa_sailing_id`, **or** officer paste of a unique SAS ID | **Provisional link** (`link_status=provisional`). Reminders wait until confirmed **or** the sailor acks (ack = confirm). | If `primary_club` and `club_1`…`club_5` are all empty → **propose** roster club. If any club is set → **leave as-is**. |
| **B — Unique name** | One candidate, score ≥ 0.90, margin ≥ 0.06 (same thresholds as results `fuzzy_auto`) | Provisional link, same as A | Same propose-if-unknown rule |
| **C — Ambiguous** | 0 candidates, or ≥2 within 0.06, or first-name-only with more than one hit at this club | `sas_id` stays null. Officer must choose. | No proposal until a person is chosen |
| **D — No person** | Normalised name matches nobody | Keep `raw_name`. Offer “create temp / add sailor” later — **not** a fake SAS ID | No club write |

Provisional is **not** silent membership. The duty board shows the suggested profile (name + avatar + SAS). Officer can reject. WhatsApp / email reminders for that slot stay off until `link_status=confirmed` **or** the sailor acknowledges in-app (which confirms the link).

### Never overwrite an existing club

A sailor “has a club” when any of `primary_club`, `club_1`…`club_5` is non-empty (after trim). Then:

- Still link the **assignment** to their `sas_id` (they can do duty at a club that is not their home club).
- **Do not** UPDATE `sas_id_personal` club columns.
- **Do not** insert `club_affiliation_proposals`.
- **Do not** rewrite `people_club_history`.

If all club slots are empty (“unknown”):

- Insert `club_affiliation_proposals` (`proposed_club_id` = the roster’s `club_id`, `status=proposed`).
- Officer sees “Propose **{club abbrev}** as club — evidence: {calendar}, {date}, {role}”.
- **Accept** fills the first empty slot (`primary_club` / `club_1` only if still empty at accept time; re-check). **Decline** leaves profile untouched.
- If another process filled a club between propose and accept, accept is a no-op and the proposal is marked `declined` with note `already_affiliated`.

HYC on the 2026/27 PDF is how we **test** “propose roster club”. ZVYC using the same board proposes **ZVYC**, not HYC.

### Provenance (calendar is evidence)

Every raw string is stored once and never overwritten:

1. `calendar_person_mentions` — who appeared, which weekend, which role, which source file/row (`source_ref`).
2. `calendar_person_matches` — every scored candidate (not just the winner). Decisions **append** (`candidate` → `provisional` / `confirmed` / `rejected`). Do not UPDATE a score row in place; insert a new decision row or set `decision` only with `decided_by` + `decided_at`.
3. `club_affiliation_proposals.mention_id` — why we thought they belong to this club.

Admin UI: “Matched to Kevin Weaving (SAS …) from HYC calendar 10 Oct 2026, Rescue — score 0.94 unique name.” Rejecting a match keeps the mention so a later officer can rematch.

Do not delete mentions when a season item is edited; set item_id and add a new mention if the name changes.

### Worked HYC examples (same engine, any club)

| Calendar text | Likely tier | Club |
| --- | --- | --- |
| Kevin Weaving (unique profile + results at HYC) | B provisional | If he already has HYC (or any club) → no proposal. If empty → propose HYC |
| Cheryl Deverson / Tim Deversen (alias + results) | B or C if two Deversons | Confirm if margin thin |
| Helen (first name only) | C — same as matching-logic rule 4 | Officer picks |
| Graig Girdlestone (typo vs Craig/Graig) | C unless one fuzzy candidate clears 0.90/0.06 | Officer picks |
| Volunteer crews / No galley | Skip — not a person | — |

### APIs (club-scoped)

`GET /api/club/{abbrev}/people/match?name=` returns:

```
{ raw_name, candidates: [{ sas_id, display_name, score, method, club_known, club_display }],
  can_provisional, can_propose_club }
```

`sas_id` is in JSON for the chooser `value` only — the officer sees **names**. `POST …/people/choose` writes mention + match + optional proposal. Super-admin can rematch; club admin only for their `club_id`.

---

## 7. Gaps vs reuse (checklist)

| Need | Reuse | Gap |
| --- | --- | --- |
| Club officer ACL | `admin_club_id` + `is_super_admin` | Super Admin already exists (13). Officers for the other 83 clubs, including HYC, optional once Super Admin can dogfood |
| `/club-manage` UI | Live GET + Phase 2–5 APIs | Retire UI after verify; APIs stay; Super Admin redirect = `/clubs` |
| Member picker | `sas_id_personal.club_*` + results | No “club members” API yet |
| Calendar name → sailor | Fuzzy scorer, `name_alias`, `GET /api/match/review` pattern | Club-scoped match + mention/match tables |
| Club proposal when unknown | `primary_club` / `club_1`…`5` (read) | `club_affiliation_proposals`; accept must not overwrite |
| Event match | Keyword helper + `GET /api/events` | Cross-host match route |
| Club-only calendar | — | `club_season_items` + `create_regatta=false` |
| Duty | — | roles + assignments + `raw_name` + `link_status` |
| In-app notify | Avatars, session | `notifications` + sailor card |
| WhatsApp send/receive | Login digits | WABA, opt-in, webhook, templates |
| Email | `MAIL_FROM` string | MX + provider |
| Personal calendar | Dates on events | ICS token |
| Reminders | Deploy cron style | `run-duty-reminders.sh` |
| Carioca / missing classes | `classes` + aliases | Do not auto-insert (already a rule) |

---

## 8. Consolidated implementation plan (plan only)

One sequence. Schema is multi-club from day one. Super Admin can verify every phase on any `/club/{abbrev}` without a Hermanus officer account. Club officers, when present, stay scoped to `admin_club_id`. §6B is Phase B, not a later add-on.

```
0 ACL + Super Admin on club pages
  → A events + season overlay + SAS match + wizard on /club/{abbrev}
  → A✓ verify then retire /club-manage (redirect; keep APIs)
  → B duties + §6B name match + in-app 1/2
  → C personal ICS
  → D WhatsApp (one WABA)
  → E email (optional, after MX)
  → F more clubs / public roster opt-in
```

### Dependencies

| Phase | Depends on | Blocks |
| --- | --- | --- |
| **0** | Live `user_accounts.role`, `GET /auth/session`, `GET /api/club/me` | All UI |
| **A** | 0; existing claim/create APIs; `events` scrape; keyword matcher | A✓, B, C |
| **A✓** | A verified on ≥2 clubs as Super Admin | Must finish before deleting `/club-manage` HTML |
| **B** | A (`club_season_items`); §6B tables; fuzzy scorer / `name_alias` | D (nothing to ack) |
| **C** | A + B assignments | — |
| **D** | B confirmed links + `whatsapp_opt_ins` | — |
| **E** | B notifications table; real MX or `notify.` provider | Never blocks A–D |
| **F** | A✓ + B stable | — |

Do not start D or E before B. Do not implement a Hermanus-only branch.

### Phase 0 — ACL (no new product tables)

**Build**

- Gate wizard / duty chrome with `GET /api/club/me`: `is_super_admin` **or** (`is_club_admin` and `admin_club_id` == page club).
- All club write APIs: Super Admin = yes for the **URL** club; officer = session club only.
- Super Admin landing for “manage” = `/clubs` (existing directory). They open `/club/hyc`, `/club/zvyc`, … and get the full wizard on each.

**Cost:** engineering only.

**Verify:** Super Admin sees Activate/Add on `/club/hyc` and `/club/zvyc`. ZVYC officer sees them only on `/club/zvyc`. Logged-out `/club/hyc` unchanged.

### Phase A — Events + club calendar (no duty, no WhatsApp)

**Build**

- `club_season_items`; `GET /api/club/events/match`; `create_regatta` / `assign_host` flags on claim/create (default false).
- Club-page chips: Claim SAS Event / Activate Club Event / Add New Event + wizard `.card` (Details → Fleets → … only for `kind=race`).
- No `regattas` for training, external, informal, cruise, ops.

**Reuse:** `POST /api/club/events`, `POST …/claim`, `GET /api/club/me/events` (scoped to **page** club), keyword match, `events.category`.

**HYC test (Super Admin on `/club/hyc`):** Activate HYC Cape Classic 2027 (SAS 380677); Claim ZVYC Cape Classic (do not steal host 3); Add Informal without a slug.

**Cost:** engineering only.

### Phase A✓ — Retire `/club-manage`

**Gate:** Phase A verify on `/club/hyc` **and** `/club/zvyc` as Super Admin (Claim, Activate, Add-without-regatta).

**Then:** `GET /club-manage` and `/club-manage-preview` → 302 as in §5.0. Keep every `/api/club/…` route. Do not add a replacement dashboard.

**Cost:** engineering only.

### Phase B — Duties + §6B matching + in-app 1/2

**Build (includes all of §6B)**

- `club_duty_roles`, `club_duty_assignments` (`raw_name`, `link_status`), `calendar_person_mentions`, `calendar_person_matches`, `club_affiliation_proposals`, `notifications`.
- Name → `sas_id_personal` + profiles: unique SAS-ID / unique ≥0.90+margin → **provisional**; ambiguous → officer confirm.
- Propose **roster club** only when `primary_club` and `club_1`…`5` are empty. Never overwrite. Mentions are evidence; do not delete on rematch.
- Admin board: acknowledged / needs reminding / no response / unassigned.
- In-app 1 = Acknowledge, 2 = Remind me again. WhatsApp off.

**Reuse:** fuzzy scorer, `name_alias`, avatars, `/api/match/choose` pattern.

**HYC test:** 10–11 Oct weekend, four roles; one unique name, one “Helen”, one unknown-club proposal. Super Admin can run the same on `/club/zvyc` with ZVYC as the proposed club.

**Cost:** engineering only.

### Phase C — Personal calendar

**Build:** `calendar_feed_tokens`, `GET /cal/{token}.ics` (my events + my duties).

**Depends on:** A items + B assignments.

**Cost:** engineering only.

### Phase D — WhatsApp

**Build:** One SailingSA WABA; Utility `duty_reminder`; opt-in; webhook 1/2; `run-duty-reminders.sh`; `WHATSAPP_ENABLED=0` kill switch.

**Depends on:** B confirmed (or ack-confirmed) links. Do not message `login_method=whatsapp` without opt-in.

**Cost:** $0 platform + **USD 0.0095**/utility; HYC test &lt; $2/month; 85-club mature ~$50–80/month. 1 000 free service replies/number/month.

### Phase E — Email (optional)

**Build:** Channel on `notification_deliveries` only after MX or `notify.sailingsa.co.za` provider. Human `@sailingsa.co.za` mailboxes are a **separate** Zoho/Workspace ticket (today: **no MX**).

**Cost:** transactional free tier then ~$10–20/mo; Workspace ~R135 pp/mo if humans need mail. Never blocks A–D.

### Phase F — Roll-out

Second officer club (ZVYC already has `club_admin`), per-club reminder offsets and role names, optional public roster. Super Admin remains able to manage any of the 85.

### Cost roll-up

| Phase | Money |
| --- | --- |
| 0, A, A✓, B, C | Time only (existing VM + Postgres) |
| D | Meta list rates above |
| E | Provider + optional human mailboxes |
| Buy Spond/TeamSnap | Rejected |

---

## 9. Cost sheet (order of magnitude)

See §8 roll-up. Detail:

| Item | When | Money |
| --- | --- | --- |
| Engineering 0–C | After approval | Time only (existing VM + Postgres) |
| Meta Cloud API | Phase D | $0 platform fee + **$0.0095**/utility; HYC test &lt; $2/month |
| 85-club mature duty volume | Later | ~$50–80/month utility if widely used |
| BSP | Only if D stalls | Extra markup — avoid |
| Google Workspace / Zoho for humans | Separate from E | R0–135 pp/mo; not required for duty |
| Transactional email | Phase E | Free tier then ~$10–20/mo |
| Spond/TeamSnap | Rejected | Would duplicate login and lose SAS |

---

## 10. What we will not do

- HYC-only tables, routes, or `if abbrev == 'hyc'`
- Auto-`regattas` for training, external, duty, informal, cruise, Christmas, work weekend
- Overwrite `primary_club` / `club_1`…`club_5` because a roster listed the sailor
- Invent a SAS ID for an unmatched calendar name
- Auto-confirm ambiguous names (Helen, duplicate surnames, low margin)
- Delete calendar mention rows after a rematch
- Host steal on Claim SAS Event
- Message WhatsApp logins without opt-in
- Treat `@sailingsa.co.za` as a working mail system
- Add header/nav notification chrome
- Keep `/club-manage` as a second Event Management UI after A✓
- Limit Super Admin to `admin_club_id` or one “home” club
- Replace `/club/{abbrev}` with `/club-manage`
- Rewrite slugs or the three scoring pilots
- Auto-insert missing classes (Carioca)
- Marketing-category WhatsApp templates
- Per-club WhatsApp numbers in v1
- Use `api/app.py` or `communication_preferences_*` as the notify stack

---

## 11. Approval

Reply to implement **Phase 0 + A only** (Super Admin on any club page + season overlay + match + claim flags). Super Admin can dogfood `/club/hyc` without a Hermanus officer. Retire `/club-manage` only after A✓.

This document is not a licence to code WhatsApp, email hosting, club-column overwrites, a Hermanus-only roster, or a replacement `/club-manage` until you say so.
