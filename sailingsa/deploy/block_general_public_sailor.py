#!/usr/bin/env python3
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"MISSING {label}")
    if text.count(old) != 1:
        raise SystemExit(f"AMBIGUOUS {label} count={text.count(old)}")
    return text.replace(old, new, 1)


def main() -> None:
    text = API.read_text(encoding="utf-8")
    text = must_replace(
        text,
        """def _sailor_spa(slug: str, request: Request):
    name, canonical_slug = _get_sailor_name_by_slug(slug)
""",
        """def _sailor_spa(slug: str, request: Request):
    raw = (slug or "").strip().lower()
    if raw in {"general-public", "generalpublic"} or raw.startswith("pub_") or raw.startswith("pub-"):
        raise HTTPException(status_code=404, detail="Sailor not found")
    name, canonical_slug = _get_sailor_name_by_slug(slug)
""",
        "sailor spa",
    )
    text = must_replace(
        text,
        """def _get_sailor_name_by_slug(slug: str):
    \"\"\"Return (full_name, canonical_slug) for sailor or (None, None). Used for server-side SEO HTML.\"\"\"
    if not slug or not slug.strip():
        return None, None
    slug = slug.strip()
""",
        """def _get_sailor_name_by_slug(slug: str):
    \"\"\"Return (full_name, canonical_slug) for sailor or (None, None). Used for server-side SEO HTML.\"\"\"
    if not slug or not slug.strip():
        return None, None
    slug = slug.strip()
    if slug.lower() in {"general-public", "generalpublic"} or slug.upper().startswith("PUB_"):
        return None, None
""",
        "name by slug",
    )
    API.write_text(text, encoding="utf-8")
    print("OK")


if __name__ == "__main__":
    main()
