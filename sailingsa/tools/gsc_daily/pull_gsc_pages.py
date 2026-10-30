"""Pull Page Indexing counts and example URLs from authenticated Chrome GSC."""

from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path

from .chrome_mac import (
    activate_chrome,
    active_url,
    exec_js,
    is_google_login_url,
    open_url,
    page_text,
    screenshot_login,
    wait_for_load,
)
from .config import GSC_HOME, GSC_PAGES, GSC_PAGES_DOMAIN, ISSUES


EXTRACT_COUNTS_JS = r"""
(() => {
  const text = document.body ? document.body.innerText : '';
  return text;
})()
"""

EXTRACT_TABLE_JS = r"""
(() => {
  const out = [];
  const seen = new Set();
  const rows = document.querySelectorAll('table tr, [role="row"]');
  rows.forEach((row) => {
    const anchors = [...row.querySelectorAll('a[href]')];
    let href = '';
    for (const a of anchors) {
      const h = a.href || '';
      if (h.startsWith('http') && !h.includes('search.google.com') && !h.includes('accounts.google.com')) {
        href = h;
        break;
      }
    }
    if (!href) {
      const m = (row.innerText || '').match(/https?:\/\/sailingsa\.co\.za[^\s]+/);
      if (m) href = m[0];
    }
    if (!href || seen.has(href)) return;
    seen.add(href);
    const cells = [...row.querySelectorAll('td, [role="cell"]')].map((c) => (c.innerText || '').trim());
    out.push({ url: href, cells });
  });
  if (!out.length) {
    const html = document.body ? document.body.innerHTML : '';
    const re = /https?:\/\/sailingsa\.co\.za[^"'<\s]+/g;
    let m;
    while ((m = re.exec(html)) && out.length < 2000) {
      const u = m[0].replace(/&amp;/g, '&');
      if (seen.has(u)) continue;
      seen.add(u);
      out.push({ url: u, cells: [] });
    }
  }
  return JSON.stringify(out);
})()
"""

CLICK_REASON_JS = r"""
(() => {
  const want = WANT_JSON;
  const nodes = [...document.querySelectorAll('a, button, [role="link"], [role="row"], [role="button"], div, span')];
  for (const el of nodes) {
    const t = (el.innerText || '').replace(/\s+/g, ' ').trim();
    if (!t || t.length > 180) continue;
    for (const name of want) {
      if (t === name || t.startsWith(name) || t.includes(name)) {
        const clickable = el.closest('a, button, [role="row"], [role="link"]') || el;
        clickable.click();
        return 'clicked:' + name;
      }
    }
  }
  return 'not-found';
})()
"""

CLICK_EXPORT_JS = r"""
(() => {
  const nodes = [...document.querySelectorAll('button, a, [role="button"], [aria-label]')];
  for (const el of nodes) {
    const label = ((el.getAttribute('aria-label') || '') + ' ' + (el.innerText || '')).toLowerCase();
    if (label.includes('export') || label.includes('download')) {
      el.click();
      return 'opened-export';
    }
  }
  return 'no-export';
})()
"""

CLICK_CSV_JS = r"""
(() => {
  const nodes = [...document.querySelectorAll('button, a, [role="menuitem"], [role="option"], span, div')];
  for (const el of nodes) {
    const t = (el.innerText || '').trim().toLowerCase();
    if (t === 'csv' || t === 'download csv' || t.includes('.csv')) {
      el.click();
      return 'clicked-csv';
    }
  }
  return 'no-csv';
})()
"""

COUNT_LINE = re.compile(
    r"^\s*(?P<name>.+?)\s+(?P<count>[\d][\d,]*)\s*$",
    re.MULTILINE,
)


class NeedKevinApproval(RuntimeError):
    pass


