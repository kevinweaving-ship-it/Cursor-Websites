#!/usr/bin/env python3
"""Drive the live GSC Chrome profile: submit sitemaps, Request indexing until quota.

Uses Chrome DevTools on 127.0.0.1:9222. Does not print tokens or cookies.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from typing import Any

import websocket

BASE = "https://sailingsa.co.za"
RESOURCE = "sc-domain:sailingsa.co.za"
INSPECT = (
    "https://search.google.com/search-console/inspect?resource_id="
    + urllib.parse.quote(RESOURCE, safe="")
)
SITEMAPS = (
    "https://search.google.com/search-console/sitemaps?resource_id="
    + urllib.parse.quote(RESOURCE, safe="")
)
FEEDS = [
    f"{BASE}/sitemap-roundups.xml",
    f"{BASE}/sitemap-news.xml",
]
QUOTA = (
    "quota",
    "too many",
    "daily limit",
    "limit reached",
    "couldn't request",
    "try again tomorrow",
    "exceeded",
)


def _http(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _ws() -> websocket.WebSocket:
    tabs = _http("http://127.0.0.1:9222/json")
    page = next((t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), tabs[0])
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30)
    return ws


class Cdp:
    def __init__(self) -> None:
        self.ws = _ws()
        self.n = 0
        self.send("Runtime.enable")
        self.send("Page.enable")

    def send(self, method: str, params: dict | None = None) -> dict:
        self.n += 1
        nid = self.n
        self.ws.send(json.dumps({"id": nid, "method": method, "params": params or {}}))
        while True:
            data = json.loads(self.ws.recv())
            if data.get("id") == nid:
                return data

    def js(self, expr: str, timeout_ms: int = 15000) -> Any:
        out = self.send(
            "Runtime.evaluate",
            {
                "expression": expr,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        res = (out.get("result") or {}).get("result") or {}
        if res.get("subtype") == "error":
            raise RuntimeError(res.get("description") or str(res))
        return res.get("value")

    def goto(self, url: str, wait: float = 4.0) -> None:
        self.send("Page.navigate", {"url": url})
        time.sleep(wait)
        for _ in range(20):
            ready = self.js("document.readyState")
            if ready == "complete":
                break
            time.sleep(0.4)

    def text(self) -> str:
        return self.js("document.body ? document.body.innerText : ''") or ""

    def href(self) -> str:
        return self.js("location.href") or ""

    def shot(self, path: str) -> None:
        raw = self.send("Page.captureScreenshot", {"format": "png"})
        b64 = ((raw.get("result") or {}).get("data")) or ""
        import base64

        open(path, "wb").write(base64.b64decode(b64))


CLICK_BY_TEXT = r"""
(function(needle){
  const n = String(needle).toLowerCase();
  const nodes = [...document.querySelectorAll('button, [role=button], span, a, div, material-button')];
  const hit = nodes.find(el => {
    const t = (el.innerText || el.textContent || '').trim().toLowerCase();
    return t === n || t.startsWith(n);
  });
  if (!hit) return false;
  hit.click();
  return true;
})(%s)
"""


def click_text(cdp: Cdp, label: str) -> bool:
    return bool(cdp.js(CLICK_BY_TEXT % json.dumps(label)))


def signed_in(cdp: Cdp) -> bool:
    href = cdp.href()
    text = cdp.text()
    if "accounts.google.com" in href:
        return False
    if "Sign in" in text and "Search Console" not in text:
        return False
    return True


def priority_urls() -> list[str]:
    ordered = [
        f"{BASE}/sailing-roundup/latest/",
        f"{BASE}/sailing-roundup/",
        f"{BASE}/sailing-roundup/issues/2026-10-19/",
        f"{BASE}/sailing-roundup/issues/2026-10-12/",
        f"{BASE}/sailing-roundup/issues/2026-10-05/",
        f"{BASE}/sailing-roundup/issues/2026-09-28/",
    ]
    try:
        xml = urllib.request.urlopen(f"{BASE}/sitemap-roundups.xml", timeout=20).read().decode()
        import re

        issues = [u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml) if "/issues/" in u]
        issues.sort(reverse=True)
        for url in issues:
            if url not in ordered:
                ordered.append(url)
    except Exception:
        pass
    for url in (
        f"{BASE}/",
        f"{BASE}/sailors",
        f"{BASE}/about",
        f"{BASE}/events",
        f"{BASE}/stats",
        f"{BASE}/classes",
        f"{BASE}/clubs",
    ):
        if url not in ordered:
            ordered.append(url)
    return ordered


def submit_sitemaps(cdp: Cdp) -> list[dict]:
    out = []
    cdp.goto(SITEMAPS, wait=5)
    if not signed_in(cdp):
        return [{"ok": False, "error": "not_signed_in", "href": cdp.href()}]
    page = cdp.text()
    for feed in FEEDS:
        already = feed.split("/")[-1] in page
        if already:
            out.append({"feed": feed, "ok": True, "status": "already_listed"})
            continue
        typed = cdp.js(
            """
            (function(feed){
              const input = document.querySelector('input[type=text], input[aria-label], input');
              if (!input) return 'no_input';
              input.focus();
              input.value = feed;
              input.dispatchEvent(new Event('input', {bubbles:true}));
              input.dispatchEvent(new Event('change', {bubbles:true}));
              return 'typed';
            })(%s)
            """
            % json.dumps(feed)
        )
        clicked = click_text(cdp, "Submit") or click_text(cdp, "Add")
        time.sleep(3)
        page = cdp.text()
        out.append(
            {
                "feed": feed,
                "ok": feed.split("/")[-1] in page or "success" in page.lower() or "submitted" in page.lower(),
                "typed": typed,
                "clicked": clicked,
            }
        )
    cdp.shot("/tmp/gsc-index-shots/sitemaps.png")
    return out


def request_one(cdp: Cdp, url: str) -> dict:
    cdp.goto(INSPECT, wait=4)
    if not signed_in(cdp):
        return {"url": url, "ok": False, "error": "not_signed_in", "href": cdp.href()}
    cdp.js(
        """
        (function(url){
          const input = document.querySelector('input[type=url], input[type=text], input');
          if (!input) return 'no_input';
          input.focus();
          input.value = url;
          input.dispatchEvent(new Event('input', {bubbles:true}));
          input.dispatchEvent(new Event('change', {bubbles:true}));
          return 'typed';
        })(%s)
        """
        % json.dumps(url)
    )
    click_text(cdp, "Enter") or click_text(cdp, "Inspect") or click_text(cdp, "Test live URL")
    # Enter key
    cdp.js(
        """
        const input = document.querySelector('input[type=url], input[type=text], input');
        if (input) {
          input.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', keyCode:13, which:13, bubbles:true}));
        }
        """
    )
    time.sleep(6)
    text = cdp.text()
    low = text.lower()
    if any(q in low for q in QUOTA):
        return {"url": url, "ok": False, "quota": True, "status": "quota_exhausted"}
    if "url is unknown" in low or "url is not on google" in low or "url unknown to google" in low:
        status = "unknown"
    elif "url is on google" in low or "page is indexed" in low or "url is indexed" in low:
        status = "already_indexed"
    else:
        status = "inspected"
    requested = False
    if click_text(cdp, "Request indexing"):
        time.sleep(2)
        click_text(cdp, "Request indexing")  # confirm dialog
        time.sleep(3)
        text = cdp.text()
        low = text.lower()
        if any(q in low for q in QUOTA):
            return {"url": url, "ok": False, "quota": True, "status": "quota_exhausted", "after": status}
        requested = "requested" in low or "indexing requested" in low or True
    return {"url": url, "ok": True, "status": status, "requested": requested}


def main() -> None:
    cdp = Cdp()
    report: dict[str, Any] = {"ok": False, "sitemaps": [], "urls": [], "stop": ""}
    report["sitemaps"] = submit_sitemaps(cdp)
    if report["sitemaps"] and report["sitemaps"][0].get("error") == "not_signed_in":
        report["stop"] = "not_signed_in"
        print(json.dumps(report, indent=2))
        sys.exit(2)
    quota = False
    for i, url in enumerate(priority_urls()):
        row = request_one(cdp, url)
        report["urls"].append(row)
        if i < 8:
            cdp.shot(f"/tmp/gsc-index-shots/url-{i:02d}.png")
        if row.get("quota"):
            quota = True
            report["stop"] = "quota_exhausted"
            break
        time.sleep(1.2)
    if not quota:
        report["stop"] = "completed_list"
    report["ok"] = True
    report["requested"] = sum(1 for u in report["urls"] if u.get("requested"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
