#!/usr/bin/env python3
"""Surgical live api.py patches: Hide red/bold, staff rows, last cam still, wa10/mmr124."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

OLD_HIDE = (
    ".mm-lipton-reels-hide{pointer-events:auto;min-height:44px;min-width:44px;margin:0;"
    "padding:0 6px;border:0;background:none;color:#64748b;font-size:0.68rem;font-weight:500;"
    "letter-spacing:0.04em;line-height:1;cursor:pointer;-webkit-appearance:none;appearance:none}"
)
NEW_HIDE = (
    ".mm-lipton-reels-hide{pointer-events:auto;min-height:44px;min-width:44px;margin:0;"
    "padding:0 6px;border:0;background:none;color:#dc2626;font-size:0.95rem;font-weight:800;"
    "letter-spacing:0.02em;line-height:1;cursor:pointer;-webkit-appearance:none;appearance:none}"
)

OLD_CLOSE = (
    ".ssa-wa-gate-actions button{display:flex;align-items:center;justify-content:center;"
    "min-height:44px;width:100%;padding:10px 12px;border-radius:6px;"
    "font:700 14px/1.2 Arial,Helvetica,sans-serif;background:#fff;color:#1a2750;"
    "border:1px solid #1a2750;cursor:pointer;box-sizing:border-box;}"
)
NEW_CLOSE = (
    ".ssa-wa-gate-actions button[data-wa-gate-close]{display:flex;align-items:center;"
    "justify-content:center;min-height:44px;width:100%;padding:10px 12px;border-radius:6px;"
    "font:700 14px/1.2 Arial,Helvetica,sans-serif;background:#fff;color:#1a2750;"
    "border:1px solid #1a2750;cursor:pointer;box-sizing:border-box;}"
)

NEW_GRAB = '''def _zvyc_live_cam_frame_jpeg(explicit_token: str = "", fresh: bool = False) -> bytes:
    """Grab one JPEG after ~2s of play. Persist last good still; never the blue 4040 card."""
    last_path = "/var/www/sailingsa/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg"
    tmp_path = last_path + ".tmp"

    def _read_last() -> bytes:
        try:
            with open(last_path, "rb") as f:
                disk = f.read()
            if disk[:2] == b"\\xff\\xd8":
                return disk
        except Exception:
            pass
        return b""

    now = time.time()
    if not fresh:
        with _ZVYC_GRAB_LOCK:
            cached = _ZVYC_GRAB_MEM.get("jpg") or b""
            if cached[:2] == b"\\xff\\xd8" and now - float(_ZVYC_GRAB_MEM.get("t") or 0) < _ZVYC_GRAB_TTL_SEC:
                return cached
    url = _zvyc_live_cam_stream_url(explicit_token)
    if url:
        ua = _ZVYC_CAM_FETCH_HEADERS.get("User-Agent") or "Mozilla/5.0"
        headers = f"Referer: {_ZVYC_LIVE_CAM_PAGE}\\r\\nUser-Agent: {ua}\\r\\n"
        cmd = [
            _ZVYC_FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-headers",
            headers,
            "-i",
            url,
            "-ss",
            "2",
            "-frames:v",
            "1",
            "-q:v",
            "5",
            "-f",
            "image2",
            "pipe:1",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=20)
            jpg = proc.stdout or b""
            if proc.returncode == 0 and jpg[:2] == b"\\xff\\xd8":
                try:
                    os.makedirs(os.path.dirname(last_path), exist_ok=True)
                    with open(tmp_path, "wb") as f:
                        f.write(jpg)
                    os.replace(tmp_path, last_path)
                except Exception as e:
                    print(f"[zvyc_live_cam] save still failed: {e}", flush=True)
                with _ZVYC_GRAB_LOCK:
                    _ZVYC_GRAB_MEM["t"] = time.time()
                    _ZVYC_GRAB_MEM["jpg"] = jpg
                return jpg
            print(f"[zvyc_live_cam] grab failed rc={proc.returncode}", flush=True)
        except Exception as e:
            print(f"[zvyc_live_cam] grab failed: {e}", flush=True)
    disk = _read_last()
    if disk:
        with _ZVYC_GRAB_LOCK:
            _ZVYC_GRAB_MEM["t"] = time.time()
            _ZVYC_GRAB_MEM["jpg"] = disk
        return disk
    with _ZVYC_GRAB_LOCK:
        cached = _ZVYC_GRAB_MEM.get("jpg") or b""
        if cached[:2] == b"\\xff\\xd8":
            return cached
    return b""


'''


def apply(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    orig = t
    n = 0

    c = t.count(OLD_HIDE)
    if c != 1:
        raise SystemExit(f"{path}: Hide CSS count {c}")
    t = t.replace(OLD_HIDE, NEW_HIDE, 1)
    n += 1
    print("Hide CSS -> red bold")

    staff = [
        (
            '("Jody Cilliers", "Finish recorder", "Bridge", "Sat/Sun", "")',
            '("Jody Cilliers", "Finish recorder", "Bridge", "", "")',
            "Jody days",
        ),
        (
            '("Anna Keytel", "Regatta Secretary", "Admin", "Sat/Sun", "3692")',
            '("Anna Keytel", "Regatta Secretary", "Boat 4", "Sat/Sun", "3692")',
            "Anna Boat 4",
        ),
        (
            '("Jemayne Wolmarans", "Staff support / bar", "Admin", "Sat/Sun", "1521")',
            '("Jemayne Wolmarans", "Staff support / bar", "Support", "Sat/Sun", "1521")',
            "Jemayne Support",
        ),
    ]
    for old, new, label in staff:
        c = t.count(old)
        if c != 1:
            raise SystemExit(f"{path}: {label} count {c}")
        t = t.replace(old, new, 1)
        n += 1
        print(label)

    sky = "https://www.skylinewebcams.com/temp/4040.jpg"
    still = "/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg"
    c = t.count(sky)
    if c < 1:
        raise SystemExit(f"{path}: 4040.jpg count {c}")
    t = t.replace(sky, still)
    n += c
    print(f"4040.jpg -> last still ({c})")

    start = "def _zvyc_live_cam_frame_jpeg(explicit_token: str = \"\", fresh: bool = False) -> bytes:\n"
    end = "def _cape_classic_has_real_reels"
    i0 = t.find(start)
    i1 = t.find(end)
    if i0 < 0 or i1 < 0 or i1 <= i0:
        raise SystemExit(f"{path}: grab markers {i0} {i1}")
    t = t[:i0] + NEW_GRAB + t[i1:]
    n += 1
    print("replaced _zvyc_live_cam_frame_jpeg")

    if t.count("regatta-slot-card.js?v=20260912wa9") != 1:
        raise SystemExit(f"{path}: wa9 count {t.count('regatta-slot-card.js?v=20260912wa9')}")
    t = t.replace("regatta-slot-card.js?v=20260912wa9", "regatta-slot-card.js?v=20260912wa10", 1)
    n += 1
    print("wa10")

    if t.count("mm-lipton-reels-card.js?v=mmr123") != 1:
        raise SystemExit(f"{path}: mmr123 count {t.count('mm-lipton-reels-card.js?v=mmr123')}")
    t = t.replace("mm-lipton-reels-card.js?v=mmr123", "mm-lipton-reels-card.js?v=mmr124", 1)
    n += 1
    print("mmr124")

    c = t.count(OLD_CLOSE)
    if c != 1:
        raise SystemExit(f"{path}: close CSS count {c}")
    t = t.replace(OLD_CLOSE, NEW_CLOSE, 1)
    n += 1
    print("close CSS scoped")

    if "mm-lipton-reels-card.js?v=mmr102" not in t:
        raise SystemExit(f"{path}: Lipton mmr102 missing after patch")
    if sky in t:
        raise SystemExit(f"{path}: 4040.jpg still present")
    if t == orig:
        raise SystemExit("NO CHANGES")
    path.write_text(t, encoding="utf-8")
    print("wrote", path, "replacements", n, "bytes", len(t))


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
