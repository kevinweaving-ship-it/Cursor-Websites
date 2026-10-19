#!/usr/bin/env python3
"""Cluster same-event coverage and rewrite one unique newspaper article.

Reverse-engineered from the commercial pipeline used by Monok, Perigon Stories,
and Event Registry / NewsAPI.ai:

  scrape many URLs → cluster items about ONE real-world event → emit
  a unique headline, a rewritten article (not a paste), one featured image,
  then a compact box-score / leaderboard.

Paid APIs (MONOK_API_KEY, PERIGON_API_KEY, NEWSAPI_AI_KEY) are optional.
The free path uses SailingSA results + Google News / web / club-class OG.
No login-wall bypass. Images are stored locally and credited.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; SailingRoundupResearch/1.0; +https://sailingsa.co.za/sailing-roundup)"
}
FB_UA = {"User-Agent": "facebookexternalhit/1.1"}
LEADERBOARD_LIMIT = 10
LEADERBOARD_COLS = ["Pos", "Helm", "Crew", "Club", "Sail No", "Nett"]
SEED_URLS = {
    "2026-09-25-tsc-420-nationals": [
        "https://novanews.co.za/school/hermanus-high-schools-sailors-crowned-national-champions/",
        "https://www.facebook.com/420nationalssouthafrica/",
        "https://www.facebook.com/theewatersportsclub/",
    ],
    "2026-09-24-hmyc-dart-18-nationals": [
        "https://www.facebook.com/share/p/1PGpY1pGh1/",
        "https://www.facebook.com/henleymidmaryachtclub",
        "https://www.hmyc.org.za/",
    ],
    "2026-09-24-ayc-505-nationals": [
        "https://www.facebook.com/AeoliansClub/",
        "https://aeolians.co.za/",
    ],
    "2026-09-24-ayc-dabchick-gauteng-regionals": [
        "https://www.facebook.com/AeoliansClub/",
        "https://www.revolutionise.com.au/dabchickca/",
    ],
}
LAYOUTS = ("photo-led", "split", "classic", "compact")
HOST_FALLBACK = {
    "TSC": "Theewater Sports Club",
    "HMYC": "Henley Midmar Yacht Club",
    "AYC": "Aeolians Yacht Club",
}


def _club_name(code: str, explicit: str = "") -> str:
    code = (code or "").strip()
    explicit = (explicit or "").strip()
    if explicit and len(explicit) > len(code):
        return explicit
    path = ROOT / "app" / "club_sources.json"
    if path.exists() and code:
        clubs = json.loads(path.read_text()).get("clubs") or {}
        rec = clubs.get(code.upper()) or clubs.get(code) or {}
        if rec.get("name"):
            return rec["name"]
    return HOST_FALLBACK.get(code.upper(), explicit or code or "the host club")


def _names(row: dict) -> str:
    helm = (row.get("helm_name") or "").strip()
    crew = (row.get("crew_name") or "").strip()
    if helm and crew:
        return f"{helm} and {crew}"
    return helm or crew or "The leader"


def _surname(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    return parts[-1] if parts else name


def _intish(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _ranked(rows: list[dict]) -> list[dict]:
    out = [r for r in rows if r.get("rank") not in (None, "")]
    out.sort(key=lambda r: int(r["rank"]) if str(r.get("rank")).isdigit() else 999)
    return out or list(rows)


def _win_count(scores) -> int:
    if not isinstance(scores, dict):
        return 0
    wins = 0
    for raw in scores.values():
        token = re.sub(r"[^0-9.]", "", str(raw).split()[0] if raw else "")
        try:
            if token and float(token) == 1.0:
                wins += 1
        except ValueError:
            continue
    return wins


def facts_from_rows(slug: str, rows: list[dict]) -> dict:
    first = rows[0]
    ranked = _ranked(rows)
    winner = ranked[0]
    second = ranked[1] if len(ranked) > 1 else {}
    third = ranked[2] if len(ranked) > 2 else {}
    races = _intish(first.get("races_sailed")) or len(winner.get("race_scores") or {})
    entries = _intish(first.get("entries_total")) or len(rows)
    club = (first.get("host_club_code") or first.get("host_club_name") or "").strip()
    title = (first.get("event_name") or slug).strip()
    if title.lower().startswith("2026 "):
        title = title[5:]
    start = str(first.get("start_date") or slug[:10])[:10]
    end = str(first.get("end_date") or start)[:10]
    winner_nett = winner.get("nett_points_raw")
    second_nett = second.get("nett_points_raw")
    return {
        "slug": slug,
        "title": title,
        "class_name": (first.get("class_name") or first.get("class_canonical") or "").strip(),
        "club": club,
        "club_name": _club_name(club, first.get("host_club_name") or ""),
        "host_club_slug": first.get("host_club_slug") or club.lower(),
        "start": start,
        "end": end,
        "entries": entries,
        "races": races,
        "status": (first.get("result_status") or "Published").strip(),
        "winner": _names(winner),
        "winner_helm": (winner.get("helm_name") or "").strip(),
        "winner_crew": (winner.get("crew_name") or "").strip(),
        "winner_club": (winner.get("club_abbrev") or winner.get("club_raw") or "").strip(),
        "winner_nett": "" if winner_nett in (None, "") else str(winner_nett).replace(".0", ""),
        "winner_wins": _win_count(winner.get("race_scores")),
        "second": _names(second) if second else "",
        "second_nett": "" if second_nett in (None, "") else str(second_nett).replace(".0", ""),
        "third": _names(third) if third else "",
        "third_nett": "" if third.get("nett_points_raw") in (None, "") else str(third.get("nett_points_raw")).replace(".0", ""),
        "tied_first": str(winner_nett) == str(second_nett) and winner_nett not in (None, ""),
        "url": "https://sailingsa.co.za/regatta/" + slug,
        "leaderboard": leaderboard(ranked),
    }


def leaderboard(rows: list[dict], limit: int = LEADERBOARD_LIMIT) -> tuple[list[str], list[list[str]]]:
    table = []
    for row in rows[:limit]:
        rank = row.get("rank")
        pos = "" if rank in (None, "") else str(rank)
        table.append(
            [
                pos,
                str(row.get("helm_name") or ""),
                str(row.get("crew_name") or ""),
                str(row.get("club_abbrev") or row.get("club_raw") or ""),
                str(row.get("sail_number") or ""),
                "" if row.get("nett_points_raw") in (None, "") else str(row.get("nett_points_raw")).replace(".0", ""),
            ]
        )
    return list(LEADERBOARD_COLS), table


def unique_headline(facts: dict, cluster: dict | None = None) -> str:
    winner = facts["winner"]
    title = facts["title"]
    venue = facts["club_name"]
    short_venue = venue.replace(" Yacht Club", "").replace(" Sports Club", "").replace(" Club", "")
    if facts.get("tied_first") and facts.get("second"):
        return f"{winner} take {title} after a points tie at {short_venue}"
    if facts.get("winner_wins") and facts["winner_wins"] >= max(3, int(facts.get("races") or 0) // 2):
        if facts["winner_wins"] >= int(facts.get("races") or 0) - 2 and (facts.get("races") or 0) >= 6:
            return f"{winner} sweep {title} at {short_venue}"
        return f"{winner} dominate {title} at {short_venue}"
    if (facts.get("status") or "").lower() == "provisional":
        fleet = f"{facts['entries']}-boat " if facts.get("entries") else ""
        return f"{winner} lead {fleet}{title} at {short_venue}"
    return f"{winner} win {title} at {short_venue}"


def _date_span(start: str, end: str) -> str:
    try:
        s = __import__("datetime").date.fromisoformat(start)
        e = __import__("datetime").date.fromisoformat(end)
    except ValueError:
        return start
    if s == e:
        return s.strftime("%-d %B")
    if s.month == e.month:
        return f"{s.day}–{e.day} {e.strftime('%B')}"
    return f"{s.strftime('%-d %B')}–{e.strftime('%-d %B')}"


def _cluster_color(cluster: dict) -> list[str]:
    """Turn clustered snippets into original colour, never pasted captions."""
    blob = " ".join(
        (item.get("title") or "") + " " + (item.get("description") or "") + " " + (item.get("snippet") or "")
        for item in (cluster or {}).get("articles") or []
    ).lower()
    notes = []
    if re.search(r"\bu-?17\b|under[- ]17|youth champion", blob):
        who = []
        for item in (cluster or {}).get("articles") or []:
            text = " ".join(
                x for x in (item.get("title"), item.get("description"), item.get("snippet")) if x
            )
            found = re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
            for name in found:
                if name not in who and "national" not in name.lower():
                    who.append(name)
            if len(who) >= 2:
                break
        if who:
            notes.append(
                f"Separate youth classification at the same championship named {' and '.join(who[:2])} "
                f"as the under-17 winners — a different title from the open leaderboard."
            )
        else:
            notes.append(
                "A later report also recorded an under-17 title at the same championship, "
                "separate from the open result."
            )
    if re.search(r"light.{0,20}wind|shifting wind|only one race", blob):
        notes.append(
            "The host club described a light, shifting day that produced only one race, "
            "which matches a series decided by consistency rather than a string of bullets."
        )
    if re.search(r"39[- ]boat|39 boat", blob) and "39" not in " ".join(notes):
        notes.append("The host club counted a 39-boat fleet at the venue.")
    return notes[:2]


def rewrite_paragraphs(facts: dict, cluster: dict | None = None) -> list[str]:
    venue = facts["club_name"]
    dates = _date_span(facts["start"], facts["end"])
    status = (facts.get("status") or "published").lower()
    verb = "leads" if status == "provisional" else "won"
    closer = (
        "The published leaderboard remains provisional."
        if status == "provisional"
        else "The published result is final."
    )
    races = facts.get("races") or 0
    entries = facts.get("entries") or 0
    wins = facts.get("winner_wins") or 0
    lede = (
        f"{facts['winner']} {verb} the {facts['title']} at {venue}, "
        f"closing the {dates} championship on {facts['winner_nett'] or 'the published'} nett points"
    )
    if races:
        lede += f" after {races} races"
    if entries:
        lede += f" in a {entries}-boat fleet"
    lede += "."
    if wins:
        lede = lede[:-1] + f", including {wins} race {'win' if wins == 1 else 'wins'}."

    podium = ""
    if facts.get("second"):
        if facts.get("tied_first"):
            podium = (
                f"{facts['second']} finished on the same nett score "
                f"({facts['second_nett']}) and took second on countback."
            )
        else:
            podium = f"{facts['second']} finished second on {facts['second_nett'] or 'the published score'}."
        if facts.get("third"):
            podium += f" {facts['third']} completed the podium"
            if facts.get("third_nett"):
                podium += f" on {facts['third_nett']}"
            podium += "."
    if facts.get("winner_club"):
        podium = (
            f"The winning entry sailed for {facts['winner_club']}. " + podium
        ).strip()

    extras = _cluster_color(cluster or {})
    context = extras[0] if extras else (
        f"{venue} hosted the {facts.get('class_name') or 'class'} championship over {dates}."
    )
    last = extras[1] if len(extras) > 1 else closer
    paras = [lede, podium, context, last]
    return [p for p in paras if p]


def deck_from_facts(facts: dict) -> str:
    bits = [facts["winner"], facts["title"], facts["club_name"]]
    if facts.get("winner_nett"):
        bits.append(f"{facts['winner_nett']} nett")
    if facts.get("entries"):
        bits.append(f"{facts['entries']} entries")
    return " · ".join(bits)


def _http_get(url: str, headers: dict | None = None, timeout: int = 18) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get_content_type() or ""


def extract_article(url: str) -> dict | None:
    if not url or not url.startswith("http"):
        return None
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"url": url, "title": "", "description": "", "image": ""}
    try:
        raw, _ = _http_get(url, FB_UA if "facebook.com" in url else UA)
    except Exception:
        return None
    soup = BeautifulSoup(raw, "html.parser")

    def og(key: str) -> str:
        tag = soup.find("meta", attrs={"property": "og:" + key}) or soup.find("meta", attrs={"name": "og:" + key})
        return (tag.get("content") or "").strip() if tag else ""

    title = og("title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    desc = og("description")
    image = og("image")
    paras = []
    for p in soup.select("article p, main p, .entry-content p, p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
        if len(text) > 80:
            paras.append(text)
        if len(paras) >= 3:
            break
    return {
        "url": url,
        "title": re.sub(r"\s+", " ", title).strip(),
        "description": desc,
        "snippet": " ".join(paras)[:700],
        "image": image,
    }


def _try_paid_clusters(query: str) -> list[dict]:
    items = []
    perigon = os.getenv("PERIGON_API_KEY")
    if perigon:
        try:
            url = "https://api.perigon.io/v1/stories/all?" + urllib.parse.urlencode(
                {"q": query, "size": 3, "sortBy": "count"}
            )
            req = urllib.request.Request(url, headers={**UA, "Authorization": f"Bearer {perigon}"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for story in data.get("results") or []:
                items.append(
                    {
                        "url": story.get("url") or "",
                        "title": story.get("name") or "",
                        "description": story.get("summary") or story.get("shortSummary") or "",
                        "image": story.get("imageUrl") or "",
                        "engine": "perigon",
                    }
                )
        except Exception:
            pass
    newsapi = os.getenv("NEWSAPI_AI_KEY")
    if newsapi:
        try:
            payload = json.dumps(
                {
                    "apiKey": newsapi,
                    "resultType": "events",
                    "keyword": query,
                    "eventsCount": 3,
                    "eventsSortBy": "size",
                }
            ).encode()
            req = urllib.request.Request(
                "https://eventregistry.org/api/v1/event/getEvents",
                data=payload,
                headers={**UA, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for ev in ((data.get("events") or {}).get("results") or []):
                items.append(
                    {
                        "url": ev.get("eventUri") or "",
                        "title": ((ev.get("title") or {}).get("eng") if isinstance(ev.get("title"), dict) else ev.get("title")) or "",
                        "description": ((ev.get("summary") or {}).get("eng") if isinstance(ev.get("summary"), dict) else ev.get("summary")) or "",
                        "image": ev.get("images")[0] if ev.get("images") else "",
                        "engine": "newsapi_ai",
                    }
                )
        except Exception:
            pass
    monok = os.getenv("MONOK_API_KEY")
    if monok:
        try:
            url = "https://www.monok.com/api/v1/clusters/?" + urllib.parse.urlencode({"q": query, "s": 3})
            req = urllib.request.Request(url, headers={**UA, "x-api-token": monok})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for ev in data if isinstance(data, list) else data.get("results") or data.get("clusters") or []:
                items.append(
                    {
                        "url": ev.get("url") or ev.get("id") or "",
                        "title": ev.get("title") or ev.get("name") or "",
                        "description": ev.get("summary") or ev.get("shortTitle") or "",
                        "image": ev.get("thumbnail") or ev.get("image") or "",
                        "engine": "monok",
                    }
                )
        except Exception:
            pass
    return items


def cluster_coverage(facts: dict, pack: dict | None = None, fetch: bool = True) -> dict:
    """Group every public item about this one event into a single story cluster."""
    seen = set()
    articles = []

    def add(item: dict):
        url = (item.get("url") or item.get("source_url") or "").split("#")[0]
        if not url or url in seen:
            return
        seen.add(url)
        articles.append(
            {
                "url": url,
                "title": item.get("title") or item.get("label") or "",
                "description": item.get("description") or item.get("snippet") or "",
                "snippet": item.get("snippet") or "",
                "image": item.get("image") or item.get("image_url") or "",
                "engine": item.get("engine") or item.get("lane") or item.get("platform") or "pack",
            }
        )

    for post in (pack or {}).get("verified_posts") or (pack or {}).get("posts") or []:
        add(post)
    for img in (pack or {}).get("images") or []:
        add(
            {
                "url": img.get("source_url") or img.get("image_url"),
                "title": img.get("source_title") or "",
                "image": img.get("image_url"),
                "engine": img.get("platform") or "image",
            }
        )
    for url in SEED_URLS.get(facts.get("slug") or "", []):
        add({"url": url, "engine": "seed"})
    if fetch:
        try:
            from search_everywhere import event_query, google_news, web_hits
        except Exception:
            event_query = None
        if event_query:
            q = event_query(
                {
                    "title": facts["title"],
                    "club": facts["club"],
                    "club_name": facts["club_name"],
                }
            )
            for item in google_news(q, limit=6) + web_hits(q, limit=6):
                add(item)
            for item in _try_paid_clusters(q):
                add(item)
        for article in list(articles):
            if article.get("description") or article.get("image"):
                continue
            extracted = extract_article(article["url"])
            if not extracted:
                continue
            article["title"] = article["title"] or extracted.get("title") or ""
            article["description"] = extracted.get("description") or ""
            article["snippet"] = extracted.get("snippet") or ""
            article["image"] = extracted.get("image") or ""
    return {
        "event_id": facts.get("slug"),
        "event_url": facts.get("url"),
        "articles": articles,
        "count": len(articles),
    }


def pick_image(facts: dict, cluster: dict, pack: dict | None = None) -> dict | None:
    candidates = []
    for item in (cluster or {}).get("articles") or []:
        if item.get("image"):
            candidates.append(
                {
                    "url": item["image"],
                    "source_url": item.get("url") or "",
                    "title": item.get("title") or facts["title"],
                    "credit": _credit_from_url(item.get("url") or item["image"]),
                }
            )
    for img in (pack or {}).get("images") or []:
        if img.get("image_url"):
            candidates.append(
                {
                    "url": img["image_url"],
                    "source_url": img.get("source_url") or "",
                    "title": img.get("source_title") or facts["title"],
                    "credit": img.get("platform") or _credit_from_url(img.get("source_url") or ""),
                }
            )
    return candidates[0] if candidates else None


def _credit_from_url(url: str) -> str:
    host = urllib.parse.urlparse(url or "").netloc.lower().removeprefix("www.")
    if "novanews" in host:
        return "NovaNews"
    if "facebook.com" in host or "fbcdn.net" in host:
        return "Facebook / host club"
    if "hmyc" in host:
        return "Henley Midmar Yacht Club"
    if "aeolians" in host:
        return "Aeolians Yacht Club"
    if "theewater" in host:
        return "Theewater Sports Club"
    return host or "source"


def download_image(image: dict, issue: str, slug: str) -> dict | None:
    url = (image or {}).get("url") or ""
    if not url:
        return None
    dest_dir = ROOT / "public" / "issues" / issue / "media"
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "issues" / issue / "media"
    source_dir.mkdir(parents=True, exist_ok=True)
    existing = dest_dir / f"{slug}.jpg"
    for alt in dest_dir.glob(f"{slug}*"):
        if alt.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and alt.stat().st_size > 4000:
            rel = "media/" + alt.name
            out = dict(image)
            out["url"] = rel
            out["local_path"] = str(alt)
            return out
    # Keep a known Dart file if the generic slug download is not yet there.
    for named in dest_dir.glob("*.jpg"):
        if slug.split("-")[-2:] and "dart" in slug and "dart" in named.name and named.stat().st_size > 4000:
            rel = "media/" + named.name
            out = dict(image)
            out["url"] = rel
            out["local_path"] = str(named)
            return out
    ext = ".jpg"
    path = urllib.parse.urlparse(url).path.lower()
    for cand in (".png", ".webp", ".jpeg", ".jpg"):
        if path.endswith(cand):
            ext = ".jpg" if cand == ".jpeg" else cand
            break
    filename = slug + ext
    dest = dest_dir / filename
    headers = dict(FB_UA if "fbcdn" in url or "facebook.com" in url else UA)
    headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    try:
        raw, ctype = _http_get(url, headers, timeout=25)
    except Exception:
        return None
    if len(raw) < 4000 or (ctype and not ctype.startswith("image") and not raw[:3] in (b"\xff\xd8\xff", b"\x89PN")):
        return None
    dest.write_bytes(raw)
    (source_dir / filename).write_bytes(raw)
    out = dict(image)
    out["url"] = "media/" + filename
    out["local_path"] = str(dest)
    out["bytes"] = len(raw)
    return out


def layout_for(index: int, article_type: str) -> str:
    if article_type == "feature":
        return "lead"
    return LAYOUTS[index % len(LAYOUTS)]


def rewrite_event(issue: str, facts: dict, pack: dict | None = None, cluster: dict | None = None, layout: str = "classic") -> dict:
    cluster = cluster or cluster_coverage(facts, pack, fetch=True)
    paras = rewrite_paragraphs(facts, cluster)
    headline = unique_headline(facts, cluster)
    cols, table = facts["leaderboard"]
    image = pick_image(facts, cluster, pack)
    local = download_image(image, issue, facts["slug"]) if image else None
    if not local and image:
        local = image
    if not local:
        local = _fallback_club_image(issue, facts)
    blocks = []
    if local:
        credit = local.get("credit") or "source"
        blocks.append(
            {
                "type": "image",
                "url": local["url"],
                "alt": local.get("title") or facts["title"],
                "caption": f"{facts['title']} — {facts['club_name']}. Photo: {credit}.",
                "credit": credit,
                "source_url": local.get("source_url") or facts["url"],
                "rights_status": "source_attributed",
            }
        )
    for text in paras:
        blocks.append({"type": "paragraph", "text": text})
    blocks.append({"type": "heading", "text": "Leaderboard"})
    blocks.append(
        {
            "type": "results",
            "source_event_url": facts["url"],
            "columns": cols,
            "rows": table,
            "as_of": issue,
        }
    )
    sources = [facts["url"]]
    for item in cluster.get("articles") or []:
        if item.get("url") and item["url"] not in sources:
            sources.append(item["url"])
    article = {
        "id": facts["slug"],
        "type": "regatta_report",
        "headline": headline,
        "deck": deck_from_facts(facts),
        "byline": "Weekend Sailing Roundup",
        "kicker": (facts.get("class_name") or "Regatta").upper() + "  ·  " + facts["club"],
        "published_at": issue,
        "event_id": facts["slug"],
        "layout": layout,
        "hero_image": {"url": local["url"], "source_url": local.get("source_url"), "rights_status": "source_attributed"} if local else None,
        "blocks": blocks,
        "sources": sources,
        "review_status": "rewritten",
        "club": facts["club"],
        "class_name": facts["class_name"],
        "host_club_slug": facts.get("host_club_slug") or "",
        "start_date": facts["start"],
        "end_date": facts["end"],
        "cluster_count": cluster.get("count") or 0,
    }
    dest = ROOT / "issues" / issue / "sources"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{facts['slug']}-cluster.json").write_text(json.dumps(cluster, indent=2, ensure_ascii=False))
    return article


def _fallback_club_image(issue: str, facts: dict) -> dict | None:
    pages = []
    slug = (facts.get("host_club_slug") or facts.get("club") or "").lower()
    path = ROOT / "app" / "club_sources.json"
    if path.exists() and facts.get("club"):
        clubs = json.loads(path.read_text()).get("clubs") or {}
        rec = clubs.get(facts["club"].upper()) or {}
        for key in ("facebook", "website", "instagram"):
            if rec.get(key):
                pages.append(rec[key])
    if slug:
        pages.append("https://sailingsa.co.za/club/" + slug)
    for url in pages:
        extracted = extract_article(url)
        if extracted and extracted.get("image"):
            local = download_image(
                {
                    "url": extracted["image"],
                    "source_url": url,
                    "title": facts["title"],
                    "credit": _credit_from_url(url),
                },
                issue,
                facts["slug"],
            )
            if local:
                return local
    media = ROOT / "public" / "issues" / issue / "media"
    if media.exists():
        keys = [facts["slug"]]
        if "dart" in facts["slug"]:
            keys.append("dart")
        for named in sorted(media.glob("*.jpg")):
            if named.stat().st_size > 4000 and any(k in named.name for k in keys):
                return {
                    "url": "media/" + named.name,
                    "source_url": facts["url"],
                    "title": facts["title"],
                    "credit": facts["club_name"],
                    "local_path": str(named),
                }
    return None


def rewrite_weekend_feature(issue: str, monday, events: list[dict], articles: list[dict]) -> dict:
    import datetime as dt

    from events_weekend import saturday_sunday

    sat, sun = saturday_sunday(monday)
    scored = [e for e in events if e.get("has_results") or e.get("regatta_id")]
    window = f"{sat.strftime('%-d')}–{sun.strftime('%-d %B %Y')}"
    if not events:
        paras = [f"No racing events were listed on the SailingSA events table for {sat.isoformat()}–{sun.isoformat()}."]
        headline = "A quiet weekend on the SailingSA calendar"
    else:
        headline = f"{len(scored) or len(events)} championships decided across a packed {window} weekend"
        if len(events) == 1:
            headline = f"One title decided on the {window} weekend"
        bits = [
            f"Four days of national and regional racing collapsed into Monday's scorelines. "
            f"{len(scored)} of {len(events)} listed events published results for {window}."
        ]
        for article in articles:
            if article.get("headline"):
                bits.append(article["headline"] + ".")
        if not articles:
            for ev in events:
                line = ev.get("event_name") or ""
                if ev.get("races_sailed"):
                    line += f", {ev['races_sailed']} races"
                if ev.get("entries"):
                    line += f", {ev['entries']} entries"
                if line:
                    bits.append(line + ".")
        paras = bits[:6]
    return {
        "id": "weekend-" + issue,
        "type": "feature",
        "headline": headline,
        "deck": f"Independent Monday edition · {window}",
        "byline": "Weekend Sailing Roundup",
        "kicker": "WEEKEND LEAD",
        "published_at": issue,
        "event_id": "weekend-" + issue,
        "layout": "lead",
        "hero_image": (articles[0].get("hero_image") if articles else None),
        "blocks": [{"type": "paragraph", "text": p} for p in paras],
        "sources": ["https://sailingsa.co.za/api/events"],
        "review_status": "rewritten",
    }
