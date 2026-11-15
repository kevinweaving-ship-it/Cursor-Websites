#!/usr/bin/env python3
"""Classifier accept tests — no network, no GSC auth."""

from sailingsa.tools.gsc_daily.classify import OK, REAL, STALE, classify
from sailingsa.tools.gsc_daily.probe_live import url_pattern


def _p(**kw):
    base = {
        "url": "https://sailingsa.co.za/x",
        "status": 200,
        "first_status": 200,
        "redirects": False,
        "final_url": "https://sailingsa.co.za/x",
        "canonical": "",
        "noindex": False,
        "in_sitemap": False,
        "redirect_chain": [],
        "title": "",
    }
    base.update(kw)
    return base


def test_5xx_real_and_stale():
    assert classify("server_error_5xx", _p(status=502, first_status=502)) == REAL
    assert classify("server_error_5xx", _p(status=200, first_status=200)) == STALE


def test_404_entity_vs_garbage():
    assert (
        classify(
            "not_found_404",
            _p(
                url="https://sailingsa.co.za/regatta/missing-event",
                status=404,
                first_status=404,
                final_url="https://sailingsa.co.za/regatta/missing-event",
            ),
        )
        == REAL
    )
    assert (
        classify(
            "not_found_404",
            _p(
                url="https://sailingsa.co.za/wp-admin",
                status=404,
                first_status=404,
                final_url="https://sailingsa.co.za/wp-admin",
            ),
        )
        == OK
    )


def test_redirect_canonical_ok():
    assert (
        classify(
            "page_with_redirect",
            _p(
                url="https://sailingsa.co.za/sailor/1-old-name",
                first_status=301,
                status=200,
                redirects=True,
                final_url="https://sailingsa.co.za/sailor/1-new-name",
            ),
        )
        == OK
    )


def test_noindex_on_indexable():
    assert (
        classify(
            "excluded_noindex",
            _p(
                url="https://sailingsa.co.za/regatta/cape-classic-2026",
                noindex=True,
                in_sitemap=True,
            ),
        )
        == REAL
    )


def test_patterns():
    assert url_pattern("https://sailingsa.co.za/sailor/12-jane-doe") == "/sailor/{id}-{slug}"
    assert url_pattern("https://sailingsa.co.za/class/4-420") == "/class/{id}-{slug}"


if __name__ == "__main__":
    test_5xx_real_and_stale()
    test_404_entity_vs_garbage()
    test_redirect_canonical_ok()
    test_noindex_on_indexable()
    test_patterns()
    print("CLASSIFY_OK")
