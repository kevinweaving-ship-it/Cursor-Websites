from sailingsa.backend.zvyc_cape_classic_2026 import zvyc_cape_classic_2026_body


def test_event_header_only_no_results_table():
    body = zvyc_cape_classic_2026_body()
    assert "ZVYC Cape Classic" in body
    assert "/club/zvyc" in body
    assert "<table" not in body
    assert "regatta-page" not in body
