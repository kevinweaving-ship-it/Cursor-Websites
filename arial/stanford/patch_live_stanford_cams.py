#!/usr/bin/env python3
"""Deploy Stanford camera card + additive go2rtc streams. Stanford only."""

from pathlib import Path

HTML_SRC = Path(__file__).with_name("index.html")
HTML_DST = Path("/var/www/sailingsa/stanford/index.html")
BRIDGE_SRC = Path(__file__).with_name("bridge_ezviz_rtp.py")
BRIDGE_DST = Path("/opt/ezvizpoc/bridge_ezviz_rtp.py")
YAML = Path("/opt/hikpoc/go2rtc.yaml")
SNIP = Path(__file__).with_name("go2rtc-stanford.snippet.yaml")


def main() -> None:
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
    if YAML.is_file() and SNIP.is_file():
        y = YAML.read_text(encoding="utf-8")
        if "bin: /opt/hikpoc/bin/ffmpeg" not in y:
            y = y.replace("log:\n", "ffmpeg:\n  bin: /opt/hikpoc/bin/ffmpeg\nlog:\n", 1)
            YAML.write_text(y, encoding="utf-8")
            y = YAML.read_text(encoding="utf-8")
            print("set go2rtc ffmpeg.bin to hikpoc ffmpeg")
        if "stanford_eb5:" not in y:
            extra = "\n".join(
                ln for ln in SNIP.read_text(encoding="utf-8").splitlines() if ln.startswith("  stanford_")
            )
            if not y.endswith("\n"):
                y += "\n"
            YAML.write_text(y + extra + "\n", encoding="utf-8")
            print("appended stanford streams to go2rtc.yaml")
        else:
            print("go2rtc.yaml already has stanford streams")


if __name__ == "__main__":
    main()
