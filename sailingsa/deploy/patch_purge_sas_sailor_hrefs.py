#!/usr/bin/env python3
"""Fix remaining public/admin hrefs that emit /sailor/{SAS_ID}. Keep SAS-id search redirect only."""
from __future__ import annotations

import py_compile
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-no-sas-hrefs-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text
    changes = []

    # --- 1) Admin registered-users table: /sailor/{sas} -> slug ---
    old_admin = (
        'f"<td><a href=\'/sailor/{sas}\'>{name}</a></td>"\n'
        '                f"<td><a href=\'/sailor/{sas}\'>{sas}</a></td>"'
    )
    # Need slug in scope - patch the loop to resolve slugs
    # Find the function containing this
    idx = text.find("f\"<td><a href='/sailor/{sas}'>{name}</a></td>\"")
    if idx < 0:
        # maybe already fixed
        if "href='/sailor/{slug}'" in text or 'href="/sailor/{slug}"' in text[text.find("body_rows = []") : text.find("body_rows = []") + 3000] if "body_rows = []" in text else False:
            changes.append("admin table maybe already slug")
        else:
            raise SystemExit("admin /sailor/{sas} block not found")
    else:
        # Find for-loop start for rows
        loop = text.rfind("for i, row in enumerate(rows, 1):", 0, idx)
        if loop < 0:
            raise SystemExit("admin rows loop not found")
        # Insert slug resolution after sas/name assignment
        # Current:
        #   sas = esc(row.get("sas_id"))
        #   name = esc(row.get("name") or "—")
        snippet = text[loop:idx]
        if "slug_map" not in snippet and "_batch_sailor_slugs_for_sas_ids" not in text[loop - 400 : loop]:
            # Add before loop: slug map for all rows
            pre = text[max(0, loop - 200) : loop]
            insert_before_loop = (
                "sas_ids_for_slug = [str(r.get('sas_id')) for r in rows if r.get('sas_id')]\n"
                "        reg_slug_map = _batch_sailor_slugs_for_sas_ids(sas_ids_for_slug) if sas_ids_for_slug else {}\n"
                "        "
            )
            text = text[:loop] + insert_before_loop + text[loop:]
            idx = text.find("f\"<td><a href='/sailor/{sas}'>{name}</a></td>\"")
            loop = text.rfind("for i, row in enumerate(rows, 1):", 0, idx)

        # Inside loop after sas = ...
        old_assign = 'sas = esc(row.get("sas_id"))\n            name = esc(row.get("name") or "—")'
        new_assign = (
            'sas_raw = str(row.get("sas_id") or "").strip()\n'
            '            sas = esc(sas_raw)\n'
            '            name = esc(row.get("name") or "—")\n'
            '            slug = (reg_slug_map.get(sas_raw) or "").strip()\n'
            '            sailor_href = f"/sailor/{esc(slug)}" if slug else ""'
        )
        if old_assign not in text[loop : loop + 800]:
            raise SystemExit("sas/name assign not found near admin loop")
        text = text[:loop] + text[loop : loop + 1200].replace(old_assign, new_assign, 1) + text[loop + 1200 :]

        old_cells = (
            'f"<td><a href=\'/sailor/{sas}\'>{name}</a></td>"\n'
            '                f"<td><a href=\'/sailor/{sas}\'>{sas}</a></td>"'
        )
        new_cells = (
            'f"<td>{(\'<a href=\"\' + sailor_href + \'\">\' + name + \'</a>\') if sailor_href else name}</td>"\n'
            '                f"<td>{(\'<a href=\"\' + sailor_href + \'\">\' + sas + \'</a>\') if sailor_href else sas}</td>"'
        )
        if old_cells not in text:
            raise SystemExit("admin cells not found after assign patch")
        text = text.replace(old_cells, new_cells, 1)
        changes.append("admin registered-users table -> slug hrefs")

    # --- 2) Any remaining /sailor/{sas} in href ---
    left = len(re.findall(r"href=['\"]/sailor/\{sas\}", text))
    if left:
        raise SystemExit(f"still have href /sailor/{{sas}} count={left}")

    # --- 3) Any remaining boat-style concat ---
    if "str(r['helm_sa_sailing_id'])" in text and "/sailor/" in text:
        # only fail if still used in sailor href context
        for m in re.finditer(r"/sailor/' \+ str\(r\['helm_sa_sailing_id'\]\)", text):
            raise SystemExit(f"boat-style sas href still at L{text[:m.start()].count(chr(10))+1}")

    # --- 4) Guard helper: document + assert pattern for future ---
    # Add a small helper if missing
    if "def _sailor_profile_href(" not in text:
        anchor = text.find("def _batch_sailor_slugs_for_sas_ids")
        if anchor < 0:
            raise SystemExit("batch slug helper missing")
        # insert after batch function ends - find next def at same level after a reasonable chunk
        # Simpler: insert just before _batch function
        helper = '''def _sailor_profile_href(sas_id, slug_map=None, *, slug: str = "") -> str:
    """Public sailor URL: always /sailor/{name-slug}. Never /sailor/{SAS_ID}.

    SAS numeric URLs are allowed only via redirect/search resolve, not as offered links.
    """
    s = (slug or "").strip()
    if not s and slug_map is not None and sas_id is not None:
        s = (slug_map.get(str(sas_id).strip()) or "").strip()
    if not s:
        return ""
    if s.isdigit():
        return ""
    return f"/sailor/{s}"


'''
        text = text[:anchor] + helper + text[anchor:]
        changes.append("added _sailor_profile_href guard helper")

    if text == orig:
        raise SystemExit("no changes applied")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK:", "; ".join(changes))
    print("remaining href /sailor/{sas}:", len(re.findall(r"href=['\"]/sailor/\{sas\}", text)))
    print("boat sas concat:", len(re.findall(r"/sailor/' \+ str\(r\['helm_sa_sailing_id'\]\)", text)))


if __name__ == "__main__":
    main()
