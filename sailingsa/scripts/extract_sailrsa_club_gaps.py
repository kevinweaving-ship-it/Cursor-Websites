#!/usr/bin/env python3
"""Compare SailRSA club pages to our clubs table. Keep only extra facts."""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKIP_MAIL = {"malcolmo@telkomsa.net", "webmaster@sailrsa.org.za"}
ALIAS = {
    "AEOLIANS": "AYC",
    "FHBSC": "FHYC",
    "ZLYC": "ZYC",
    "BOSKOP": "BYC",
    "STILLBAAIYC": "STYC",
    "WYC": "WYAC",
}
REGION = {
    "SAS_ECape_Club_index.htm": "EC",
    "SAS_WCape_Club_index.htm": "WC",
    "SAS_N_Club_index.htm": "GP",
    "SAS_KZN_Club_index.htm": "KZN",
}


def cf_decode(hexstr: str) -> str:
    try:
        raw = bytes.fromhex(hexstr)
    except ValueError:
        return ""
    if not raw:
        return ""
    key = raw[0]
    return "".join(chr(b ^ key) for b in raw[1:])


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.bits: list[str] = []
        self.hrefs: list[str] = []
        self.title = ""
        self.h1 = ""
        self.h2 = ""
        self._capture = ""
        self.cfemails: list[str] = []

    def handle_starttag(self, tag, attrs):
        ad = {k.lower(): v or "" for k, v in attrs}
        if tag == "a" and ad.get("href"):
            self.hrefs.append(ad["href"])
        if ad.get("data-cfemail"):
            self.cfemails.append(ad["data-cfemail"])
        if tag in {"title", "h1", "h2"}:
            self._capture = tag

    def handle_endtag(self, tag):
        if tag == self._capture:
            self._capture = ""

    def handle_data(self, data):
        t = re.sub(r"\s+", " ", data).strip()
        if not t:
            return
        if self._capture == "title":
            self.title += t
        elif self._capture == "h1":
            self.h1 += t
        elif self._capture == "h2":
            self.h2 += t
        self.bits.append(t)


def _section(text: str, heads: tuple[str, ...]) -> str:
    low = text.lower()
    for h in heads:
        i = low.find(h.lower())
        if i < 0:
            continue
        chunk = text[i + len(h) :]
        nxt = len(chunk)
        for stop in (
            "Contact Info",
            "CONTACT INFO",
            "ADDRESS",
            "SITUATION",
            "Description",
            "CLASSES CATERED",
            "Website",
            "EMail",
            "Club Website",
            "Tel",
        ):
            if stop.lower() == h.lower():
                continue
            j = chunk.lower().find(stop.lower())
            if 0 <= j < nxt:
                nxt = j
        out = chunk[:nxt].strip(" :\n\r\t-")
        out = re.sub(r"\s+", " ", out).strip()
        if out:
            return out[:1200]
    return ""


