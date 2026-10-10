#!/usr/bin/env python3
"""Pull PY lists and crawl SailRSA into a reference box.

Sources (save as-is + parsed JSON):
  https://www.rya.org.uk/racing/portsmouth-yardstick/
  RYA Asset Bank: 2026 PY list, limited-data list, class config, pursuit, NOR
  https://cdn.revolutionise.com.au/cups/sas/files/ruou7obyk3wzgeqf.pdf
  https://sailrsa.org.za/  (classes, clubs, results history)

Does not write the gold classes table. Output is reference only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urldefrag, urlparse
from urllib.request import Request, urlopen

UA = "SailingSA-reference/1.0 (+https://sailingsa.co.za)"
RYA_PAGE = "https://www.rya.org.uk/racing/portsmouth-yardstick/"
SAS_PY_PDF = "https://cdn.revolutionise.com.au/cups/sas/files/ruou7obyk3wzgeqf.pdf"
SAILRSA = "https://sailrsa.org.za/"
RYA_ASSETS = {
    "50500": "Current PY list",
    "50501": "Limited Data List",
    "77123": "Class configuration list",
    "50502": "Pursuit race calculator",
    "48002": "PY Notice of Race and Sailing Instructions Advice",
    "48003": "PY Running Races",
}
_ROW_RE = re.compile(
    r"^(\d+)\s+(.+?)\s+([123])\s+([SUsu])\s+([0CAcA?])\s+(\d{3,4})\s+(-?\d+)\s*(.*)$"
)
_SAS_ROW_RE = re.compile(
    r"^(.+?)\s+([123])\s+([USA])\s+([0CA?])\s+(\d{3,4})\s*$"
)
_SKIP_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".css",
    ".js",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".svg",
    ".mp4",
    ".swf",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_url(url: str) -> str:
    parts = urlparse(url)
    path = quote(parts.path, safe="/:@")
    return parts._replace(path=path).geturl()


def fetch(url: str, timeout: int = 40) -> tuple[bytes, str, str]:
    req = Request(_safe_url(url), headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        final = str(resp.geturl() or url)
        ctype = str(resp.headers.get("Content-Type") or "")
    return data, final, ctype


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".vendor"))
        from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        parts.append(f"\n----- page {i} -----\n")
        parts.append(page.extract_text() or "")
    return "".join(parts)


def parse_rya_rows(text: str, source: str) -> list[dict]:
    rows = []
    buf = ""
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or line.startswith("-----"):
            continue
        if re.match(r"^(RYA |Portsmouth |Last update|Verion|The RYA|For classes|CLUBS TO|Experimental)", line):
            buf = ""
            continue
        cand = f"{buf} {line}".strip() if buf else line
        m = _ROW_RE.match(cand)
        if m:
            rows.append(
                {
                    "rya_id": int(m.group(1)),
                    "class_name": re.sub(r"\s+", " ", m.group(2)).strip(),
                    "persons": int(m.group(3)),
                    "rig": m.group(4).upper(),
                    "spinnaker": m.group(5).upper(),
                    "py": int(m.group(6)),
                    "change": int(m.group(7)),
                    "notes": (m.group(8) or "").strip(),
                    "source": source,
                }
            )
            buf = ""
            continue
        if re.match(r"^\d+\s+", line):
            buf = line
        elif buf:
            buf = f"{buf} {line}"
    return rows


def parse_sas_rows(text: str) -> list[dict]:
    rows = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        m = _SAS_ROW_RE.match(line)
        if not m:
            continue
        name = m.group(1).strip()
        if name.lower() in {"class", "class persons rig spinnaker pyh"}:
            continue
        rows.append(
            {
                "class_name": name,
                "persons": int(m.group(2)),
                "rig": m.group(3).upper(),
                "spinnaker": m.group(4).upper(),
                "py": int(m.group(5)),
                "source": "sas-py-la-2019",
                "notes": "pilot" if False else "",
            }
        )
    return rows


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.title = ""
        self._in_title = False
        self._title_bits: list[str] = []
        self.text_bits: list[str] = []

    def handle_starttag(self, tag, attrs):
        ad = {k.lower(): v or "" for k, v in attrs}
        if tag == "a" and ad.get("href"):
            self.hrefs.append(ad["href"])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            self.title = " ".join(self._title_bits).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_bits.append(data)
        t = data.strip()
        if t:
            self.text_bits.append(t)


def ingest_py(out: Path) -> dict:
    py_dir = out / "py"
    py_dir.mkdir(parents=True, exist_ok=True)
    page, final, _ = fetch(RYA_PAGE)
    write_bytes(py_dir / "rya-portsmouth-yardstick.html", page)
    assets = []
    for asset_id, label in RYA_ASSETS.items():
        url = f"https://assets.rya.org.uk/assetbank-rya-assets/action/directLinkImage?assetId={asset_id}"
        data, final_u, ctype = fetch(url)
        name = Path(urlparse(final_u).path).name or f"asset-{asset_id}.bin"
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        dest = py_dir / "rya" / name
        write_bytes(dest, data)
        item = {
            "asset_id": asset_id,
            "label": label,
            "source_url": url,
            "resolved_url": final_u.split("?", 1)[0],
            "file": str(dest.relative_to(out)),
            "bytes": len(data),
            "sha256": sha256(data),
            "content_type": ctype,
        }
        if dest.suffix.lower() == ".pdf":
            txt = pdf_text(dest)
            dest.with_suffix(".txt").write_text(txt, encoding="utf-8")
            item["text_file"] = str(dest.with_suffix(".txt").relative_to(out))
        assets.append(item)
        time.sleep(0.2)

    sas_data, sas_final, _ = fetch(SAS_PY_PDF)
    sas_pdf = py_dir / "sas" / "sas-dinghy-catamaran-py-la-2019.pdf"
    write_bytes(sas_pdf, sas_data)
    sas_txt = pdf_text(sas_pdf)
    sas_pdf.with_suffix(".txt").write_text(sas_txt, encoding="utf-8")

    rya_list = next((a for a in assets if a["asset_id"] == "50500"), None)
    rya_rows = []
    if rya_list:
        rya_rows = parse_rya_rows((out / rya_list["text_file"]).read_text(encoding="utf-8"), "rya-2026-v4")
    limited = next((a for a in assets if a["asset_id"] == "50501"), None)
    limited_rows = []
    if limited and limited.get("text_file"):
        limited_rows = parse_rya_rows((out / limited["text_file"]).read_text(encoding="utf-8"), "rya-2026-limited")
    sas_rows = parse_sas_rows(sas_txt)

    index = {
        "scraped_at": now_iso(),
        "scheme_page": final,
        "sas_pdf": sas_final,
        "rya_assets": assets,
        "counts": {
            "rya_2026": len(rya_rows),
            "rya_2026_limited": len(limited_rows),
            "sas_py_la_2019": len(sas_rows),
        },
    }
    write_json(py_dir / "index.json", index)
    write_json(py_dir / "rya-2026-portsmouth-numbers.json", rya_rows)
    write_json(py_dir / "rya-2026-limited-data.json", limited_rows)
    write_json(py_dir / "sas-2019-py-la.json", sas_rows)

    merged = []
    seen = set()
    for row in sas_rows + rya_rows + limited_rows:
        key = (row["class_name"].lower(), row.get("persons"), row.get("rig"), row.get("spinnaker"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    write_json(py_dir / "portsmouth-numbers.json", merged)
    return index


def _same_host(url: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host in {"sailrsa.org.za", ""}


def crawl_sailrsa(out: Path, max_pages: int = 8000) -> dict:
    root = out / "sailrsa"
    root.mkdir(parents=True, exist_ok=True)
    start = [
        urljoin(SAILRSA, "index.htm"),
        urljoin(SAILRSA, "Class_index.htm"),
        urljoin(SAILRSA, "Club_index.htm"),
        urljoin(SAILRSA, "Services_index.htm"),
        urljoin(SAILRSA, "Result_index.htm"),
        urljoin(SAILRSA, "links.htm"),
        urljoin(SAILRSA, "News/News_index.htm"),
        urljoin(SAILRSA, "Class/class_junior.htm"),
        urljoin(SAILRSA, "Class/class_cat.htm"),
        urljoin(SAILRSA, "Class/class_dinghy.htm"),
        urljoin(SAILRSA, "Class/class_dingspin.htm"),
        urljoin(SAILRSA, "Class/class_keel.htm"),
        urljoin(SAILRSA, "Class/class_radio.htm"),
    ]
    queued = list(dict.fromkeys(start))
    seen: set[str] = set()
    pages: list[dict] = []
    classes: list[dict] = []
    clubs: list[dict] = []
    results: list[dict] = []

    while queued and len(seen) < max_pages:
        url = queued.pop(0)
        url, _ = urldefrag(url)
        if url in seen or not _same_host(url):
            continue
        path = urlparse(url).path.lower()
        if any(path.endswith(ext) for ext in _SKIP_EXT):
            continue
        seen.add(url)
        rel = urlparse(url).path.lstrip("/") or "index.htm"
        dest = root / "site" / rel
        if dest.suffix == "":
            dest = dest / "index.htm"
        try:
            cached = dest.is_file() and dest.stat().st_size > 0
            if cached:
                data = dest.read_bytes()
                final, ctype = url, ""
            else:
                data, final, ctype = fetch(url)
                write_bytes(dest, data)
        except Exception as exc:
            pages.append({"url": url, "error": str(exc)})
            continue
        rec = {
            "url": final,
            "file": str(dest.relative_to(out)),
            "bytes": len(data),
            "sha256": sha256(data),
            "content_type": ctype,
        }
        if b"<html" in data[:800].lower() or dest.suffix.lower() in {".htm", ".html"}:
            html = data.decode("utf-8", "replace")
            parser = _LinkParser()
            try:
                parser.feed(html)
            except Exception:
                pass
            rec["title"] = parser.title
            rec["text"] = " ".join(parser.text_bits)[:4000]
            for href in parser.hrefs:
                nxt, _ = urldefrag(urljoin(final, href))
                if nxt not in seen and _same_host(nxt):
                    queued.append(nxt)
            low = (parser.title + " " + rec["text"]).lower()
            if "/class" in final.lower() or "class" in dest.name.lower():
                classes.append(
                    {
                        "url": final,
                        "title": parser.title,
                        "file": rec["file"],
                        "excerpt": rec["text"][:800],
                    }
                )
            if "/club" in final.lower() or "club" in dest.name.lower():
                clubs.append({"url": final, "title": parser.title, "file": rec["file"]})
            if "/result" in final.lower() or re.search(r"20\d\d", dest.name):
                results.append({"url": final, "title": parser.title, "file": rec["file"]})
            rec.pop("text", None)
            rec["text_excerpt"] = " ".join(parser.text_bits)[:600]
        pages.append(rec)
        if not cached:
            time.sleep(0.05)

    index = {
        "scraped_at": now_iso(),
        "start": SAILRSA,
        "pages": len(pages),
        "ok": sum(1 for p in pages if not p.get("error")),
        "class_pages": len(classes),
        "club_pages": len(clubs),
        "result_pages": len(results),
    }
    write_json(root / "index.json", index)
    write_json(root / "pages.json", pages)
    write_json(root / "classes.json", classes)
    write_json(root / "clubs.json", clubs)
    write_json(root / "results.json", results)
    return index


def copy_compact(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in (
        "portsmouth-numbers.json",
        "sas-2019-py-la.json",
        "rya-2026-portsmouth-numbers.json",
        "rya-2026-limited-data.json",
        "index.json",
    ):
        p = src / "py" / name
        if p.is_file():
            (dest / name).write_bytes(p.read_bytes())


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ssa-reference").resolve()
    compact = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    print("OUT", out)
    py = ingest_py(out)
    print("PY", py["counts"])
    sail = crawl_sailrsa(out)
    print("SAILRSA", sail)
    if compact:
        copy_compact(out, compact)
        print("COMPACT", compact)
    print("DONE", now_iso())


if __name__ == "__main__":
    main()
