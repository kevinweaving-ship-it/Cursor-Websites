"""Sitemap sailors must be result-holders, never the SAS catalogue."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    ROOT / "utils" / "sitemap_builder.py",
    ROOT / "sailingsa" / "utils" / "sitemap_builder.py",
)


def _fetch_sailors_src(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.index("def _fetch_sailors")
    end = text.index("\ndef ", start + 1)
    return text[start:end]


def test_fetch_sailors_requires_event_result_not_catalogue():
    for path in FILES:
        src = _fetch_sailors_src(path)
        assert "FROM results" in src, path
        assert "sas_id_personal" in src, path
        assert "has_event_result" in src or "EXISTS" in src, path
        assert "raced IS TRUE" not in src, path


if __name__ == "__main__":
    test_fetch_sailors_requires_event_result_not_catalogue()
    print("ok")
