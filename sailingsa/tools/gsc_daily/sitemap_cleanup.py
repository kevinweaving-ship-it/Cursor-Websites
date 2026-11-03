#!/usr/bin/env python3
"""Server-side GSC sitemap submit/delete. No Mac Chrome. No site file changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import (
    GSC_OAUTH_SCOPE,
    GSC_OAUTH_SCOPE_WRITE,
    GSC_RESOURCE,
    OBSOLETE_SITEMAP_NAMES,
    ROOT_SITEMAP,
    SERVER_SECRET_DIR,
    SITE,
)
from .server_api import delete_sitemap, list_sitemaps, list_sites, submit_sitemap
from .server_auth import NeedGoogleConsent, access_token


def _paths(sitemaps: list[dict]) -> list[str]:
    return [s.get("path") or "" for s in sitemaps]


def _match(path: str, name: str) -> bool:
    p = (path or "").rstrip("/")
    return p.endswith("/" + name) or p.endswith(name) or p == name


def _summarize(sitemaps: list[dict]) -> list[dict]:
    out = []
    for s in sitemaps:
        out.append(
            {
                "path": s.get("path"),
                "lastSubmitted": s.get("lastSubmitted"),
                "lastDownloaded": s.get("lastDownloaded"),
                "errors": s.get("errors"),
                "warnings": s.get("warnings"),
                "isPending": s.get("isPending"),
            }
        )
    return out


def inspect_secret_dir(secret: Path) -> dict:
    client = secret / "client_secret.json"
    token = secret / "token.json"
    info = {
        "dir": str(secret),
        "dir_exists": secret.is_dir(),
        "client_secret_json": client.is_file(),
        "token_json": token.is_file(),
        "token_scopes": [],
        "has_refresh_token": False,
    }
    if token.is_file():
        try:
            tok = json.loads(token.read_text(encoding="utf-8"))
        except Exception:
            tok = {}
        info["has_refresh_token"] = bool(tok.get("refresh_token"))
        scopes = tok.get("scopes") or tok.get("scope") or []
        if isinstance(scopes, str):
            scopes = scopes.split()
        info["token_scopes"] = list(scopes)
        info["write_scope"] = GSC_OAUTH_SCOPE_WRITE in info["token_scopes"] or (
            any(s.endswith("/webmasters") and not s.endswith("readonly") for s in info["token_scopes"])
        )
    return info


def run(secret_dir: Path | None = None) -> dict:
    secret = secret_dir or SERVER_SECRET_DIR
    auth_meta = inspect_secret_dir(secret)
    report = {
        "property": GSC_RESOURCE,
        "root": ROOT_SITEMAP,
        "auth": auth_meta,
        "sites": [],
        "before": [],
        "deleted": [],
        "skipped_not_submitted": [],
        "submitted": None,
        "after": [],
        "google": {},
        "human_consent_required": False,
    }
    try:
        token = access_token(secret)
    except NeedGoogleConsent as e:
        report["human_consent_required"] = True
        report["google"] = {"error": str(e), "needed_scope": GSC_OAUTH_SCOPE}
        return report

    try:
        report["sites"] = [s.get("siteUrl") for s in list_sites(token)]
        site = GSC_RESOURCE
        if site not in report["sites"]:
            # URL-prefix fallback if domain property missing
            alt = SITE.rstrip("/") + "/"
            if alt in report["sites"]:
                site = alt
                report["property"] = site
        before = list_sitemaps(token, site)
        report["before"] = _summarize(before)
        before_paths = _paths(before)

        for name in OBSOLETE_SITEMAP_NAMES:
            hits = [p for p in before_paths if _match(p, name)]
            if not hits:
                report["skipped_not_submitted"].append(name)
                continue
            for feed in hits:
                try:
                    delete_sitemap(token, feed, site)
                    report["deleted"].append({"path": feed, "result": "deleted"})
                except RuntimeError as e:
                    if "403" in str(e) and "insufficient" in str(e).lower():
                        report["human_consent_required"] = True
                        report["google"] = {
                            "error": str(e),
                            "needed_scope": GSC_OAUTH_SCOPE_WRITE,
                        }
                        return report
                    report["deleted"].append({"path": feed, "result": str(e)})

        try:
            submit_sitemap(token, ROOT_SITEMAP, site)
            report["submitted"] = {"path": ROOT_SITEMAP, "result": "submitted"}
        except RuntimeError as e:
            if "403" in str(e) and "insufficient" in str(e).lower():
                report["human_consent_required"] = True
                report["google"] = {"error": str(e), "needed_scope": GSC_OAUTH_SCOPE_WRITE}
                return report
            report["submitted"] = {"path": ROOT_SITEMAP, "result": str(e)}

        after = list_sitemaps(token, site)
        report["after"] = _summarize(after)
        report["google"] = {"ok": True, "listed": len(after)}
    except NeedGoogleConsent as e:
        report["human_consent_required"] = True
        report["google"] = {"error": str(e), "needed_scope": GSC_OAUTH_SCOPE}
    except Exception as e:
        report["google"] = {"error": f"{type(e).__name__}: {e}"}
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GSC sitemap cleanup via official API")
    ap.add_argument("--secret-dir", default="")
    args = ap.parse_args(argv)
    secret = Path(args.secret_dir) if args.secret_dir else None
    report = run(secret)
    print(json.dumps(report, indent=2))
    if report.get("human_consent_required"):
        print("STOP_NEED_KEVIN_GOOGLE_APPROVAL", file=sys.stderr)
        return 3
    if not report.get("submitted") or str((report.get("submitted") or {}).get("result")) != "submitted":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
