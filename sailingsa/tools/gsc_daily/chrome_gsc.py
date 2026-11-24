"""Drive the visible Search Console UI. Never reads or prints cookies."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import signal
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .config import (
    GSC_CDP_PORT,
    GSC_CHROME_PROFILE_LINUX,
    GSC_HOME,
    GSC_INSPECT_UI,
    GSC_RESOURCE,
    server_data_root,
)

INDEXED_MARKERS = (
    "url is on google",
    "submitted and indexed",
    "page is indexed",
)
NOT_INDEXED_MARKERS = (
    "url is unknown to google",
    "discovered - currently not indexed",
    "crawled - currently not indexed",
    "discovered – currently not indexed",
    "crawled – currently not indexed",
)
SUCCESS_MARKERS = (
    "indexing requested",
    "indexing request submitted",
    "request submitted",
)
QUOTA_MARKERS = (
    "daily limit",
    "quota",
    "too many indexing requests",
    "you've reached the maximum",
    "you have reached the maximum",
)
ALREADY_REQUESTED = (
    "you can request indexing again",
    "indexing already requested",
)
LOGIN_HOSTS = (
    "accounts.google.com",
    "signin",
    "challenge",
    "accountchooser",
    "servicelogin",
)

CLICK_JS = r"""
(() => {
  const want = WANT_JSON;
  const seen = [];
  const visit = (root, depth) => {
    if (!root || depth > 8) return null;
    const nodes = root.querySelectorAll ? root.querySelectorAll('*') : [];
    for (const el of nodes) {
      const t = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
      if (t && t.length < 80) seen.push(t.slice(0, 80));
      for (const w of want) {
        const low = t.toLowerCase();
        if (t && (low === w || low.startsWith(w) || (t.length < 48 && low.includes(w)))) {
          const clickable = el.closest('button, [role="button"], a, div[jsaction], span') || el;
          try { clickable.click(); return t.slice(0, 80); } catch (e) {}
        }
      }
      if (el.shadowRoot) {
        const hit = visit(el.shadowRoot, depth + 1);
        if (hit) return hit;
      }
    }
    return null;
  };
  return JSON.stringify({ clicked: visit(document, 0), sample: seen.slice(0, 40) });
})()
"""

TEXT_JS = "(document.body && document.body.innerText || '').slice(0, 4000)"


class NeedKevin(RuntimeError):
    def __init__(self, action: str, hostpath: str = "", title: str = "", shot: str = ""):
        super().__init__(action)
        self.action = action
        self.hostpath = hostpath
        self.title = title
        self.shot = shot


class QuotaHit(RuntimeError):
    def __init__(self, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


def inspect_ui_url(page_url: str) -> str:
    return (
        f"{GSC_INSPECT_UI}&id={urllib.parse.quote(page_url, safe='')}"
    )


def is_login(url: str) -> bool:
    u = (url or "").lower()
    return any(x in u for x in LOGIN_HOSTS)


def classify_text(text: str) -> str:
    low = (text or "").lower().replace("’", "'")
    if any(m in low for m in QUOTA_MARKERS):
        return "quota"
    if any(m in low for m in SUCCESS_MARKERS):
        return "indexing_requested"
    if any(m in low for m in ALREADY_REQUESTED):
        return "already_requested"
    if any(m in low for m in INDEXED_MARKERS) and "not indexed" not in low:
        return "indexed"
    if any(m in low for m in NOT_INDEXED_MARKERS):
        return "not_indexed"
    if "request indexing" in low:
        return "can_request"
    if "url inspection" in low or "inspection" in low:
        return "inspecting"
    return "unknown"


def coverage_from_text(text: str) -> str:
    low = (text or "").lower()
    for marker in NOT_INDEXED_MARKERS + INDEXED_MARKERS:
        if marker in low:
            return marker
    kind = classify_text(text)
    if kind == "indexed":
        return "URL is on Google"
    if kind == "indexing_requested":
        return "Indexing requested"
    return kind


class ChromeSession:
    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.port = GSC_CDP_PORT
        self.ws = ""
        self.darwin = os.uname().sysname == "Darwin"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, *exc):
        if exc_type is NeedKevin:
            return False
        self.stop()

    def start(self) -> None:
        if self.darwin:
            from . import chrome_mac

            if not chrome_mac.chrome_running():
                subprocess.run(["open", "-a", "Google Chrome"], check=False)
                time.sleep(2)
            chrome_mac.activate_chrome()
            chrome_mac.open_url(f"{GSC_HOME}?resource_id={urllib.parse.quote(GSC_RESOURCE)}")
            time.sleep(3)
            return
        if self._cdp_up():
            self.ws = self._pick_ws()
            return
        profile = GSC_CHROME_PROFILE_LINUX
        profile.mkdir(parents=True, exist_ok=True)
        log = Path("/tmp/sailingsa-gsc-chrome.log")
        self.proc = subprocess.Popen(
            [
                "xvfb-run",
                "-a",
                "-s",
                "-screen 0 1280x900x24",
                "google-chrome-stable",
                f"--user-data-dir={profile}",
                f"--remote-debugging-port={self.port}",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,900",
                f"{GSC_HOME}?resource_id={urllib.parse.quote(GSC_RESOURCE)}",
            ],
            stdout=log.open("ab"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.time() + 35
        while time.time() < deadline:
            if self._cdp_up():
                time.sleep(4)
                self.ws = self._pick_ws()
                return
            if self.proc.poll() is not None:
                tail = log.read_text(errors="replace")[-500:] if log.is_file() else ""
                raise RuntimeError(f"Chrome exited {self.proc.returncode}: {tail}")
            time.sleep(0.4)
        raise RuntimeError("Search Console Chrome CDP did not start")

    def stop(self) -> None:
        if not self.proc:
            return
        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=8)
        except Exception:
            self.proc.kill()
        self.proc = None

    def _cdp_up(self) -> bool:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=1).read()
            return True
        except Exception:
            return False

    def _get(self, path: str):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return json.loads(r.read().decode())

    def _pick_ws(self) -> str:
        tabs = self._get("/json/list")
        for tab in tabs:
            if "google" in (tab.get("url") or ""):
                return tab.get("webSocketDebuggerUrl") or ""
        return (tabs[0].get("webSocketDebuggerUrl") if tabs else "") or ""

    def _cdp(self, method: str, params=None, timeout: int = 40):
        async def run():
            import websockets

            async with websockets.connect(self.ws, max_size=20_000_000, open_timeout=timeout) as ws:
                await ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
                deadline = time.time() + timeout
                while time.time() < deadline:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                    if msg.get("id") == 1:
                        if msg.get("error"):
                            raise RuntimeError(msg["error"])
                        return msg.get("result") or {}
                raise TimeoutError(method)

        return asyncio.run(run())

    def _eval(self, expr: str) -> str:
        if self.darwin:
            from . import chrome_mac

            return chrome_mac.exec_js(expr) or ""
        result = self._cdp(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
        )
        inner = result.get("result") or {}
        val = inner.get("value")
        return "" if val is None else str(val)

    def _href(self) -> str:
        if self.darwin:
            from . import chrome_mac

            return chrome_mac.active_url()
        return self._eval("location.href")

    def _title(self) -> str:
        if self.darwin:
            from . import chrome_mac

            try:
                return chrome_mac.active_title()
            except Exception:
                return self._eval("document.title")
        return self._eval("document.title")

    def open(self, url: str) -> None:
        if self.darwin:
            from . import chrome_mac

            chrome_mac.open_url(url)
            chrome_mac.wait_for_load(45)
            return
        self._cdp("Page.navigate", {"url": url})
        time.sleep(2)

    def screenshot(self, dest: Path) -> Path | None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.darwin:
            from . import chrome_mac

            return chrome_mac.screenshot_login(dest)
        try:
            data = self._cdp("Page.captureScreenshot", {"format": "png"}).get("data") or ""
            dest.write_bytes(base64.b64decode(data))
            return dest
        except Exception:
            return None

    def _raise_if_login(self, shot: Path) -> None:
        href = self._href()
        title = self._title()
        hostpath = ""
        try:
            p = urlparse(href)
            hostpath = f"{p.scheme}://{p.netloc}{p.path}"
        except Exception:
            hostpath = href
        if is_login(href) or "sign in" in (title or "").lower():
            path = self.screenshot(shot)
            raise NeedKevin(
                "Sign in to Google as the Search Console owner (kevinweaving@gmail.com) "
                "for sc-domain:sailingsa.co.za, complete MFA/account chooser if shown, "
                "then leave Chrome signed in. Do not paste the password into chat.",
                hostpath=hostpath,
                title=title,
                shot=str(path or ""),
            )

    def inspect_and_request(self, page_url: str, dest: Path | None = None, skip_click: bool = False) -> dict:
        dest = dest or server_data_root()
        shot = dest / "gsc-ui-last.png"
        self.open(inspect_ui_url(page_url))
        text = ""
        kind = "unknown"
        deadline = time.time() + 55
        while time.time() < deadline:
            time.sleep(2.5)
            self._raise_if_login(shot)
            try:
                text = self._eval(TEXT_JS)
            except RuntimeError as exc:
                msg = str(exc)
                if "Apple Events" in msg:
                    raise NeedKevin(
                        "In Google Chrome: View → Developer → Allow JavaScript from Apple Events, then rerun.",
                        hostpath=self._href(),
                        title=self._title(),
                    ) from exc
                raise
            kind = classify_text(text)
            if kind in (
                "indexed",
                "not_indexed",
                "can_request",
                "indexing_requested",
                "quota",
                "already_requested",
            ):
                break
        self._raise_if_login(shot)
        coverage = coverage_from_text(text)
        href = self._href()
        title = self._title()
        if kind == "quota":
            self.screenshot(shot)
            raise QuotaHit(text[:400])
        if kind == "indexed":
            return {
                "coverage": coverage,
                "google_response": "already indexed",
                "accepted": False,
                "indexed": True,
                "ui_url": href,
                "title": title,
                "snippet": text[:400],
            }
        if kind in ("indexing_requested", "already_requested"):
            return {
                "coverage": coverage,
                "google_response": text[:240] or kind,
                "accepted": True,
                "indexed": False,
                "ui_url": href,
                "title": title,
                "snippet": text[:400],
            }
        if skip_click or kind not in ("can_request", "not_indexed"):
            return {
                "coverage": coverage,
                "google_response": text[:240] or kind,
                "accepted": False,
                "indexed": False,
                "ui_url": href,
                "title": title,
                "snippet": text[:400],
                "outcome": kind,
            }
        clicked = self._eval(CLICK_JS.replace("WANT_JSON", json.dumps(["request indexing"])))
        time.sleep(2)
        # Confirm dialog, if any.
        self._eval(CLICK_JS.replace("WANT_JSON", json.dumps(["request indexing", "go"])))
        deadline = time.time() + 40
        outcome = "unknown"
        while time.time() < deadline:
            time.sleep(2)
            self._raise_if_login(shot)
            text = self._eval(TEXT_JS)
            outcome = classify_text(text)
            if outcome in ("indexing_requested", "already_requested", "quota", "indexed"):
                break
        self.screenshot(shot)
        if outcome == "quota":
            raise QuotaHit(text[:400])
        accepted = outcome in ("indexing_requested", "already_requested")
        if not accepted:
            low = (text or "").lower()
            if "captcha" in low or "unusual traffic" in low or "verify" in low and "robot" in low:
                raise NeedKevin(
                    "Google presented a challenge on Search Console. Complete it in the open Chrome window, then rerun.",
                    hostpath=href,
                    title=title,
                    shot=str(shot),
                )
        return {
            "coverage": coverage_from_text(text),
            "google_response": (text[:240] if accepted else text[:400]) or outcome,
            "accepted": accepted,
            "indexed": outcome == "indexed",
            "clicked": clicked,
            "ui_url": href,
            "title": title,
            "snippet": text[:400],
            "outcome": outcome,
        }
