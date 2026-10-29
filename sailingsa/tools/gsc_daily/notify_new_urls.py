"""When the public sitemap gains URLs, tell Google via the sitemap index.

Official path for events / sailors / weekly roundups:
  1. Rebuild sitemap.xml (already every 15 minutes)
  2. If the URL set grew, PUT only https://sailingsa.co.za/sitemap.xml
  3. Inspect a few new URLs (read-only)

Do NOT call the Indexing API. That API accepts JobPosting and
BroadcastEvent only. Sailor / regatta / roundup URLs are rejected.
Do NOT click Validate Fix. Do NOT PUT child sitemaps.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .config import ROOT_SITEMAP, SITE, server_data_root

SAST = ZoneInfo("Africa/Johannesburg")
PREV_NAME = "sitemap_urls_prev.txt"
INSPECT_NEW = 8
PRIORITY_PREFIX = ("/regatta/", "/sailing-roundup/", "/sailor/", "/events")


def collect_locs(web_root: Path) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for path in sorted(web_root.glob("sitemap-*.xml")):
        text = path.read_text(encoding="utf-8")
        for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text):
            if loc.endswith(".xml") or loc in seen:
                continue
            seen.add(loc)
            found.append(loc)
    return found


def load_prev(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}


def save_list(path: Path, urls: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(urls) + "\n", encoding="utf-8")


def prioritize(added: list[str]) -> list[str]:
    def key(url: str) -> tuple:
        path = urlparse(url).path or "/"
        for i, prefix in enumerate(PRIORITY_PREFIX):
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                return (i, path)
        return (len(PRIORITY_PREFIX), path)

    return sorted(added, key=key)


def run(
    *,
    web_root: Path,
    data_root: Path | None = None,
    secret_dir: Path | None = None,
    inspect_budget: int = INSPECT_NEW,
    submit: bool = True,
) -> dict:
    root = data_root or server_data_root()
    prev_path = root / PREV_NAME
    current = collect_locs(web_root)
    prev = load_prev(prev_path)
    added = sorted(set(current) - prev) if prev else []
    removed = sorted(prev - set(current)) if prev else []
    first_seen = not prev
    save_list(prev_path, current)
    payload: dict = {
        "as_of": datetime.now(SAST).isoformat(),
        "sitemap": ROOT_SITEMAP,
        "current_n": len(current),
        "added": added,
        "removed": removed,
        "first_seen": first_seen,
        "submitted": False,
        "inspected": [],
        "note": (
            "Google Indexing API is not used (JobPosting/BroadcastEvent only). "
            "New URLs are published on the sitemap index; GSC is PUT only when "
            "the URL set grows."
        ),
    }
    if first_seen or not added:
        dest = root / datetime.now(SAST).date().isoformat()
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "notify_new_urls.json").write_text(json.dumps(payload, indent=2) + "\n")
        return payload

    if submit:
        try:
            from .server_api import inspect_url, submit_sitemap
            from .server_auth import NeedGoogleConsent, access_token

            token = access_token(secret_dir)
            submit_sitemap(token)
            payload["submitted"] = True
            payload["submit_action"] = "put_index"
            watch = prioritize(added)[:inspect_budget]
            for url in watch:
                try:
                    ins = inspect_url(token, url)
                    st = ins.get("indexStatusResult") or {}
                    payload["inspected"].append(
                        {
                            "url": url,
                            "coverage": st.get("coverageState") or "",
                            "verdict": st.get("verdict") or "",
                        }
                    )
                except Exception as exc:
                    payload["inspected"].append(
                        {"url": url, "error": f"{type(exc).__name__}: {exc}"[:240]}
                    )
        except NeedGoogleConsent as exc:
            payload["auth"] = "PENDING"
            payload["auth_error"] = str(exc)
        except Exception as exc:
            payload["submit_error"] = f"{type(exc).__name__}: {exc}"[:400]

    dest = root / datetime.now(SAST).date().isoformat()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "notify_new_urls.json").write_text(json.dumps(payload, indent=2) + "\n")
    (dest / "new_urls.txt").write_text("\n".join(added) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="PUT sitemap index when new public URLs appear")
    ap.add_argument("--web-root", default="/var/www/sailingsa")
    ap.add_argument("--data-root", default="")
    ap.add_argument("--no-submit", action="store_true")
    args = ap.parse_args(argv)
    payload = run(
        web_root=Path(args.web_root),
        data_root=Path(args.data_root) if args.data_root else None,
        submit=not args.no_submit,
    )
    print(
        "NEW {n} | removed {r} | submitted {s} | total {t}".format(
            n=len(payload.get("added") or []),
            r=len(payload.get("removed") or []),
            s=payload.get("submitted"),
            t=payload.get("current_n"),
        )
    )
    for u in (payload.get("added") or [])[:12]:
        print(" +", u.replace(SITE, ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
