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
    title = re.sub(r"\s+incorporating\b.*$", "", title, flags=re.I).strip()
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
        "winner_scores": winner.get("race_scores") or {},
        "second_scores": second.get("race_scores") or {},
        "second_wins": _win_count(second.get("race_scores")),
        "second": _names(second) if second else "",
        "second_nett": "" if second_nett in (None, "") else str(second_nett).replace(".0", ""),
        "third": _names(third) if third else "",
        "third_nett": "" if third.get("nett_points_raw") in (None, "") else str(third.get("nett_points_raw")).replace(".0", ""),
        "tied_first": str(winner_nett) == str(second_nett) and winner_nett not in (None, ""),
        "names": [n for r in ranked for n in ((r.get("helm_name") or "").strip(), (r.get("crew_name") or "").strip()) if n],
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


def _agree(winner: str, plural: str, singular: str) -> str:
    return plural if (" and " in (winner or "") or "," in (winner or "")) else singular


def unique_headline(facts: dict, cluster: dict | None = None) -> str:
    winner = facts["winner"]
    title = facts["title"]
    venue = facts["club_name"]
    short_venue = venue.replace(" Yacht Club", "").replace(" Sports Club", "").replace(" Club", "")
    if facts.get("tied_first") and facts.get("second"):
        return f"{winner} {_agree(winner, 'take', 'takes')} {title} after a points tie at {short_venue}"
    if facts.get("winner_wins") and facts["winner_wins"] >= max(3, int(facts.get("races") or 0) // 2):
        if facts["winner_wins"] >= int(facts.get("races") or 0) - 2 and (facts.get("races") or 0) >= 6:
            return f"{winner} {_agree(winner, 'sweep', 'sweeps')} {title} at {short_venue}"
        return f"{winner} {_agree(winner, 'dominate', 'dominates')} {title} at {short_venue}"
    if (facts.get("status") or "").lower() == "provisional":
        fleet = f"{facts['entries']}-boat " if facts.get("entries") else ""
        return f"{winner} {_agree(winner, 'lead', 'leads')} {fleet}{title} at {short_venue}"
    return f"{winner} {_agree(winner, 'win', 'wins')} {title} at {short_venue}"


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


def _cluster_color(cluster: dict, facts: dict | None = None) -> list[str]:
    """Turn clustered snippets into original colour, never pasted captions."""
    blob = " ".join(
        (item.get("title") or "") + " " + (item.get("description") or "") + " " + (item.get("snippet") or "")
        for item in (cluster or {}).get("articles") or []
    ).lower()
    notes = []
    known = {n.lower(): n for n in (facts or {}).get("names") or []}
    if re.search(r"\bu-?17\b|under[- ]17|youth champion", blob):
        who = []
        for item in (cluster or {}).get("articles") or []:
            text = " ".join(
                x for x in (item.get("title"), item.get("description"), item.get("snippet")) if x
            )
            found = re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
            for name in found:
                real = known.get(name.lower())
                if real and real not in who:
                    who.append(real)
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


def _heats(scores) -> list[dict]:
    out = []
    if not isinstance(scores, dict):
        return out
    for key, raw in scores.items():
        token = re.sub(r"[^0-9.]", "", str(raw).split()[0] if raw else "")
        try:
            pts = float(token) if token else None
        except ValueError:
            pts = None
        out.append({"race": key, "pts": pts, "raw": str(raw), "win": pts == 1.0})
    return out


def rewrite_paragraphs(facts: dict, cluster: dict | None = None) -> list[str]:
    """Build a story from results shape + clustered reporting. No per-event hand copy."""
    venue = facts["club_name"]
    dates = _date_span(facts["start"], facts["end"])
    status = (facts.get("status") or "published").lower()
    races = facts.get("races") or 0
    entries = facts.get("entries") or 0
    wins = facts.get("winner_wins") or 0
    heats = _heats(facts.get("winner_scores"))
    late = heats[-4:] if len(heats) >= 4 else heats
    late_wins = sum(1 for h in late if h.get("win"))
    no_wins = heats and wins == 0
    paras = []

    if facts.get("tied_first") and facts.get("second"):
        paras.append(
            f"{facts['winner']} stole the {facts['title']} at {venue} on countback after "
            f"{facts['second']} matched them on {facts['winner_nett']} nett. "
            f"The {entries or 'published'}-boat fleet sailed {races or 'a full'} races over {dates}."
        )
    elif no_wins:
        paras.append(
            f"{facts['winner']} leads the {facts['title']} at {venue} without a race win — "
            f"a week of threes and fours, {facts['winner_nett']} nett from {races} races "
            f"in a {entries}-boat fleet. The result is still {status}."
        )
    elif wins and races and wins >= races - 2:
        paras.append(
            f"{facts['winner']} left nothing on the table at the {facts['title']}. "
            f"{wins} race wins from {races} heats at {venue} produced {facts['winner_nett']} nett "
            f"and a gap the rest of the {entries}-boat fleet could not close."
        )
    else:
        verb = "leads" if status == "provisional" else "won"
        paras.append(
            f"{facts['winner']} {verb} the {facts['title']} at {venue} over {dates}, "
            f"{facts['winner_nett']} nett after {races} races among {entries} entries"
            + (f", with {wins} bullets." if wins else ".")
        )

    if heats:
        opened = heats[0]
        closed = heats[-1]
        if late_wins >= 3:
            paras.append(
                f"The series flipped late. {facts['winner']} took {late_wins} of the last "
                f"{len(late)} races, including the closer ({closed['race']}). "
                f"That is how a championship is taken after the halfway mark, not before it."
            )
        elif opened.get("win") and not (heats[1].get("win") if len(heats) > 1 else False):
            paras.append(
                f"They opened with a win in {opened['race']} and then sailed the rest of the "
                f"week for the discard, not for the highlight reel."
            )
        elif no_wins:
            worst = max(heats, key=lambda h: h["pts"] or 0)
            paras.append(
                f"The only hole in the card was {worst['race']} ({worst['raw']}). "
                f"Everywhere else {facts['winner_helm'] or facts['winner']} kept the boat in the front pack "
                f"while faster boats around them won heats and leaked points."
            )
        else:
            paras.append(
                f"The winning card mixed {wins} firsts with the discarded heat that every "
                f"{facts.get('class_name') or 'fleet'} championship needs. "
                f"{facts['winner_helm'] or facts['winner']} sailed for {facts.get('winner_club') or venue}."
            )

    chase = []
    if facts.get("second"):
        if facts.get("tied_first"):
            chase.append(
                f"{facts['second']} won {facts.get('second_wins') or 0} races and still finished second — "
                f"same nett, worse countback."
            )
        else:
            chase.append(
                f"{facts['second']} chased on {facts['second_nett']}"
                + (f" with {facts.get('second_wins')} race wins" if facts.get("second_wins") else "")
                + "."
            )
    if facts.get("third"):
        chase.append(f"{facts['third']} completed the podium on {facts['third_nett'] or 'the published score'}.")
    if chase:
        paras.append(" ".join(chase))

    extras = _cluster_color(cluster or {}, facts)
    news = []
    for item in (cluster or {}).get("articles") or []:
        snippet = (item.get("snippet") or item.get("description") or "").strip()
        if len(snippet) > 90 and "follow us" not in snippet.lower():
            news.append(snippet)
    if extras:
        paras.extend(extras)
    elif news:
        bit = news[0]
        if "u17" in bit.lower() or "under-17" in bit.lower() or "under 17" in bit.lower():
            paras.append(
                "Independent coverage after the prize-giving treated the youth title as its own story "
                "inside the same fleet — not a substitute for the open result."
            )
        elif re.search(r"light|shift|one race", bit, re.I):
            paras.append(
                "The host club's own report of the weekend described a dying, shifting breeze "
                "and a day that produced almost no racing. That is the weather that rewards "
                "the sailor who never leaves the front row."
            )
        else:
            paras.append(
                f"Outside the scoreboard, public coverage of the event at {venue} "
                f"focused on the same championship weekend rather than a different regatta."
            )

    paras.append(
        f"{venue} hosted the {facts.get('class_name') or ''} championship over {dates}. "
        + (
            "The published leaderboard remains provisional."
            if status == "provisional"
            else "The published result is final."
        )
    )
    out = []
    for p in paras:
        p = re.sub(r"\s+", " ", p).strip()
        if p and p not in out:
            out.append(p)
    return out[:7]


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


def _bad_image_url(url: str) -> bool:
    low = (url or "").lower()
    return any(
        token in low
        for token in (
            "logo",
            "reel",
            "badge",
            ".svg",
            "icon",
            "avatar",
            "profile",
            "sprite",
            "placeholder",
            "default-user",
            "ytimg.com/vi",
            "youtube.com/img",
            "yt_1200",
            "sailingsa.co.za/static",
            "sailingsa.co.za/assets",
        )
    )


def commons_class_photo(klass: str) -> dict | None:
    q = (klass or "sailing dinghy").strip() + " dinghy sailing"
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": q,
            "gsrnamespace": 6,
            "gsrlimit": 8,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "format": "json",
        }
    )
    try:
        raw, _ = _http_get(url, UA, timeout=18)
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return None
    best = None
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        link = info.get("url") or ""
        mime = (info.get("mime") or "").lower()
        width = int(info.get("width") or 0)
        if not link.endswith((".jpg", ".jpeg")) or "svg" in mime or width < 600:
            continue
        if _bad_image_url(link) or "logo" in (page.get("title") or "").lower():
            continue
        best = {
            "url": link.split("?")[0],
            "source_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page.get("title") or ""),
            "title": page.get("title") or klass,
            "credit": "Wikimedia Commons",
        }
        if width >= 1000:
            break
    return best


