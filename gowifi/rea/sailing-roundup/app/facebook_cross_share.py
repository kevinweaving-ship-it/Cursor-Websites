#!/usr/bin/env python3
"""Resolve Facebook share links and match cross-posted pages to SailingSA URLs.

Club/class/sailor/sponsor pages often share each other. A share URL such as
https://www.facebook.com/share/g/1Jh51CDMew/ is stored as the local 420 Class RSA
group and linked to https://sailingsa.co.za/class/420.

Does not log in or bypass Facebook walls. Uses public redirects + Open Graph.
"""
from __future__ import annotations

import html as html_module
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from entity_match import match_text, normalize_facebook

FB_HIT = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Accept": "text/html",
}
MOBILE = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html",
}

SHARE_RE = re.compile(r"facebook\.com/share/(?P<kind>[pvg])/(?P<id>[A-Za-z0-9]+)", re.I)
GROUP_RE = re.compile(r"facebook\.com/groups/(?P<id>\d+)", re.I)
PAGE_RE = re.compile(r"facebook\.com/(?P<slug>[A-Za-z0-9.]+)/?(?:$|[?#])", re.I)
POST_PAGE_RE = re.compile(r"facebook\.com/(?P<slug>[A-Za-z0-9.]+)/posts/", re.I)
SHARED_RE = re.compile(
    r"(?P<dst>.+?)\s+shared\s+(?:a\s+post\s+from\s+|(?P<src>.+?)(?:'s|’s)\s+post)",
    re.I,
)
OG_TITLE = re.compile(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', re.I)
OG_URL = re.compile(r'property=["\']og:url["\'][^>]*content=["\']([^"\']+)', re.I)
OG_DESC = re.compile(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)', re.I)
OG_IMAGE = re.compile(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
FB_MESSAGE = re.compile(r'"message":\{"text":"((?:\\.|[^"\\]){20,})"')


def facebook_message_from_html(html: str) -> str:
    """Full post caption. og:description is truncated; the JSON message is not."""
    best = ""
    for raw in FB_MESSAGE.findall(html or ""):
        try:
            text = json.loads('"' + raw + '"')
        except Exception:
            continue
        if isinstance(text, str) and len(text) > len(best):
            best = text
    return best.strip()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _request(url: str, headers: dict, timeout: int = 16, method: str = "GET"):
    req = urllib.request.Request(url, headers=headers, method=method)
    return _OPENER.open(req, timeout=timeout)


def _apply_location(out: dict, location: str, original: str) -> None:
    final = urllib.parse.urljoin(original, location)
    group = GROUP_RE.search(final)
    if group:
        out["kind"] = "facebook_group"
        out["page_id"] = group.group("id")
        out["canonical_url"] = f"https://www.facebook.com/groups/{out['page_id']}/"
        out["status"] = "redirect"
    page = PAGE_RE.search(final)
    if page and page.group("slug") not in {"share", "groups", "watch", "reel", "login"}:
        out["canonical_url"] = f"https://www.facebook.com/{page.group('slug')}/"
        out["status"] = out.get("status") if out.get("status") != "unresolved" else "redirect"


def _clean_title(raw: str) -> str:
    text = re.sub("<[^>]+>", "", raw or "")
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s*\|\s*Facebook\s*$", "", text, flags=re.I).strip()


def resolve_facebook_url(url: str) -> dict:
    """Turn a share/g or share/p link into a canonical public Facebook URL."""
    original = (url or "").strip()
    out = {
        "input_url": original,
        "canonical_url": normalize_facebook(original),
        "share_url": original if "/share/" in original else "",
        "kind": "unknown",
        "page_id": "",
        "page_url": "",
        "title": "",
        "description": "",
        "image": "",
        "status": "unresolved",
    }
    share = SHARE_RE.search(original)
    group = GROUP_RE.search(original)
    if group:
        out["kind"] = "facebook_group"
        out["page_id"] = group.group("id")
        out["canonical_url"] = f"https://www.facebook.com/groups/{out['page_id']}/"
    elif share:
        out["kind"] = {"g": "facebook_group", "p": "facebook_page", "v": "facebook_video"}.get(
            share.group("kind").lower(), "facebook"
        )
        out["share_url"] = f"https://www.facebook.com/share/{share.group('kind')}/{share.group('id')}/"

    html = ""
    final = original
    for method in ("HEAD", "GET"):
        for headers in (FB_HIT, MOBILE):
            try:
                with _request(original, headers, method=method) as resp:
                    final = resp.geturl()
                    loc = resp.headers.get("Location") if resp.headers else ""
                    if loc:
                        _apply_location(out, loc, original)
                    if method == "GET":
                        html = resp.read().decode("utf-8", "replace")
                    if out.get("page_id") or html:
                        break
            except urllib.error.HTTPError as exc:
                loc = exc.headers.get("Location") if exc.headers else ""
                if loc:
                    _apply_location(out, loc, original)
                    final = urllib.parse.urljoin(original, loc)
                    if out.get("page_id"):
                        break
                if exc.code in (400, 405):
                    continue
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
        if out.get("page_id"):
            break

    group = GROUP_RE.search(final) or GROUP_RE.search(html)
    if group:
        out["kind"] = "facebook_group"
        out["page_id"] = group.group("id")
        out["canonical_url"] = f"https://www.facebook.com/groups/{out['page_id']}/"
    og_url = OG_URL.search(html)
    if og_url:
        out["canonical_url"] = normalize_facebook(og_url.group(1))
        group = GROUP_RE.search(og_url.group(1))
        if group:
            out["kind"] = "facebook_group"
            out["page_id"] = group.group("id")
    title = OG_TITLE.search(html) or TITLE_RE.search(html)
    if title:
        out["title"] = _clean_title(title.group(1))
    desc = OG_DESC.search(html)
    if desc:
        out["description"] = html_module.unescape(desc.group(1).strip())
    message = facebook_message_from_html(html)
    if len(message) > len(out.get("description") or ""):
        out["description"] = message
    image = OG_IMAGE.search(html)
    if image:
        out["image"] = html_module.unescape(image.group(1).strip())
    page = POST_PAGE_RE.search(out.get("canonical_url") or "") or PAGE_RE.search(out.get("canonical_url") or "")
    if page and page.group("slug") not in {"share", "groups", "watch", "reel", "login", "posts"}:
        out["page_url"] = f"https://www.facebook.com/{page.group('slug')}/"
        if "/posts/" in (out.get("canonical_url") or "") or (out.get("share_url") or "").find("/share/p/") >= 0:
            out["kind"] = "facebook_post"
    if out["title"] or out["page_id"] or out.get("page_url"):
        out["status"] = "ok"
    elif out["status"] == "unresolved" and out["canonical_url"] != original:
        out["status"] = "redirect"
    return out


def parse_shared_post(text: str) -> dict | None:
    """'Theewater Sports Club shared 420 Class RSA's post' → dest + source page names."""
    match = SHARED_RE.search(text or "")
    if not match:
        return None
    dest = (match.group("dst") or "").strip(" -|")
    source = (match.group("src") or "").strip(" -|")
    if not dest:
        return None
    return {"shared_by": dest, "shared_from": source}


def page_identity(url: str, title: str = "", snippet: str = "") -> dict:
    resolved = resolve_facebook_url(url) if "facebook.com" in (url or "") else {
        "input_url": url,
        "canonical_url": (url or "").split("?")[0],
        "share_url": "",
        "kind": "website",
        "page_id": "",
        "title": title,
        "description": snippet,
        "status": "passthrough",
    }
    label = title or resolved.get("title") or ""
    shared = parse_shared_post(" ".join(x for x in (label, snippet, resolved.get("description") or "") if x))
    resolved["shared"] = shared
    resolved["label"] = label or resolved.get("title") or ""
    return resolved


def match_cross_shares(posts: list[dict], index: list[dict]) -> list[dict]:
    """For each post, match the hosting page and any shared-from page to SailingSA URLs."""
    found = []
    seen = set()
    for post in posts or []:
        url = post.get("url") or post.get("source_url") or ""
        title = post.get("title") or post.get("headline") or ""
        snippet = post.get("description") or post.get("snippet") or ""
        if "facebook.com/share/" in url:
            ident = page_identity(url, title, snippet)
        else:
            ident = {
                "canonical_url": normalize_facebook(url) if "facebook.com" in url else url,
                "label": title,
                "shared": parse_shared_post(f"{title} {snippet}"),
                "kind": "facebook_group" if "/groups/" in url else "facebook",
                "share_url": "",
                "title": title,
                "description": snippet,
            }
        host_name = ident.get("label") or ident.get("title") or ""
        host_match = match_text(host_name, index) or match_text(ident.get("canonical_url") or url, index)
        shared = ident.get("shared") or parse_shared_post(f"{title} {snippet}")
        source_match = match_text(shared["shared_from"], index) if shared and shared.get("shared_from") else None
        dest_match = match_text(shared["shared_by"], index) if shared and shared.get("shared_by") else host_match
        if not (host_match or source_match or dest_match or shared):
            continue
        key = (
            ident.get("canonical_url") or url,
            (source_match or {}).get("sailingsa_url"),
            (dest_match or {}).get("sailingsa_url"),
        )
        if key in seen:
            continue
        seen.add(key)
        found.append(
            {
                "post_url": url,
                "facebook_url": ident.get("canonical_url") or url,
                "share_url": ident.get("share_url") or "",
                "facebook_kind": ident.get("kind"),
                "page_title": host_name,
                "shared": shared,
                "host_entity": host_match,
                "shared_from_entity": source_match,
                "shared_by_entity": dest_match,
                "sailingsa_url": (source_match or dest_match or host_match or {}).get("sailingsa_url"),
            }
        )
    return found
