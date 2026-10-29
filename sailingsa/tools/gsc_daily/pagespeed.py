"""PageSpeed Insights: measure homepage + backend-only remediations.

Does not change public URLs or landing-page HTML.
Official API: pagespeedonline/v5. No Validate Fix. No page edits.

Autofix (authorised backend only):
  - recompress oversized landing PNGs in place (same path)
  - ensure /assets/ cache + webp-negotiate snippet (same URL)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import SITE

SAST = ZoneInfo("Africa/Johannesburg")
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
HOME = SITE.rstrip("/") + "/"
STRATEGIES = ("mobile", "desktop")
WEB_ASSETS = Path("/var/www/sailingsa/assets")
LANDING_PNGS = (
    "temp-landing-feedback-hero.png",
    "temp-landing-claim-profile-banner.png",
)
PNG_MAX = 180_000
SNIPPET_SRC = Path("/var/www/sailingsa/sailingsa/deploy/nginx/sailingsa-assets-cache.conf")
SNIPPET_DEST = Path("/etc/nginx/snippets/sailingsa-assets-cache.conf")
SITE_NGINX = Path("/etc/nginx/sites-enabled/sailingsa")
INCLUDE_LINE = "    include /etc/nginx/snippets/sailingsa-assets-cache.conf;\n"


def _score(cat: dict | None) -> int | None:
    if not cat:
        return None
    s = cat.get("score")
    if s is None:
        return None
    return int(round(float(s) * 100))


def _ms(audit: dict | None) -> float | None:
    if not audit:
        return None
    v = audit.get("numericValue")
    if v is None:
        return None
    return round(float(v) / 1000.0, 2)


def summarise_psi(raw: dict, strategy: str) -> dict:
    lr = raw.get("lighthouseResult") or {}
    cats = lr.get("categories") or {}
    audits = lr.get("audits") or {}
    lcp = audits.get("largest-contentful-paint") or {}
    items = ((lcp.get("details") or {}).get("items")) or []
    lcp_el = ""
    if items and isinstance(items[0], dict):
        lcp_el = (items[0].get("node") or {}).get("snippet") or items[0].get("id") or ""
    return {
        "strategy": strategy,
        "performance": _score(cats.get("performance")),
        "accessibility": _score(cats.get("accessibility")),
        "best_practices": _score(cats.get("best-practices")),
        "seo": _score(cats.get("seo")),
        "fcp_s": _ms(audits.get("first-contentful-paint")),
        "lcp_s": _ms(audits.get("largest-contentful-paint")),
        "tbt_ms": (audits.get("total-blocking-time") or {}).get("numericValue"),
        "cls": (audits.get("cumulative-layout-shift") or {}).get("numericValue"),
        "si_s": _ms(audits.get("speed-index")),
        "lcp_element": lcp_el[:180],
        "fetch_time": lr.get("fetchTime") or "",
    }


def fetch_psi(url: str, strategy: str, timeout: int = 90) -> dict:
    q = urllib.parse.urlencode(
        {
            "url": url,
            "strategy": strategy,
            "category": "performance",
        },
        doseq=True,
    )
    # categories: repeat the key
    extra = "&".join(
        "category=" + c
        for c in ("accessibility", "best-practices", "seo")
    )
    req = urllib.request.Request(
        f"{PSI}?{q}&{extra}",
        headers={"User-Agent": "SailingSA-GSC-Daily/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        return {"strategy": strategy, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"strategy": strategy, "error": f"{type(e).__name__}: {e}"}
    return summarise_psi(raw, strategy)


def compress_landing_pngs(assets: Path = WEB_ASSETS) -> list[dict]:
    """Same filename. Same pixels. Smaller PNG. No HTML/URL change."""
    out: list[dict] = []
    pngquant = shutil.which("pngquant")
    for name in LANDING_PNGS:
        path = assets / name
        row = {"file": name, "ok": False, "before": 0, "after": 0}
        if not path.is_file():
            row["error"] = "missing"
            out.append(row)
            continue
        before = path.stat().st_size
        row["before"] = before
        if before <= PNG_MAX:
            row["ok"] = True
            row["after"] = before
            row["action"] = "already_small"
            out.append(row)
            continue
        bak = path.with_suffix(path.suffix + ".pre-psi")
        if not bak.is_file():
            shutil.copy2(path, bak)
        if pngquant:
            tmp = path.with_suffix(".png.qtmp")
            proc = subprocess.run(
                [
                    pngquant,
                    "--quality=70-90",
                    "--speed=1",
                    "--skip-if-larger",
                    "--force",
                    "--output",
                    str(tmp),
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0 and tmp.is_file() and tmp.stat().st_size < before:
                tmp.replace(path)
                row["ok"] = True
                row["after"] = path.stat().st_size
                row["action"] = "pngquant"
            else:
                if tmp.is_file():
                    tmp.unlink()
                row["after"] = before
                row["action"] = "pngquant_skip"
                row["ok"] = True
                row["note"] = (proc.stderr or proc.stdout or "")[:160]
        else:
            row["error"] = "pngquant_missing"
        out.append(row)
    return out


def ensure_assets_cache() -> dict:
    """Install nginx /assets/ cache snippet. Does not change public routes."""
    actions: list[str] = []
    if SNIPPET_SRC.is_file():
        dest_text = SNIPPET_DEST.read_text() if SNIPPET_DEST.is_file() else ""
        src_text = SNIPPET_SRC.read_text()
        if dest_text != src_text:
            SNIPPET_DEST.write_text(src_text)
            actions.append("wrote_assets_snippet")
    if SITE_NGINX.is_file() and INCLUDE_LINE.strip() not in SITE_NGINX.read_text():
        text = SITE_NGINX.read_text()
        needle = "    include /etc/nginx/snippets/sailingsa-soft404.conf;\n"
        if needle not in text:
            return {"ok": False, "actions": actions, "error": "include_anchor_missing"}
        subprocess.run(["chattr", "-i", str(SITE_NGINX)], check=False)
        try:
            SITE_NGINX.write_text(text.replace(needle, needle + INCLUDE_LINE, 1))
            actions.append("included_snippet")
        finally:
            subprocess.run(["chattr", "+i", str(SITE_NGINX)], check=False)
    test = subprocess.run(
        ["nginx", "-t"], capture_output=True, text=True, timeout=20
    )
    if test.returncode != 0:
        return {
            "ok": False,
            "actions": actions,
            "error": (test.stderr or test.stdout)[-300:],
        }
    if actions:
        subprocess.run(["systemctl", "reload", "nginx"], timeout=20, check=False)
        actions.append("nginx_reloaded")
    return {"ok": True, "actions": actions}


def render_lines(payload: dict) -> list[str]:
    lines = ["PAGESPEED (API — do not paste PSI)"]
    for strat in STRATEGIES:
        row = (payload.get("scores") or {}).get(strat) or {}
        if row.get("error"):
            lines.append(f"{strat}: ERROR {row['error'][:120]}")
            continue
        lines.append(
            "{s}: perf {p} | LCP {lcp}s | FCP {fcp}s | CLS {cls} | SEO {seo}".format(
                s=strat,
                p=row.get("performance"),
                lcp=row.get("lcp_s"),
                fcp=row.get("fcp_s"),
                cls=round(float(row.get("cls") or 0), 3),
                seo=row.get("seo"),
            )
        )
    fx = payload.get("autofix") or {}
    if fx.get("pngs"):
        bits = [
            f"{r.get('file')} {r.get('before')}→{r.get('after')}"
            for r in fx["pngs"]
            if r.get("before")
        ]
        if bits:
            lines.append("PNG in-place: " + " | ".join(bits))
    if fx.get("nginx"):
        lines.append("nginx assets: " + ",".join(fx["nginx"].get("actions") or ["unchanged"]))
    return lines


def write_pagespeed(dest: Path, payload: dict) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "pagespeed.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    (dest / "pagespeed.txt").write_text("\n".join(render_lines(payload)) + "\n")
    return path


def run(
    *,
    dest: Path | None = None,
    apply: bool = True,
    fetch: bool = True,
    url: str = HOME,
) -> dict:
    payload: dict = {
        "as_of": datetime.now(SAST).isoformat(),
        "url": url,
        "note": (
            "Backend only: same public URLs and landing HTML. "
            "PNG files may shrink in place; /assets/ is cached. Public URLs unchanged."
        ),
        "scores": {},
        "autofix": {},
    }
    if apply:
        payload["autofix"]["pngs"] = compress_landing_pngs()
        try:
            payload["autofix"]["nginx"] = ensure_assets_cache()
        except Exception as e:
            payload["autofix"]["nginx"] = {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
            }
    if fetch:
        for strat in STRATEGIES:
            payload["scores"][strat] = fetch_psi(url, strat)
    if dest:
        write_pagespeed(dest, payload)
    return payload