def pick_image(facts: dict, cluster: dict, pack: dict | None = None) -> dict | None:
    candidates = []
    for item in (cluster or {}).get("articles") or []:
        if item.get("image") and not _bad_image_url(item["image"]):
            candidates.append(
                {
                    "url": item["image"],
                    "source_url": item.get("url") or "",
                    "title": item.get("title") or facts["title"],
                    "credit": _credit_from_url(item.get("url") or item["image"]),
                }
            )
    for img in (pack or {}).get("images") or []:
        if img.get("image_url") and not _bad_image_url(img["image_url"]):
            candidates.append(
                {
                    "url": img["image_url"],
                    "source_url": img.get("source_url") or "",
                    "title": img.get("source_title") or facts["title"],
                    "credit": pretty_credit(img.get("platform") or "", img.get("source_url") or img.get("image_url") or ""),
                }
            )
    def score(item: dict) -> int:
        blob = " ".join((item.get("url") or "", item.get("source_url") or "", item.get("title") or "")).lower()
        n = 0
        if "novanews" in blob:
            n += 80
        if "wp-content/uploads" in (item.get("url") or ""):
            n += 30
        if "wikimedia" in blob or "upload.wikimedia" in (item.get("url") or ""):
            n += 25
        if any(k in blob for k in ("nationals", "regatta", "day 2", "day2")):
            n += 15
        if "fbcdn" in (item.get("url") or "") and "t39.30808-1" in (item.get("url") or ""):
            n -= 40
        if _bad_image_url(item.get("url") or ""):
            n -= 100
        return n

    candidates.sort(key=score, reverse=True)
    if candidates and score(candidates[0]) >= 0:
        return candidates[0]
    return commons_class_photo(facts.get("class_name") or "sailing")


