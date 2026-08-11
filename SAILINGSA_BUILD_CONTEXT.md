# SailingSA — Overall Build Context (living)

Last updated: 2026-08-11 (Cursor catch-up after Trae)

This file tracks **what we are building**, **what is agreed/locked**, and **which ChatGPT chats matter**.  
Chat **titles/URLs** come from Chrome history (169 ChatGPT chats total; ~22 clearly SailingSA-titled). Full message bodies still need Accessibility (or paste) — see bottom.

---

## 1) Product in one sentence

**South African sailing results + rankings platform**, expanding into **event ops / club ops** so clubs can replace WhatsApp spreadsheets — flagship target **Youth Nationals 2026 ops** (iterative; HYC first).

---

## 2) LOCKED core (do not destabilize)

From Master Spec + live platform:

- `race_results` = **single source of truth**
- Appendix A fleet scoring engine = scoring authority
- Event states: `upcoming → live → completed → archived`
- No stored overall standings — calculate on save
- Sailor Identity Engine (SIE): SAS ID, OFFICIAL / PROVISIONAL
- Scraping governance / anti-duplication locked
- Internal results only (PDFs not authoritative)
- **Mobile portrait = SSOT** for UI (PC shows mobile modules; no desktop redesign)
- Gold Header is sacred — no collateral header edits
- Micro-edit deploy: SCP full `api.py` only; visual verify; no regex SSH patches  
  (see `AGENTS.md`)

### Navigation / lists (user rule)
Every meaningful datum clickable to its entity page; all lists: search, sort, URL state, row click, mobile-first 44px targets.

---

## 3) Version roadmap (agreed)

| Ver | Scope | Status |
|-----|--------|--------|
| **V1** | Sailors, events, fleets, results, regatta/sailor/class/club pages, rankings | **Live baseline** |
| **V2** | Event Entry & Admin: registrations, payment ledger (private), docs+ack, noticeboard, org dashboards/exports | **Next major build** |
| **V3** | Volunteers & Officials by SAS ID; service record on sailor profiles; public Officials tab | Planned |
| **V4** | Galley / meals | Planned |
| **V5** | Accommodation / camping / gate lists | Planned |
| **V6** | Club ops / training weekends | Planned |
| **V7** | Comms automation (FB/email; WhatsApp later) | Planned |
| **V8** | TSL integration | Planned |
| **V9+** | Full club OS | Later |

**Immediate delivery intent:** V2 MVP → feature-flag on a small HYC/training event → then V3.

---

## 4) What Trae built recently (Aug 8–11) — current front of work

Active workspace: `~/Desktop/sailingsa-clean`  
Edit source: `api.py.V26_EDIT_SOURCE_COPY.py`

| Area | Agreed / done | Still open |
|------|----------------|------------|
| Gold header restore | Restored after regressions | Leave alone |
| `/api/search` SAS-ID fast path | ~31× faster | Keep |
| `/dev-1/` sandbox | Mobile profile prototype + layout editor | Continue |
| Verified sailor badge | Green seal on avatar; DB-gated | Placement still fussy |
| Provinces | 9 in `app.provinces` + colors; clubs mapped | Province icon layout (avatar L / pin R) |
| Class URL audit | Slug/ID bugs found | Fix when scheduled |

---

## 5) Most recent ChatGPT chats to keep in context

Ranked by Chrome last-visit (SailingSA-related). Full index:  
`backups/chatgpt_digest/sailingsa_chats_ranked.tsv`

### Hot right now (2026-08-11)
1. **Open Code for SailingSA** — https://chatgpt.com/c/6a793b31-0ab4-83ea-88aa-82a95d98d6ef  
2. **SA Sailing Event Categories** — https://chatgpt.com/c/6a75dc03-d2a8-83ea-b967-a3091e700276  
3. **Loading Time Concern** — https://chatgpt.com/c/6a77a73d-95f0-83ea-87ae-401679188ef3  
4. **Landing Page Analysis** — https://chatgpt.com/c/6a71c4f6-c2a0-83ea-9cad-4eb589eea08d (29 visits)

