#!/usr/bin/env python3
"""Cluster same-event coverage and rewrite one unique magazine article.

Reverse-engineered from Perplexity Discover / RAG news synthesis, plus
Ground News clustering, Artifact de-baited headlines, Monok stored articles,
and Sportradar/United Robots box-score recaps:

  scrape the event's own primary sources (club, class, host Facebook, local
  news) → keep only items about THIS event → write one article locked to
  those texts and the results card (RAG: no fact that is not in a source) →
  inline citations → photographs from those same sources (podium and on the
  water are both valid; more than one photo is allowed) → 1st/2nd/3rd.

Wikimedia / Wikipedia is never a source. A 1954 stock boat is not a source.
Paid APIs are optional. No login-wall bypass.
"""
from __future__ import annotations

import hashlib
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
LEADERBOARD_LIMIT = 3
LEADERBOARD_COLS = ["Pos", "Helm", "Crew", "Club", "Sail No", "Nett"]
WRONG_CLASS = {
    "420": ("505", "dart 18", "dabchick", "hobie", "optimist"),
    "505": ("420", "dart 18", "dabchick", "hobie", "optimist"),
    "Dart 18": ("420", "505", "dabchick", "hobie", "optimist"),
    "Dabchick": ("420", "505", "dart", "hobie", "505er"),
}
SEED_URLS = {
    "2026-09-25-tsc-420-nationals": [
        "https://www.facebook.com/420nationalssouthafrica/",
        "https://novanews.co.za/school/hermanus-high-schools-sailors-crowned-national-champions/",
        "https://www.facebook.com/theewatersportsclub/",
        "https://www.facebook.com/share/g/1Jh51CDMew/",
        "https://www.theewater.co.za/",
    ],
    "2026-09-24-hmyc-dart-18-nationals": [
        "https://www.facebook.com/share/p/1PGpY1pGh1/",
        "https://www.facebook.com/share/g/19VLSkGHBk/",
        "https://www.facebook.com/henleymidmaryachtclub",
        "https://www.hmyc.org.za/events/367984",
        "https://www.hmyc.org.za/",
    ],
    "2026-09-24-ayc-505-nationals": [
        "https://rsa505.org.za/index.php?option=com_content&view=article&id=338:505-nationals-2026-great-event-at-aeolians&catid=11&Itemid=101",
        "https://rsa505.org.za/",
        "https://www.facebook.com/share/g/1MHJNWcFSM/",
        "https://www.facebook.com/AeoliansClub/",
        "https://aeolians.co.za/",
    ],
    "2026-09-24-ayc-dabchick-gauteng-regionals": [
        "https://www.revolutionise.com.au/dabchickca/events/358939",
        "https://www.revolutionise.com.au/dabchickca/",
        "https://www.revolutionise.com.au/dabchickca/gallery",
        "https://www.facebook.com/dabchicksailingrsa",
        "https://www.facebook.com/AeoliansClub/",
    ],
    "2026-10-04-free-state-youth-provincial-champs": [
        "https://sailingsa.co.za/regatta/2026-10-04-free-state-youth-provincial-champs",
        "https://www.ldyc.co.za/",
        "https://www.ldyc.co.za/youthsailing",
        "https://www.ldyc.co.za/free-state",
    ],
}
LAYOUTS = ("photo-led", "split", "classic", "compact")
HOST_FALLBACK = {
    "TSC": "Theewater Sports Club",
    "HMYC": "Henley Midmar Yacht Club",
    "AYC": "Aeolians Yacht Club",
    "LDYC": "Lake Deneys Yacht Club",
}
JUNK_CLUSTER = (
    "dart.dev",
    "dartpad.dev",
    "dart.org",
    "dartcontainer.com",
    "wikipedia.org",
    "wikimedia.org",
    "upload.wikimedia",
    "commons.wikimedia",
    "instagram.com/accounts/login",
    "music.youtube",
    "tiktok.com/@",
    "tiktok.com/api",
)
PLACE_LINE = re.compile(
    r"(?P<place>\d+)(?:st|nd|rd|th)\s*[–\-]\s*(?P<name>[A-Za-z][A-Za-z \-']+?)"
    r"(?:\s*\((?P<club>[A-Z0-9]{2,8})\))?\s*[–\-]\s*Sail\s+(?P<sail>\S+)",
    re.I,
)
SPECIAL_MENTION = re.compile(
    r"special mention to ([A-Za-z][A-Za-z \-']+), finishing (\d+)(?:st|nd|rd|th)?",
    re.I,
)


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
    title = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", title).strip()
    title = re.sub(r"\s+incorporating\b.*$", "", title, flags=re.I).strip()
    start = str(first.get("start_date") or slug[:10])[:10]
    end = str(first.get("end_date") or start)[:10]
    winner_nett = winner.get("nett_points_raw")
    second_nett = second.get("nett_points_raw")
    classes = list(dict.fromkeys((r.get("class_name") or r.get("class_canonical") or "").strip() for r in ranked if (r.get("class_name") or r.get("class_canonical") or "").strip()))
    mixed_class = len(classes) > 1
    return {
        "slug": slug,
        "title": title,
        "class_name": "" if mixed_class else (first.get("class_name") or first.get("class_canonical") or "").strip(),
        "classes": classes,
        "mixed_class": mixed_class,
        "club": club,
        "club_name": _club_name(club, first.get("host_club_name") or ""),
        "host_club_slug": first.get("host_club_slug") or club.lower(),
        "start": start,
        "end": end,
        "entries": entries,
        "races": races,
        "status": (first.get("result_status") or "Published").strip(),
        "winner": _names(winner),
        "winner_class": (winner.get("class_name") or winner.get("class_canonical") or "").strip(),
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
        "ranked_rows": ranked,
    }


