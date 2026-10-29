"""GSC sitemap 'submitted' must not double-count the index plus its children."""


def summarize(sitemaps):
    submitted = 0
    index_submitted = 0
    for sm in sitemaps:
        for c in sm.get("contents") or []:
            n = int(c.get("submitted") or 0)
            submitted += n
            if sm.get("isSitemapsIndex") or str(sm.get("path") or "").endswith("/sitemap.xml"):
                if c.get("type") == "web":
                    index_submitted = max(index_submitted, n)
    if index_submitted:
        submitted = index_submitted
    return submitted


def test_index_plus_children_is_not_doubled():
    rows = [
        {"path": "https://sailingsa.co.za/sitemap-sailors.xml", "contents": [{"type": "web", "submitted": "2609"}]},
        {"path": "https://sailingsa.co.za/sitemap.xml", "isSitemapsIndex": True,
         "contents": [{"type": "web", "submitted": "3525"}, {"type": "news", "submitted": "1"}]},
    ]
    assert summarize(rows) == 3525


if __name__ == "__main__":
    test_index_plus_children_is_not_doubled()
    print("ok")
