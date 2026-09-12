#!/usr/bin/env python3
"""Cape Classic: pin ZVYC live cam last in the MM rail after sortVideos."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/mm-lipton-reels-card.js")

JS_REPLACEMENTS = [
    (
        '''  function sortVideos(videos) {
    return (videos || []).slice().sort(function (a, b) {
      return String(b.started_at || '').localeCompare(String(a.started_at || ''));
    });
  }''',
        '''  function sortVideos(videos) {
    var list = (videos || []).slice().sort(function (a, b) {
      return String(b.started_at || '').localeCompare(String(a.started_at || ''));
    });
    if (!isCapeClassic()) return list;
    var mm = [];
    var cam = [];
    var i;
    for (i = 0; i < list.length; i++) {
      if (isWebcam(list[i])) cam.push(list[i]);
      else mm.push(list[i]);
    }
    return mm.concat(cam);
  }''',
    ),
]

API_REPLACEMENTS = [
    (
        "mm-lipton-reels-card.js?v=mmr120",
        "mm-lipton-reels-card.js?v=mmr121",
    ),
]


def apply(path: Path, reps: list) -> None:
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(reps, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    api = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    js = Path(sys.argv[2]) if len(sys.argv) > 2 else JS
    apply(js, JS_REPLACEMENTS)
    apply(api, API_REPLACEMENTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