def _official_results_card(facts: dict) -> dict:
    """SailingSA results are already live by the Monday publisher. Always source [1]."""
    bits = [
        f"Official SAS-sanctioned {facts.get('title') or 'event'} at {facts.get('club_name') or facts.get('club') or 'the host club'}.",
    ]
    if facts.get("winner"):
        bits.append(f"1st {facts['winner']}.")
    if facts.get("second"):
        bits.append(f"2nd {facts['second']}.")
    if facts.get("third"):
        bits.append(f"3rd {facts['third']}.")
    if facts.get("entries") or facts.get("races"):
        bits.append(f"{facts.get('entries') or 0} entries, {facts.get('races') or 0} races.")
    if facts.get("status"):
        bits.append(f"Results are {facts['status']}.")
    return {
        "url": facts.get("url") or "",
        "title": f"{facts.get('title') or 'Event'} — SailingSA results",
        "description": " ".join(bits),
        "snippet": " ".join(bits),
        "engine": "sailingsa",
        "role": "official_results",
        "published": facts.get("end") or "",
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


def event_finished(facts: dict, issue: str | None = None) -> bool:
    """Monday magazine is written after racing. Live tense only if the issue date is still inside the event."""
    if "finished" in facts:
        return bool(facts["finished"])
    try:
        start = __import__("datetime").date.fromisoformat(str(facts.get("start") or "")[:10])
        end = __import__("datetime").date.fromisoformat(str(facts.get("end") or "")[:10])
    except ValueError:
        return True
    if not issue:
        return True
    try:
        day = __import__("datetime").date.fromisoformat(str(issue)[:10])
    except ValueError:
        return True
    return not (start <= day <= end)


def unique_headline(facts: dict, cluster: dict | None = None) -> str:
    winner = facts["winner"]
    title = facts["title"]
    venue = facts["club_name"]
    short_venue = venue.replace(" Yacht Club", "").replace(" Sports Club", "").replace(" Club", "")
    finished = event_finished(facts)
    if facts.get("tied_first") and facts.get("second"):
        return f"{winner} {_agree(winner, 'take', 'takes')} {title} after a points tie at {short_venue}"
    if facts.get("winner_wins") and facts["winner_wins"] >= max(3, int(facts.get("races") or 0) // 2):
        if facts["winner_wins"] == int(facts.get("races") or 0) and (facts.get("races") or 0) >= 6:
            return f"{winner} {_agree(winner, 'sweep', 'sweeps')} {title} at {short_venue}"
        return f"{winner} {_agree(winner, 'dominate', 'dominates')} {title} at {short_venue}"
    # Live "leads" only while the event is still racing. After it ends, they won.
    if (facts.get("status") or "").lower() == "provisional" and not finished:
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


def _cluster_text(item):
    from evidence_pipeline import text_of
    return text_of(item)


def _keep_cluster_item(item, facts):
    from evidence_pipeline import verify
    return verify(item,facts)["accepted"]


def _host_source(cluster: dict | None, facts: dict | None = None) -> dict | None:
    best = None
    best_len = 0
    slug = str((facts or {}).get("slug") or "")
    for item in (cluster or {}).get("articles") or []:
        text = _cluster_text(item)
        score = len(text)
        url = (item.get("url") or "") + " " + (item.get("share_url") or "")
        if "1PGpY1pGh1" in url and "dart-18-nationals" not in slug:
            continue
        if "host_club" in (item.get("engine") or "") + (item.get("provenance") or ""):
            score += 200
        if score > best_len:
            best = dict(item, text=text)
            best_len = score
    return best if best and best_len >= 40 else None


def citation_index(cluster: dict | None, facts: dict | None = None) -> list[dict]:
    """Numbered primary sources. [1] is always the SailingSA results card."""
    out = []
    seen = set()

    def add(url: str, title: str = "", text: str = ""):
        url = (url or "").split("#")[0].strip()
        if not url or url in seen or _wiki_url(url):
            return
        seen.add(url)
        out.append({"n": len(out) + 1, "url": url, "title": title or url, "text": text or ""})

    if facts:
        add(facts.get("url") or "", facts.get("title") or "SailingSA results")
    for item in (cluster or {}).get("articles") or []:
        add(
            item.get("url") or item.get("share_url") or item.get("source_url") or "",
            item.get("title") or "",
            _cluster_text(item),
        )
    return out


def _cite(n: int) -> str:
    return f"[{int(n)}]"


def _source_for_url(index: list[dict], url: str) -> dict | None:
    url = (url or "").split("#")[0]
    for item in index:
        if item["url"] == url or url and url in item["url"]:
            return item
    return None


def _cluster_color(cluster, facts=None, index=None):
    from evidence_pipeline import source_notes
    return source_notes(cluster,facts or {},index or citation_index(cluster,facts))


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


def rewrite_paragraphs(facts, cluster=None, index=None):
    from evidence_pipeline import recap
    return recap(facts,cluster or {},index or citation_index(cluster,facts))


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


def extract_article(url):
    from evidence_pipeline import extract
    return extract(url)


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
    perplexity = os.getenv("PERPLEXITY_API_KEY")
    if perplexity:
        try:
            payload = json.dumps(
                {
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Return only South African sailing sources for this event. No Wikipedia.",
                        },
                        {
                            "role": "user",
                            "content": "Primary club, class Facebook, and news URLs for: " + query,
                        },
                    ],
                }
            ).encode()
            req = urllib.request.Request(
                "https://api.perplexity.ai/chat/completions",
                data=payload,
                headers={**UA, "Authorization": "Bearer " + perplexity, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            citations = (((data.get("choices") or [{}])[0].get("message") or {}).get("citations")) or data.get("citations") or []
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            urls = list(citations) + re.findall(r"https?://[^\s)>\]]+", text)
            for link in urls:
                if _wiki_url(link):
                    continue
                items.append({"url": link, "title": "", "description": text[:400], "engine": "perplexity"})
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


def cluster_coverage(facts, pack=None, fetch=True):
    from evidence_pipeline import verified_cluster
    candidates=[_official_results_card(facts)]
    for post in (pack or {}).get("verified_posts") or (pack or {}).get("posts") or []:
        candidates.append(dict(post))
    # Previously retrieved source text is evidence, never a trusted identity label.
    issue=str((pack or {}).get("issue") or "2026-09-28")
    old=ROOT/"data"/("reference-"+issue+".json")
    if not old.exists():old=ROOT/"issues"/issue/"issue.json"
    if old.exists():
        data=json.loads(old.read_text())
        for article in data.get("articles",[]):
            if article.get("event_id")!=facts["slug"]:continue
            for cite in article.get("citations",[]):
                candidates.append({"url":cite["url"],"title":cite.get("title",""),"body":cite.get("text",""),"engine":"cached_evidence"})
    candidates += [{"url":u,"engine":"seed"} for u in SEED_URLS.get(facts["slug"],[])]
    if fetch:
        from search_everywhere import discovery_queries,google_news,web_hits
        import concurrent.futures
        ctx=dict(facts,id=facts["slug"],event_url=facts["url"])
        queries=discovery_queries(ctx)[:4]
        def query(q):
            return google_news(q,limit=4)+web_hits(q,limit=5)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for hits in pool.map(query,queries):candidates.extend(hits)
    seen=set();unique=[]
    for item in candidates:
        from evidence_pipeline import canonical
        key=canonical(item.get("url") or item.get("source_url"))
        if key and key not in seen:
            seen.add(key);unique.append(item)
    cluster=verified_cluster(facts,unique,fetch=fetch)
    # The official record needs no network extraction and is always citation 1.
    cluster["articles"].sort(key=lambda a:a["verification"]["reason"]!="official_results")
    return cluster


def _wiki_url(url: str) -> bool:
    low = (url or "").lower()
    return any(token in low for token in ("wikipedia.org", "wikimedia.org", "upload.wikimedia", "commons.wikimedia"))


def _page_avatar_media(url: str) -> bool:
    match = re.search(r"media_id=(\d+)", url or "")
    if not match:
        return False
    mid = match.group(1)
    return mid.startswith("1000") and len(mid) == 15


def _facebook_page_chrome(url: str, image: str = "") -> bool:
    """Facebook page/profile OG images are logos. Posts and group albums can be photographs."""
    img = (image or "").lower()
    if "lookaside.fbsbx.com" in img or "/t39.30808-6/" in img:
        return False
    low = (url or "").lower()
    if "facebook.com" not in low:
        return False
    if any(
        token in low
        for token in ("/posts/", "/share/p/", "/share/g/", "/groups/", "/permalink", "/photo.php", "/photo/")
    ):
        return False
    path = urllib.parse.urlparse(low).path.strip("/")
    if path.endswith("/photos") or "/photos/" in low:
        return True
    return bool(path)


def _bad_image_url(url: str) -> bool:
    low = (url or "").lower()
    if _wiki_url(low):
        return True
    if _page_avatar_media(low):
        return True
    if "/t39.30808-1/" in low:
        return True
    if "sailingsa.co.za/api/og" in low:
        return True
    return any(
        token in low
        for token in (
            "logo",
            "flogo",
            "reel",
            "badge",
            "burgee",
            "flag",
            "banner",
            "enternow",
            "enter-now",
            "enter_now",
            ".svg",
            "icon",
            "avatar",
            "profile",
            "sprite",
            "placeholder",
            "default-user",
            "favicon",
            "ytimg.com/vi",
            "youtube.com/img",
            "yt_1200",
            "sailingsa.co.za/static",
            "sailingsa.co.za/assets",
        )
    )


def _image_size(raw: bytes) -> tuple[int, int] | None:
    if raw[:2] == b"\xff\xd8":
        i = 2
        while i < len(raw) - 8:
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h = int.from_bytes(raw[i + 5 : i + 7], "big")
                w = int.from_bytes(raw[i + 7 : i + 9], "big")
                return w, h
            if marker == 0xD8:
                i += 2
                continue
            if i + 4 > len(raw):
                break
            seglen = int.from_bytes(raw[i + 2 : i + 4], "big")
            i += 2 + seglen
        return None
    if raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
        w = int.from_bytes(raw[16:20], "big")
        h = int.from_bytes(raw[20:24], "big")
        return w, h
    return None


def _flat_block_ratio(raw: bytes) -> float:
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:
        return 0.0
    try:
        im = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        return 0.0
    block = 16
    w, h = im.size
    flats = total = 0
    for y in range(0, h - block + 1, block):
        for x in range(0, w - block + 1, block):
            crop = im.crop((x, y, x + block, y + block))
            total += 1
            if len(set(crop.getdata())) <= 6:
                flats += 1
    return flats / total if total else 0.0


def _is_event_photograph(raw: bytes) -> bool:
    """Keep prizegiving and on-water shots. Drop flags, logos, and 'enter now' posters."""
    if not raw or len(raw) < 12000:
        return False
    size = _image_size(raw)
    if not size:
        return False
    w, h = size
    if min(w, h) < 320:
        return False
    aspect = w / h if h else 0
    if aspect < 0.62 or aspect > 1.85:
        return False
    if 0.92 <= aspect <= 1.08 and min(w, h) >= 600:
        return False
    if _flat_block_ratio(raw) >= 0.55:
        return False
    return True


def _wrong_class(blob: str, klass: str) -> bool:
    blob = (blob or "").lower()
    klass = (klass or "").strip()
    for token in WRONG_CLASS.get(klass, ()):
        if re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", blob):
            return True
    return False


LOOKASIDE_RE = re.compile(r"https://lookaside\.fbsbx\.com/lookaside/crawler/media/\?media_id=\d+")
CLASS_GALLERIES = {
    "Dabchick": "https://www.revolutionise.com.au/dabchickca/",
    "505": "https://rsa505.org.za/",
    "420": "https://www.facebook.com/420nationalssouthafrica/",
    "Dart 18": "https://www.facebook.com/henleymidmaryachtclub",
}


def harvest_source_images(url: str) -> list[dict]:
    """Pull photographs from the event's own page. Never wiki."""
    if not url or not url.startswith("http") or _wiki_url(url):
        return []
    if "facebook.com" in url:
        return facebook_source_images(url)
    return website_source_images(url)


def facebook_source_images(url: str) -> list[dict]:
    try:
        from facebook_cross_share import resolve_facebook_url

        resolved = resolve_facebook_url(url)
    except Exception:
        resolved = {"canonical_url": url, "title": "", "image": ""}
    out = []
    source = resolved.get("canonical_url") or url
    credit = _credit_from_url(source)
    if resolved.get("image") and not _bad_image_url(resolved["image"]):
        out.append(
            {
                "url": resolved["image"],
                "source_url": source,
                "title": resolved.get("title") or "",
                "credit": credit,
            }
        )
    html = ""
    for headers in (FB_UA, {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", "Accept": "text/html"}):
        try:
            raw, _ = _http_get(resolved.get("canonical_url") or url, headers, timeout=20)
            html = raw.decode("utf-8", "replace")
            if "og:title" in html.lower() or "og:image" in html.lower():
                break
        except Exception:
            continue
    seen = {item["url"] for item in out}
    for link in LOOKASIDE_RE.findall(html):
        if link in seen or _bad_image_url(link):
            continue
        seen.add(link)
        out.append({"url": link, "source_url": source, "title": resolved.get("title") or "", "credit": credit})
        if len(out) >= 12:
            break
    return out


def website_source_images(url: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup

        raw, _ = _http_get(url, UA, timeout=20)
        soup = BeautifulSoup(raw, "html.parser")
    except Exception:
        return None if False else []
    credit = _credit_from_url(url)
    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
    found = []
    for tag in soup.select('meta[property="og:image"], meta[name="twitter:image"], article img, main img, .gallery img, img'):
        src = tag.get("content") or tag.get("src") or tag.get("data-src") or ""
        if not src:
            continue
        link = urllib.parse.urljoin(url, src)
        if _bad_image_url(link) or _wiki_url(link):
            continue
        if not re.search(r"\.(jpe?g|png|webp)(\?|$)", link, re.I):
            continue
        alt = (tag.get("alt") or title or "").strip()
        found.append({"url": link, "source_url": url, "title": alt, "credit": credit})
    # Class homepages often lead with a team lineup; keep later gallery shots.
    gallery = [item for item in found if "gallery" in (item.get("url") or "").lower()]
    if len(gallery) >= 3:
        skip = gallery[0]["url"]
        found = [item for item in found if item["url"] != skip]
    uniq = []
    seen = set()
    for item in found:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:16]


def class_gallery_photo(klass: str) -> dict | None:
    page = CLASS_GALLERIES.get((klass or "").strip())
    if not page:
        return None
    images = harvest_source_images(page)
    for item in images:
        if not _bad_image_url(item.get("url") or ""):
            return item
    return None


def _event_photo_score(item: dict, facts: dict) -> int:
    """Score only photographs that belong to this event. Wiki and stock boats lose."""
    klass = (facts.get("class_name") or "").strip()
    blob = " ".join((item.get("url") or "", item.get("source_url") or "", item.get("title") or "")).lower()
    photo = (item.get("url") or "").lower()
    source = (item.get("source_url") or "").lower()
    n = 0
    if _wiki_url(blob) or _wiki_url(photo) or _wiki_url(source):
        return -10000
    if _bad_image_url(photo) or _wrong_class(blob, klass):
        return -100
    if _facebook_page_chrome(source, photo) and "facebook.com" in source:
        return -80
    if klass and klass.lower() in blob:
        n += 30
    slug = str(facts.get("slug") or "").lower()
    if "1pgpy1pgh1" in blob or "1633819895206118" in blob:
        if "dart-18-nationals" not in slug:
            return -10000
        n += 220
    if "1MHJNWcFSM".lower() in blob or "230542873685522" in blob:
        n += 140
    if "19VLSkGHBk".lower() in blob or "310727125653436" in blob:
        if "dart-18-nationals" not in slug:
            return -10000
        n += 140
    if "420nationalssouthafrica" in blob and klass == "420":
        n += 160
    if "id=338" in source or "505-nationals-2026" in blob:
        if "505-nationals" not in slug:
            return -10000
        n += 180
    if "rsa505.org.za" in blob and klass == "505":
        n += 80
    if "20261013" in photo:
        n += 60
    if "dabchickca/events/358939" in blob and klass == "Dabchick":
        n += 180
    if "novanews" in blob and "hermanus-high-schools-sailors" in blob:
        n += 90
    if "hmyc.org.za/events/367984" in blob:
        if "dart-18-nationals" not in slug:
            return -10000
        n += 80
    if any(k in blob for k in ("prize", "trophy", "podium", "final result")):
        n += 50
    if "lookaside.fbsbx.com" in photo or "scontent" in photo:
        n += 70
    if "cdn.revolutionise.com.au/events/" in photo:
        n += 40
    if "wp-content/uploads/2026/09" in photo:
        n += 40
    if photo.endswith(".jpg") or photo.endswith(".jpeg") or "lookaside" in photo:
        n += 15
    path = urllib.parse.urlparse(source).path.strip("/")
    host = urllib.parse.urlparse(source).netloc.lower()
    if path in ("", "home") and "facebook.com" not in host and "rsa505.org.za" not in host:
        n -= 80
    if "enter now" in blob:
        n -= 10
    return n


def seed_media_images(facts: dict) -> list[dict]:
    """Local event photographs checked into data/seed-media/<slug>.<ext>."""
    slug = (facts.get("slug") or "").strip()
    if not slug:
        return []
    folder = ROOT / "data" / "seed-media"
    found = []
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = folder / (slug + ext)
        if not path.is_file():
            continue
        found.append(
            {
                "url": str(path),
                "source_url": facts.get("url") or "",
                "title": facts.get("title") or slug,
                "credit": "Event photography",
                "local_file": str(path),
                "seed": True,
            }
        )
    return found


def pick_images(facts: dict, cluster: dict, pack: dict | None = None, limit: int = 2) -> list[dict]:
    """Prizegiving and on-the-water shots from this event's sources. Never wiki or logos."""
    candidates = []
    seen = set()
    from evidence_pipeline import canonical, MEDIA_EXCLUSIONS, other_event_conflict
    accepted_sources = {canonical(x.get("url")) for x in cluster.get("articles", [])}
    accepted_sources.add(canonical(facts.get("url") or ""))

    def add(item: dict):
        url = (item.get("url") or "").split("#")[0]
        source = item.get("source_url") or ""
        original_title = item.get("title") or ""
        # Never copy this event's headline onto a foreign photo before the conflict check.
        if other_event_conflict({"url": source, "source_url": source, "title": original_title, "body": original_title}, facts):
            return
        if cluster.get("schema_version") == "verified-evidence-1" and canonical(source) not in accepted_sources:
            return
        if not url or url in seen or _wiki_url(url) or canonical(url) in MEDIA_EXCLUSIONS:
            return
        if not item.get("local_file") and (_bad_image_url(url) or (_facebook_page_chrome(source, url) and _event_photo_score(item, facts) < 40)):
            return
        seen.add(url)
        candidates.append(item)

    for item in (cluster or {}).get("articles") or []:
        if item.get("image"):
            add(
                {
                    "url": item["image"],
                    "source_url": item.get("url") or item.get("share_url") or "",
                    "title": item.get("title") or "",
                    "credit": _credit_from_url(item.get("url") or item["image"]),
                }
            )
    for document in (cluster or {}).get("articles") or []:
        for attachment in document.get("images") or []:
            add({"url":attachment["url"],"source_url":document.get("url") or "",
                 "title":attachment.get("title") or "","credit":_credit_from_url(document.get("url") or "")})
    for img in (pack or {}).get("images") or []:
        if img.get("image_url"):
            add(
                {
                    "url": img["image_url"],
                    "source_url": img.get("source_url") or "",
                    "title": img.get("source_title") or "",
                    "credit": pretty_credit(img.get("platform") or "", img.get("source_url") or img.get("image_url") or ""),
                }
            )
    ranked = [item for item in candidates if item.get("seed") or _event_photo_score(item, facts) >= 40]
    ranked.sort(key=lambda item: (1 if item.get("seed") else 0, _event_photo_score(item, facts)), reverse=True)
    return (seed_media_images(facts) + ranked)[:limit]


def pick_image(facts: dict, cluster: dict, pack: dict | None = None) -> dict | None:
    chosen = pick_images(facts, cluster, pack, limit=1)
    return chosen[0] if chosen else None


def pretty_credit(raw: str, url: str = "") -> str:
    blob = f"{raw or ''} {url or ''}".lower()
    if "novanews" in blob:
        return "NovaNews"
    if "420nationalssouthafrica" in blob:
        return "420 Sailing South Africa"
    if "rsa505" in blob:
        return "RSA 505"
    if "dabchick" in blob or "revolutionise.com.au/dabchickca" in blob:
        return "Dabchick Class Association"
    if "henleymidmar" in blob or "hmyc" in blob:
        return "Henley Midmar Yacht Club"
    if "theewater" in blob:
        return "Theewater Sports Club"
    if "aeolians" in blob:
        return "Aeolians Yacht Club"
    if "ldyc" in blob or "lakedeneys" in blob or "deneys" in blob:
        return "Lake Deneys Yacht Club"
    if "youtube" in blob or "youtu.be" in blob:
        return "YouTube"
    if "facebook" in blob or "fbcdn" in blob or "lookaside.fbsbx" in blob:
        return "Facebook / host club"
    host = urllib.parse.urlparse(url or raw or "").netloc.lower().removeprefix("www.")
    return host or (raw or "source").strip()


def _credit_from_url(url: str) -> str:
    return pretty_credit("", url)


def download_image(image: dict, issue: str, slug: str, index: int = 0) -> dict | None:
    url = (image or {}).get("url") or ""
    local_file = (image or {}).get("local_file") or ""
    if (not url and not local_file) or _wiki_url(url):
        return None
    dest_dir = ROOT / "public" / "issues" / issue / "media"
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "issues" / issue / "media"
    source_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    path = (local_file or urllib.parse.urlparse(url).path).lower()
    for cand in (".png", ".webp", ".jpeg", ".jpg"):
        if path.endswith(cand):
            ext = ".jpg" if cand == ".jpeg" else cand
            break
    if "lookaside.fbsbx" in url or "fbcdn" in url:
        ext = ".jpg"
    suffix = "" if index == 0 else f"-{index + 1}"
    filename = slug + suffix + ext
    dest = dest_dir / filename
    raw = b""
    ctype = ""
    if local_file and pathlib.Path(local_file).is_file():
        raw = pathlib.Path(local_file).read_bytes()
        ctype = "image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    else:
        headers = dict(
            FB_UA
            if any(token in url for token in ("fbcdn", "facebook.com", "lookaside.fbsbx"))
            else UA
        )
        headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        try:
            raw, ctype = _http_get(url, headers, timeout=25)
        except Exception:
            return None
    if len(raw) < 8000 or (ctype and not str(ctype).startswith("image") and raw[:3] not in (b"\xff\xd8\xff", b"\x89PN")):
        return None
    if not image.get("seed") and not _is_event_photograph(raw):
        return None
    dest.write_bytes(raw)
    (source_dir / filename).write_bytes(raw)
    out = dict(image)
    out["url"] = "media/" + filename
    out["local_path"] = str(dest)
    out["bytes"] = len(raw)
    out["digest"] = hashlib.md5(raw).hexdigest()
    return out


def layout_for(index: int, article_type: str) -> str:
    if article_type == "feature":
        return "lead"
    return LAYOUTS[index % len(LAYOUTS)]


def rewrite_event(issue: str, facts: dict, pack: dict | None = None, cluster: dict | None = None, layout: str = "classic") -> dict:
    facts = dict(facts)
    facts["finished"] = event_finished(facts, issue)
    fetched_cluster = cluster is None
    cluster = cluster or cluster_coverage(facts, pack, fetch=True)
    cites = citation_index(cluster, facts)
    paras = rewrite_paragraphs(facts, cluster, cites)
    headline = unique_headline(facts, cluster)
    cols, table = facts["leaderboard"]
    images = pick_images(facts, cluster, pack, limit=2)
    locals = []
    seen_hash = set()
    for idx, image in enumerate(images):
        local = download_image(image, issue, facts["slug"], index=idx)
        if not local:
            continue
        digest = local.get("digest") or local.get("url")
        if digest in seen_hash:
            continue
        seen_hash.add(digest)
        locals.append(local)
    blocks = []
    from evidence_pipeline import photo_caption
    for local in locals:
        credit = pretty_credit(local.get("credit") or "", local.get("source_url") or local.get("url") or "")
        blocks.append(
            {
                "type": "image",
                "url": local["url"],
                "alt": local.get("title") or facts["title"],
                "caption": photo_caption(local,facts,cluster) + f" Photo: {credit}.",
                "credit": credit,
                "source_url": local.get("source_url") or facts["url"],
                "rights_status": "source_attributed",
            }
        )
    for text in paras:
        blocks.append({"type": "paragraph", "text": text})
    blocks.append({"type": "heading", "text": "1st, 2nd, 3rd"})
    blocks.append(
        {
            "type": "results",
            "source_event_url": facts["url"],
            "columns": cols,
            "rows": table,
            "as_of": issue,
        }
    )
    sources = [item["url"] for item in cites]
    for item in cluster.get("articles") or []:
        if item.get("url") and item["url"] not in sources and not _wiki_url(item["url"]):
            sources.append(item["url"])
    hero = locals[0] if locals else None
    article = {
        "id": facts["slug"],
        "type": "regatta_report",
        "headline": headline,
        "deck": deck_from_facts(facts),
        "byline": "SailingSA",
        "kicker": (
            (
                " / ".join(facts.get("classes") or [])
                if facts.get("mixed_class")
                else (facts.get("class_name") or "Regatta")
            ).upper()
            + "  ·  "
            + facts["club"]
        ),
        "published_at": issue,
        "event_id": facts["slug"],
        "layout": layout,
        "hero_image": {"url": hero["url"], "source_url": hero.get("source_url"), "rights_status": "source_attributed"} if hero else None,
        "blocks": blocks,
        "sources": sources,
        "citations": cites,
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


def _seed_event_images(facts: dict) -> list[dict]:
    """Last resort: scrape this event's seed URLs. Never wiki or a club homepage stock shot."""
    found = []
    for url in SEED_URLS.get(facts.get("slug") or "", []):
        if _wiki_url(url):
            continue
        for item in harvest_source_images(url):
            if _event_photo_score(item, facts) >= 40:
                found.append(item)
    found.sort(key=lambda item: _event_photo_score(item, facts), reverse=True)
    uniq = []
    seen = set()
    for item in found:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:2]


def rewrite_weekend_feature(issue,monday,events,articles):
    from evidence_pipeline import feature
    return feature(issue,monday,events,articles)
