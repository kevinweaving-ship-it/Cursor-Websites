#!/usr/bin/env python3
"""Scan live active frontend + api.py for offered /sailor/{SAS_ID} links."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/var/www/sailingsa")
API = ROOT / "api" / "api.py"


def scan_api() -> None:
    t = API.read_text(encoding="utf-8")
    print("=== LIVE api/api.py hard checks ===")
    checks = [
        (r"href=['\"]/sailor/\{sas\}", "href /sailor/{sas}"),
        (r"href=['\"]/sailor/\{sid\}", "href /sailor/{sid}"),
        (r"href=['\"]/sailor/\{sa_id\}", "href /sailor/{sa_id}"),
        (r"href=['\"]/sailor/\{sailor_id\}", "href /sailor/{sailor_id}"),
        (r"/sailor/' \+ str\(r\['helm_sa_sailing_id'\]\)", "boat helm sas"),
        (r"/sailor/' \+ str\(r\['crew_sa_sailing_id'\]\)", "boat crew sas"),
        (r"/sailor/' \+ str\([^)]*sas_id", "concat sas_id"),
        (r'/sailor/" \+ str\([^)]*sas_id', "concat sas_id dq"),
        (r"f['\"]/sailor/\{[^}]*sas_id[^}]*\}", "f sailor sas_id"),
    ]
    bad = 0
    for pat, label in checks:
        ms = list(re.finditer(pat, t, re.I))
        print(f"{label}: {len(ms)}")
        for m in ms:
            line = t[: m.start()].count("\n") + 1
            print(f"  L{line}: {t[m.start()-40:m.end()+40].replace(chr(10),' ')[:160]}")
            bad += 1
    # Allowed redirect-only patterns (report count)
    print("RedirectResponse to slug:", len(re.findall(r'RedirectResponse\(url=f"/sailor/\{canonical_slug\}"', t)))
    print("_sailor_profile_href present:", "def _sailor_profile_href(" in t)
    print("BAD_COUNT", bad)


def scan_frontend() -> None:
    print("\n=== active frontend ===")
    paths: list[Path] = []
    for rel in [
        "index.html",
        "blank.html",
        "blank69.html",
        "boat-passport.html",
        "boat_pedigree.html",
        "boats-directory.html",
        "search.html",
        "js",
        "public",
        "components",
    ]:
        p = ROOT / rel
        if p.is_file():
            paths.append(p)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.suffix in (".js", ".html") and ".bak" not in f.name and "backup" not in f.name.lower():
                    paths.append(f)

    plus = re.compile(
        r"""/sailor/(?:'|"|`)?\s*\+\s*(?:encodeURIComponent\()?([A-Za-z0-9_$.]+)""",
        re.I,
    )
    tmpl = re.compile(r"/sailor/\$\{([^}]+)\}")
    file_hits = 0
    for p in paths:
        try:
            s = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        local = []
        for m in plus.finditer(s):
            var = m.group(1)
            frag = s[max(0, m.start() - 80) : m.end() + 60]
            fl = frag.lower()
            if "slug" in fl or "base + '-' +" in frag or "base + \"-\" +" in frag:
                continue
            if var.lower() in ("slug", "sslug", "helmslug", "crewslug", "canonical"):
                continue
            # numeric-only id navigation without name base is bad
            local.append(("plus+" + var, frag.replace("\n", " ")[:170]))
        for m in tmpl.finditer(s):
            var = m.group(1)
            if "slug" in var.lower():
                continue
            frag = s[max(0, m.start() - 50) : m.end() + 40]
            local.append(("tmpl+" + var, frag.replace("\n", " ")[:170]))
        if local:
            file_hits += 1
            print(p.relative_to(ROOT))
            for a, b in local[:10]:
                print(" ", a, ":", b)
    print("files_with_suspects", file_hits, "scanned", len(paths))


if __name__ == "__main__":
    scan_api()
    scan_frontend()
