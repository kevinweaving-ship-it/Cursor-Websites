#!/usr/bin/env python3
"""Tuya icon library builder (step 2): cache the exact Tuya device/product icons for every shared device, once per
unique source, into the site's static assets, and write manifest.json.

Sources, in order: device `icon` (smart/icon/... or smart/program_category_icon/...) -> program_category_icon/<cat>.png
-> local generic fallback. Hosts are allow-listed; originals are kept as delivered (PNG/JPEG/WebP); every write is
atomic; every file is SHA-256 hashed. The manifest contains ids, names, URLs and hashes only - never tokens, keys or uid.

Runs from cron/systemd as root (needs the collector control token) and writes files owned by www-data.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(os.getenv("TUYA_ICON_ROOT") or "/var/www/sailingsa/assets/tuya")
URL_BASE = "/assets/tuya"
SCAN_URL = os.getenv("TUYA_SCAN_URL") or "http://127.0.0.1:8007/scan"
TOKEN = ""
for line in open("/etc/tuya-sharing.env", encoding="utf-8"):
    if line.startswith("TUYA_SHARING_CTRL_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"')
CDN_HOSTS = ["images.tuyaeu.com", "images.tuyacn.com", "images.tuyaus.com"]          # tried in order
ALLOWED_HOST_RE = re.compile(r"^(images\.tuya(eu|cn|us)\.com|[a-z0-9.-]+\.thingclips\.com)$")
PATH_RE = re.compile(r"^smart/[A-Za-z0-9_./-]+\.(png|jpg|jpeg|webp)$", re.I)
MAGIC = {b"\x89PNG\r\n\x1a\n": ("png", "image/png"), b"\xff\xd8\xff": ("jpg", "image/jpeg"), b"RIFF": ("webp", "image/webp")}
UA = "SailingSA-Arial tuya-icon-cache/1 (+https://sailingsa.co.za)"
OWNER = ("www-data", "www-data")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def chown_tree(path: Path) -> None:
    try:
        import pwd, grp
        uid, gid = pwd.getpwnam(OWNER[0]).pw_uid, grp.getgrnam(OWNER[1]).gr_gid
        for p in [path, *path.rglob("*")]:
            os.chown(p, uid, gid)
    except (KeyError, PermissionError) as exc:
        log("chown skipped:", exc)


def sniff(data: bytes):
    for magic, (ext, mime) in MAGIC.items():
        if data.startswith(magic):
            if ext == "webp" and data[8:12] != b"WEBP":
                continue
            return ext, mime
    return None, None


def fetch(rel_path: str):
    """Download a Tuya CDN asset by relative path. Returns (bytes, url, ext, mime) or None."""
    if not PATH_RE.match(rel_path) or ".." in rel_path:
        log("rejected path", rel_path)
        return None
    for host in CDN_HOSTS:
        if not ALLOWED_HOST_RE.match(host):
            continue
        url = f"https://{host}/{rel_path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status != 200:
                    continue
                data = r.read(2_000_000)
        except Exception as exc:  # noqa: BLE001
            log("fetch failed", url, exc.__class__.__name__)
            continue
        ext, mime = sniff(data)
        if not ext or len(data) < 200:
            log("not an image", url)
            continue
        return data, url, ext, mime
    return None


def scan_devices() -> list[dict]:
    req = urllib.request.Request(SCAN_URL, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    if not d.get("ok"):
        raise SystemExit(f"scan failed: {d}")
    return d["devices"]


FALLBACK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" stroke="#64748b" stroke-width="3" '
                'stroke-linecap="round" stroke-linejoin="round"><rect x="10" y="14" width="44" height="36" rx="6"/>'
                '<path d="M22 50v6h20v-6"/><circle cx="32" cy="32" r="8"/></svg>')


def main() -> int:
    devices = scan_devices()
    log("devices from collector:", len(devices))
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest = {"generated_at": now, "url_base": URL_BASE, "hosts": CDN_HOSTS,
                "devices": {}, "products": {}, "categories": {}, "weather": {}, "controls": {}, "fallback": {}}
    try:   # controls (tuya-panel-kit import) are maintained by import_controls.py; carry them over
        prev = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["controls"] = prev.get("controls") or {}
        if prev.get("controls_license"):
            manifest["controls_license"] = prev["controls_license"]
    except (OSError, ValueError):
        pass
    # generic fallback (ours, SVG)
    fb = ROOT / "fallback" / "device.svg"
    atomic_write(fb, FALLBACK_SVG.encode())
    manifest["fallback"]["device"] = {"local_path": f"{URL_BASE}/fallback/device.svg", "source_type": "local", "mime": "image/svg+xml",
                                      "sha256": hashlib.sha256(FALLBACK_SVG.encode()).hexdigest()}
    # unique source -> cached file (deduped by source path)
    cache: dict[str, dict] = {}

    def cached(rel_path: str, kind: str, key: str):
        """kind: products | categories. key: file stem (hash of the source path, or the category code)."""
        if rel_path in cache:
            return cache[rel_path]
        got = fetch(rel_path)
        if not got:
            cache[rel_path] = None
            return None
        data, url, ext, mime = got
        sha = hashlib.sha256(data).hexdigest()
        fname = f"{key}.{ext}"
        path = ROOT / kind / fname
        changed = True
        if path.exists():
            changed = hashlib.sha256(path.read_bytes()).hexdigest() != sha
        if changed:
            atomic_write(path, data)
        rec = {"local_path": f"{URL_BASE}/{kind}/{fname}", "original_source": url, "source_path": rel_path, "source_type": kind[:-1] if kind != "categories" else "category",
               "mime": mime, "bytes": len(data), "sha256": sha, "downloaded_at": now, "changed": changed}
        cache[rel_path] = rec
        return rec

    stats = {"device_icon": 0, "category_fallback": 0, "generic": 0}
    for d in devices:
        dev_id, cat = d["id"], str(d.get("category") or "")
        icon = str(d.get("icon") or "")
        rec = None
        src = None
        if icon:
            if icon.startswith("smart/program_category_icon/"):
                rec = cached(icon, "categories", cat or Path(icon).stem)
                src = "category"
            else:
                rec = cached(icon, "products", hashlib.sha256(icon.encode()).hexdigest()[:16])
                src = "device_icon"
        if rec is None and cat:
            rec = cached(f"smart/program_category_icon/{cat}.png", "categories", cat)
            src = "category_fallback"
        entry = {"name": d.get("name"), "home": d.get("home"), "category": cat, "product_id": d.get("product_id"),
                 "product_name": d.get("product_name"), "icon": icon or None}
        if rec:
            entry.update({"local_path": rec["local_path"], "original_source": rec["original_source"], "source_type": src,
                          "mime": rec["mime"], "sha256": rec["sha256"], "status": "ok"})
            stats["device_icon" if src == "device_icon" else "category_fallback"] += 1
        else:
            entry.update({"local_path": manifest["fallback"]["device"]["local_path"], "source_type": "generic", "status": "fallback"})
            stats["generic"] += 1
        manifest["devices"][dev_id] = entry
        if d.get("product_id") and rec and src == "device_icon":
            manifest["products"].setdefault(d["product_id"], {"product_name": d.get("product_name"), "category": cat, **rec})
        # every category we own also gets its program_category_icon cached (canonical category map)
        if cat and cat not in manifest["categories"]:
            crec = cached(f"smart/program_category_icon/{cat}.png", "categories", cat)
            if crec:
                manifest["categories"][cat] = {"name": None, **crec}
    unique_files = {r["local_path"] for r in cache.values() if r}
    manifest["summary"] = {"devices": len(devices), "unique_assets": len(unique_files), **stats}
    atomic_write(ROOT / "manifest.json", json.dumps(manifest, indent=1, ensure_ascii=False).encode())
    chown_tree(ROOT)
    log("done", manifest["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
