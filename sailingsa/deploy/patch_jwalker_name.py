#!/usr/bin/env python3
"""J-Walker is the boat name. North Sails is a logo. Never 'powered by North Sails' text."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
OLD = '"8": ("J-Walker powered by North Sails", "RCYCA")'
NEW = '"8": ("J-Walker", "RCYCA")'
LOCK = '''    is_jwalker = (
        "j-walker" in low
        or "jaywalker" in low.replace("-", "")
        or low.replace(" ", "").replace("-", "").startswith("jwalker")
    )
    if is_jwalker:
        slug_name = "J-Walker"
        boat_slug = None
        if _boat_names_directory is not None:
            try:
                boat_slug = _boat_profile_slug_for_name(slug_name, norm_slug_map)
            except Exception:
                boat_slug = None
        boat_href = f"/boat-name/{html_module.escape(boat_slug)}" if boat_slug else ""
        parts = [html_module.escape("J-Walker")]
        north = _fleet_sheet_sponsor_logo_img_html(
            "/artwork/Sponsor Logo/North-Sails.png", "North Sails", "rs-boat-sponsor-logo"
        )
        if north:
            parts.append(north)
        return _wrap("".join(parts))

'''
ANCHOR = '''        return _wrap("".join(parts))

    brands = [
        (r"north\\s+sails", "/artwork/Sponsor Logo/North-Sails.png", "North Sails"),
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if OLD in text:
        text = text.replace(OLD, NEW, 1)
        print("identity map -> J-Walker")
    elif '"8": ("J-Walker", "RCYCA")' in text:
        print("identity map already J-Walker")
    else:
        print("WARN: identity map bow 8 not found")
    if "is_jwalker = (" in text and 'slug_name = "J-Walker"' in text:
        print("renderer lock already present")
    else:
        if ANCHOR not in text:
            print("ERROR: baby j anchor not found")
            return 1
        text = text.replace(ANCHOR, LOCK + ANCHOR, 1)
        print("renderer lock added")
    if "J-Walker powered by North Sails" in text:
        print("ERROR: long name still in api.py")
        return 1
    API.write_text(text, encoding="utf-8")
    print("patched api.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
