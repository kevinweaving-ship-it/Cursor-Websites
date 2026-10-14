# Club Event + Calendar + Duty Roster + Messaging — unified plan

**Status:** Plan only. Do not code or deploy until this document is approved.

**Date:** 14 October 2026.

**Scope:** Every SailingSA club (`GET /api/clubs` = **85** clubs). **HYC is the first test case**, not a Hermanus-only product. Do not implement the HYC PDF path in isolation.

**Depends on (do not replace):**

- `docs/CLUB_PAGE_EVENT_WIZARD_PLAN.md` — officer home is `/club/{abbrev}`
- `docs/HYC_CALENDAR_CLUB_PAGE_PLAN.md` — first-club checklist, SAS match, no auto-`regattas` for training / external / duty
- `docs/CLUB_EVENT_SELF_SERVICE_PLAN.md` — Phases 1–5 already live (permissions, claim/create, entries, ingest, publish)

**Ask:** Approve the architecture, tables, APIs, WhatsApp/email decisions, costs, and phases before any implementation.

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

club_duty_assignments ──► notifications (in-app, always)
                       ├─ optional WhatsApp Cloud API (opt-in, reply 1 / 2)
                       └─ optional email later (only after real MX)

sailor personal calendar ──► signed ICS feed of my events + my duties
club admin board ──► who acknowledged / needs remind / no response
```

**Officer home stays `/club/{abbrev}`.** Visitors keep today’s club page. Header / nav stay locked (no new header bell unless separately authorised).

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
| `GET /api/club/me` | `admin_club_id`, `club_abbrev` | Officer gate on `/club/{abbrev}` |
| `sas_id_personal` | Name, `club_1`…`club_5`, `primary_club`, `email`, `phone_primary` / `phone_secondary`, `parent_guardian_id` | Resolve who a duty name is; junior → parent for WhatsApp |
| Live roles | sailor ~69, super_admin 13, HMYC `club_manager` (98), ZVYC `club_admin` (3) | **HYC has no officer yet** — prerequisite for the test case |
| `POST /auth/login`, `POST /api/register-account` | WhatsApp number required at register | Source of digits; still need opt-in |

**Do not reuse as ACL:** `sas_id_personal.commodore` / `club_secretary` / `communication_preferences_1`–`4` (documented **empty**). `member_roles` + `roles` are SA **qualifications** (Instructor, Judge) via `GET /api/member/{sa_id}/roles` — display only, not duty roster.

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
4. **Named people, not typed SAS IDs in the UI.** Dropdown = club members (from `sas_id_personal.club_*` + results at this club + registered users). IDs stay in JS.
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
  sas_id           text                 -- null = unfilled slot
  status           text NOT NULL DEFAULT 'unassigned'
                   -- unassigned | pending | acknowledged | snoozed | declined | no_response
  remind_at        timestamptz
  acknowledged_at  timestamptz
  snooze_count     int DEFAULT 0
  UNIQUE (item_id, role_id)             -- one person per role per weekend (v1)

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
| GET/POST/PATCH | `/api/club/{abbrev}/duties` | Assign / status. Admin sees counts: acknowledged / snoozed / pending / unassigned |
| POST | `/api/club/{abbrev}/duties/{id}/remind` | Queue reminder now |
| GET | `/api/me/duties` | Logged-in sailor: my slots + status |
| POST | `/api/me/duties/{id}/ack` | In-app 1 |
| POST | `/api/me/duties/{id}/snooze` | In-app 2 |
| GET | `/api/me/notifications` | In-app inbox |
| GET | `/cal/{token}.ics` | Personal calendar (events + duties). No session cookie (token is the secret) |
| GET | `/api/whatsapp/webhook` + POST | Meta verify + inbound 1/2 |
| POST | `/api/me/whatsapp/opt-in` | Store E.164 + consent |

Reuse unchanged: `/api/club/me`, fleet/entry/ingest/publish, `/api/events`, public club HTML.

### 5.4 UI slots (every `/club/{abbrev}`)

Same chrome as the club-page wizard plan, mapped to **live** cards (`.sa-home-regatta-actions`, Upcoming heading). HYC PDF is how we **test** the slots, not a second layout.

| Who | Slot | Control |
| --- | --- | --- |
| Admin of this club | Upcoming heading | **Add New Event** |
| Admin | Card actions | **Claim SAS Event** / **Activate Club Event** / **Manage** |
| Admin | New `.card` below Upcoming, above Past/Sailors | Wizard (after a choice) **or** Duty board |
| Admin | Duty board table | Role, sailor (named dropdown), status pill, Remind |
| Logged-in member of this club | “My duties” `.card` | Weekend, role, Acknowledge / Remind me again |
| Visitor | Unchanged Upcoming / Past / Other / Sailors | No duty names unless the club later opts into a public roster (default **off**) |

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

## 7. Gaps vs reuse (checklist)

| Need | Reuse | Gap |
| --- | --- | --- |
| Club officer ACL | `admin_club_id` | Officers for the other 83 clubs, including HYC |
| Member picker | `sas_id_personal.club_*` + results | No “club members” API yet |
| Event match | Keyword helper + `GET /api/events` | Cross-host match route |
| Club-only calendar | — | `club_season_items` + `create_regatta=false` |
| Duty | — | roles + assignments + status |
| In-app notify | Avatars, session | `notifications` + sailor card |
| WhatsApp send/receive | Login digits | WABA, opt-in, webhook, templates |
| Email | `MAIL_FROM` string | MX + provider |
| Personal calendar | Dates on events | ICS token |
| Reminders | Deploy cron style | `run-duty-reminders.sh` |
| Carioca / missing classes | `classes` + aliases | Do not auto-insert (already a rule) |

---

## 8. Phased implementation (after approval)

HYC dogfoods each phase; schema and routes are already multi-club.

### Phase A — Season overlay + match (no WhatsApp, no duty)

- `club_season_items`, match API, claim/create flags
- Club-page Claim / Activate / Add on **any** `/club/{abbrev}`
- No `regattas` unless race + confirm
- Test: HYC Cape Classic 2027 Activate; ZVYC Classic Claim; Informal Add without slug

### Phase B — Duty roster + admin board + in-app 1/2

- `club_duty_roles` (seed on first open), `club_duty_assignments`, `notifications`
- Admin table + member “My duties”
- Remind = in-app only
- Test: HYC 10–11 Oct weekend, four roles, named sailors

### Phase C — Personal ICS

- `calendar_feed_tokens`, `/cal/{token}.ics`
- Test: subscribe HYC member in Google Calendar

### Phase D — WhatsApp (one WABA)

- Meta verification, `duty_reminder` template, opt-in, webhook, cron
- Test: same HYC weekend, 1/2 on a real phone, admin board updates
- Kill switch: `WHATSAPP_ENABLED=0`

### Phase E — Email channel (optional)

- Decide human mailbox hosting **or** transactional-only
- Add MX/SPF/DKIM for `notify.` if sending
- Never block duty on email

### Phase F — Roll out

- Invite second club (ZVYC already has `club_admin`)
- Club-configurable reminder offsets and role names
- Public roster opt-in

**Do not start at Phase D.** Without A–B the WhatsApp replies have nothing to update.

---

## 9. Cost sheet (order of magnitude)

| Item | When | Money |
| --- | --- | --- |
| Engineering Phases A–C | After approval | Time only (existing VM + Postgres) |
| Meta Cloud API | Phase D | $0 platform fee + **$0.0095**/utility; HYC test &lt; $2/month |
| 85-club mature duty volume | Later | ~$50–80/month utility if widely used |
| BSP | Only if A stalls | Extra markup — avoid |
| Google Workspace / Zoho for humans | Separate | R0–135 pp/mo; not required for duty |
| Transactional email | Phase E | Free tier then ~$10–20/mo |
| Spond/TeamSnap | Rejected | Would duplicate login and lose SAS |

---

## 10. What we will not do

- HYC-only tables, routes, or `if abbrev == 'hyc'`
- Auto-`regattas` for training, external, duty, informal, cruise, Christmas, work weekend
- Host steal on Claim SAS Event
- Message WhatsApp logins without opt-in
- Treat `@sailingsa.co.za` as a working mail system
- Add header/nav notification chrome
- Replace `/club/{abbrev}` with `/club-manage`
- Rewrite slugs or the three scoring pilots
- Auto-insert missing classes (Carioca)
- Marketing-category WhatsApp templates
- Per-club WhatsApp numbers in v1
- Use `api/app.py` or `communication_preferences_*` as the notify stack

---

## 11. Approval

Reply to implement **Phase A only** (multi-club season overlay + match + claim flags), with HYC as the first logged-in test club once a Hermanus `admin_club_id` exists.

This document is not a licence to code WhatsApp, email hosting, or a Hermanus-only roster until you say so.
