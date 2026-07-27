# Sailor Profile Tabs & Logged-In Flow (Future Plan)

**Status:** Plan for later cleanup. Not implemented yet.

**Goal:** One consistent newsfeed-style display for sailor info. When a sailor is logged in, the same layout shows their profile by default; search and regatta search drive which content appears in which tab (News24-style).

---

## 1. Same display for sailor (logged in or from search)

- Use the **same** newsfeed/timeline layout for:
  - **Logged-in sailor** when search is clear (default view = their profile).
  - **Searched sailor** when user picks a sailor from the search list.
- No separate “my profile” vs “other profile” UI — one layout, different data source (logged-in `sa_id` vs selected `sa_id`).

---

## 2. Sailor search + clear behaviour

| State | What shows |
|-------|------------|
| **Search clear** + sailor logged in | Logged-in sailor’s profile (Sailor Profile tab content = their info, same tabs: Profile \| Regattas Sailed \| Media \| Activity). |
| **User chooses another sailor** from list | That sailor’s info in the same tabbed layout; logged-in sailor’s info is hidden for as long as that sailor is “selected”. |
| **User clears sailor search** | Return to showing logged-in sailor’s info in the same newsfeed-style display. |

So: “selected sailor” is either the logged-in sailor (when search is clear) or the sailor chosen from search. One place renders that selected sailor’s data.

---

## 3. Regatta search + Regatta tab

| Action | Result |
|--------|--------|
| **User uses Regatta search** | Open the **Regatta** tab and show the regatta search results list there (not in a separate page). |
| **User clears Regatta search** | Regatta tab shows the **logged-in sailor’s** regatta list / results (their “Sailing Career – Regatta History” style content), News24-style. |

So the Regatta tab is either:
- Regatta search results (when user has searched regattas), or  
- Logged-in sailor’s regattas (when regatta search is clear).

---

## 4. Tab metaphor (News24-style)

- **Sailor Profile** (like “Top Stories”) — Selected sailor’s profile: name, career summary, breakdown by class. Default tab when viewing a sailor.
- **Regattas Sailed** (like “SA News”) — Either:
  - logged-in sailor’s regatta list when regatta search is clear, or  
  - regatta search results when user has searched regattas.
- **Media** — Public Mentions & Media for the selected sailor.
- **Activity** — Sailor Activity (by year) for the selected sailor.

Same tab bar; content of each tab depends on:
- Who is “selected” (logged-in vs searched sailor).
- Whether sailor search is clear or a sailor is chosen from the list.
- Whether regatta search is in use (Regatta tab = search results) or clear (Regatta tab = logged-in sailor’s regattas).

---

## 5. Cleanup implied by this plan

- **Single “sailor view” component** — One place that renders tabs + panels; input = `sa_id` (and optionally “is logged-in sailor” for copy/links).
- **Search state** — Track “selected sailor”: either `null`/clear → logged-in sailor, or the sailor chosen from sailor search.
- **Regatta search state** — Track “regatta search active”; when true, Regatta tab shows regatta list; when false, Regatta tab shows logged-in sailor’s regattas.
- **Tab routing** — When user does Regatta search, switch active tab to Regatta and show search results there.

---

## 6. Not in scope of this doc

- Auth / login implementation.
- Exact tab labels (e.g. “Top Stories” vs “Sailor Profile”) — can be tuned later; behaviour above stays the same.

---

*When you implement login and this flow, use this doc as the behaviour spec; then refactor the current sailor + regatta search and tabs to match.*
