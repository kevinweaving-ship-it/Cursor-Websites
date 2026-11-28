#!/usr/bin/env python3
"""Verify every class with artwork has non-brand OG; warm PNGs; FB scrape logo classes."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, "/var/www/sailingsa/api")
os.environ.setdefault(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
os.environ.setdefault("STATIC_DIR", "/var/www/sailingsa")

import api  # noqa: E402
import facebook_og as fb  # noqa: E402
import psycopg2  # noqa: E402

TOKEN = "885045914172033|2ed3b503762ecc5f58d0d6404e74adc0"
BRAND = "/var/www/sailingsa/assets/logos/Live/logo-wordmark-on-white.png"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "-", (name or "").lower()).strip("-")


def public_slug(cname: str) -> str:
    # Prefer site canonical slug when available
    try:
        return api._class_canonical_slug(cname) or slugify(cname)
    except Exception:
        return slugify(cname)


def is_brand(path: str | None) -> bool:
    if not path:
        return True
    ap = os.path.abspath(path)
    brand_paths = {
        os.path.abspath(BRAND),
        "/var/www/sailingsa/assets/logos/sailingsa-logo.png",
        "/var/www/sailingsa/assets/logos/sailingsa-logo-on-white.png",
        "/var/www/sailingsa/favicon-192.png",
    }
    return ap in brand_paths or "logo-wordmark" in ap or ap.endswith("sailingsa-logo.png")


def fb_scrape(url: str) -> dict:
    body = urllib.parse.urlencode(
        {"id": url, "scrape": "true", "access_token": TOKEN}
    ).encode()
    req = urllib.request.Request("https://graph.facebook.com/v19.0/", data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    conn = psycopg2.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT class_id, NULLIF(btrim(class_name), '') FROM classes "
        "WHERE COALESCE(active, true) = true ORDER BY class_name"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    logo_ok = []
    logo_bad = []
    no_logo = []

    for cid, cname in rows:
        if not cname:
            continue
        key = public_slug(cname)
        # ensure slug resolves
        rcid, _ = api._resolve_class_slug_to_class_id(key)
        if not rcid:
            key2 = slugify(cname)
            rcid, _ = api._resolve_class_slug_to_class_id(key2)
            if rcid:
                key = key2
        pub = api._fb_og_class_logo_public_url(key)
        path = api._fb_og_resolve_local_path("class", key)
        art = api._artwork_class_logo_path_for_class_name(cname)
        has_art = bool(art) or (pub and "Class Logo" in pub) or (
            path and "Class Logo" in path
        )
        if has_art and not is_brand(path):
            prep = api._fb_og_prepare("class", key, source_url=pub)
            logo_ok.append((cid, key, cname, pub, path, prep))
        elif has_art and is_brand(path):
            logo_bad.append((cid, key, cname, pub, path, art))
        else:
            no_logo.append((cid, key, cname))

    print("CLASSES", len(rows))
    print("WITH_LOGO_OK", len(logo_ok))
    print("WITH_LOGO_BAD", len(logo_bad))
    print("NO_LOGO_BRAND_OK", len(no_logo))
    if logo_bad:
        print("--- STILL BAD ---")
        for row in logo_bad:
            print(row)

    # Warm OG PNGs for all logo classes
    print("--- WARM ---")
    for cid, key, cname, pub, path, prep in logo_ok:
        if not prep:
            continue
        try:
            urllib.request.urlopen(prep, timeout=90).read()
            print("warmed", key)
        except Exception as e:
            print("warm_fail", key, e)

    # FB scrape all logo class pages
    print("--- FB SCRAPE ---")
    for cid, key, cname, pub, path, prep in logo_ok:
        page = f"https://sailingsa.co.za/class/{key}"
        fb = fb_scrape(page)
        img = None
        if isinstance(fb.get("image"), list) and fb["image"]:
            img = fb["image"][0].get("url")
        ok = bool(img and "/api/og/class/" in img and key in urllib.parse.unquote(img))
        print(("FB_OK" if ok else "FB_BAD"), key, "img=", img, "err=", fb.get("error"))
        time.sleep(0.35)

    # Also scrape a few no-logo classes to ensure brand fallback still works
    print("--- FB SCRAPE NO-LOGO SAMPLE ---")
    for cid, key, cname in no_logo[:5]:
        page = f"https://sailingsa.co.za/class/{key}"
        fb = fb_scrape(page)
        img = None
        if isinstance(fb.get("image"), list) and fb["image"]:
            img = fb["image"][0].get("url")
        print("FB_NOLOGO", key, "img=", img)
        time.sleep(0.35)


if __name__ == "__main__":
    main()
