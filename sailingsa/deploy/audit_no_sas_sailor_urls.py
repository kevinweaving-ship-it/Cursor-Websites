#!/usr/bin/env python3
"""Audit live api.py + web root for /sailor/{SAS_ID} link generation."""
from __future__ import annotations

import os
import re
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
ROOT = Path("/var/www/sailingsa")

# Suspicious: /sailor/ + something that looks like an id field (not slug)
SUSPECT_RE = re.compile(
    r"""(?:
        /sailor/['"]?\s*\+\s*(?:str\()?[^;\n]{0,80}?(?:sas_id|sa_sailing_id|helm_sa|crew_sa|sailor_id|sa_id)\b
      | /sailor/\{[^}]*(?:sas_id|sa_sailing_id|helm_sa|crew_sa|sailor_id|sa_id|sid)\b[^}]*\}
      | href=['"]/sailor/['"]?\s*\+\s*(?:encodeURIComponent\()?[^;\n]{0,60}?(?:sas|sid|id|helmId|crewId)\b
      | /sailor/\$\{[^}]*(?:sas|sid|Id|ID)[^}]*\}
    )""",
    re.I | re.X,
)

# Allowed: redirects that resolve TO slug, resolve API, bot detectors, comments
ALLOW_HINTS = (
    "canonical_slug",
    "canonical_url",
    "RedirectResponse",
    "_is_sailor_sas_id",
    "numeric /sailor",
    "SAS ID URLs",
    "bot signal",
    "Never link to bare",
    "digits",
)


def scan_text(path: str, text: str) -> list[tuple[int, str]]:
    hits = []
    for m in SUSPECT_RE.finditer(text):
        line = text[: m.start()].count("\n") + 1
        # context window
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 80)
        ctx = text[start:end].replace("\n", " ")
        low = ctx.lower()
        # skip slug-based builders
        if any(x in low for x in ("slug", "canonical_slug", "likely_slug", "helm_slug", "crew_slug", "sslug", "j.slug")):
            # still flag if ALSO concatenating raw sas into path without slug map
            if "helm_sa_sailing_id" in low and "slug" not in low[low.find("/sailor/") : low.find("/sailor/") + 120]:
                pass
            else:
                # if the /sailor/ expression uses slug variable, skip
                frag = m.group(0).lower()
                if "slug" in frag or "canonical" in frag:
                    continue
        hits.append((line, ctx[:220]))
    return hits


def main() -> None:
    print("=== api.py ===")
    t = API.read_text(encoding="utf-8", errors="replace")
    hits = scan_text(str(API), t)
    # Extra hard checks for known bad patterns
    for pat, label in [
        (r"/sailor/' \+ str\(r\['helm_sa_sailing_id'\]\)", "boat helm sas concat"),
        (r"/sailor/\{sas\}", "f-string {sas}"),
        (r"/sailor/\{sid\}", "f-string {sid}"),
        (r"/sailor/\{sa_id\}", "f-string {sa_id}"),
        (r"/sailor/\{sailor_id\}", "f-string {sailor_id}"),
        (r"/sailor/\$\{[^}]*sas", "js ${sas...}"),
        (r'f"/sailor/\{[^}]*sas_id', "f sailor sas_id"),
        (r"f'/sailor/\{[^}]*sas_id", "f sailor sas_id sq"),
    ]:
        for m in re.finditer(pat, t, re.I):
            line = t[: m.start()].count("\n") + 1
            ctx = t[max(0, m.start() - 80) : m.end() + 80].replace("\n", " ")
            print(f"HARD {label} L{line}: {ctx[:200]}")
    print(f"suspect regex hits: {len(hits)}")
    for line, ctx in hits[:80]:
        print(f"L{line}: {ctx}")

    print("\n=== static/js/html (non-bak) ===")
    skip_dirs = {".git", "venv", "node_modules", "__pycache__", "bak"}
    file_hits = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith("_LANDING") and not d.startswith("bak")]
        for fn in files:
            if not fn.endswith((".js", ".html", ".py")):
                continue
            if ".bak" in fn or fn.endswith(".backup"):
                continue
            p = Path(root) / fn
            try:
                s = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            local = []
            for pat, label in [
                (r"/sailor/' \+ (?:String\()?[^;\n]{0,40}?(?:sas_id|sa_sailing|helm_sa|crew_sa|sailor_id|\bsid\b|\bid\b)", "concat"),
                (r'/sailor/" \+ (?:String\()?[^;\n]{0,40}?(?:sas_id|sa_sailing|helm_sa|crew_sa|sailor_id|\bsid\b)', "concat2"),
                (r"/sailor/\$\{(?:sas|sid|id|helmId|crewId|sailorId)[^}]*\}", "tmpl"),
                (r"/sailor/\{(?:sas|sid|sa_id|sailor_id)[^}]*\}", "pyf"),
            ]:
                for m in re.finditer(pat, s, re.I):
                    # allow name-slug builders: base + '-' + sid
                    frag = s[max(0, m.start() - 60) : m.end() + 40]
                    if "base + '-' +" in frag or 'base + "-" +' in frag or "base+'-'+" in frag:
                        continue
                    if "slug" in frag.lower() and "sas_id" not in m.group(0).lower():
                        continue
                    line = s[: m.start()].count("\n") + 1
                    local.append((label, line, frag.replace("\n", " ")[:180]))
            if local:
                file_hits += 1
                rel = str(p.relative_to(ROOT))
                print(f"\n{rel}")
                for label, line, frag in local[:12]:
                    print(f"  {label} L{line}: {frag}")
    print(f"\nfiles_with_hits={file_hits}")


if __name__ == "__main__":
    main()
