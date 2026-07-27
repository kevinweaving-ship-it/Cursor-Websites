# Public Regatta Mentions — Data Model (Conceptual / Schema Only)

**Purpose:** Prepare the structure for public regatta coverage (media & links). Regatta is the primary owner of public mentions. Sailor pages will later inherit coverage via participation only — no sailor-level storage of mentions.

---

## 1. Regatta entity

Already exists. See `docs/README_regattas_table.md`. No changes required for this prep.

---

## 2. RegattaMention entity (conceptual schema)

Use for future regatta-level public coverage. Names may vary; logic must match.

| Field | Type | Description |
|-------|------|-------------|
| `regatta_id` | FK → regattas | Regatta this mention belongs to. |
| `source_url` | TEXT | Canonical URL of the mention (article, post, photo, video). |
| `source_domain` | TEXT | Domain of the source (e.g. `sailing.org.za`, `facebook.com`). |
| `platform` | TEXT | `web` \| `facebook` (no other platforms without explicit design). |
| `content_type` | TEXT | `results` \| `article` \| `photo` \| `video`. |
| `title` | TEXT | Short title for display. |
| `short_summary` | TEXT | One-line context / summary. |
| `first_seen` | TIMESTAMP | When we first recorded this mention. |
| `last_verified` | TIMESTAMP | Last time we verified the link/content. |
| `status` | TEXT | `active` \| `inactive`. |
| `engagement_allowed` | BOOLEAN | `true` only for Facebook **Pages**; see Facebook rules below. |

**Constraints (conceptual):**

- No sailor-level storage of mentions. Sailors inherit visibility of mentions only through participation in a regatta (derived at read time).
- Unique constraint on `(regatta_id, source_url)` (or equivalent) when implementing.

---

## 3. Facebook handling rules (guardrails for future work)

**These rules MUST be reflected in code comments and any implementation:**

1. **Storage level**  
   Facebook URLs may be stored **only at regatta level** (e.g. in `RegattaMention` with `platform = 'facebook'`). Never store Facebook mention rows keyed by sailor.

2. **Engagement**  
   **Only Facebook Pages** allow engagement.  
   Facebook Groups and personal profiles are **record-only** (we may store links/metadata, but no likes, shares, or other engagement).

3. **No automation**  
   No automated Facebook actions will ever be implemented (no auto-like, auto-share, auto-comment, etc.). This is a read-only, factual public sports archive.

4. **Inheritance**  
   Sailor public pages show mentions only by inheriting from regattas they participated in — no separate sailor-level crawling or storage for Facebook (or any platform).

---

## 4. Design principle

This is a **factual public sports archive**, not a social network. Everything must stay:

- **Read-only**  
- **Neutral**  
- **Regatta-centric**

Sailor pages inherit coverage; they do not own or store their own mention rows.