def _parse_counts(text: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for issue in ISSUES:
        for alias in issue["aliases"]:
            pat = re.compile(
                rf"{re.escape(alias)}\s+([\d][\d,]*)",
                re.IGNORECASE,
            )
            m = pat.search(text)
            if m:
                found[issue["key"]] = int(m.group(1).replace(",", ""))
                break
    if not found:
        for m in COUNT_LINE.finditer(text):
            name = m.group("name").strip()
            for issue in ISSUES:
                if any(name.lower() == a.lower() or a.lower() in name.lower() for a in issue["aliases"]):
                    found.setdefault(issue["key"], int(m.group("count").replace(",", "")))
    return found


def _open_pages_or_stop(run_path: Path) -> str:
    activate_chrome()
    open_url(GSC_PAGES)
    url = wait_for_load()
    if is_google_login_url(url):
        shot = screenshot_login(run_path / "STOP_NEED_KEVIN_GOOGLE_APPROVAL.png")
        raise NeedKevinApproval(f"Google login at {url}; screenshot={shot}")
    text = page_text()
    if "page indexing" not in text.lower() and "why pages" not in text.lower():
        open_url(GSC_PAGES_DOMAIN)
        url = wait_for_load()
        if is_google_login_url(url):
            shot = screenshot_login(run_path / "STOP_NEED_KEVIN_GOOGLE_APPROVAL.png")
            raise NeedKevinApproval(f"Google login at {url}; screenshot={shot}")
        text = page_text()
    if is_google_login_url(active_url()) or "sign in" in text.lower() and "accounts" in active_url():
        shot = screenshot_login(run_path / "STOP_NEED_KEVIN_GOOGLE_APPROVAL.png")
        raise NeedKevinApproval(f"Google login; screenshot={shot}")
    return text


def _click_reason(issue: dict) -> str:
    js = CLICK_REASON_JS.replace("WANT_JSON", json.dumps(issue["aliases"]))
    return exec_js(js)


def _extract_rows() -> list[dict]:
    raw = exec_js(EXTRACT_TABLE_JS)
    if not raw:
        return []
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out = []
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        cells = row.get("cells") or []
        last_crawl = ""
        for cell in cells:
            if re.search(r"\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2}", cell):
                last_crawl = cell
                break
        out.append({"url": url, "last_crawl": last_crawl, "cells": cells})
    return out


def _try_export(dest_dir: Path, key: str) -> str | None:
    downloads = Path.home() / "Downloads"
    before = {p.name: p.stat().st_mtime for p in downloads.glob("*.csv")} if downloads.is_dir() else {}
    opened = exec_js(CLICK_EXPORT_JS)
    time.sleep(0.8)
    csv_click = exec_js(CLICK_CSV_JS) if opened == "opened-export" else "skipped"
    deadline = time.time() + 20
    while time.time() < deadline:
        if downloads.is_dir():
            for p in downloads.glob("*.csv"):
                if p.name not in before or p.stat().st_mtime > before.get(p.name, 0):
                    target = dest_dir / f"{key}.csv"
                    target.write_bytes(p.read_bytes())
                    return str(target)
        time.sleep(0.5)
    return None if csv_click != "clicked-csv" else None


def _urls_from_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for rec in reader:
            url = ""
            last = ""
            for k, v in rec.items():
                lk = (k or "").lower()
                if not url and v and ("url" in lk or "page" in lk or "address" in lk):
                    url = v.strip()
                if v and ("crawl" in lk or "date" in lk):
                    last = v.strip()
            if not url:
                vals = [x for x in rec.values() if x and str(x).startswith("http")]
                url = vals[0] if vals else ""
            if url:
                rows.append({"url": url, "last_crawl": last, "cells": list(rec.values())})
    return rows


def pull(run_path: Path) -> dict:
    run_path.mkdir(parents=True, exist_ok=True)
    text = _open_pages_or_stop(run_path)
    (run_path / "pages_index.txt").write_text(text, encoding="utf-8")
    counts = _parse_counts(text)
    issues_out = []
    for issue in ISSUES:
        open_url(GSC_PAGES)
        wait_for_load()
        time.sleep(1.0)
        click = _click_reason(issue)
        time.sleep(2.0)
        if is_google_login_url(active_url()):
            shot = screenshot_login(run_path / "STOP_NEED_KEVIN_GOOGLE_APPROVAL.png")
            raise NeedKevinApproval(f"Google login mid-pull; screenshot={shot}")
        drill_text = page_text()
        (run_path / f"{issue['key']}_ui.txt").write_text(drill_text, encoding="utf-8")
        validation = ""
        for line in drill_text.splitlines():
            if re.search(r"validat|not started|failed|passed", line, re.I):
                validation = line.strip()
                break
        export_path = _try_export(run_path, issue["key"])
        rows = _urls_from_csv(Path(export_path)) if export_path else _extract_rows()
        issues_out.append(
            {
                "key": issue["key"],
                "label": issue["label"],
                "google_count": counts.get(issue["key"]),
                "click": click,
                "validation_status": validation,
                "export_path": export_path,
                "source": "gsc_export_csv" if export_path else "gsc_ui_table",
                "urls": rows,
                "urls_supplied": len(rows),
            }
        )
        open_url(GSC_PAGES)
        wait_for_load()
    payload = {
        "property": "https://sailingsa.co.za",
        "gsc_home": GSC_HOME,
        "active_url": active_url(),
        "counts": counts,
        "issues": issues_out,
    }
    (run_path / "gsc_pull.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