### Recent product/ops (Aug 4–5)
5. SSL Ranking Issue  
6. SailingSA Traffic Stats  
7. Sponsorship Presentation Suggestions  
8. FB post for SailingSA  
9. Sailing SA New Mar 2026 – Tim and Hayden Sailing  

### Earlier theme chats (still relevant)
10. Ranking System Overview  
11. Fleet Class Division Sailing  
12. Mobile Event Results Optimization  
13. Final Landing Page Review  
14. Regatta Completion Badges  
15. SailingSA Overview (10 visits)  
16. SailingSA Integration Plan  
17. Class Logos (Old/New)  
18. Brass Monkey Regatta / Results  
19. Sailing GPS Tracker Options  

### Canonical offline GPT archive (Feb 2026)
`Desktop/Sailing SA Full Build Spec GPT 20 Feb 26/`  
- `SailingSA_MASTER_SPEC/` (roadmap, data model, URLs, API, permissions, event ops)  
- `GPT chat Feb 2026.txt` (~38k lines)  
- Planning PDFs / zips  

---

## 6) Agreed build themes (across GPT + Trae + specs)

**Platform / UX**
- Mobile-first modules; compact UI; Gold Header parity  
- Entity pages: sailor, club, class, regatta/event, rankings  
- Verified account badge on avatars  
- Province identity (code + color + map-pin icon)  
- Performance: sailor profile / search must stay fast  

**Content / domain**
- Rankings + SAS points explanations  
- Class logos / fleet divisions  
- Event categories taxonomy (active ChatGPT thread)  
- Badges (regatta completion, etc.)  
- Traffic / sponsorship surfaces  

**Event ops (V2→V5)**
- Entry forms + live counts  
- Private payments + public Paid/Outstanding  
- Docs + acknowledgements  
- Noticeboard replacing WhatsApp  
- Volunteers/officials → sailor service record  

---

## 7) Suggested near-term build order (practical)

1. Finish `/dev-1` profile SSOT pieces (badge + province icon) without touching Gold Header  
2. Absorb **Open Code / Landing / Load time / Event categories** GPT conclusions (paste or Accessibility)  
3. Protect performance wins; no regressions on `/sailor/*`  
4. Start **V2 Entry Layer** behind feature flag (per Master Spec)  
5. Keep chat index updated whenever new SailingSA GPT threads appear  

---

## 8) Mobile module workflow (vibe / phone)

**Use case:** On phone, pass an event result (photo / PDF / text / Sailwave export).  
Agent must: match to existing regatta/event URL → update `race_results` → show live on sailingsa.co.za.

**How (simple):**
1. Cursor mobile → repo `Cursor-Websites` → branch `sailingsa-clean`
2. One module per chat, e.g. “Ingest Brass Monkey Day 2 results → match `/regatta/...` → update live”
3. Keep model **Auto**, Max Mode **off** (credits)

**Agent must follow:**
- Match existing event by date/name/club — do **not** invent duplicate regattas
- Write into `race_results` (SSOT); never treat PDF as authority after ingest
- Confirm live URL after update
- No Gold Header / unrelated UI edits in a results module

**Cloud agents need** Cursor Dashboard secrets for live SSH/DB (Mac has `~/.ssh/sailingsa_live_key`; cloud must have the same secret configured once).

---

## 9) Tracking ritual (so Cursor stays aligned with GPT)

Until Accessibility is enabled for Cursor→Chrome:

- Say **“digest active”** after focusing a ChatGPT tab → I’ll copy/save when permissions allow  
- Or paste key **Agreed:** bullets into this file / chat  

With Accessibility ON:

- I can Cmd+A/C active chat → append under `backups/chatgpt_digest/` and update this context  

Chrome history index refreshes anytime from:  
`backups/chatgpt_digest/chrome_chatgpt_history.tsv`
