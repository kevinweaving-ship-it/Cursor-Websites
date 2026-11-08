"""Search Console API client (urllib). No cookies. No Validate Fix."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .config import GSC_INSPECT, GSC_RESOURCE, GSC_WEBMASTERS, ROOT_SITEMAP


def _read(req: urllib.request.Request) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:800]
        raise RuntimeError(f"GSC HTTP {e.code}: {body}") from e


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _get(token: str, url: str) -> dict:
    return _read(urllib.request.Request(url, headers=_headers(token)))


def _post(token: str, url: str, payload: dict) -> dict:
    hdrs = _headers(token)
    hdrs["Content-Type"] = "application/json"
    return _read(
        urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            method="POST",
            headers=hdrs,
        )
    )


def _put(token: str, url: str) -> dict:
    return _read(
        urllib.request.Request(url, data=b"", method="PUT", headers=_headers(token))
    )


def _delete(token: str, url: str) -> dict:
    return _read(
        urllib.request.Request(url, method="DELETE", headers=_headers(token))
    )


def _enc_site(site: str) -> str:
    return urllib.parse.quote(site, safe="")


def _enc_feed(feedpath: str) -> str:
    return urllib.parse.quote(feedpath, safe="")


def _sitemap_url(site: str, feedpath: str) -> str:
    return f"{GSC_WEBMASTERS}/sites/{_enc_site(site)}/sitemaps/{_enc_feed(feedpath)}"


def list_sites(token: str) -> list[dict]:
    data = _get(token, f"{GSC_WEBMASTERS}/sites")
    return data.get("siteEntry") or []


def list_sitemaps(token: str, site: str = GSC_RESOURCE) -> list[dict]:
    data = _get(token, f"{GSC_WEBMASTERS}/sites/{_enc_site(site)}/sitemaps")
    return data.get("sitemap") or []


def submit_sitemap(token: str, feedpath: str = ROOT_SITEMAP, site: str = GSC_RESOURCE) -> dict:
    """PUT sitemaps.submit — needs webmasters (write) scope."""
    return _put(token, _sitemap_url(site, feedpath))


def delete_sitemap(token: str, feedpath: str, site: str = GSC_RESOURCE) -> dict:
    """DELETE sitemaps.delete — needs webmasters (write) scope."""
    return _delete(token, _sitemap_url(site, feedpath))


def search_analytics_totals(
    token: str, site: str = GSC_RESOURCE, start: str = "", end: str = ""
) -> dict:
    payload = {
        "startDate": start,
        "endDate": end,
        "dimensions": [],
        "rowLimit": 1,
    }
    data = _post(
        token,
        f"{GSC_WEBMASTERS}/sites/{_enc_site(site)}/searchAnalytics/query",
        payload,
    )
    rows = data.get("rows") or []
    if not rows:
        return {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0, "rows": 0}
    r = rows[0]
    return {
        "clicks": r.get("clicks") or 0,
        "impressions": r.get("impressions") or 0,
        "ctr": r.get("ctr") or 0,
        "position": r.get("position") or 0,
        "rows": 1,
    }


def inspect_url(token: str, url: str, site: str = GSC_RESOURCE) -> dict:
    data = _post(
        token,
        GSC_INSPECT,
        {"inspectionUrl": url, "siteUrl": site, "languageCode": "en-US"},
    )
    return data.get("inspectionResult") or {}
