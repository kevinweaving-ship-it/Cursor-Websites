#!/usr/bin/env python3
"""
Scrape SAS events list from https://www.sailing.org.za/events/
- List: title, details_url, dates, venue, category, sas_event_id, external_host/id.
- Detail (every event): host, location, address, start/end date, NOR URL, SI URL,
  results URL, other doc URLs, description, contact, organiser.
- Output: one CSV with all fields. Use --no-detail for list-only (quick run).

Daily auto: run with --output-dir DIR --date-stamp; cron e.g. 0 4 * * * run-daily-events-scrape.sh
"""
from __future__ import annotations

import argparse
import csv
import html as html_module
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE = "https://www.sailing.org.za"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# First date in "Sat 07 Mar 2026 09:00" or "Fri 20 Mar 2026 09:00 - Mon 23 Mar 2026 09:00"
DATE_RE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s+(\d{2}:\d{2})"
)
# "7-8 March 2026" style
DATE_RANGE_RE = re.compile(
    r"(\d{1,2})\s*-\s*(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"
)
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

# Event link: <a href="URL">Title</a> where URL contains /events/ and digits
EVENT_LINK_RE = re.compile(
    r'<a\s+href="(https?://[^"]+/events/\d+)"[^>]*>([^<]+)</a>',
    re.I
)
# Relative SAS link
EVENT_LINK_REL_RE = re.compile(
    r'<a\s+href="(/events/(\d+))"[^>]*>([^<]+)</a>',
    re.I
)
# Any <a href="...">...</a> for doc link matching
LINK_RE = re.compile(r'<a\s+href="(https?://[^"]+)"[^>]*>([^<]*)</a>', re.I)
# Google Maps link: query=... or link text as location
MAPS_QUERY_RE = re.compile(r'query=([^"&\s]+)', re.I)
MAPS_LINK_RE = re.compile(r'<a\s+href="[^"]*maps[^"]*"[^>]*>([^<]+)</a>', re.I)


def is_invalid_venue_text(s: str) -> bool:
    """Reject venue/host values that are HTML fragments or links. Do not store these."""
    if not s or not isinstance(s, str):
        return True
    t = s.strip().lower()
    if "target=" in t or "href=" in t or "http" in t or "blank" in t:
        return True
    return False


def extract_text_only(value: str) -> str:
    """Strip all HTML tags and normalize whitespace; return trimmed text."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html_module.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_host_club(host_line: str) -> str:
    """For 'Association · Club', ignore left side and return club. For map lines, return the first comma-delimited part."""
    if not host_line:
        return ""
    h = extract_text_only(host_line).strip().lstrip(">").strip()
    if not h:
        return ""
    parts = [p.strip(" .,:;-") for p in re.split(r"[·•|]", h) if p.strip(" .,:;-")]
    if len(parts) >= 2:
        h = parts[-1]
    if "," in h:
        h = h.split(",", 1)[0].strip()
    return h


def parse_start_end(text_block: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Return (start_date, end_date, start_time, end_time) from first two DATE_RE matches. Time from group(4)."""
    matches = list(DATE_RE.finditer(text_block))
    if not matches:
        return None, None, None, None
    def to_iso(m):
        day, month_name, year, _ = m.groups()
        month = MONTHS.get(month_name, 1)
        return f"{year}-{month:02d}-{int(day):02d}"
    def to_time(m):
        return (m.group(4) or "").strip() or None if m.lastindex >= 4 else None
    start_date = to_iso(matches[0])
    start_time = to_time(matches[0])
    if len(matches) > 1:
        end_date = to_iso(matches[1])
        end_time = to_time(matches[1])
    else:
        end_date = start_date
        end_time = start_time
    return start_date, end_date, start_time, end_time


