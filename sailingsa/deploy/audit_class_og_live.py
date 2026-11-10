#!/usr/bin/env python3
"""Audit every class OG: real class logo right, not SSA brand fallback."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, "/var/www/sailingsa/api")
os.environ.setdefault(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
os.environ.setdefault("STATIC_DIR", "/var/www/sailingsa")

import psycopg2  # noqa: E402
import api  # noqa: E402
import facebook_og as fb  # noqa: E402


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def main() -> None:
    brand = fb.resolve_brand_favicon_path(
        "/var/www/sailingsa/artwork/Class Logo/420-Class-Logo.png",
        "/var/www/sailingsa",
    )
    brand_paths = set()
    for p in (
        brand,
        "/var/www/sailingsa/assets/logos/Live/logo-wordmark-on-white.png",
        "/var/www/sailingsa/assets/logos/sailingsa-logo.png",
        "/var/www/sailingsa/assets/logos/sailingsa-logo-on-white.png",
        "/var/www/sailingsa/favicon-192.png",
    ):
        if p and os.path.isfile(p):
            brand_paths.add(os.path.abspath(p))
    print("BRAND", brand)

    conn = psycopg2.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT class_id, NULLIF(btrim(class_name), ''), NULLIF(btrim(logo_path), '') "
        "FROM classes WHERE COALESCE(active, true) = true "
        "ORDER BY class_name NULLS LAST, class_id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    print("DB classes", len(rows))

    # Also pull href keys from classes directory if available
    dir_keys = set()
    try:
        items = api._directory_classes()
        for it in items or []:
            if isinstance(it, dict):
                for k in ("slug", "href", "key", "class_slug"):
                    if it.get(k):
                        dir_keys.add(str(it[k]).strip("/").split("/")[-1])
                if it.get("name"):
                    dir_keys.add(slugify(str(it["name"])))
            elif isinstance(it, (list, tuple)) and it:
                dir_keys.add(slugify(str(it[0])))
    except Exception as e:
        print("directory_classes err", e)
    print("directory keys sample", list(sorted(dir_keys))[:20], "count", len(dir_keys))

    ok = bad = 0
    results = []
    for cid, cname, logo_path in rows:
        candidates = []
        if cname:
            # Prefer exact public slug patterns used on site
            candidates.append(slugify(cname))
            candidates.append(cname.strip())
            candidates.append(cname.strip().lower())
            compact = re.sub(r"\s+", "", cname.strip())
            candidates.append(compact.lower())
        candidates.append(str(cid))

        key = None
        for cand in candidates:
            if not cand:
                continue
            rcid, _rname = api._resolve_class_slug_to_class_id(cand)
            if rcid is not None and int(rcid) == int(cid):
                key = cand
                break
        if not key:
            key = slugify(cname) if cname else str(cid)

        pub = api._fb_og_class_logo_public_url(key)
        path = api._fb_og_resolve_local_path("class", key)
        try:
            prep = api._fb_og_prepare("class", key, source_url=pub)
        except Exception as e:
            prep = f"ERR:{e}"

        is_brand = bool(path and os.path.abspath(path) in brand_paths)
        status = "OK"
        if not path or not os.path.isfile(path):
            status = "NO_FILE"
        elif is_brand:
            status = "FALLBACK_BRAND"
        elif not isinstance(prep, str) or "/api/og/class/" not in prep:
            status = "BAD_PREPARE"

        expected = None
        if logo_path:
            lp = logo_path if str(logo_path).startswith("/") else "/" + str(logo_path)
            expected = api._fb_url_to_local(lp)
        if not expected and cname and hasattr(api, "_artwork_class_logo_path_for_class_name"):
            art = api._artwork_class_logo_path_for_class_name(cname)
            if art:
                expected = api._fb_url_to_local(art)

        if status == "OK" and expected and os.path.isfile(expected):
            if os.path.abspath(path) != os.path.abspath(expected):
                if "Class Logo" not in (path or "") and "class" not in (path or "").lower():
                    status = "WRONG_ASSET"

        # Path-versioned URL must include key segment
        if status == "OK" and isinstance(prep, str):
            if f"/api/og/class/{key}/" not in prep:
                # URL-encoded key?
                from urllib.parse import quote

                if f"/api/og/class/{quote(key, safe='')}/" not in prep:
                    status = "BAD_URL_KEY"

        if status == "OK":
            ok += 1
        else:
            bad += 1
        results.append((status, cid, key, cname, pub, path, expected, prep))

    print("SUMMARY ok", ok, "bad", bad, "total", len(results))
    print("--- BAD ---")
    for status, cid, key, cname, pub, path, expected, prep in results:
        if status != "OK":
            print(status, "cid=", cid, "key=", key, "name=", cname)
            print("  pub=", pub)
            print("  path=", path)
            print("  expected=", expected)
            print("  prep=", prep)
    print("--- ALL ---")
    for status, cid, key, cname, pub, path, expected, prep in results:
        print(f"{status}\t{cid}\t{key}\t{cname}\t{pub}")


if __name__ == "__main__":
    main()
