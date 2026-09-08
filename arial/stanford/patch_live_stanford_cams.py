#!/usr/bin/env python3
"""Patch Stanford go2rtc streams onto Bing EZVIZ exec. Default: yaml + start script only."""

import argparse
from pathlib import Path

HTML_SRC = Path(__file__).with_name("index.html")
HTML_DST = Path("/var/www/sailingsa/stanford/index.html")
BRIDGE_SRC = Path(__file__).with_name("bridge_ezviz_rtp.py")
BRIDGE_DST = Path("/opt/ezvizpoc/bridge_ezviz_rtp.py")
BING_SRC = Path(__file__).with_name("bridge_ezviz_bing.sh")
BING_DST = Path("/opt/ezvizpoc/bridge_ezviz_bing.sh")
SNAP_SRC = Path(__file__).with_name("bridge_ezviz_snap.py")
SNAP_DST = Path("/opt/ezvizpoc/bridge_ezviz_snap.py")
LIVE_SRC = Path(__file__).with_name("start_stanford_live.sh")
LIVE_DST = Path("/opt/ezvizpoc/start_stanford_live.sh")
BING_HTML_SRC = Path(__file__).resolve().parent.parent / "bing" / "index.html"
BING_HTML_DST = Path("/var/www/sailingsa/bing/index.html")
YAML = Path("/opt/hikpoc/go2rtc.yaml")
SNIP = Path(__file__).with_name("go2rtc-stanford.snippet.yaml")


def patch_yaml() -> None:
    if not YAML.is_file() or not SNIP.is_file():
        raise SystemExit("missing go2rtc.yaml or snippet")
    y = YAML.read_text(encoding="utf-8")
    extra = "\n".join(
        ln for ln in SNIP.read_text(encoding="utf-8").splitlines() if ln.startswith("  stanford_")
    )
    if not extra:
        raise SystemExit("snippet has no stanford_ stream lines")
    if "carport_test:" not in y:
        raise SystemExit("refusing to write yaml: carport_test gold line missing")
    if "bridge_ezviz.sh BA3858958" not in y:
        raise SystemExit("refusing to write yaml: Bing carport_test exec missing")
    if "garage:" not in y or "driveway:" not in y:
        raise SystemExit("refusing to write yaml: Voëlklip streams missing")
    lines = y.splitlines()
    kept = [ln for ln in lines if not ln.startswith("  stanford_")]
    y2 = "\n".join(kept)
    if not y2.endswith("\n"):
        y2 += "\n"
    YAML.write_text(y2 + extra + "\n", encoding="utf-8")
        print("wrote stanford streams (RTP HEVC + Bing 640p ffmpeg) to go2rtc.yaml")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="also write HTML/bridges (dangerous; default is yaml only)")
    args = ap.parse_args()
    if BRIDGE_SRC.is_file():
        BRIDGE_DST.write_text(BRIDGE_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        BRIDGE_DST.chmod(0o755)
        print("wrote", BRIDGE_DST)
    if LIVE_SRC.is_file():
        LIVE_DST.write_text(LIVE_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        LIVE_DST.chmod(0o755)
        print("wrote", LIVE_DST)
    if not args.all:
        patch_yaml()
        return
    if HTML_SRC.is_file() and HTML_DST.parent.is_dir():
        bak = HTML_DST.with_name("index.html.bak_stanfordcams_20260908")
        if HTML_DST.is_file() and not bak.is_file():
            bak.write_text(HTML_DST.read_text(encoding="utf-8"), encoding="utf-8")
        HTML_DST.write_text(HTML_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        print("wrote", HTML_DST)
    if BRIDGE_SRC.is_file():
        BRIDGE_DST.write_text(BRIDGE_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        BRIDGE_DST.chmod(0o755)
        print("wrote", BRIDGE_DST)
    if BING_SRC.is_file():
        BING_DST.write_text(BING_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        BING_DST.chmod(0o755)
        print("wrote", BING_DST)
    if SNAP_SRC.is_file():
        SNAP_DST.write_text(SNAP_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        SNAP_DST.chmod(0o755)
        print("wrote", SNAP_DST)
    if LIVE_SRC.is_file():
        LIVE_DST.write_text(LIVE_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        LIVE_DST.chmod(0o755)
        print("wrote", LIVE_DST)
    if BING_HTML_SRC.is_file() and BING_HTML_DST.parent.is_dir():
        bak = BING_HTML_DST.with_name("index.html.bak_ezvizoverlay_20260908")
        if BING_HTML_DST.is_file() and not bak.is_file():
            bak.write_text(BING_HTML_DST.read_text(encoding="utf-8"), encoding="utf-8")
        BING_HTML_DST.write_text(BING_HTML_SRC.read_text(encoding="utf-8"), encoding="utf-8")
        print("wrote", BING_HTML_DST)
    patch_yaml()


if __name__ == "__main__":
    main()
