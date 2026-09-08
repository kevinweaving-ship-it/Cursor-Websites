#!/opt/hikpoc/venv/bin/python
"""EZVIZ cloud snapshot → 640p JPEG (Bing Carport size). Usage:
  bridge_ezviz_snap.py SERIAL OUT_640.jpg

Keeps the last good file on EZVIZ 2009 / busy. Does not print secrets.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pyezvizapi.client import EzvizClient

ENV = Path("/opt/ezvizpoc/.env")
TOKEN = Path("/opt/ezvizpoc/token.json")
FFMPEG = Path("/opt/hikpoc/bin/ffmpeg")
SERIAL = sys.argv[1]
OUT = Path(sys.argv[2])


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def have_cache() -> bool:
    return OUT.is_file() and OUT.stat().st_size > 800


def scale_to(src: Path, dest: Path) -> None:
    tmp = dest.with_suffix(".tmp.jpg")
    subprocess.run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-vf",
            "scale=640:-2",
            "-q:v",
            "4",
            "-y",
            str(tmp),
        ],
        check=True,
    )
    tmp.replace(dest)


def main() -> None:
    env = load_env()
    tok = json.loads(TOKEN.read_text())
    client = EzvizClient(token=tok, account=env.get("EZVIZ_ACCOUNT"), password=env.get("EZVIZ_PASSWORD"))
    try:
        pic = client.capture_picture(SERIAL, 1)
        url = (pic.get("captureInfo") or {}).get("picUrl")
        if not url:
            raise RuntimeError("no snapshot url")
        resp = client._session.get(url, timeout=20)
        resp.raise_for_status()
        if len(resp.content) < 800 or resp.content[:2] != b"\xff\xd8":
            raise RuntimeError("snapshot is not a jpeg")
        raw = Path("/tmp") / f"ezviz_{SERIAL}.jpg"
        raw.write_bytes(resp.content)
        try:
            scale_to(raw, OUT)
        finally:
            try:
                raw.unlink()
            except OSError:
                pass
        web_name = OUT.name.replace("_640.jpg", ".jpg")
        web = Path("/var/www/sailingsa/stanford/thumbs") / web_name
        web.parent.mkdir(parents=True, exist_ok=True)
        web.write_bytes(OUT.read_bytes())
        print("snap", SERIAL, "ok", OUT.stat().st_size, file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print("snap", SERIAL, "reuse_cache" if have_cache() else "fail", type(exc).__name__, file=sys.stderr)
        if not have_cache():
            raise SystemExit(1)


if __name__ == "__main__":
    main()