def parse_club_html(path: Path) -> dict:
    html = path.read_text(errors="replace")
    p = _Text()
    try:
        p.feed(html)
    except Exception:
        pass
    text = " ".join(p.bits)
    name = (p.h2 or p.h1 or p.title or path.stem).strip()
    name = re.sub(r"^SailRSA:?\s*", "", name, flags=re.I)
    name = re.sub(r"\s+Club$", " Club", name).strip()
    emails = []
    for hx in p.cfemails:
        em = cf_decode(hx).strip().lower()
        if em and "@" in em and em not in SKIP_MAIL and "skipper" not in em:
            emails.append(em)
    websites = []
    for href in p.hrefs:
        if href.startswith("mailto:"):
            continue
        if re.search(r"https?://", href, re.I) and "sailrsa.org.za" not in href.lower() and "cdn-cgi" not in href:
            if not re.search(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", href, re.I):
                websites.append(href.rstrip("/"))
    phone = ""
    m = re.search(r"\bTel\b\s*:?\s*([0-9][0-9 +()\-]{6,})", text, re.I)
    if m:
        phone = re.sub(r"\s+", " ", m.group(1)).strip()
    return {
        "abbrev": path.stem.upper(),
        "name": name,
        "file": str(path),
        "website": websites[0] if websites else "",
        "email": emails[0] if emails else "",
        "phone": phone,
        "address": _section(text, ("ADDRESS", "Address")),
        "situation": _section(text, ("SITUATION", "Situation & Directions", "Situation")),
        "description": _section(text, ("Description", "DESCRIPTION")),
        "classes": _section(text, ("CLASSES CATERED FOR", "Classes sailed")),
    }


def load_ours(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["clubs"] if isinstance(data, dict) and "clubs" in data else data


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _core(s: str) -> str:
    n = _norm(s)
    n = n.replace("denysville", "deneysville").replace("lakedenys", "lakedeneys")
    for w in ("yachtandaquatic", "sailingandsports", "university", "yachtclub", "sailingclub", "sportsclub", "sailing", "club"):
        n = n.replace(w, "")
    return n


def _names_ok(a: str, b: str) -> bool:
    ca, cb = _core(a), _core(b)
    if not ca or not cb:
        return True
    return ca == cb or ca in cb or cb in ca


def match_ours(row: dict, ours: list[dict]) -> dict | None:
    ab = ALIAS.get((row.get("abbrev") or "").upper(), (row.get("abbrev") or "").upper())
    name = row.get("name") or ""
    for o in ours:
        oa = (o.get("club_abbrev") or "").upper()
        if ab and oa == ab:
            if _names_ok(name, o.get("club_fullname") or ""):
                return o
            continue
    n = _norm(name)
    for o in ours:
        on = _norm(o.get("club_fullname") or "")
        if n and on and n == on:
            return o
    return None


def extras(src: dict, ours: dict | None) -> dict:
    gap = {}
    if not ours:
        return {
            "status": "unknown_club",
            "sailrsa": {k: src[k] for k in ("abbrev", "name", "website", "email", "phone", "address", "situation", "description", "classes") if src.get(k)},
        }
    mapping = {
        "website": "website_url",
        "email": "email",
        "phone": "phone",
        "address": "address",
        "situation": "about_text",
        "description": "about_text",
        "classes": "about_text",
    }
    for src_k, our_k in mapping.items():
        val = (src.get(src_k) or "").strip()
        have = str(ours.get(our_k) or "").strip()
        if not val:
            continue
        if src_k in {"situation", "description", "classes"}:
            if val.lower()[:40] in have.lower():
                continue
            if have and src_k != "situation":
                continue
            gap[src_k] = val
            continue
        if not have:
            gap[src_k] = val
        elif src_k == "website" and val.rstrip("/") not in have:
            if re.sub(r"^https?://(www\.)?", "", val, flags=re.I) not in have.lower():
                gap["website_alt"] = val
    if not gap:
        return {"status": "already_have", "matched": ours.get("club_abbrev")}
    return {
        "status": "new_fields",
        "matched": ours.get("club_abbrev"),
        "club_id": ours.get("club_id"),
        "our_name": ours.get("club_fullname"),
        "new": gap,
    }


def main() -> None:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/data/reference/sailrsa/site")
    ours_path = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/our_clubs.json")
    out = Path(sys.argv[3] if len(sys.argv) > 3 else "/workspace/data/reference/sailrsa/club-enrichment.json")
    ours = load_ours(ours_path)
    region_map = {}
    for idx, code in REGION.items():
        p = site / "Clubs" / idx
        if not p.is_file():
            continue
        html = p.read_text(errors="replace")
        for m in re.finditer(r"Detail/([^\"']+\.htm)", html, re.I):
            region_map[Path(m.group(1)).stem.upper()] = code
    detail = site / "Clubs" / "Detail"
    rows = []
    for p in sorted(detail.glob("*.htm")) + sorted(detail.glob("*.html")):
        row = parse_club_html(p)
        row["province"] = region_map.get(row["abbrev"], "")
        hit = extras(row, match_ours(row, ours))
        hit["sailrsa_abbrev"] = row["abbrev"]
        hit["sailrsa_name"] = row["name"]
        hit["province"] = row["province"]
        hit["source_url"] = f"https://sailrsa.org.za/Clubs/Detail/{p.name}"
        rows.append(hit)
    unknown = [r for r in rows if r["status"] == "unknown_club"]
    newf = [r for r in rows if r["status"] == "new_fields"]
    have = [r for r in rows if r["status"] == "already_have"]
    packet = {
        "source": "https://sailrsa.org.za/",
        "our_clubs": len(ours),
        "sailrsa_detail_pages": len(rows),
        "already_have": len(have),
        "new_fields": len(newf),
        "unknown_clubs": len(unknown),
        "clubs": rows,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {out} pages={len(rows)} new_fields={len(newf)} unknown={len(unknown)} have={len(have)}"
    )
    for r in unknown:
        print("UNKNOWN", r["sailrsa_abbrev"], r["sailrsa_name"])
    for r in newf:
        print("NEW", r.get("matched"), r["sailrsa_name"], sorted((r.get("new") or {}).keys()))


if __name__ == "__main__":
    main()
