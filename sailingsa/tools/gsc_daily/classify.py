"""Classify a live probe vs the Google Page Indexing reason. No auto-fixes."""

from __future__ import annotations

from urllib.parse import urlparse

INDEXABLE_PREFIXES = (
    "/sailor/",
    "/regatta/",
    "/event/",
    "/class/",
    "/club/",
    "/events/",
)

LIST_OR_UTILITY = (
    "/sailors",
    "/regattas",
    "/classes",
    "/clubs",
    "/events",
    "/boat-names",
    "/about",
    "/stats",
    "/yearly-events",
    "/events-logos",
    "/search",
    "/admin",
    "/login",
    "/dev-1",
)

REAL = "REAL DEFECT"
STALE = "ALREADY FIXED — GOOGLE STALE"
OK = "INTENTIONAL/CORRECT"
HUMAN = "NEEDS HUMAN DECISION"


def _path(url: str) -> str:
    return urlparse(url).path or "/"


def _looks_indexable_entity(url: str) -> bool:
    p = _path(url)
    return any(p.startswith(x) for x in INDEXABLE_PREFIXES)


def _looks_garbage(url: str) -> bool:
    p = _path(url).lower()
    if any(x in p for x in ("wp-admin", "wp-login", ".php", "/null", "/undefined", "//")):
        return True
    if p.startswith("/cgi-bin") or p.endswith(".sql"):
        return True
    return False


FETCH_TO_ISSUE = {
    "NOT_FOUND": "not_found_404",
    "SERVER_ERROR": "server_error_5xx",
    "ACCESS_FORBIDDEN": "forbidden_403",
    "SOFT_404": "soft_404",
    "REDIRECT_ERROR": "redirect_error",
    "BLOCKED_4XX": "other_4xx",
    "ACCESS_DENIED": "other_4xx",
    "BLOCKED_ROBOTS_TXT": "excluded_noindex",
}


def issue_key_from_inspect(index_status: dict | None, probe: dict) -> str:
    """Map URL Inspection pageFetchState to a Page Indexing-like key."""
    st = index_status or {}
    fetch = (st.get("pageFetchState") or "").upper()
    indexing = (st.get("indexingState") or "").upper()
    if indexing in ("BLOCKED_BY_META_TAG", "BLOCKED_BY_HTTP_HEADER"):
        return "excluded_noindex"
    if fetch in FETCH_TO_ISSUE:
        return FETCH_TO_ISSUE[fetch]
    if probe.get("redirects"):
        return "page_with_redirect"
    status = probe.get("first_status") or probe.get("status") or 0
    if status == 404:
        return "not_found_404"
    if status == 403:
        return "forbidden_403"
    if 500 <= int(status or 0) < 600:
        return "server_error_5xx"
    if status in (301, 302, 307, 308):
        return "page_with_redirect"
    if int(status or 0) == 200 or fetch in ("SUCCESSFUL", ""):
        return "indexed_ok"
    return "not_found_404"


def classify(issue_key: str, probe: dict) -> str:
    status = probe.get("first_status") or probe.get("status") or 0
    final = probe.get("status") or 0
    redirects = bool(probe.get("redirects"))
    noindex = bool(probe.get("noindex"))
    canonical = (probe.get("canonical") or "").strip()
    url = probe.get("url") or ""
    final_url = probe.get("final_url") or ""
    in_sitemap = bool(probe.get("in_sitemap"))

    if issue_key == "indexed_ok":
        if int(final or 0) == 200 and not noindex:
            return OK
        if 500 <= int(status or 0) < 600 or 500 <= int(final or 0) < 600:
            return REAL
        if int(status or 0) in (403, 404) or int(final or 0) in (403, 404):
            return REAL if _looks_indexable_entity(url) else HUMAN
        return HUMAN

    if status == 0:
        return HUMAN

    if issue_key == "server_error_5xx":
        if 500 <= status < 600 or 500 <= final < 600:
            return REAL
        if final == 200 and not redirects:
            return STALE
        return HUMAN

    if issue_key == "forbidden_403":
        if status == 403 or final == 403:
            return REAL if _looks_indexable_entity(url) else HUMAN
        if final == 200:
            return STALE
        return HUMAN

    if issue_key == "not_found_404":
        if status == 404 and _looks_garbage(url):
            return OK
        if status == 404 and _looks_indexable_entity(url):
            return REAL
        if status == 404 and in_sitemap:
            return REAL
        if status == 404:
            return OK
        if final == 200:
            return STALE
        if redirects and final == 200:
            return STALE
        return HUMAN

    if issue_key == "soft_404":
        if final == 200 and (probe.get("title") or "").strip() and not noindex:
            return STALE
        if final == 404:
            return OK
        return HUMAN

    if issue_key == "other_4xx":
        if 400 <= status < 500 and status not in (403, 404):
            return REAL if _looks_indexable_entity(url) or in_sitemap else HUMAN
        if final == 200:
            return STALE
        return HUMAN

    if issue_key == "redirect_error":
        chain = probe.get("redirect_chain") or []
        codes = [h.get("status") for h in chain]
        if any(c in (404, 410) or (c and 500 <= c < 600) for c in codes):
            return REAL
        if len(chain) >= 8:
            return REAL
        hops = [h.get("url") for h in chain]
        if hops and hops[0] in hops[1:]:
            return REAL
        if status in (301, 302, 307, 308) and final == 200 and final_url.rstrip("/") != url.rstrip("/"):
            return STALE
        if final == 200 and not redirects:
            return STALE
        return HUMAN

    if issue_key == "page_with_redirect":
        if status in (301, 302, 307, 308) and final == 200:
            if _same_entity(url, final_url):
                return OK
            if in_sitemap:
                return REAL
            return OK
        if final == 200 and not redirects:
            return STALE
        if 500 <= status < 600 or 500 <= final < 600:
            return REAL
        return HUMAN

    if issue_key == "excluded_noindex":
        if noindex and (_looks_indexable_entity(url) or in_sitemap):
            return REAL
        if noindex:
            return OK
        if not noindex and final == 200:
            return STALE
        return HUMAN

    if issue_key == "duplicate_no_canonical":
        if final == 200 and not canonical:
            return HUMAN
        if final == 200 and canonical:
            return STALE
        return HUMAN

    if issue_key == "alternative_canonical":
        if redirects or (canonical and _norm(canonical) != _norm(url)):
            return OK
        if final == 200 and (not canonical or _norm(canonical) == _norm(url)):
            return HUMAN
        return OK

    if in_sitemap and final not in (200,):
        return REAL
    return HUMAN


def _norm(url: str) -> str:
    p = urlparse(url)
    host = (p.netloc or "").lower()
    path = (p.path or "/").rstrip("/") or "/"
    return f"{p.scheme}://{host}{path}"


def _same_entity(a: str, b: str) -> bool:
    pa, pb = _path(a).rstrip("/"), _path(b).rstrip("/")
    if pa == pb:
        return True
    # /sailor/123-old → /sailor/123-new
    def head(p: str) -> str:
        parts = [x for x in p.split("/") if x]
        if len(parts) >= 2 and parts[1][:1].isdigit():
            return parts[0] + "/" + parts[1].split("-", 1)[0]
        return p

    return head(pa) == head(pb)