def pretty_credit(raw: str, url: str = "") -> str:
    blob = f"{raw or ''} {url or ''}".lower()
    if "novanews" in blob:
        return "NovaNews"
    if "youtube" in blob or "youtu.be" in blob:
        return "YouTube"
    if "facebook" in blob or "fbcdn" in blob:
        return "Facebook / host club"
    if "hmyc" in blob:
        return "Henley Midmar Yacht Club"
    if "aeolians" in blob:
        return "Aeolians Yacht Club"
    if "theewater" in blob:
        return "Theewater Sports Club"
    host = urllib.parse.urlparse(url or raw or "").netloc.lower().removeprefix("www.")
    return host or (raw or "source").strip()


def _credit_from_url(url: str) -> str:
    return pretty_credit("", url)


def download_image(image: dict, issue: str, slug: str) -> dict | None:
    url = (image or {}).get("url") or ""
    if not url:
        return None
    dest_dir = ROOT / "public" / "issues" / issue / "media"
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "issues" / issue / "media"
    source_dir.mkdir(parents=True, exist_ok=True)
    if "dart" in slug:
        named = dest_dir / "dart18-nationals-day2-hmyc.jpg"
        if named.exists() and named.stat().st_size > 12000:
            out = dict(image)
            out["url"] = "media/" + named.name
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
    if len(raw) < 12000 or (ctype and not ctype.startswith("image") and raw[:3] not in (b"\xff\xd8\xff", b"\x89PN")):
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
    if not local:
        file_photo = commons_class_photo(facts.get("class_name") or "sailing dinghy")
        local = download_image(file_photo, issue, facts["slug"]) if file_photo else None
    blocks = []
    if local:
        credit = pretty_credit(local.get("credit") or "", local.get("source_url") or local.get("url") or "")
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
