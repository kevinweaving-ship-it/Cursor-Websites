"""PageSpeed helper summarises PSI JSON and does not rewrite public URLs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sailingsa.tools.gsc_daily.pagespeed import HOME, LANDING_PNGS, render_lines, summarise_psi


def test_same_public_url():
    assert HOME == "https://sailingsa.co.za/"
    assert all(name.endswith(".png") for name in LANDING_PNGS)
    assert "temp-landing-feedback-hero.png" in LANDING_PNGS


def test_summarise_scores():
    raw = {
        "lighthouseResult": {
            "fetchTime": "2026-10-29T07:00:00.000Z",
            "categories": {
                "performance": {"score": 0.58},
                "accessibility": {"score": 0.92},
                "best-practices": {"score": 0.96},
                "seo": {"score": 1.0},
            },
            "audits": {
                "first-contentful-paint": {"numericValue": 1700},
                "largest-contentful-paint": {
                    "numericValue": 17300,
                    "details": {"items": [{"node": {"snippet": "<img>"}}]},
                },
                "total-blocking-time": {"numericValue": 0},
                "cumulative-layout-shift": {"numericValue": 0.162},
                "speed-index": {"numericValue": 11300},
            },
        }
    }
    row = summarise_psi(raw, "mobile")
    assert row["performance"] == 58
    assert row["seo"] == 100
    assert row["lcp_s"] == 17.3
    assert row["fcp_s"] == 1.7
    text = "\n".join(render_lines({"scores": {"mobile": row}, "autofix": {}}))
    assert "do not paste PSI" in text
    assert "mobile: perf 58" in text


if __name__ == "__main__":
    test_same_public_url()
    test_summarise_scores()
    print("ok")
