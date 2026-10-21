import time

import site_watch as sw


def test_compose_olarm_offline_headline():
    text = sw.compose_olarm({"label": "Hansekop", "url": "https://sailingsa.co.za/arial/"}, "down", 1792552587)
    assert text.splitlines()[1] == "Olarm Offline"
    assert "Heartbeat fail" in text
    assert "https://sailingsa.co.za/arial/" in text


def test_compose_tuya_fail_headline():
    text = sw.compose_tuya({"label": "Hansekop"}, "down", 1791797832.324, "sharing link stale")
    assert text.splitlines()[1] == "Tuya reporting fail"
    assert "Last power reading" in text
    assert "sharing link stale" in text


def test_olarm_offline_from_panel():
    assert sw.olarm_offline({"device": {"deviceStatus": "offline"}}) is True
    assert sw.olarm_offline({"device": {"deviceStatus": "online"}}) is False
    assert sw.olarm_offline(None) is True


def test_tuya_last_reading_prefers_last_reading_ts():
    probe = {
        "lastReading": {"ts": 1791797832.324},
        "readingTs": 1,
        "sharing": {"meterLastReadingAt": 2},
    }
    assert sw.tuya_last_reading(probe) == 1791797832.324


def test_tuya_fail_stale_and_fresh():
    now = 1792560000.0
    stale = {"deviceOk": False, "tokenOk": False, "readingTs": now - 400, "tuyaMsg": "sharing link stale"}
    fail, detail = sw.tuya_fail(stale, now, stale_s=180)
    assert fail is True
    assert "stale" in detail
    fresh = {"deviceOk": True, "tokenOk": True, "readingTs": now - 20}
    fail, detail = sw.tuya_fail(fresh, now, stale_s=180)
    assert fail is False
    assert detail == ""


def test_edge_confirms_then_nags():
    st = {}
    now = time.time()
    assert sw._edge(st, True, now) is None
    assert sw._edge(st, True, now) is None
    assert sw._edge(st, True, now) == "down"
    sw.mark_sent(st, now)
    assert sw._edge(st, True, now + 10) is None
    assert sw._edge(st, True, now + sw.NAG_S + 1) == "nag"
    assert sw._edge(st, False, now + sw.NAG_S + 2) == "up"
    assert sw._edge(st, False, now + sw.NAG_S + 3) is None
