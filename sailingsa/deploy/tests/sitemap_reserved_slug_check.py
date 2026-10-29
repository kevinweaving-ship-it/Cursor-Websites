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


def test_none_and_unknown_are_reserved():
    assert _is_reserved_public_slug("none")
    assert _is_reserved_public_slug("NONE")
    assert _is_reserved_public_slug("unknown")
    assert not _is_reserved_public_slug("fbyc")
    assert "none" in RESERVED_PUBLIC_SLUGS


if __name__ == "__main__":
    test_none_and_unknown_are_reserved()
    print("ok")
