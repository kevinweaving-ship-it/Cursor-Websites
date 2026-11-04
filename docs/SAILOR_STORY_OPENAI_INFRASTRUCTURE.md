# SailingSA AI Sailor Story — isolated integration

Status: development branch only. NOT deployed. Production login/search/profile unchanged.

## Existing code
Production has `/var/www/sailingsa/api/modules/sailor_bio.py`, a deterministic sentence generator. Do not replace it until its consumers have been traced. Existing deployed `api.py` is protected by the production edit protocol.

## New backend module
`sailingsa/backend/sailor_story_openai.py` calls OpenAI's current Responses API via Python stdlib, using a server-side environment variable `OPENAI_API_KEY`. Optional `SAILINGSA_STORY_MODEL` defaults to `gpt-4.1-mini`. No browser API key. No inbound public endpoint is added. The module accepts only allowlisted, explicitly verified result-derived fields and returns a headline, second-person teaser, evidence IDs and deterministic content fingerprint.

## Deployment / prerequisite checks
1. Identify the existing API key or billing project securely, without printing or committing secrets. If already present, reuse it. ChatGPT Plus subscription is distinct from API billing.
2. Verify key/billing with a small authenticated call using a synthetic verified fixture. The module cannot run without the key.
3. Create a facts assembler that resolves an exact SAS ID (not fuzzy name matching), deduplicates regattas/results and distinguishes race entries from starts.
4. Require independent source-to-claim verification; `evidence_ids` are references only, NOT proof that the text is true.
5. Add persistent DB cache keyed on `story_fingerprint`, with expiry/invalidation when verified results change; enforce rate limiting and spend caps.
6. Rebuild approved image as locked HTML/CSS/SVG and regression-test at <=480px; no AI image generation at request time.
7. Publish to staff-only preview first. Only after mobile QA and controlled A/B test should the search/claim UI be touched.

## Safety
- No raw free-text user prompt forwarded to OpenAI.
- Do not include DOB, email, phone, account identifiers or other private profile fields.
- Do not pass secrets to the browser.
- A successful API response is not a factual audit.
- On any API error, fail closed to the current non-AI experience.
- Follow `sailingsa/deploy/SSH_LIVE.md` and production backup/immutable-file rules before any deployment.

## Minimal call (once verified facts are available)
```python
from sailingsa.backend.sailor_story_openai import generate_story
result = generate_story(sas_id, verified_public_facts)
# result: headline, teaser, evidence_ids, cache_key
```
