"""SailingSA sailor-story OpenAI adapter. Private server-side use only.

No route is registered here. Call generate_story() with prevalidated, public,
sailor-specific facts; never send raw database rows or private contact details.
The caller is responsible for checking factual claims against source records.
"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

API_URL = "https://api.openai.com/v1/responses"
PROMPT_VERSION = "sailor-story-v1"

class StoryGenerationError(RuntimeError):
    pass

def _extract_text(response):
    parts = []
    for output in response.get("output", []):
        if output.get("type") != "message":
            continue
        for item in output.get("content", []):
            if item.get("type") == "output_text" and isinstance(item.get("text"), str):
                parts.append(item["text"])
    return "\n".join(parts).strip()

def story_fingerprint(sas_id, facts):
    payload = json.dumps([PROMPT_VERSION, str(sas_id), facts], sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def generate_story(sas_id, facts, *, api_key=None, model=None, timeout=25):
    """Returns {headline, teaser, evidence_ids, cache_key}; not a rendered card.

    Only accept factual, non-sensitive, explicitly allowlisted fields. Generate
    nothing for ambiguous IDs, invalid/empty evidence, or missing credentials.
    """
    if not re.fullmatch(r"[0-9]{1,12}", str(sas_id)):
        raise ValueError("A single verified numeric SAS ID is required")
    if not isinstance(facts, dict) or not facts.get("source_results"):
        raise ValueError("Verified source_results are required")
    allowed = ("first_name", "first_recorded_date", "regatta_count", "race_entries_count",
               "class_histories", "fleet_histories", "boat_names", "sail_numbers",
               "highlights", "source_results")
    clean = {key: facts[key] for key in allowed if key in facts}
    if len(json.dumps(clean, default=str)) > 32000:
        raise ValueError("Fact payload too large")
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise StoryGenerationError("OPENAI_API_KEY is not configured")
    model = model or os.environ.get("SAILINGSA_STORY_MODEL", "gpt-4.1-mini")
    instructions = (
        "You write SailingSA teaser biographies addressed directly to the sailor as 'you'. "
        "Use only supplied verified results. Never invent a fact, result, skill, coach, "
        "partnership or improvement. 'First recorded' does not mean first ever. "
        "Distinguish Optimist A/B fleets from separate sailing classes; classes may overlap. "
        "Race entries do not prove completed starts. Avoid private personal facts. "
        "Keep teaser 55-90 words, compelling but not clickbait. "
        "Return ONLY JSON with headline (max 70 chars), teaser (string), "
        "evidence_ids (array of identifiers from supplied source_results supporting claims)."
    )
    data = {
        "model": model, "instructions": instructions,
        "input": json.dumps(clean, ensure_ascii=False, default=str),
        "store": False, "max_output_tokens": 400,
    }
    request = urllib.request.Request(
        API_URL, data=json.dumps(data).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as result:
            response = json.load(result)
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise StoryGenerationError("OpenAI request failed; inspect protected server logs") from error
    raw = _extract_text(response)
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise StoryGenerationError("Model response is not valid JSON") from error
    if not isinstance(result, dict) or not isinstance(result.get("headline"), str) or not isinstance(result.get("teaser"), str) or not isinstance(result.get("evidence_ids"), list):
        raise StoryGenerationError("Model response schema invalid")
    if not result["headline"].strip() or len(result["headline"]) > 70 or not 40 <= len(result["teaser"].split()) <= 105:
        raise StoryGenerationError("Model response failed length validation")
    ids = {str(x.get("id")) for x in clean["source_results"] if isinstance(x, dict) and x.get("id") is not None}
    if not ids or any(str(i) not in ids for i in result["evidence_ids"]) or not result["evidence_ids"]:
        raise StoryGenerationError("Model returned missing/unverified evidence IDs")
    result["cache_key"] = story_fingerprint(sas_id, clean)
    return result
