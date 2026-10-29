"""Reserved slugs must never appear in a sitemap loc."""

RESERVED_PUBLIC_SLUGS = frozenset(
    {
        "unknown",
        "none",
        "na",
        "n-a",
        "tbc",
        "tba",
        "tbd",
        "unnamed",
        "anonymous",
        "null",
        "undefined",
    }
)


def _is_reserved_public_slug(slug: str) -> bool:
    return (slug or "").strip().lower() in RESERVED_PUBLIC_SLUGS


REGATTA_ALIAS_IDS = frozenset(
    {
        "2026-02-15-hyc-cape-classic",
        "2025-09-28-sa-sailing-national-championships-finn-class",
        "2025-12-31-dabchick-wc-regionals",
        "2025-03-16-nr-interschools",
        "2025-12-31-wc-extra-regionals",
    }
)


def _is_regatta_alias_id(regatta_id: str) -> bool:
    return (regatta_id or "").strip().lower() in REGATTA_ALIAS_IDS


def test_none_and_unknown_are_reserved():
    assert _is_reserved_public_slug("none")
    assert _is_reserved_public_slug("NONE")
    assert _is_reserved_public_slug("unknown")
    assert not _is_reserved_public_slug("fbyc")
    assert "none" in RESERVED_PUBLIC_SLUGS


def test_known_301_regatta_aliases_are_skipped():
    assert _is_regatta_alias_id("2026-02-15-hyc-cape-classic")
    assert _is_regatta_alias_id("2025-12-31-wc-extra-regionals")
    assert not _is_regatta_alias_id("2026-02-16-hyc-cape-classic")
    assert not _is_regatta_alias_id("2026-09-24-hmyc-dart-18-nationals")


if __name__ == "__main__":
    test_none_and_unknown_are_reserved()
    test_known_301_regatta_aliases_are_skipped()
    print("ok")