def extract_event_id_from_url(url: str) -> tuple[str | None, str | None, str | None]:
    """
    Return (sas_event_id, external_host, external_event_id).
    - SAS: sailing.org.za/events/293438 -> ("293438", None, None)
    - Revolutionise: .../events/334371 -> (None, "revolutionise", "334371")
    - laser.org.za: .../events/301648 -> (None, "laser_org_za", "301648")
    """
    url = url.strip().rstrip("/")
    m = re.search(r"/events/(\d+)(?:\?|$|/)", url)
    if not m:
        return None, None, None
    eid = m.group(1)
    if "sailing.org.za" in url:
        return eid, None, None
    if "revolutionise.com.au" in url:
        return None, "revolutionise", eid
    if "laser.org.za" in url:
        return None, "laser_org_za", eid
    # Other external
    host = re.sub(r"^https?://([^/]+).*", r"\1", url).replace(".", "_")
    return None, host, eid


def fetch_list_page(path: str) -> str:
    url = BASE + path if path.startswith("/") else f"{BASE}/{path}"
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_detail_page(url: str) -> str | None:
    """Fetch event detail page HTML. Returns None on error."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[detail] {url}: {e}", file=sys.stderr)
        return None


def parse_detail_html(html: str, base_url: str) -> dict:
    """
    Extract all details from event detail page. Works for SAS and generic external pages.
    Returns dict: host, location, address, nor_url, si_url, results_url, other_docs,
    description, contact, organiser, start_date, end_date (overrides when present).
    """
    out = {
        "host": "",
        "location": "",
        "address": "",
        "nor_url": "",
        "si_url": "",
        "results_url": "",
        "other_docs": "",
        "description": "",
        "contact": "",
        "organiser": "",
        "category": "",
        "start_date": "",
        "end_date": "",
        "start_time": "",
        "end_time": "",
    }
    # Strip script/style to reduce noise
    html_clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html_clean = re.sub(r"<style[^>]*>.*?</style>", "", html_clean, flags=re.S | re.I)

    # Details card: venue from Location row (text only; strip HTML, no href/target)
    for label in ("Location", "Venue", "Host"):
        idx = html_clean.find(label)
        if idx == -1:
            continue
        # Slice after the label so we get the value node only
        block = html_clean[idx + len(label) : idx + 350]
        text = extract_text_only(block)
        for part in (text.split("\n") if "\n" in text else [text]):
            part = part.strip().strip(":").strip()
            if 3 <= len(part) <= 120 and not is_invalid_venue_text(part):
                out["location"] = part
                out["host"] = extract_host_club(part)
                break
        if out["location"]:
            break

    # Category from Details card (e.g. "Regional Championships")
    for label in ("Category", "Event type", "Type"):
        idx = html_clean.find(label)
        if idx == -1:
            continue
        block = html_clean[idx + len(label) : idx + 200]
        text = extract_text_only(block).strip().strip(":").strip()
        if 2 <= len(text) <= 80 and not is_invalid_venue_text(text):
            out["category"] = text
            break

    # Dates and times: first two DATE_RE matches = start, end (full datetime); persist times when present.
    date_matches = list(DATE_RE.finditer(html_clean))
    if date_matches:
        def to_iso(m):
            day, month_name, year, _ = m.groups()
            month = MONTHS.get(month_name, 1)
            return f"{year}-{month:02d}-{int(day):02d}"
        def to_time(m):
            time_str = (m.group(4) or "").strip() if m.lastindex >= 4 else ""
            if time_str and re.match(r"^\d{1,2}:\d{2}(?::\d{2})?$", time_str):
                return time_str if time_str.count(":") >= 2 else time_str + ":00"
            return ""
        out["start_date"] = to_iso(date_matches[0])
        out["start_time"] = to_time(date_matches[0])
        if len(date_matches) > 1:
            out["end_date"] = to_iso(date_matches[1])
            out["end_time"] = to_time(date_matches[1])
        else:
            out["end_date"] = out["start_date"]
            out["end_time"] = out["start_time"]
    else:
        range_m = DATE_RANGE_RE.search(html_clean)
        if range_m:
            d1, d2, month_name, year = range_m.groups()
            month = MONTHS.get(month_name, 1)
            out["start_date"] = f"{year}-{month:02d}-{int(d1):02d}"
            out["end_date"] = f"{year}-{month:02d}-{int(d2):02d}"

    # Location: Google Maps link text or query= (only if Details card did not set it)
    if not out["location"]:
        maps_m = re.search(r'<a[^>]+href="[^"]*maps[^"]*"[^>]*>(.*?)</a>', html_clean, re.I | re.S)
        if maps_m:
            loc_text = extract_text_only(maps_m.group(1)).replace("&nbsp;", " ").strip()
            if loc_text and len(loc_text) < 300 and not is_invalid_venue_text(loc_text):
                out["location"] = loc_text
                out["host"] = extract_host_club(loc_text)
        if not out["location"]:
            maps_q = MAPS_QUERY_RE.search(html_clean)
            if maps_q:
                addr = maps_q.group(1).replace("+", " ").replace("%2C", ",").replace("%20", " ").strip()
                if addr and len(addr) < 300 and not is_invalid_venue_text(addr):
                    out["address"] = addr
                    out["location"] = addr
                    out["host"] = extract_host_club(addr[:80])
    # External pages often mention the real club in the body: "...will be held at Club Mykonos..."
    if not out["host"] or out["host"] == out["location"].split(",", 1)[0].strip():
        body_host_m = re.search(r"\bheld at\s+([A-Z][A-Za-z0-9&'()./\-\s]+?)(?:,|\s+with|\s+on|\.)", extract_text_only(html_clean), re.I)
        if body_host_m:
            body_host = extract_host_club(body_host_m.group(1))
            if body_host:
                out["host"] = body_host
    # Final validation: reject any location/host that looks like HTML
    if is_invalid_venue_text(out["location"]):
        out["location"] = ""
    if is_invalid_venue_text(out["host"]):
        out["host"] = ""

    # Doc links: NOR, SI, Results, other PDFs
    nor_pat = re.compile(r"nor|notice\s*of\s*race|notice\s*of\s*race\s*\(nor\)", re.I)
    si_pat = re.compile(r"sailing\s*instructions|^\s*si\s*$|^sis\s*$", re.I)
    results_pat = re.compile(r"^results\s*$|event\s*results", re.I)
    for m in LINK_RE.finditer(html_clean):
        href, text = m.groups()
        href = href.strip()
        text = (text or "").strip()
        if not href or href.startswith("#") or "javascript:" in href.lower():
            continue
        # Resolve relative URLs
        if href.startswith("/"):
            parsed = urlparse(base_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        if nor_pat.search(text) or nor_pat.search(href):
            out["nor_url"] = href
        elif si_pat.search(text) or (".pdf" in href.lower() and "si" in href.lower()):
            out["si_url"] = href
        elif results_pat.search(text):
            out["results_url"] = href
        elif ".pdf" in href.lower() or "/file/" in href or "document" in text.lower():
            if out["other_docs"]:
                out["other_docs"] += " | " + href
            else:
                out["other_docs"] = href

    # Description: first substantial paragraph after "Details" or "Event information"
    for sep in ("Event information", "Details", "Description", "About"):
        idx = html_clean.find(sep)
        if idx == -1:
            continue
        block = html_clean[idx:idx + 2000]
        # First <p>...</p> or div text
        p_m = re.search(r"<p[^>]*>([^<]+)</p>", block, re.I)
        if p_m:
            desc = re.sub(r"\s+", " ", p_m.group(1)).strip()
            if len(desc) > 20 and len(desc) < 2000:
                out["description"] = desc
                break
        # Or text between tags
        text_block = re.sub(r"<[^>]+>", " ", block).strip()
        text_block = re.sub(r"\s+", " ", text_block)
        if 30 < len(text_block) < 1500:
            out["description"] = text_block[:1500]
            break

    # Contact: email or phone pattern
    email_m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html_clean)
    if email_m:
        out["contact"] = email_m.group(0)
    phone_m = re.search(r"(\+?27|0)\s*\d{2}\s*\d{3}\s*\d{4}", html_clean)
    if phone_m and not out["contact"]:
        out["contact"] = phone_m.group(0).strip()

    # Organiser: often same as host or "Organiser"/"Organizer" label
    org_m = re.search(r"Organi[sz]er[:\s]*([^<\n]+)", html_clean, re.I)
    if org_m:
        out["organiser"] = re.sub(r"<[^>]+>", "", org_m.group(1)).strip()[:200]

    return out


# Category strings that appear on the SAS list page (capture as event type; do not use as venue)
LIST_CATEGORY_STRINGS = (
    "Dinghy Event", "National Championships", "Regional Championships", "Training", "Meetings",
    "Multiclass Event", "Keel Boat Event", "Interschools", "Team Sailing Events", "Youth Events",
    "District Competitions",
)


def recover_list_host_from_block_text(block_text: str, title: str, category_line: str) -> str:
    """Recover host from normalized SAS list block text when HTML splits 'Association · Club' across tags/lines."""
    tail = block_text or ""
    if title and title in tail:
        tail = tail.split(title, 1)[1]
    date_matches = list(DATE_RE.finditer(tail))
    if date_matches:
        tail = tail[date_matches[min(len(date_matches), 2) - 1].end():]
    if category_line and category_line in tail:
        tail = tail.split(category_line, 1)[0]
    if "Details" in tail:
        tail = tail.split("Details", 1)[0]
    candidate = extract_host_club(tail.strip())
    return candidate


def parse_list_html(html: str, is_past: bool) -> list[dict]:
    events = []
    # Prefer full URLs (covers SAS + external)
    for m in EVENT_LINK_RE.finditer(html):
        url, title = m.groups()
        title = title.strip()
        if not title or title.lower() in ("list", "calendar", "details", "finder", "past", "upcoming"):
            continue
        # Skip category/filter links (they point to /events/list)
        if "/events/list" in url and "/events/\d" not in url:
            continue
        sas_id, ext_host, ext_id = extract_event_id_from_url(url)
        # Context block for date/venue/type (allow enough room for host + event type + details link)
        start_idx = max(0, m.start() - 50)
        end_idx = min(len(html), m.end() + 1200)
        block = html[start_idx:end_idx]
        block_text = extract_text_only(block)
        start_iso, end_iso, start_t, end_t = parse_start_end(block)
        # Venue/host and category: scan block lines; category from list so upcoming events get event_type
        venue_line = ""
        category_line = ""
        for cat in LIST_CATEGORY_STRINGS:
            if cat.lower() in block_text.lower():
                category_line = cat
                break
        lines = block.split("\n")
        for i, line in enumerate(lines):
            clean = re.sub(r"<[^>]+>", "", line.strip()).strip()
            if not clean or not DATE_RE.search(clean):
                continue
            for j in range(i + 1, len(lines)):
                next_clean = re.sub(r"<[^>]+>", "", lines[j].strip()).strip()
                if not next_clean or len(next_clean) > 200:
                    continue
                if DATE_RE.search(next_clean):
                    break
                if next_clean in LIST_CATEGORY_STRINGS:
                    if not category_line:
                        category_line = next_clean
                    continue
                if next_clean in ("Details", "Closed"):
                    continue
                if "class=" in next_clean or next_clean.startswith("div") or "pb-" in next_clean:
                    continue
                if next_clean.lstrip(">").strip() == title:
                    continue
                if 5 <= len(next_clean) <= 120 and not is_invalid_venue_text(next_clean):
                    if not venue_line:
                        venue_line = extract_host_club(next_clean)
                    continue
            break
        if not venue_line or not category_line:
            for line in lines:
                line = line.strip()
                if not line or line.startswith("<"):
                    continue
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if not clean or len(clean) > 200 or DATE_RE.search(clean):
                    continue
                if clean.lstrip(">").strip() == title:
                    continue
                if clean in LIST_CATEGORY_STRINGS:
                    if not category_line:
                        category_line = clean
                    continue
                if clean in ("Details", "Closed"):
                    continue
                if "class=" in clean or clean.startswith("div") or "pb-" in clean:
                    continue
                if 5 <= len(clean) <= 120 and not is_invalid_venue_text(clean):
                    if not venue_line:
                        venue_line = extract_host_club(clean)
                    continue
        if (not venue_line or venue_line.endswith("·")) and block_text:
            recovered = recover_list_host_from_block_text(block_text, title, category_line)
            if recovered:
                venue_line = recovered
        events.append({
            "title": title,
            "details_url": url,
            "start_date": start_iso or "",
            "end_date": end_iso or "",
            "start_time": start_t or "",
            "end_time": end_t or "",
            "venue_text": venue_line,
            "category": category_line,
            "sas_event_id": sas_id or "",
            "external_host": ext_host or "",
            "external_event_id": ext_id or "",
            "is_past": is_past,
            "host": "", "location": "", "address": "", "nor_url": "", "si_url": "", "results_url": "",
            "other_docs": "", "description": "", "contact": "", "organiser": "",
        })
    # Also catch relative SAS links if we missed any
    for m in EVENT_LINK_REL_RE.finditer(html):
        path, eid, title = m.groups()
        title = title.strip()
        if not title or title.lower() in ("list", "calendar", "details", "finder", "past", "upcoming"):
            continue
        full_url = BASE + path
        if any(e["details_url"] == full_url for e in events):
            continue
        start_idx = max(0, m.start() - 50)
        end_idx = min(len(html), m.end() + 1200)
        block = html[start_idx:end_idx]
        block_text = extract_text_only(block)
        start_iso, end_iso, start_t, end_t = parse_start_end(block)
        venue_line = ""
        category_line = ""
        for cat in LIST_CATEGORY_STRINGS:
            if cat.lower() in block_text.lower():
                category_line = cat
                break
        lines = block.split("\n")
        for i, line in enumerate(lines):
            clean = re.sub(r"<[^>]+>", "", line.strip()).strip()
            if not clean or not DATE_RE.search(clean):
                continue
            for j in range(i + 1, len(lines)):
                next_clean = re.sub(r"<[^>]+>", "", lines[j].strip()).strip()
                if not next_clean or len(next_clean) > 200 or DATE_RE.search(next_clean):
                    continue
                if next_clean in LIST_CATEGORY_STRINGS:
                    if not category_line:
                        category_line = next_clean
                    continue
                if "class=" in next_clean or next_clean.startswith("div") or "pb-" in next_clean:
                    continue
                if next_clean.lstrip(">").strip() == title:
                    continue
                if 5 <= len(next_clean) <= 120 and not is_invalid_venue_text(next_clean):
                    if not venue_line:
                        venue_line = extract_host_club(next_clean)
                    continue
            break
        if not venue_line or not category_line:
            for line in lines:
                line = line.strip()
                if not line or line.startswith("<"):
                    continue
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if not clean or len(clean) > 200 or DATE_RE.search(clean):
                    continue
                if clean.lstrip(">").strip() == title:
                    continue
                if clean in LIST_CATEGORY_STRINGS:
                    if not category_line:
                        category_line = clean
                    continue
                if "class=" in clean or clean.startswith("div") or "pb-" in clean:
                    continue
                if 5 <= len(clean) <= 120 and not is_invalid_venue_text(clean):
                    if not venue_line:
                        venue_line = extract_host_club(clean)
                    continue
        if (not venue_line or venue_line.endswith("·")) and block_text:
            recovered = recover_list_host_from_block_text(block_text, title, category_line)
            if recovered:
                venue_line = recovered
        events.append({
            "title": title,
            "details_url": full_url,
            "start_date": start_iso if start_iso else "",
            "end_date": end_iso if end_iso else "",
            "start_time": start_t or "",
            "end_time": end_t or "",
            "venue_text": venue_line,
            "category": category_line,
            "sas_event_id": eid,
            "external_host": "",
            "external_event_id": "",
            "is_past": is_past,
            "host": "", "location": "", "address": "", "nor_url": "", "si_url": "", "results_url": "",
            "other_docs": "", "description": "", "contact": "", "organiser": "",
        })
    return events


def main():
    parser = argparse.ArgumentParser(description="Scrape SAS events list + full detail per event (host, location, NOR, SI, etc.).")
    parser.add_argument("--output-dir", type=str, default=None, help="Write CSV here (default: script dir)")
    parser.add_argument("--date-stamp", action="store_true", help="Also write sas_events_list_YYYYMMDD.csv for daily runs")
    parser.add_argument("--no-detail", action="store_true", help="Skip fetching each event detail page (list-only, faster)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve() if args.output_dir else Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    all_events: list[dict] = []
    seen_urls: set[str] = set()

    # path, is_past, paginate (fetch page=1,2,... until empty)
    list_config = [
        ("/events/", False, False),
        ("/events/list", False, True),   # upcoming: all pages
        ("/events/list/past", True, True),  # past: all pages
    ]
    max_pages = 200
    for path, is_past, paginate in list_config:
        page = 1
        while page <= max_pages:
            url_path = f"{path}?page={page}" if (paginate and page > 1) else path
            print(f"Fetching list {url_path} ...", file=sys.stderr)
            try:
                html = fetch_list_page(url_path)
                batch = parse_list_html(html, is_past)
                new_count = 0
                for e in batch:
                    if e["details_url"] in seen_urls:
                        continue
                    seen_urls.add(e["details_url"])
                    all_events.append(e)
                    new_count += 1
                if not batch:
                    break
                if paginate and batch:
                    print(f"  page {page}: +{new_count} events (total {len(all_events)})", file=sys.stderr)
                page += 1
                if not paginate:
                    break
            except Exception as err:
                print(f"Error {url_path}: {err}", file=sys.stderr)
                break
            time.sleep(0.7)

    # Fetch detail page for each event to get host, location, NOR, SI, etc.
    if not args.no_detail and all_events:
        print(f"Fetching detail for {len(all_events)} events ...", file=sys.stderr)
        for i, ev in enumerate(all_events):
            url = ev["details_url"]
            list_host = (ev.get("venue_text") or "").strip()
            html = fetch_detail_page(url)
            if html:
                detail = parse_detail_html(html, url)
                for k, v in detail.items():
                    if v and isinstance(v, str):
                        ev[k] = v
                # Keep list-page host as source of truth; only fall back to detail host when list host is blank.
                if list_host and not is_invalid_venue_text(list_host):
                    ev["venue_text"] = list_host
                else:
                    detail_host = (ev.get("host") or "").strip()
                    if detail_host and not is_invalid_venue_text(detail_host):
                        ev["venue_text"] = detail_host
            time.sleep(0.7)
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(all_events)}", file=sys.stderr)

    # Sort: past first (by start_date asc), then upcoming
    def sort_key(ev):
        sd = ev.get("start_date") or ""
        return (1 if ev.get("is_past") else 0, sd)
    all_events.sort(key=sort_key)

    fieldnames = [
        "title", "details_url", "start_date", "end_date", "start_time", "end_time",
        "venue_text", "category",
        "host", "location", "address", "nor_url", "si_url", "results_url", "other_docs",
        "description", "contact", "organiser",
        "sas_event_id", "external_host", "external_event_id", "is_past"
    ]

    # Ensure every row has all keys (fill missing)
    for ev in all_events:
        for k in fieldnames:
            if k not in ev:
                ev[k] = ""

    out_csv = out_dir / "sas_events_list.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_events)
    print(f"Wrote {len(all_events)} events to {out_csv}", file=sys.stderr)

    if args.date_stamp:
        stamped_csv = out_dir / f"sas_events_list_{stamp}.csv"
        with open(stamped_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_events)
        print(f"Wrote {stamped_csv}", file=sys.stderr)

    with_nor = sum(1 for e in all_events if e.get("nor_url"))
    with_host = sum(1 for e in all_events if e.get("host") or e.get("location"))
    print(f"Detail: {with_host} with host/location, {with_nor} with NOR URL", file=sys.stderr)


if __name__ == "__main__":
    main()
