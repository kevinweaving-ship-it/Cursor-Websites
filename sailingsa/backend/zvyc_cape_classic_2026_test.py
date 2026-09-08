from sailingsa.backend.zvyc_cape_classic_2026 import add_default_site_header

_FAKE = (
    "<!DOCTYPE html><html><head><title>x</title>"
    "<style>.header{display:grid}</style></head>"
    '<body><div class="regatta-page"><div class="regatta-header-wrap">'
    '<div class="header"><div class="regatta-name">KEEP</div></div></div></div></body></html>'
)


def test_adds_site_header_keeps_event_header():
    out = add_default_site_header(_FAKE)
    assert 'class="site-header"' in out
    assert "/css/main.css" in out
    assert 'class="regatta-name">KEEP' in out
    assert ".header{display:grid}" in out
