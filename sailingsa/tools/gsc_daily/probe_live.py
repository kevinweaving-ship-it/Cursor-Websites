"""Read-only live tests of Google's exact URLs. No site changes."""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .config import SITE, UA

CTX = ssl.create_default_context()


class _CanonRobots(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonical = ""
        self.robots = ""
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "link" and d.get("rel", "").lower() == "canonical":
            self.canonical = d.get("href", "")
        if tag.lower() == "meta" and d.get("name", "").lower() == "robots":
            self.robots = d.get("content", "")
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener():
    return urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPSHandler(context=CTX))


def _req(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})


def _fetch(url: str, method: str = "GET") -> tuple[int, dict, bytes]:
    opener = _opener()
    req = _req(url)
    req.method = method
    try:
        with opener.open(req, timeout=25) as resp:
            body = resp.read(200_000) if method == "GET" else b""
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, body
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(200_000)
        except Exception:
            pass
        return e.code, {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}, body
    except Exception as e:
        return 0, {"error": str(e)}, b""


def probe(url: str) -> dict:
    chain = []
    current = url
    final_url = url
    final_status = 0
    headers: dict = {}
    body = b""
    for _ in range(10):
        status, hdrs, body = _fetch(current, "GET")
        loc = hdrs.get("location", "")
        chain.append({"url": current, "status": status, "location": loc})
        final_url, final_status, headers = current, status, hdrs
        if status in (301, 302, 303, 307, 308) and loc:
            current = urljoin(current, loc)
            continue
        break
    html_meta = {"canonical": "", "robots": "", "noindex": False, "title": ""}
    ctype = headers.get("content-type", "")
    if body and "html" in ctype:
        p = _CanonRobots()
        try:
            p.feed(body.decode("utf-8", "replace"))
        except Exception:
            pass
        html_meta = {
            "canonical": p.canonical,
            "robots": p.robots,
            "noindex": "noindex" in (p.robots or "").lower(),
            "title": (p.title or "").strip()[:180],
        }
    return {
        "url": url,
        "status": final_status,
        "first_status": chain[0]["status"] if chain else 0,
        "redirect_chain": chain,
        "redirects": len(chain) > 1,
        "final_url": final_url,
        "content_type": ctype,
        **html_meta,
    }


def load_sitemap_urls(cache_path=None) -> set[str]:
    urls: set[str] = set()
    status, _, body = _fetch(f"{SITE}/sitemap.xml")
    if status != 200 or not body:
        return urls
    xml = body.decode("utf-8", "replace")
    child = re.findall(r"<loc>\s*([^<]+)\s*</loc>", xml)
    to_fetch = []
    if "<sitemapindex" in xml:
        to_fetch = child
    else:
        urls.update(child)
    for loc in to_fetch:
        st, _, b = _fetch(loc)
        if st == 200 and b:
            urls.update(re.findall(r"<loc>\s*([^<]+)\s*</loc>", b.decode("utf-8", "replace")))
        time.sleep(0.05)
    if cache_path:
        cache_path.write_text("\n".join(sorted(urls)), encoding="utf-8")
    return urls


def url_pattern(url: str) -> str:
    path = urlparse(url).path or "/"
    rules = [
        (r"^/sailor/\d+-[^/]+/?$", "/sailor/{id}-{slug}"),
        (r"^/sailor/\d+/?$", "/sailor/{id}"),
        (r"^/sailor/[^/]+/?$", "/sailor/{slug}"),
        (r"^/regatta/[^/]+/?$", "/regatta/{slug}"),
        (r"^/event/[^/]+/?$", "/event/{slug}"),
        (r"^/events/[^/]+/?$", "/events/{slug}"),
        (r"^/class/\d+-[^/]+/?$", "/class/{id}-{slug}"),
        (r"^/class/\d+/?$", "/class/{id}"),
        (r"^/class/[^/]+/?$", "/class/{slug}"),
        (r"^/club/[^/]+/?$", "/club/{slug}"),
        (r"^/boat-names/?$", "/boat-names"),
        (r"^/events-logos/?$", "/events-logos"),
        (r"^/yearly-events/?$", "/yearly-events"),
        (r"^/sailors/?$", "/sailors"),
        (r"^/regattas/?$", "/regattas"),
        (r"^/classes/?$", "/classes"),
        (r"^/clubs/?$", "/clubs"),
        (r"^/events/?$", "/events"),
        (r"^/about/?$", "/about"),
        (r"^/?$", "/"),
    ]
    for pat, name in rules:
        if re.match(pat, path):
            return name
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "/"
    return "/" + "/".join(f"{{{i}}}" if re.fullmatch(r"\d+", p) else p for i, p in enumerate(parts[:3]))


def test_urls(urls: list[str], sitemap: set[str] | None = None) -> list[dict]:
    sitemap = sitemap if sitemap is not None else load_sitemap_urls()
    out = []
    for i, url in enumerate(urls):
        row = probe(url)
        row["in_sitemap"] = url in sitemap or row.get("final_url") in sitemap
        row["pattern"] = url_pattern(url)
        out.append(row)
        if i % 25 == 24:
            time.sleep(0.2)
        else:
            time.sleep(0.04)
    return out


def save_probes(path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
