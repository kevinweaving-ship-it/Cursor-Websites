#!/usr/bin/env python3
"""Match a Facebook/web page back to a SailingSA club, class, sailor, or sponsor URL."""
from __future__ import annotations

import re
import urllib.parse

KIND_PATH = {
    "club": "/club/",
    "class": "/class/",
    "sailor": "/sailor/",
    "sponsor": "/sponsor/",
}

KEEP = {
    "420",
    "505",
    "29er",
    "49er",
    "j22",
    "df95",
    "ilca",
    "l26",
    "hobie",
    "tsc",
    "hmyc",
    "ayc",
    "rsa",
}
DROP = {
    "the",
    "and",
    "yacht",
    "club",
    "sports",
    "sailing",
    "sail",
    "south",
    "african",
    "africa",
    "association",
    "national",
    "nationals",
    "class",
    "page",
    "group",
    "official",
    "facebook",
    "instagram",
}


def slugify(text: str) -> str:
    text = (text or "").strip().lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for word in words:
        if word in KEEP or (len(word) > 2 and word not in DROP):
            out.add(word)
    return out


def sailingsa_url(kind: str, key: str) -> str:
    return "https://sailingsa.co.za" + KIND_PATH.get(kind, f"/{kind}/") + slugify(key)


def normalize_facebook(url: str) -> str:
    parsed = urllib.parse.urlsplit(url or "")
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    if "facebook.com" not in host:
        return (url or "").split("?")[0].rstrip("/")
    if path.startswith("/share/"):
        return f"https://www.facebook.com{path}"
    return f"https://www.facebook.com{path}"


def _index_row(kind: str, key: str, name: str, extra: str = "", url: str = "") -> dict:
    label = " ".join(x for x in (name, extra, key) if x)
    return {
        "entity_type": kind,
        "entity_key": slugify(key) or slugify(name),
        "display_name": name or key,
        "sailingsa_url": url or sailingsa_url(kind, key or name),
        "tokens": tokens(label),
        "aliases": {slugify(key), slugify(name), *(slugify(a) for a in extra.split() if a)},
    }


def build_index(
    clubs: list[dict] | None = None,
    classes: list[dict] | None = None,
    sailors: list[dict] | None = None,
    sponsors: list[dict] | None = None,
) -> list[dict]:
    rows = []
    for club in clubs or []:
        code = (club.get("code") or club.get("club_abbrev") or "").strip()
        name = (club.get("name") or club.get("club_fullname") or code).strip()
        slug = (club.get("slug") or slugify(name)).strip()
        rows.append(
            _index_row(
                "club",
                slug or code,
                name,
                extra=code,
                url="https://sailingsa.co.za/club/" + slugify(slug or code),
            )
        )
    for klass in classes or []:
        name = (klass.get("name") or klass.get("class_name") or "").strip()
        slug = (klass.get("slug") or slugify(name)).strip()
        if not name and not slug:
            continue
        rows.append(
            _index_row(
                "class",
                slug,
                name,
                extra=klass.get("aliases") or "",
                url="https://sailingsa.co.za/class/" + slugify(slug),
            )
        )
    for sailor in sailors or []:
        name = (sailor.get("name") or sailor.get("full_name") or "").strip()
        slug = (sailor.get("slug") or "").strip()
        sid = str(sailor.get("sa_id") or sailor.get("sas_id") or "").strip()
        if not name:
            continue
        key = slug or slugify(name + ("-" + sid if sid else ""))
        url = sailor.get("sailingsa_url") or (
            "https://sailingsa.co.za/sailor/" + key if key else ""
        )
        rows.append(_index_row("sailor", key, name, extra=sid, url=url))
    for sponsor in sponsors or []:
        name = (sponsor.get("name") or "").strip()
        if not name:
            continue
        slug = (sponsor.get("slug") or slugify(name)).strip()
        rows.append(_index_row("sponsor", slug, name, extra=sponsor.get("aliases") or ""))
    return rows


def match_text(text: str, index: list[dict], kinds: tuple[str, ...] | None = None) -> dict | None:
    """Best SailingSA entity for a page title, share caption, or URL path."""
    blob = (text or "").strip()
    if not blob:
        return None
    raw_tokens = tokens(blob)
    slug = slugify(blob)
    path = urllib.parse.urlsplit(blob).path.strip("/").split("/")
    path_slug = slugify(path[1] if path and path[0] in {"club", "class", "sailor", "sponsor"} and len(path) > 1 else path[-1] if path else "")
    best = None
    best_score = 0
    for row in index:
        if kinds and row["entity_type"] not in kinds:
            continue
        score = 0
        if slug and slug in row["aliases"]:
            score += 8
        if path_slug and path_slug in row["aliases"]:
            score += 8
        if row["entity_key"] and row["entity_key"] in slug:
            score += 4
        overlap = raw_tokens & row["tokens"]
        if overlap:
            score += min(6, 2 * len(overlap))
        # Unique token that is the entity key (420, tsc, dabchick).
        if row["entity_key"] in raw_tokens:
            score += 5
        if score > best_score:
            best = row
            best_score = score
    if not best or best_score < 5:
        return None
    return {
        "entity_type": best["entity_type"],
        "entity_key": best["entity_key"],
        "display_name": best["display_name"],
        "sailingsa_url": best["sailingsa_url"],
        "score": best_score,
        "matched_text": blob[:160],
    }


DEFAULT_SPONSORS = [
    {"name": "North Sails", "aliases": "northsails"},
    {"name": "Ullman Sails", "aliases": "ullman"},
    {"name": "Nitro", "aliases": "nitro"},
    {"name": "AMTEC", "aliases": "amtec"},
    {"name": "H2O", "aliases": "h2o"},
    {"name": "Zhik", "aliases": "zhik"},
    {"name": "Hobie", "aliases": "hobie sa hobiesa"},
]
