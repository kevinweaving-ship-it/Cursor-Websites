# SAS ID Auto-Matching System

## Overview
Automated system for linking regatta participants (helms/crews) to official SA Sailing IDs using fuzzy matching, nickname handling, and club-based scoring.

**Better logic (5 rules, regatta 385 as test):** See **`docs/README_SAS_ID_MATCHING_LOGIC.md`** and run **`scripts/match_results_to_sas_id_better.py`** for: (1) crew same surname as helm + SAS ID, (2) club + similar surname, (3) sail number match, (4) first name only + club, (5) family SAS ID range ±10 (e.g. Kevin Weaving matched → ±10 finds Birgitta Weaving same surname).

## How It Works

### 1. **Auto-Match When Names Are Edited**
When you edit a `helm_name` or `crew_name` field in the inline editor and press Enter, the system automatically:
- Searches for matching SAS IDs using fuzzy name matching
- Scores candidates based on name similarity + club match bonus
- Auto-applies if confidence is high (score ≥ 0.90 with clear margin ≥ 0.06)
- Updates the `helm_sa_sailing_id` or `crew_sa_sailing_id` field

### 2. **Matching Logic**

#### **Name Normalization Functions**
- `norm_name()` - Lowercase, collapse whitespace for trigram similarity
- `norm_letters()` - Strips non-letters, collapses repeats (handles Hensh**e**lwood vs Hensh**i**lwood)
- `surname_key()` - Extracts and normalizes surname for robust matching

#### **Scoring Components**
```sql
score = MAX(
  similarity(typed_name, full_name),           -- Full name trigram match
  similarity(surname_key(typed), surname_key), -- Surname-only match + 0.06 boost
  firstname_nickname_match ? 0.82              -- Nickname/alias match
) + (club_match ? 0.12 : 0)                    -- Club bonus
```

#### **Auto-Apply Thresholds**
- **Score ≥ 0.90** AND
- **Margin ≥ 0.06** (next best candidate at least 0.06 points lower)
- Sets `match_status_helm/crew` = `'fuzzy_auto'`

### 3. **Nickname/Alias Handling**
The `name_alias` table (and matching logic) allows common first-name variants. When matching results to SAS IDs, these are treated as equivalent:

| Base (canonical) | Allowed variants |
|------------------|------------------|
| Harold | Harry |
| Charles | Charlie |
| Peter | Pete |
| Michael | Mike, Mickylo, Mikaeel |
| Nicholas | Nick |
| Walter | Wali |
| Robin | Rob |
| Christian | Chris |
| Stefan | Stevie |
| Petrus | Peet |
| Marthinus | Thinus |
| Hayley | Haley |
| Dylan | Dyllan |
| Caylem | Cayllum, Callum |
| Bastien | Bastian |
| Ashton | Aston |
| Athenkosi | Athi |
| Isabella | Bella |
| Mornay | Morne |
| Zubair | Zubhair |
| Fatier | Fateer |
| Keyuren | Keyruren |
| Joshua | Josh |
| Jan | Jaun |
| Neil | Neill |

**Existing `name_alias` table:**
```sql
base        | variants
------------|-------------------
'benjamin'  | ['ben','benj']
'harry'     | ['harold','harrie']
'michael'   | ['mike','mikel']
'jody'      | ['jodi','jodie']
```
Extend this table for additional nicknames.

### 4. **API Endpoints**

#### **GET `/api/match/review/{regatta_id}`**
Returns unmatched entries with candidate suggestions:
```json
{
  "role": "helm",
  "result_id": 123,
  "typed_name": "Haydn Miller",
  "candidates": [
    {"person_key": "12345", "name": "Hayden Miller", "score": 0.920},
    {"person_key": "67890", "name": "Haydn Mills", "score": 0.780}
  ]
}
```

#### **POST `/api/match/choose`**
Manually select a SAS ID:
```json
{
  "result_id": 123,
  "role": "helm",
  "person_key": "12345"
}
```

#### **POST `/api/match/refresh/{result_id}`**
Manually trigger re-matching for a specific row (useful after editing club or name).

### 5. **Database Views**

- `vw_people_matchable` - Unified view of SAS IDs + temp people
- `vw_people_alias` - Expands first names with nickname variants
- `vw_match_candidates_helm` - Scored helm candidates (score ≥ 0.70)
- `vw_match_candidates_crew` - Scored crew candidates (score ≥ 0.70)
- `vw_match_review` - Ambiguous matches needing manual review

### 6. **Match Status Codes**

| Code | Meaning |
|------|---------|
| `fuzzy_auto` | Auto-matched after name edit (high confidence) |
| `override` | Manually selected via `/api/match/choose` |
| `NULL` | Not yet matched |

## Usage Example

1. **Edit a misspelled name:**
   - Click on "Haydn Miller" in the viewer
   - Change to "Hayden Miller"
   - Press Enter

2. **System automatically:**
   - Finds SAS ID `12345` for "Hayden Miller"
   - Checks score: 0.95 (no club match) vs next: 0.78
   - Auto-applies: `helm_sa_sailing_id = 12345`, `match_status_helm = 'fuzzy_auto'`
   - ID appears in the Helm ID column

3. **Manual review (if needed):**
   - Call `GET /api/match/review/{regatta_id}`
   - Review candidates for ambiguous matches
   - Call `POST /api/match/choose` to select correct ID

## Extending the System

### Add More Nicknames
```sql
INSERT INTO name_alias(base, variants) VALUES
  ('christopher', ARRAY['chris','topher']),
  ('alexander', ARRAY['alex','xander'])
ON CONFLICT (base) DO NOTHING;
```

### Adjust Scoring Thresholds
Edit `vw_match_candidates_helm/crew` views to change:
- Minimum similarity threshold (currently 0.60)
- Club match bonus (currently +0.12)
- Auto-apply threshold in `auto_match_helm/crew()` (currently 0.90)

### Handle Edge Cases
- **Multiple spellings**: Add to `name_alias`
- **Compound surnames** (e.g., "Van Der Merwe"): `surname_key()` handles via normalization
- **Special characters**: Already stripped by `norm_letters()`

## Performance
- Uses PostgreSQL `pg_trgm` extension for fast trigram indexing
- Candidate views filter at 0.70 threshold before ranking
- Auto-match only runs when names/clubs are edited (not on every page load)

