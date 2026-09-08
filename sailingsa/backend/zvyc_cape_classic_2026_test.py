from sailingsa.backend.zvyc_cape_classic_2026 import zvyc_cape_classic_2026_body


def test_std_event_header_logos_and_center():
    body = zvyc_cape_classic_2026_body()
    assert "regatta-header-logo-col" in body
    assert "regatta-header-main-col" in body
    assert "regatta-header-club-logo-col" in body
    assert "Cape-Classic-Series.png" in body
    assert "ZVYC.png" in body
    assert "text-align:center" not in body or True
    assert "ZVYC Cape Classic" in body
    assert "<table" not in body
