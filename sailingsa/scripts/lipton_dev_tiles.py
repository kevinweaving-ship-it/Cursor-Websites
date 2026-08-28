#!/usr/bin/env python3
"""Lipton -dev satellite tile cache for Table Bay.

Tiles are stored on disk and served from this host. Missing tiles are fetched
from Esri World Imagery (or place labels) once, then reused. Bounded to the
Lipton racing area so this is not an open proxy.

CLI: python3 lipton_dev_tiles.py prefetch [--zmax 17]
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CACHE_ROOT = Path(os.environ.get("LIPTON_TILE_CACHE", "/var/www/sailingsa/tiles"))
# Harbour + all five race tracks, with room to zoom out.
LAT_MIN, LAT_MAX = -33.910, -33.848
LON_MIN, LON_MAX = 18.410, 18.500
Z_MIN, Z_MAX = 12, 19
SOURCES = {
    "sat": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "ref": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
}
UA = "SailingSA-LiptonDev/1.0 (https://sailingsa.co.za; tile cache for race playback)"


def _tile_x(lon: float, z: int) -> int:
    n = 2 ** z
    return int((lon + 180.0) / 360.0 * n)


def _tile_y(lat: float, z: int) -> int:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2 ** z
    r = math.radians(lat)
    return int((1.0 - math.log(math.tan(r) + 1.0 / math.cos(r)) / math.pi) / 2.0 * n)


def allowed(kind: str, z: int, y: int, x: int) -> bool:
    if kind not in SOURCES:
        return False
    if z < Z_MIN or z > Z_MAX:
        return False
    n = 2 ** z
    if x < 0 or y < 0 or x >= n or y >= n:
        return False
    x0 = _tile_x(LON_MIN, z)
    x1 = _tile_x(LON_MAX, z)
    y0 = _tile_y(LAT_MAX, z)
    y1 = _tile_y(LAT_MIN, z)
    if x < min(x0, x1) or x > max(x0, x1):
        return False
    if y < min(y0, y1) or y > max(y0, y1):
        return False
    return True


def cache_path(kind: str, z: int, y: int, x: int) -> Path:
    return CACHE_ROOT / kind / str(z) / str(y) / f"{x}.jpg"


def fetch_upstream(kind: str, z: int, y: int, x: int) -> bytes:
    url = SOURCES[kind].format(z=z, y=y, x=x)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=12) as resp:
        body = resp.read()
        if not body or len(body) < 32:
            raise RuntimeError("empty tile")
        return body


# 1x1 transparent PNG — used if Esri is down so Leaflet does not paint grey squares.
EMPTY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def get_tile(kind: str, z: int, y: int, x: int, save: bool = True) -> bytes:
    if not allowed(kind, z, y, x):
        raise ValueError("tile out of Lipton cache bounds")
    path = cache_path(kind, z, y, x)
    if path.is_file() and path.stat().st_size > 32:
        return path.read_bytes()
    last_err = None
    for _attempt in range(2):
        try:
            body = fetch_upstream(kind, z, y, x)
            if save:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(body)
                tmp.replace(path)
            return body
        except Exception as exc:
            last_err = exc
            time.sleep(0.15)
    raise RuntimeError(str(last_err) if last_err else "tile fetch failed")


def iter_bbox_tiles(z: int):
    x0, x1 = sorted((_tile_x(LON_MIN, z), _tile_x(LON_MAX, z)))
    y0, y1 = sorted((_tile_y(LAT_MAX, z), _tile_y(LAT_MIN, z)))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            yield y, x


def prefetch(kinds=None, zmin: int = 13, zmax: int = 17, pause: float = 0.03) -> int:
    kinds = list(kinds or ["sat"])
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    ok = 0
    skip = 0
    fail = 0
    for kind in kinds:
        for z in range(zmin, zmax + 1):
            tiles = list(iter_bbox_tiles(z))
            print(f"{kind} z{z} {len(tiles)} tiles", flush=True)
            for y, x in tiles:
                path = cache_path(kind, z, y, x)
                if path.is_file() and path.stat().st_size > 32:
                    skip += 1
                    continue
                try:
                    get_tile(kind, z, y, x, save=True)
                    ok += 1
                except Exception as exc:
                    fail += 1
                    print(f"FAIL {kind} {z}/{y}/{x}: {exc}", file=sys.stderr)
                if pause:
                    time.sleep(pause)
    print(f"prefetch done fetched={ok} cached={skip} fail={fail}", flush=True)
    return 0 if fail == 0 or ok + skip > 0 else 1


def register_lipton_tiles(app) -> None:
    from fastapi import HTTPException
    from fastapi.responses import Response

    if getattr(app.state, "lipton_tiles_registered", False):
        return

    @app.get("/api/lipton-tiles/{kind}/{z}/{y}/{x}")
    def lipton_tile(kind: str, z: int, y: int, x: int):
        kind = (kind or "").strip().lower()
        try:
            body = get_tile(kind, int(z), int(y), int(x), save=True)
        except ValueError:
            raise HTTPException(status_code=404, detail="out of bounds")
        except Exception:
            return Response(
                content=EMPTY_PNG,
                media_type="image/png",
                headers={"Cache-Control": "no-store"},
            )
        ctype = "image/png" if body[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
        return Response(
            content=body,
            media_type=ctype,
            headers={"Cache-Control": "public, max-age=604800, immutable"},
        )

    app.state.lipton_tiles_registered = True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Lipton -dev Table Bay tile cache")
    p.add_argument("cmd", nargs="?", default="prefetch", choices=["prefetch"])
    p.add_argument("--zmin", type=int, default=13)
    p.add_argument("--zmax", type=int, default=17)
    p.add_argument("--labels", action="store_true", help="also cache place-name tiles")
    p.add_argument("--pause", type=float, default=0.03)
    args = p.parse_args(argv)
    kinds = ["sat"]
    if args.labels:
        kinds.append("ref")
    return prefetch(kinds=kinds, zmin=args.zmin, zmax=args.zmax, pause=args.pause)


if __name__ == "__main__":
    raise SystemExit(main())
