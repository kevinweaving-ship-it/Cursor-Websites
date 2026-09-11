"""Server-made A4 results PDFs for standalone /regatta parent and child URLs.

Each event keeps a parent PDF; each fleet child URL keeps its own PDF.
Orientation is portrait unless any table is wider than A4 portrait (194mm).
A fleet is never split across pages.

Print / Download / Share open these files. They are written on save and
rebuilt on first request if missing.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Iterable, Optional

from sailingsa.backend.regatta_print_compact_css import (
    PRINT_A4_PORTRAIT_CONTENT_MM,
    PRINT_DOCUMENT_CSS,
    print_orientation_for_tables,
)

PDF_URL_SUFFIX = "/results.pdf"
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def pdf_root() -> Path:
    env = (os.environ.get("SSA_REGATTA_PDF_DIR") or "").strip()
    if env:
        return Path(env)
    live = Path("/var/www/sailingsa/data/regatta-pdfs")
    if live.parent.is_dir():
        return live
    return Path(__file__).resolve().parents[2] / "data" / "regatta-pdfs"


def pdf_rel_url(slug: str, class_slug: Optional[str] = None) -> str:
    slug = (slug or "").strip().strip("/")
    if class_slug:
        return f"/regatta/{slug}/class-{class_slug}{PDF_URL_SUFFIX}"
    return f"/regatta/{slug}{PDF_URL_SUFFIX}"


def pdf_abs_path(slug: str, class_slug: Optional[str] = None) -> Path:
    slug = (slug or "").strip().strip("/")
    if class_slug:
        return pdf_root() / slug / f"class-{class_slug}.pdf"
    return pdf_root() / slug / "results.pdf"


def pdf_download_name(slug: str, class_slug: Optional[str] = None) -> str:
    slug = (slug or "").strip().strip("/")
    if class_slug:
        return f"{slug}-class-{class_slug}.pdf"
    return f"{slug}.pdf"


def _lock_for(slug: str) -> threading.Lock:
    with _LOCKS_GUARD:
        lock = _LOCKS.get(slug)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[slug] = lock
        return lock


def kinds_from_fleet_html(html: str) -> list[str]:
    kinds: list[str] = []
    for attrs, inner in re.findall(r"<th([^>]*)>(.*?)</th>", html or "", flags=re.I | re.S):
        cls_m = re.search(r'class="([^"]*)"', attrs or "", flags=re.I)
        cls = cls_m.group(1) if cls_m else ""
        txt = re.sub(r"<[^>]+>", "", inner or "")
        txt = re.sub(r"\s+", " ", txt).strip().lower()
        if "class-col" in cls or txt == "class":
            kinds.append("class")
        elif "race-col" in cls or re.match(r"^r\d+$", txt):
            kinds.append("race")
        elif "helm-col" in cls or txt == "helm":
            kinds.append("helm")
        elif "crew-col" in cls or txt == "crew":
            kinds.append("crew")
        elif "sail-col" in cls or txt in {"sail no", "sail", "sailno"}:
            kinds.append("sail")
        elif "club-col" in cls or txt == "club":
            kinds.append("club")
        elif "rank-col" in cls or txt == "rank":
            kinds.append("rank")
        elif "total-col" in cls or txt == "total":
            kinds.append("total")
        elif "nett-col" in cls or txt == "nett":
            kinds.append("nett")
        elif "disc-col" in cls or txt in {"disc", "discard"}:
            kinds.append("disc")
        elif "boat-name-col" in cls or txt in {"boat name", "boat"}:
            kinds.append("boat")
        elif "wc-meta-col" in cls or txt in {
            "age",
            "bow",
            "bow no",
            "jib",
            "jib no",
            "hull",
            "hull no",
        }:
            kinds.append("meta")
        else:
            kinds.append("other")
    return kinds


def orientation_from_fleet_htmls(fleet_htmls: Iterable[str]) -> str:
    tables = [kinds_from_fleet_html(h) for h in fleet_htmls]
    tables = [t for t in tables if t]
    return print_orientation_for_tables(tables)


def _add_fleet_class(html: str, extra: str) -> str:
    extra = extra.strip()
    if not extra or not html:
        return html

    def _repl(m: re.Match) -> str:
        cls = m.group(1)
        if extra in cls.split():
            return m.group(0)
        return f'class="{cls} {extra}"'

    return re.sub(r'class="([^"]*fleet-section[^"]*)"', _repl, html, count=1, flags=re.I)


def paginate_fleet_htmls(fleets: list[dict], orient: str) -> list[dict]:
    """Keep each fleet on one page. Move a fleet to the next page if it will not fit."""
    page_mm = 188 if orient == "landscape" else 275
    row_mm = 4.0 if orient == "landscape" else 4.3
    used = 22.0
    out: list[dict] = []
    for i, fleet in enumerate(fleets):
        item = dict(fleet)
        html = item.get("html") or ""
        n_rows = int(item.get("n_rows") or 0)
        h = 16.0 + n_rows * row_mm
        if h > page_mm:
            fit = "ssa-print-fit-3" if h > page_mm * 1.35 else (
                "ssa-print-fit-2" if h > page_mm * 1.15 else "ssa-print-fit-1"
            )
            html = _add_fleet_class(html, fit)
            h = page_mm
        if i > 0 and used + h > page_mm:
            html = _add_fleet_class(html, "ssa-print-new-page")
            used = h
        else:
            used += h
        item["html"] = html
        out.append(item)
    return out


def build_print_document(
    *,
    event_name: str,
    host: str,
    status_line: str,
    sheet_url: str,
    fleets: list[dict],
    orient: str,
    left_logo: str = "",
    right_logo: str = "",
) -> str:
    name = escape(event_name or "")
    host_s = escape(host or "")
    status_s = escape(status_line or "")
    url_s = escape(sheet_url or "")
    left = ""
    if left_logo:
        left = (
            f'<div class="regatta-header-logo-col">'
            f'<img src="{escape(left_logo)}" alt="" class="regatta-header-logo-img" />'
            f"</div>"
        )
    right = ""
    if right_logo:
        right = (
            f'<div class="regatta-header-club-logo-col">'
            f'<img src="{escape(right_logo)}" alt="" class="regatta-header-club-logo-img" />'
            f"</div>"
        )
    header = (
        '<div class="regatta-header-wrap"><div class="header">'
        f"{left}"
        '<div class="regatta-header-main-col">'
        f'<div class="regatta-name">{name}</div>'
        f'<div class="host-club">Host: {host_s}</div>'
        f'<div class="status-line">{status_s}</div>'
        "</div>"
        f"{right}"
        "</div></div>"
    )
    body = "".join(f.get("html") or "" for f in fleets)
    footer = (
        f'<div class="ssa-print-page-footer"><span class="ssa-print-footer-name">{name}</span>'
        f'<a class="ssa-print-footer-url" href="{url_s}">{url_s}</a></div>'
    )
    css = PRINT_DOCUMENT_CSS.replace("A4 portrait", f"A4 {orient}")
    base = ""
    if left_logo or right_logo:
        base = '<base href="https://sailingsa.co.za/">'
    return (
        "<!DOCTYPE html><html class=\"ssa-print-"
        f'{orient}" data-ssa-print-orient="{orient}">'
        '<head><meta charset="UTF-8">'
        f"{base}"
        f"<title>{name}</title><style>{css}</style></head>"
        f'<body class="ssa-print-doc">{header}{body}{footer}</body></html>'
    )


def find_chrome() -> Optional[str]:
    env = (os.environ.get("SSA_CHROME") or "").strip()
    candidates = [
        env,
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/opt/google/chrome/chrome",
    ]
    for c in candidates:
        if not c:
            continue
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def html_to_pdf(html: str, dest: Path, timeout_sec: int = 90) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Chrome/Chromium is required to write results PDFs")
    with tempfile.TemporaryDirectory(prefix="ssa-regatta-pdf-") as td:
        src = Path(td) / "sheet.html"
        tmp_pdf = Path(td) / "sheet.pdf"
        src.write_text(html, encoding="utf-8")
        cmd = [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-pdf-header-footer",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
            f"--timeout={max(5000, int(timeout_sec * 1000))}",
            f"--print-to-pdf={tmp_pdf}",
            src.resolve().as_uri(),
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = timeout_sec
        waited = 0.0
        while waited < deadline:
            if tmp_pdf.is_file() and tmp_pdf.stat().st_size >= 500:
                # Chrome often keeps the file open; wait a beat then stop it.
                time.sleep(0.4)
                break
            if proc.poll() is not None:
                break
            time.sleep(0.2)
            waited += 0.2
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        if not tmp_pdf.is_file() or tmp_pdf.stat().st_size < 500:
            raise RuntimeError("Chrome did not write a results PDF")
        os.replace(tmp_pdf, dest)
    return dest


@dataclass
class WrittenPdfs:
    slug: str
    orient: str
    parent: Path
    children: dict[str, Path]


def write_event_pdfs(
    *,
    slug: str,
    event_name: str,
    host: str,
    status_line: str,
    sheet_url: str,
    fleets: list[dict],
    left_logo: str = "",
    right_logo: str = "",
) -> WrittenPdfs:
    slug = (slug or "").strip()
    if not slug:
        raise ValueError("slug required")
    htmls = [f.get("html") or "" for f in fleets]
    orient = orientation_from_fleet_htmls(htmls)
    parent_fleets = paginate_fleet_htmls(fleets, orient)
    parent_html = build_print_document(
        event_name=event_name,
        host=host,
        status_line=status_line,
        sheet_url=sheet_url or f"https://sailingsa.co.za/regatta/{slug}",
        fleets=parent_fleets,
        orient=orient,
        left_logo=left_logo,
        right_logo=right_logo,
    )
    children: dict[str, Path] = {}
    with _lock_for(slug):
        parent_path = pdf_abs_path(slug)
        html_to_pdf(parent_html, parent_path)
        for fleet in fleets:
            cslug = (fleet.get("class_slug") or "").strip()
            if not cslug:
                continue
            child_orient = orientation_from_fleet_htmls([fleet.get("html") or ""])
            child_fleets = paginate_fleet_htmls([fleet], child_orient)
            child_url = f"https://sailingsa.co.za/regatta/{slug}/class-{cslug}"
            child_html = build_print_document(
                event_name=event_name,
                host=host,
                status_line=status_line,
                sheet_url=child_url,
                fleets=child_fleets,
                orient=child_orient,
                left_logo=left_logo,
                right_logo=right_logo,
            )
            cpath = pdf_abs_path(slug, cslug)
            html_to_pdf(child_html, cpath)
            children[cslug] = cpath
    return WrittenPdfs(slug=slug, orient=orient, parent=parent_path, children=children)
