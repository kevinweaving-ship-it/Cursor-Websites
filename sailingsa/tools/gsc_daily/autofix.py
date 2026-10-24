"""Known Search Console remediations for the existing 09:00 daily job.

This is not a second tool. run_server_daily calls run() after it classifies
today's probes. Idempotent. Does not click GSC Validate Fix.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import SITE, UA

NGINX = Path("/etc/nginx/sites-enabled/sailingsa")
API = Path("/var/www/sailingsa/api/api.py")
WEB_ROOT = Path("/var/www/sailingsa")
SITEMAP_CRON = Path("/var/www/sailingsa/deploy/refresh-sitemap-cron.sh")
FIVE_XX_RESTART_AT = 5

CONTRACT = (
    {
        "id": "www_roundup",
        "url": "https://www.sailingsa.co.za/sailing-roundup/",
        "want_status": 301,
        "location_host": "sailingsa.co.za",
        "fix": "nginx",
    },
    {
        "id": "home",
        "url": f"{SITE}/home",
        "want_status": 301,
        "location_path": "/",
        "fix": "nginx",
    },
    {
        "id": "podium_empty",
        "url": f"{SITE}/regatta/class/podium/podium.html?regatta_id=",
        "want_status": 301,
        "location_path": "/events",
        "fix": "nginx",
    },
    {
        "id": "sailors_title",
        "url": f"{SITE}/sailors",
        "want_status": 200,
        "title_has": "South African Sailors",
        "fix": "api",
    },
    {
        "id": "sitemap_roundups",
        "url": f"{SITE}/sitemap-roundups.xml",
        "want_status": 200,
        "fix": "sitemaps",
    },
    {
        "id": "sitemap_news",
        "url": f"{SITE}/sitemap-news.xml",
        "want_status": 200,
        "fix": "sitemaps",
    },
    {
        "id": "hub_canonical",
        "url": f"{SITE}/sailing-roundup/",
        "want_status": 200,
        "has_canonical": True,
        "fix": "seo",
    },
)


def first_hop(url: str, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(80_000)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "status": resp.status,
                "location": headers.get("location") or "",
                "body": body,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read(80_000)
        except Exception:
            pass
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return {
            "status": exc.code,
            "location": headers.get("location") or "",
            "body": body,
            "error": "",
        }
    except Exception as exc:
        return {"status": 0, "location": "", "body": b"", "error": f"{type(exc).__name__}: {exc}"}


def _title(body: bytes) -> str:
    match = re.search(br"<title>([^<]+)</title>", body, re.I)
    return match.group(1).decode("utf-8", "replace") if match else ""


def evaluate_row(spec: dict[str, Any], hop: dict[str, Any]) -> dict[str, Any]:
    status = int(hop.get("status") or 0)
    location = hop.get("location") or ""
    body = hop.get("body") or b""
    reasons: list[str] = []
    if spec.get("want_status") and status != spec["want_status"]:
        reasons.append(f"status {status} want {spec['want_status']}")
    loc = urlparse(location)
    if spec.get("location_host") and loc.netloc and loc.netloc != spec["location_host"]:
        reasons.append(f"location host {loc.netloc}")
    if spec.get("location_path"):
        want = spec["location_path"].rstrip("/") or "/"
        got = (loc.path or urlparse(location).path or "/").rstrip("/") or "/"
        if want == "/":
            if got != "/":
                reasons.append(f"location path {location}")
        elif want != got and not got.endswith(want):
            reasons.append(f"location path {location}")
    if spec.get("title_has") and spec["title_has"] not in _title(body):
        reasons.append(f"title {_title(body)[:60]!r}")
    if spec.get("has_canonical") and b'rel="canonical"' not in body.lower() and b"rel='canonical'" not in body.lower():
        reasons.append("missing canonical")
    if hop.get("error"):
        reasons.append(str(hop["error"])[:120])
    return {
        "id": spec["id"],
        "url": spec["url"],
        "ok": not reasons,
        "status": status,
        "detail": "; ".join(reasons),
        "fix": spec["fix"],
    }


def five_xx_count(probes: list[dict] | None) -> int:
    n = 0
    for row in probes or []:
        status = int(row.get("first_status") or row.get("status") or 0)
        if 500 <= status < 600:
            n += 1
    return n


def decide(findings: list[dict], *, five_xx: int = 0) -> list[str]:
    actions: list[str] = []
    for row in findings:
        if row.get("ok"):
            continue
        fix = row.get("fix")
        if fix and fix not in actions:
            actions.append(fix)
    if five_xx >= FIVE_XX_RESTART_AT and "restart_api" not in actions:
        actions.append("restart_api")
    return actions


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _deploy_file(filename: str) -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "deploy" / filename,
        Path("/opt/sailingsa-gsc/sailingsa/deploy") / filename,
        Path("/var/www/sailingsa/deploy") / filename,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _chattr(path: Path, locked: bool) -> None:
    flag = "+i" if locked else "-i"
    subprocess.run(["chattr", flag, str(path)], check=False, capture_output=True)


def _apply_nginx() -> dict[str, Any]:
    script = _deploy_file("apply_gsc_nginx_fixes.py")
    if not script or not NGINX.is_file():
        return {"ok": False, "error": "nginx patch or site file missing"}
    mod = _load(script, "apply_gsc_nginx_fixes")
    before = NGINX.read_text(encoding="utf-8")
    after = mod.patch(before)
    if after == before:
        return {"ok": True, "changed": False}
    _chattr(NGINX, False)
    backup = Path("/root/gsc-backups")
    backup.mkdir(parents=True, exist_ok=True)
    (backup / "nginx.sailingsa.autofix.bak").write_text(before, encoding="utf-8")
    NGINX.write_text(after, encoding="utf-8")
    test = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if test.returncode != 0:
        NGINX.write_text(before, encoding="utf-8")
        _chattr(NGINX, True)
        return {"ok": False, "error": (test.stderr or test.stdout)[:240]}
    subprocess.run(["systemctl", "reload", "nginx"], check=False)
    _chattr(NGINX, True)
    return {"ok": True, "changed": True}


def _apply_api() -> dict[str, Any]:
    script = _deploy_file("live_patch_gsc_api.py")
    if not script or not API.is_file():
        return {"ok": False, "error": "api patch or api.py missing"}
    mod = _load(script, "live_patch_gsc_api")
    before = API.read_text(encoding="utf-8")
    after = mod.patch(before)
    if after == before:
        return {"ok": True, "changed": False}
    _chattr(API, False)
    Path("/root/gsc-backups").mkdir(parents=True, exist_ok=True)
    Path("/root/gsc-backups/api.py.autofix.bak").write_text(before, encoding="utf-8")
    API.write_text(after, encoding="utf-8")
    _chattr(API, True)
    return {"ok": True, "changed": True}


def _apply_sitemaps() -> dict[str, Any]:
    writer = None
    for path in (
        Path("/tmp/roundup-gsc/write_google_sitemaps.py"),
        Path("/opt/sailingsa-gsc/sailingsa/deploy/write_google_sitemaps.py"),
        Path(__file__).resolve().parents[3] / "gowifi" / "rea" / "sailing-roundup" / "app" / "write_google_sitemaps.py",
    ):
        if path.is_file():
            writer = path
            break
    if writer:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(writer.parent) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        proc = subprocess.run(
            [sys.executable, str(writer), "--web-root", str(WEB_ROOT), "--no-ping"],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        return {"ok": proc.returncode == 0, "out": (proc.stdout or proc.stderr)[:240]}
    if SITEMAP_CRON.is_file():
        proc = subprocess.run(["bash", str(SITEMAP_CRON)], capture_output=True, text=True, timeout=180)
        return {"ok": proc.returncode == 0, "out": (proc.stdout or proc.stderr)[-240:]}
    return {"ok": False, "error": "no sitemap writer"}


def _apply_seo() -> dict[str, Any]:
    for path in (
        Path("/tmp/roundup-gsc/seo_head.py"),
        Path("/opt/sailingsa-gsc/sailingsa/deploy/seo_head.py"),
        Path(__file__).resolve().parents[3] / "gowifi" / "rea" / "sailing-roundup" / "app" / "seo_head.py",
    ):
        if not path.is_file():
            continue
        env = os.environ.copy()
        env["PYTHONPATH"] = str(path.parent)
        code = (
            "import json,seo_head; "
            "print(json.dumps(seo_head.patch_web_root(%r)))" % str(WEB_ROOT)
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout)[:240]}
        try:
            return {"ok": True, "result": json.loads(proc.stdout.strip() or "{}")}
        except Exception:
            return {"ok": True, "out": proc.stdout[:240]}
    return _apply_sitemaps()


def _restart_api() -> dict[str, Any]:
    proc = subprocess.run(
        ["systemctl", "restart", "sailingsa-api"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {"ok": proc.returncode == 0, "out": (proc.stderr or proc.stdout)[:180]}


APPLIERS = {
    "nginx": _apply_nginx,
    "api": _apply_api,
    "sitemaps": _apply_sitemaps,
    "seo": _apply_seo,
    "restart_api": _restart_api,
}


def check_contract() -> list[dict[str, Any]]:
    return [evaluate_row(spec, first_hop(spec["url"])) for spec in CONTRACT]


def run(*, apply: bool = True, probes: list[dict] | None = None) -> dict[str, Any]:
    findings = check_contract()
    five_xx = five_xx_count(probes)
    actions = decide(findings, five_xx=five_xx)
    applied: dict[str, Any] = {}
    if apply:
        need_restart = "restart_api" in actions
        for name in actions:
            if name == "restart_api":
                continue
            try:
                applied[name] = APPLIERS[name]()
                if name == "api" and applied[name].get("changed"):
                    need_restart = True
            except Exception as exc:
                applied[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if need_restart:
            try:
                applied["restart_api"] = _restart_api()
            except Exception as exc:
                applied["restart_api"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        findings_after = check_contract()
    else:
        findings_after = findings
    return {
        "apply": apply,
        "five_xx": five_xx,
        "actions": actions,
        "applied": applied,
        "before": findings,
        "after": findings_after,
        "still_broken": [r["id"] for r in findings_after if not r.get("ok")],
    }
