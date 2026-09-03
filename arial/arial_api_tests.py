"""Tests for Arial Olarm enrich + local profile auth (no live Olarm required)."""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import arial_api

SAMPLE = {
    "deviceId": "d6f25654-5fe8-4a85-a7ba-f8ff1449144a",
    "deviceName": "Home - Voelklip",
    "deviceStatus": "online",
    "deviceState": {
        "areas": ["notready", "disarm"],
        "zones": ["c", "a", "c", "c", "c", "c", "c", "c", "a"],
        "powerAC": "ok",
        "powerBattery": "ok",
    },
    "deviceProfile": {
        "areasLimit": 2,
        "areasLabels": ["Main House", "Garage"],
        "zonesLimit": 16,
        "zonesLabels": [
            "Garage PIR",
            "Main Bedroom PIR",
            "Office  Stairs PIR",
            "Lounge  Stairs PIR",
            "Zone 5",
            "",
            "",
            "",
            "Front Door Mag",
        ],
        "zonesTypes": [20, 20, 20, 20, 0, 0, 0, 0, 10],
    },
}


def test_enrich_device_areas_and_named_zones():
    out = arial_api.enrich_device(SAMPLE)
    assert len(out["arialAreas"]) == 2
    assert out["arialAreas"][0]["label"] == "Main House"
    assert out["arialAreas"][0]["state"] == "notready"
    assert out["arialAreas"][1]["label"] == "Garage"
    zones = {z["num"]: z for z in out["arialZones"]}
    assert zones[1]["typeLabel"] == "Indoor PIR"
    assert zones[1]["stateLabel"] == "Closed"
    assert zones[2]["stateLabel"] == "Active"
    assert zones[9]["typeLabel"] == "Door"
    assert 5 in zones  # labelled "Zone 5"
    assert 6 not in zones  # empty label skipped
    assert out["arialPower"]["acOk"] is True
    assert out["arialPower"]["batteryOk"] is True


def test_olarm_power_fault_and_event_tabs():
    fail = json.loads(json.dumps(SAMPLE))
    fail["deviceState"]["powerAC"] = "fail"
    fail["deviceState"]["powerBattery"] = "low"
    p = arial_api.enrich_device(fail)["arialPower"]
    assert p["acOk"] is False
    assert p["batteryOk"] is False
    device = arial_api.enrich_device(SAMPLE)
    zone = arial_api.format_olarm_event(
        {
            "eventAction": "zone",
            "eventState": "active",
            "eventNum": 1,
            "eventMsg": "ACTIVE - Zone 1 - Garage PIR",
            "eventTime": 1700000000000,
            "userFullname": "",
        },
        device,
    )
    assert zone["tab"] == "zones"
    assert zone["title"] == "Garage PIR"
    assert "ACTIVE" in zone["activity"]
    assert arial_api.classify_olarm_event(
        {"eventAction": "area", "eventState": "disarm", "eventMsg": "DISARMED - Area 1 - Facility Building"}
    ) == "areas"
    assert arial_api.classify_olarm_event(
        {"eventAction": "zone_alarm", "eventState": "alarm", "eventMsg": "ZONE 1 IN ALARM - Zone 1 - Front Door"}
    ) == "zones"
    assert arial_api.classify_olarm_event(
        {"eventAction": "power", "eventState": "fail", "eventMsg": "POWER FAILURE"}
    ) == "power"
    assert arial_api.is_noise_olarm_event(
        {"eventAction": "zones_idle", "eventState": "alert", "eventMsg": "System Idle for 60 minutes"}
    )
    assert arial_api.is_noise_olarm_event(
        {"eventAction": "device", "eventState": "online", "eventMsg": "Olarm Device ONLINE"}
    )
    assert not arial_api.is_noise_olarm_event(
        {"eventAction": "zone_alarm", "eventState": "alarm", "eventMsg": "ZONE 1 IN ALARM - Zone 1 - Front Door"}
    )


def test_activity_card_markup_and_zone_labels():
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert 'out.push("Zone " + n + " Open")' not in js
    assert "function panelIssues(" in js
    assert 'out.push("Power Failure")' in js
    assert 'out.push("Low Battery")' in js
    assert 'data-tab="all"' in html
    assert 'data-tab="zones"' in html
    assert 'data-tab="areas"' in html
    assert 'data-tab="alarms"' not in html
    assert 'data-tab="power"' in html
    assert 'id="activity-more"' in html
    assert 'class="activity-list"' in html
    assert "ACTIVITY_PREVIEW = 4" in js
    assert "/api/arial/activity" in js
    assert "color: #ffe14d" in css
    assert "activity-mark" in css
    assert "max-width: 377px;" in css.split(".arial-below {", 1)[1].split("}", 1)[0]
    assert 'class="container arial-below" hidden' in html
    assert "below.hidden = !on" in js
    assert "if (!isLoggedIn()) return;" in js
    assert "white-space: nowrap;" in css.split(".activity-text {", 1)[1].split("}", 1)[0]
    assert "border: 1.6px solid #6a7378;" in css.split(".arial-below .card {", 1)[1].split("}", 1)[0]
    assert 'id="arial-breaker"' in html
    assert "Hansekop Main Breaker" in html
    assert 'class="breaker-dials"' in html
    assert 'id="breaker-spark"' not in html  # sparkline removed; day chart is the history
    assert 'class="breaker-info"' in html
    assert 'id="breaker-hist-range"' in html
    assert 'id="breaker-w-now"' in html
    assert 'breaker-dial-power' in html
    assert 'id="breaker-detail"' not in html
    assert 'id="breaker-chart-w"' in html and html.count('class="breaker-echart"') == 3
    assert '/arial/vendor/echarts-arial.min.js' in html
    assert "function breakerGaugeOption" in js and "valueAnimation: true" in js
    assert "breaker-spark-fill" not in html
    assert "function loadBreaker" in js
    assert "function setBreakerGauge" in js
    assert '"info info w"' in css
    assert "arialBreaker.hansekop" in js
    assert "/api/arial/tuya/probe?device_id=bf90676b1341ecb34dse39" in js
    assert "loadBreaker();" in js
    assert ".breaker-dials" in css
    assert "grid-template-columns: 0.92fr 0.92fr 1.22fr;" in css
    assert ".breaker-echart" in css
    assert ".breaker-detail" not in css
    assert ".arial-below .card + .card" in css
    assert "#arial-activity,\n#arial-breaker" in css
    assert "align-items: stretch;" in css.split(".arial-below:not([hidden]) {", 1)[1].split("}", 1)[0]


def test_activity_route_uses_zone_labels(monkeypatch):
    async def fake_request(method, path, **kwargs):
        if str(path).endswith("/events"):
            return {
                "data": [
                    {
                        "eventAction": "zone",
                        "eventState": "closed",
                        "eventNum": 6,
                        "eventMsg": "CLOSED - Zone 6 - Cabinet Front",
                        "eventTime": 1700000000000,
                        "userFullname": "",
                    }
                ]
            }
        return SAMPLE

    monkeypatch.setattr(arial_api, "_olarm_request", fake_request)
    arial_api._activity_cache["data"] = None
    arial_api._activity_cache["at"] = 0.0
    app = FastAPI()
    app.include_router(arial_api.router)
    client = TestClient(app)
    r = client.get("/api/arial/activity")
    assert r.status_code == 200, r.text
    row = r.json()["events"][0]
    assert row["tab"] == "zones"
    assert row["title"] == "Cabinet Front"
    assert "OPEN" not in row["activity"]


def test_countdown_from_numeric_detail():
    d = {
        "deviceState": {"areas": ["countdown"], "areasDetail": ["47"]},
        "deviceProfile": {"areasLimit": 1, "areasLabels": ["House"], "zonesLimit": 0},
    }
    out = arial_api.enrich_device(d)
    assert out["arialCountdown"] == 47
    assert out["arialAreas"][0]["countdown"] == 47
    assert out["arialExitDelay"] == 60


def test_countdown_from_detail_object():
    d = {
        "deviceState": {"areas": ["countdown"], "areasDetail": [{"time": 12}]},
        "deviceProfile": {"areasLimit": 1, "areasLabels": ["House"], "zonesLimit": 0},
    }
    assert arial_api.enrich_device(d)["arialCountdown"] == 12


def test_countdown_ignores_zone_names_when_armed():
    d = {
        "deviceState": {"areas": ["arm"], "areasDetail": ["Zone 12 PIR"]},
        "deviceProfile": {"areasLimit": 1, "areasLabels": ["House"], "zonesLimit": 0},
    }
    assert arial_api.enrich_device(d)["arialCountdown"] is None


def test_profile_exit_delay():
    d = {
        "deviceState": {"areas": ["disarm"], "areasDetail": [""]},
        "deviceProfile": {
            "areasLimit": 1,
            "areasLabels": ["House"],
            "zonesLimit": 0,
            "exitDelay": 30,
        },
    }
    assert arial_api.enrich_device(d)["arialExitDelay"] == 30


def test_profile_exit_delay_ten_is_unset():
    d = {
        "deviceState": {"areas": ["disarm"], "areasDetail": [""]},
        "deviceProfile": {
            "areasLimit": 1,
            "areasLabels": ["House"],
            "zonesLimit": 0,
            "exitDelay": 10,
        },
    }
    assert arial_api.enrich_device(d)["arialExitDelay"] == 60


def test_arm_disarm_pending_and_thirty_second_exit():
    root = Path(__file__).resolve().parent
    js = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert "var EXIT_DEFAULT = 60;" in js
    assert "var EXIT_SHOW_FROM = 20;" in js
    assert "var EXIT_FAST_FROM = 7;" in js
    assert "n > 10 && n <= 180" in js
    assert "var disarmPending = false;" in js
    assert "function showSystemDisarmed()" in js
    assert 'setLcdStatus("System Disarmed", "");' in js
    assert "disarmPending = true;" in js
    assert "startLocalExit(exitDelaySecs(window.arialDevice));" in js
    assert "if (apiCd > 0) syncLocalExitFromApi(apiCd)" in js
    assert "if (apiCd > 0 && !armPending)" not in js
    assert "if (armPending && local > 0) return local;" not in js
    assert "var exitCountStarted = false;" in js
    assert "var exitClockFromApi = false;" in js
    assert "function settleArm()" in js
    assert "function localExitExpired()" in js
    assert "if (localExitExpired()) return;" in js
    assert "startOlarmLive();" in js
    assert "function startOlarmLive()" in js
    assert "function kickExitAudio()" in js
    assert "pageshow" in js
    assert "visibilitychange" in js
    assert "function playExitChirp(fast)" in js
    assert "startExitBeeps._on && !exitBeepTimer" in js
    assert "if (left > 20)" in js
    assert "if (left > 7)" in js
    assert "tone(1600, 0.14, 0.55)" in js
    assert "n <= 7" in js
    assert "disarmNeedsStatus" in js
    assert "hold-disarmed" in js
    assert "login-error" in js
    assert "function rejectGong()" in js
    assert 'setWelcome("Login", 2200)' not in js
    assert 'setLcdStatus(main, "Login")' in js
    assert ".lcd.login-error #lcd-welcome" in css
    assert 'setLcdStatus("System Armed", "Login")' not in js
    assert 'setLcdStatus("Login", "");' not in js
    assert "function rejectNeedLogin()" in js
    assert "if (disarmPending) return false;" in js
    assert "btn.setAttribute(\"data-armed\"" in js
    assert "setInterval(syncArmToggle, 400)" in js
    assert "loginErrorUntil" in js
    assert ".lcd.login-error #lcd-status-issue::before" in css
    assert "function startExitBeeps()" in js
    assert "exitIntroUntil" in js
    assert "storeSet(\"arialExitUntil\"" in js
    assert "localStorage.setItem(k, v)" in js
    assert "startExitBeeps._nextFast = now + 500" in js
    assert "playOsc(1000, 2.0, 0.72, true)" in js
    assert "longArmedBeep();" in js.split("function showArmed()", 1)[1].split("function showArming", 1)[0]
    assert "Date.now() - start + 333 <= 2500" in js
    assert "setTimeout(ping, 333)" in js
    assert "if (key === \"TOGGLE\" && isArmed && isLoggedIn())" in js
    assert "else if (key === \"TOGGLE\") {" in js
    assert "doArm();" in js
    assert "selectSite(\"tuys\")" not in js
    assert "key === \"ARM\") {\n            doArm()" not in js
    assert "sendLiveAction(\"area-stay\")" not in js
    assert "disarmBeep();" in js


def test_panel_cache_ttl(monkeypatch):
    arial_api._cached_panel(clear=True)
    fake = {"deviceName": "HANSEKOP"}
    now = {"t": 1000.0}
    monkeypatch.setattr(arial_api.time, "time", lambda: now["t"])
    arial_api._cached_panel(fake)
    assert arial_api._cached_panel() is fake
    now["t"] = 1001.0
    assert arial_api._cached_panel() is fake
    now["t"] = 1006.0
    assert arial_api._cached_panel() is None
    arial_api._cached_panel(fake)
    arial_api._cached_panel(clear=True)
    assert arial_api._cached_panel() is None


def test_welcome_credits_roll_and_fade():
    root = Path(__file__).resolve().parent
    css = (root / "arial.css").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    assert "playWelcomeCredits" in js
    assert 'el.textContent = "WELCOME"' in js
    assert "text-transform: uppercase;" in css.split("#lcd-welcome.credits {", 1)[1].split("}", 1)[0]
    assert "playWelcomeCredits();" in js
    assert "playWelcomeCredits(user.from" not in js
    assert "rollThenFade" not in js
    assert "--welcome-x" in js
    credits = css.split("#lcd-welcome.credits {", 1)[1].split("}", 1)[0]
    assert "left: 2px;" in credits
    assert "bottom: 0;" in credits
    assert "font-size: 32px;" in credits
    assert "align-self: flex-end;" in css.split("#lcd-welcome {", 1)[1].split("}", 1)[0]
    assert "welcomeAcross" in css
    assert "welcomeBackLeft" in css
    assert "translateX(var(--welcome-x, 0px))" in css
    assert "logoRollIn" in css
    assert "inset(0 0 0 100%)" in css
    assert "}, 220)" in js
    assert "credits-playing" in js
    assert "hero-credits" in js
    assert "hero-credits" in css
    assert ", 500)" in js
    assert "logo-in" in js


def test_lcd_site_date_time_stack_right():
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert 'id="lcd-site"' in html
    assert 'id="lcd-date"' in html
    assert 'id="lcd-time"' in html
    head = css.split(".lcd-head {", 1)[1].split("}", 1)[0]
    assert "flex-direction: column;" in head
    assert "align-items: flex-end;" in head
    assert "#lcd-site {\n    font-size: 13.75px;" in css
    assert "object-position: right bottom;" in css
    assert "position: absolute;" in css.split(".lcd-mid {", 1)[1].split("}", 1)[0]
    assert html.split('id="lcd-time"', 1)[1].split('id="lcd-welcome"', 1)[0].count('id="lcd-user-logo"') == 1
    logo = css.split("#lcd-user-logo {", 1)[1].split("}", 1)[0]
    assert "max-width: 52%;" not in logo
    assert "position: absolute;" in logo
    assert "top: 52%;" in logo
    assert "height: 44%;" in logo
    assert "max-width: 40%;" in logo
    assert "object-position: right bottom;" in logo


def _reset_keypad_log(monkeypatch, tmp_path):
    monkeypatch.setenv("ARIAL_KEYPAD_LOG", str(tmp_path / "arial_keypad_log.json"))
    arial_api._last_keypad = None
    arial_api._keypad_log = []
    arial_api._keypad_log_mtime = -1.0
    path = tmp_path / "arial_keypad_log.json"
    if path.exists():
        path.unlink()


def test_area_arm_uses_pingoa_not_olarm_user(tmp_path, monkeypatch):
    _reset_keypad_log(monkeypatch, tmp_path)
    actor = arial_api._remember_keypad("7302", "area-arm")
    assert actor["from"] == "Pingoa"
    device = {"arialActor": actor, "arialAreas": [{"num": 1, "label": "Facility Building"}]}
    row = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "arm",
            "eventNum": 1,
            "eventMsg": "ARMED - Area 1 - Facility Building",
            "eventTime": int(actor["at"] * 1000) + 30_000,
            "userFullname": "Kevin",
        },
        device,
    )
    assert row["actor"] == "Pingoa"
    assert "Pingoa" in row["activity"]
    assert "Remote" in row["activity"]
    assert "Kevin" not in row["activity"]
    assert "ALARM SYSTEM" not in row["activity"]
    countdown = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "countdown",
            "eventNum": 1,
            "eventMsg": "COUNTDOWN - Area 1 - Facility Building",
            "eventTime": int(actor["at"] * 1000) + 2_000,
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert countdown["actor"] == "Pingoa"
    _reset_keypad_log(monkeypatch, tmp_path)
    amoroc = arial_api._remember_keypad("7102", "area-disarm")
    assert amoroc["from"] == "Amoroc"
    disarmed = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "disarm",
            "eventNum": 1,
            "eventMsg": "DISARMED - Area 1 - Facility Building",
            "eventTime": int(amoroc["at"] * 1000) + 5_000,
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert disarmed["actor"] == "Amoroc"
    assert "Kevin" not in disarmed["activity"]
    _reset_keypad_log(monkeypatch, tmp_path)
    mapped = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "arm",
            "eventNum": 1,
            "eventMsg": "ARMED - Area 1 - Facility Building",
            "eventTime": int(time.time() * 1000),
            "userFullname": "Marc",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert mapped["actor"] == "Pingoa"
    assert "Marc" not in mapped["activity"]
    stray = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "arm",
            "eventNum": 1,
            "eventMsg": "ARMED - Area 1 - Facility Building",
            "eventTime": int(time.time() * 1000),
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert stray["actor"] == ""
    assert "Kevin" not in stray["activity"]
    assert stray["via"] == "App"
    assert stray["activity"].endswith("· App")


def test_lights_key_popup_and_switch_endpoint(monkeypatch):
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert '<span class="key-label">LIGHTS</span>' in html
    assert 'data-key="STAY"' in html  # key geometry untouched
    assert 'id="lights-pop"' in html and html.count('class="light-btn"') == 4
    assert "LIGHTS_HOLD_MS = 650" in js and "function lightsPressStart" in js
    assert '/api/arial/tuya/lights?device_id=' in js and '"/api/arial/tuya/switch"' in js
    assert ".lights-grid" in css and "grid-template-columns: 1fr 1fr;" in css.split(".lights-grid {", 1)[1].split("}", 1)[0]
    app = FastAPI()
    app.include_router(arial_api.router)
    client = TestClient(app)
    assert client.post("/api/arial/tuya/switch", json={"code": "0001", "switch": "switch_1", "value": True}).status_code == 401
    assert client.post("/api/arial/tuya/switch", json={"code": "2640", "switch": "switch_9", "value": True}).status_code == 400
    sent: list[Any] = []
    monkeypatch.setattr(arial_api, "_tuya_creds", lambda: {"client_id": "x", "secret": "y", "endpoint": "https://e", "device_id": "m"})
    monkeypatch.setattr(arial_api, "_tuya_send_commands", lambda creds, device, commands: (sent.append((device, commands)) or {"success": True}))
    monkeypatch.setattr(arial_api, "_lights_payload", lambda device: {"ok": True, "deviceId": device, "online": True, "switches": [{"code": "switch_1", "on": True}], "tuyaMsg": ""})
    monkeypatch.setattr(arial_api, "_remember_keypad", lambda code, cmd: {"from": "Comnet", "at": time.time()})
    out = client.post("/api/arial/tuya/switch", json={"code": "2640", "switch": "all", "value": False}).json()
    assert out["actor"]["from"] == "Comnet"
    assert sent[0][0] == arial_api.TUYA_LIGHTS_ID
    assert [c["code"] for c in sent[0][1]] == list(arial_api.LIGHT_SWITCHES)
    assert all(c["value"] is False for c in sent[0][1])


def test_olarm_app_disarm_arrives_as_notready():
    row = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "notready",
            "eventNum": 1,
            "eventMsg": "DISARMED - Area 1 - Facility Building",
            "eventTime": 1_788_346_035_000,
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert row["state"] == "DISARMED"
    assert row["tab"] == "areas"
    assert "Kevin" not in row["activity"]
    assert not arial_api.is_skip_activity_event(
        {"eventAction": "area", "eventState": "notready", "eventMsg": "DISARMED - Area 1 - Facility Building"}
    )
    assert arial_api.is_skip_activity_event(
        {"eventAction": "area", "eventState": "notready", "eventMsg": "NOTREADY - Area 1 - Facility Building"}
    )
    assert arial_api.classify_olarm_event({"eventAction": "zone_bypass", "eventState": "bypass_on", "eventMsg": "BYPASS ON - Zone 8"}) == "zones"
    assert arial_api.classify_olarm_event({"eventAction": "area", "eventState": "alarm", "eventMsg": "ALARM! - Area 1 - Facility Building"}) == "zones"


def test_keypad_who_survives_api_worker_restart(tmp_path, monkeypatch):
    _reset_keypad_log(monkeypatch, tmp_path)
    actor = arial_api._remember_keypad("7302", "area-arm")
    arial_api._last_keypad = None
    arial_api._keypad_log = []
    arial_api._keypad_log_mtime = -1.0
    row = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "arm",
            "eventNum": 1,
            "eventMsg": "ARMED - Area 1 - Facility Building",
            "eventTime": int(actor["at"] * 1000) + 45_000,
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert row["actor"] == "Pingoa"
    assert "Pingoa" in row["activity"]
    bundle = arial_api._stamp_activity_actors(
        {
            "ok": True,
            "events": [
                {
                    "tab": "areas",
                    "title": "Facility Building",
                    "state": "ARMED",
                    "activity": "Facility Building  ARMED",
                    "actor": "",
                    "at": int(actor["at"] * 1000) + 45_000,
                }
            ],
        }
    )
    assert bundle["events"][0]["actor"] == "Pingoa"
    assert "Pingoa" in bundle["events"][0]["activity"]


def test_onguard_pin_7777_and_logo(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parent
    assert (root / "users" / "onguard.png").is_file()
    js = (root / "app.js").read_text(encoding="utf-8")
    assert '"7777"' in js
    assert "/arial/users/onguard.png" in js
    assert 'from: "Onguard"' in js
    _reset_keypad_log(monkeypatch, tmp_path)
    actor = arial_api._remember_keypad("7777", "area-disarm")
    assert actor["from"] == "Onguard"
    row = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "disarm",
            "eventNum": 1,
            "eventMsg": "DISARMED - Area 1 - Facility Building",
            "eventTime": int(actor["at"] * 1000) + 8_000,
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert row["actor"] == "Onguard"
    assert "Onguard" in row["activity"]
    assert "Kevin" not in row["activity"]


def test_comnet_pin_2640_and_logo(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parent
    assert (root / "users" / "comnet.png").is_file()
    js = (root / "app.js").read_text(encoding="utf-8")
    assert '"2640"' in js
    assert "/arial/users/comnet.png" in js
    assert 'from: "Comnet"' in js
    _reset_keypad_log(monkeypatch, tmp_path)
    actor = arial_api._remember_keypad("2640", "area-disarm")
    assert actor["from"] == "Comnet"
    row = arial_api.format_olarm_event(
        {
            "eventAction": "area",
            "eventState": "disarm",
            "eventNum": 1,
            "eventMsg": "DISARMED - Area 1 - Facility Building",
            "eventTime": int(actor["at"] * 1000) + 8_000,
            "userFullname": "Kevin",
        },
        {"arialAreas": [{"num": 1, "label": "Facility Building"}]},
    )
    assert row["actor"] == "Comnet"
    assert "Comnet" in row["activity"]
    assert "Kevin" not in row["activity"]
    assert arial_api._activity_via("Comnet") == "Remote"
    assert arial_api._map_our_actor("Comnet") == "Comnet"


def test_breaker_energy_bins_and_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIAL_ENERGY_LOG", str(tmp_path / "energy.json"))
    arial_api._energy_bins.clear()
    arial_api._energy_last.clear()
    arial_api._energy_loaded = False
    dev = "unit-meter"
    t0 = 1_756_800_000.0
    for i in range(3):
        arial_api._energy_record_sample(dev, [{"code": "cur_power", "value": 100000}], now=t0 + 60 * i)
    days = arial_api._energy_days_from_bins(dev, now=t0 + 120)
    assert len(days) == 3
    assert days[0]["label"] == "Today" and days[1]["label"] == "Yesterday"
    assert days[0]["totalKwh"] == 0.033
    assert days[0]["hoursWithData"] == 1
    assert len(days[0]["hours"]) == 24
    assert days[1]["totalKwh"] is None
    arial_api._energy_record_sample(dev, [{"code": "cur_power", "value": 100000}], now=t0 + 1000)
    assert arial_api._energy_days_from_bins(dev, now=t0 + 1000)[0]["totalKwh"] == 0.033
    monkeypatch.setattr(arial_api, "_tuya_creds", lambda: {"client_id": "", "secret": "", "endpoint": "", "device_id": dev})
    app = FastAPI()
    app.include_router(arial_api.router)
    out = TestClient(app).get("/api/arial/tuya/energy").json()
    assert out["source"] == "none" and out["days"] == []
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert 'id="breaker-bars"' in html
    assert 'id="breaker-day-prev"' in html and 'id="breaker-day-next"' in html
    assert 'id="breaker-tip"' in html
    assert "/api/arial/tuya/energy?device_id=bf90676b1341ecb34dse39" in js
    assert "function bindBreakerDay" in js
    assert "bindBreakerDay();" in js
    assert '.breaker-day[data-day="1"] { --day-colour: #1565c0; }' in css
    assert '.breaker-day[data-day="2"] { --day-colour: #64748b; }' in css
    assert 'id="breaker-flag"' in html
    assert "function sinceLabel" in js and "function renderBreakerMeta" in js
    assert '"Since restore "' in js
    assert '.breaker-flag[data-flag="check"]' in css


def test_breaker_power_restore_and_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIAL_ENERGY_LOG", str(tmp_path / "energy.json"))
    arial_api._energy_bins.clear()
    arial_api._energy_last.clear()
    arial_api._energy_recent.clear()
    arial_api._energy_loaded = False
    arial_api._power_state.update({"loaded": False, "online": None, "acOk": None, "offSince": None, "restoreAt": None, "outages": []})
    dev = "unit-meter"
    t0 = 1_756_800_000.0
    arial_api._power_mark(online=True, now=t0 - 7200)
    arial_api._power_mark(online=False, now=t0 - 3600)
    arial_api._power_mark(online=True, now=t0 - 600)
    snap = arial_api._power_snapshot(t0)
    assert snap["restoreAt"] == t0 - 600
    assert snap["recovery"] is True
    assert snap["sinceRestoreS"] == 600
    for i in range(3):
        arial_api._energy_note_recent(dev, [{"code": "cur_power", "value": 120000}], t0 - 120 + 60 * i)
    an = arial_api._energy_analysis(dev, arial_api._energy_days_from_bins(dev, now=t0), t0)
    assert an["flag"] == "recovery"
    assert an["recentKw"] == 1.2
    later = t0 + 9000
    yday = (datetime.fromtimestamp(later, tz=timezone.utc).astimezone(arial_api._SAST) - timedelta(days=1)).strftime("%Y%m%d")
    arial_api._energy_bins[dev] = {f"{yday}{h:02d}": 0.8 for h in range(24)}
    arial_api._energy_recent[dev] = [(later - 60 * i, 800.0) for i in range(5)]
    an = arial_api._energy_analysis(dev, arial_api._energy_days_from_bins(dev, now=later), later)
    assert an["flag"] == "normal" and an["baselineKw"] == 0.8 and an["avgDayKwh"] == 19.2
    arial_api._energy_recent[dev] = [(later - 60 * i, 1300.0) for i in range(5)]
    an = arial_api._energy_analysis(dev, arial_api._energy_days_from_bins(dev, now=later), later)
    assert an["flag"] == "check" and an["deltaPct"] == 62
    arial_api._energy_recent[dev] = [(later - 60 * i, 1050.0) for i in range(5)]
    assert arial_api._energy_analysis(dev, arial_api._energy_days_from_bins(dev, now=later), later)["flag"] == "above"


def test_breaker_outages_from_tuya_lifecycle_log():
    def ev(stamp, kind):
        ts = datetime.strptime("2026-" + stamp, "%Y-%b %d %H:%M:%S").replace(tzinfo=arial_api._SAST).timestamp()
        return {"event_time": int(ts * 1000), "event_id": kind}
    rows = [
        ev("Aug 31 10:30:56", 2), ev("Sep 01 18:56:42", 1), ev("Sep 01 18:56:50", 9),
        ev("Sep 01 19:03:04", 2), ev("Sep 01 19:03:09", 1),  # 5 s wifi blip
        ev("Sep 02 11:19:57", 2), ev("Sep 02 11:26:13", 1),  # 6 min, no restart -> not mains
        ev("Sep 02 18:01:04", 2), ev("Sep 02 18:01:36", 1),
    ]
    out = arial_api._outages_from_lifecycle(rows)
    assert len(out) == 1
    assert datetime.fromtimestamp(out[0]["to"], arial_api._SAST).strftime("%d %H:%M:%S") == "01 18:56:42"
    assert datetime.fromtimestamp(out[0]["from"], arial_api._SAST).strftime("%d %H:%M:%S") == "31 10:30:56"


def test_olarm_poll_acks_until_newer_record(tmp_path, monkeypatch):
    _reset_keypad_log(monkeypatch, tmp_path)
    arial_api._activity_cache = {"at": 0.0, "data": None, "last_key": ""}
    arial_api._olarm_store.clear()
    monkeypatch.setenv("ARIAL_LIVE_STATE", str(tmp_path / "live.json"))
    older = {
        "eventAction": "area",
        "eventState": "arm",
        "eventNum": 1,
        "eventMsg": "ARMED - Area 1 - Facility Building",
        "eventTime": 1_700_000_000_000,
        "userFullname": "Kevin",
    }
    newer = dict(older)
    newer["eventTime"] = 1_700_000_100_000
    newer["eventState"] = "disarm"
    newer["eventMsg"] = "DISARMED - Area 1 - Facility Building"
    assert arial_api.apply_olarm_events([older]) == "insert"
    first = list((arial_api._activity_cache["data"] or {}).get("events") or [])
    assert arial_api.apply_olarm_events([older]) == "ack"
    assert list((arial_api._activity_cache["data"] or {}).get("events") or []) == first
    assert arial_api.apply_olarm_events([newer, older]) == "insert"
    rows = (arial_api._activity_cache["data"] or {}).get("events") or []
    assert rows[0]["state"] == "DISARMED"
    assert any(r.get("state") == "ARMED" for r in rows)
    assert arial_api.apply_olarm_events([newer, older]) == "ack"
    payload = arial_api._activity_payload(arial_api._activity_cache["data"], ack=True)
    assert payload["lastKey"]
    assert payload["checksum"]
    assert payload["ack"] is True
    assert int(arial_api._activity_cache.get("seq") or 0) >= 2


def test_live_push_includes_activity():
    js = (Path(__file__).resolve().parent / "app.js").read_text(encoding="utf-8")
    assert "function applyActivityPayload" in js
    assert "data.activity" in js
    assert 'prependActivity("DISARMED")' in js
    assert "new EventSource(\"/api/arial/live\")" in js
    src = Path(__file__).resolve().parents[1] / "arial_api.py"
    api = src.read_text(encoding="utf-8")
    assert 'push["activity"]' in api
    assert "area_changed" in api


def test_activity_keeps_30_day_store_and_checksums_on_login():
    js = (Path(__file__).resolve().parent / "app.js").read_text(encoding="utf-8")
    html = (Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")
    assert "arialActivity.hansekop" in js
    assert "30 * 24 * 60 * 60 * 1000" in js
    assert "function restoreActivityStore" in js
    assert "function allActivityThere" in js
    assert "function activityChecksum" in js
    assert "loadActivity({ history: true })" not in js
    assert 'prependActivity("ARMED")' in js
    assert 'prependActivity("COUNTDOWN")' not in js
    assert "function tidyActivity" in js
    assert "function skipActivityRow" in js
    assert 'via: who ? "Remote" : ""' in js
    assert 'prependActivity("DISARMED")' in js
    assert "setInterval(loadActivity, 3000)" in js
    assert "restoreActivityStore();" in js
    assert "app.js?v=214" in html


def test_activity_armed_once_remote_no_countdown_or_notready():
    js = (Path(__file__).resolve().parent / "app.js").read_text(encoding="utf-8")
    assert "blob.indexOf(\"NOTREADY\")" in js
    assert "activityRows = tidyActivity(activityRows);" in js.split("function renderActivity()", 1)[1]
    assert "tidyActivity" in js
    assert 'title + " " + state + " · " + who + " · Remote"' in js
    line = arial_api._activity_line("Facility Building", "ARMED", "Onguard", "Remote")
    assert line == "Facility Building ARMED · Onguard · Remote"
    assert arial_api.is_skip_activity_event(
        {"eventState": "countdown", "eventMsg": "COUNTDOWN - Area 1 - Facility Building"}
    )
    assert arial_api.is_skip_activity_event(
        {"eventState": "notready", "eventMsg": "NOTREADY - Area 1 - Facility Building"}
    )
    assert arial_api.is_skip_activity_event(
        {"eventState": "not ready", "eventMsg": "System Not Ready - Area 1 - Facility Building"}
    )
    assert arial_api.is_skip_activity_event(
        {"eventState": "arm", "eventMsg": "ARMED", "title": "System Not Ready"}
    ) is True
    assert not arial_api.is_skip_activity_event(
        {"eventState": "arm", "eventMsg": "ARMED - Area 1 - Facility Building"}
    )
    rows = [
        {"tab": "areas", "title": "Facility Building", "state": "ARMED", "actor": "Onguard", "at": 5},
        {"tab": "areas", "title": "Facility Building", "state": "ARMED", "actor": "Onguard", "at": 4},
        {"tab": "areas", "title": "Facility Building", "state": "COUNTDOWN", "at": 5},
        {"tab": "areas", "title": "Facility Building", "state": "NOT READY", "activity": "Facility Building NOT READY", "at": 4},
        {"tab": "areas", "title": "Facility Building", "state": "notready", "at": 3},
        {"tab": "areas", "title": "Facility Building", "state": "DISARMED", "actor": "Onguard", "at": 2},
        {"tab": "areas", "title": "Facility Building", "state": "ARMED", "actor": "Pingoa", "at": 1},
    ]
    out = arial_api.dedupe_area_activity(rows)
    states = [r["state"] for r in out]
    assert "COUNTDOWN" not in states
    assert "notready" not in states
    assert "NOT READY" not in states
    assert states == ["ARMED", "DISARMED", "ARMED"]
    device = {"arialAreas": [{"num": 1, "label": "Facility Building"}]}
    bundle = arial_api._activity_bundle(
        device,
        [
            {
                "eventAction": "area",
                "eventState": "countdown",
                "eventNum": 1,
                "eventMsg": "COUNTDOWN - Area 1 - Facility Building",
                "eventTime": 3000,
            },
            {
                "eventAction": "area",
                "eventState": "notready",
                "eventNum": 1,
                "eventMsg": "NOTREADY - Area 1 - Facility Building",
                "eventTime": 2000,
            },
            {
                "eventAction": "area",
                "eventState": "arm",
                "eventNum": 1,
                "eventMsg": "ARMED - Area 1 - Facility Building",
                "eventTime": 1000,
            },
        ],
    )
    assert [r["state"] for r in bundle["events"]] == ["ARMED"]


def test_status_label_under_status_led():
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert 'class="led-status-label">Status</div>' in html
    assert ".led-status-label" in css
    assert "font-weight: 900;" in css.split(".led-status-label {", 1)[1].split("}", 1)[0]
    assert "animation: none;" in css.split(".lcd.armed ~ .led.status,\n.led.status.armed {", 1)[1].split("}", 1)[0]
    assert "ledAlarmSwap" in css
    assert 'setLed(document.getElementById("led-status"), "alarm")' in (root / "app.js").read_text(encoding="utf-8")


def test_ac_led_is_blue_under_status_led():
    css = (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")
    assert ".led.ac {\n    top: 45.2%;\n    --led-fill: #1565c0;" in css
    assert ".led.ac.on {\n    --led-fill: #1565c0;" in css


def test_housing_sides_inset_toward_leds():
    html = (Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")
    assert "L19 372" in html
    assert "L6 372" not in html
    assert 'x="64"' in html
    assert "left: 12.6%;" in (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")
    assert "width: 74.8%;" in (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")
    assert "height: 17.47%;" in (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")


def test_keypad_is_scaled_with_side_gaps():
    css = (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")
    assert "width: 99%;" in css
    assert "max-width: 416px;" in css
    assert "position: sticky;" in css
    assert "overscroll-behavior: none;" not in css
    html = (Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")
    assert "user-scalable=yes" in html
    js = (Path(__file__).resolve().parent / "app.js").read_text(encoding="utf-8")
    assert 'document.addEventListener("touchmove"' not in js


def test_compact_crop_shows_full_function_keys():
    css = (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")
    assert ".pad-wrap.compact .hot-more" in css
    assert "aspect-ratio: 368 / 199" in css
    visible = 199 / 427
    assert visible > 0.453


def test_lcd_status_text_is_bold():
    css = (Path(__file__).resolve().parent / "arial.css").read_text(encoding="utf-8")
    html = (Path(__file__).resolve().parent / "index.html").read_text(encoding="utf-8")
    js = (Path(__file__).resolve().parent / "app.js").read_text(encoding="utf-8")
    assert 'class="lcd-toprow"' in html
    block = css.split("\n#lcd-2 {", 1)[1].split("}", 1)[0]
    assert "justify-content: center;" in block
    assert "font-family: Anton" in block
    assert "font-size: 32px;" in block
    assert "overflow: visible;" in block
    assert "padding: 6px 0 2px;" in block
    assert "text-transform: uppercase;" in block
    assert "lcdTextFlash" in css
    assert "lcdTextFlashSlow" in css
    assert "6s ease-in-out infinite" in css
    assert "0%, 74% { opacity: 1; }" in css
    assert ".lcd.armed #lcd-2,\n.lcd.arming #lcd-2,\n.lcd.disarmed #lcd-2" in css
    assert "font-size: 32px;" in css.split(".lcd.armed #lcd-2,\n.lcd.arming #lcd-2,\n.lcd.disarmed #lcd-2 {", 1)[1].split("}", 1)[0]
    assert "font-size: 44px;" not in css
    assert "line-height: 0.82;" not in css
    assert "-webkit-text-stroke" not in css
    assert "var size = 32;" in js
    assert "h + 10" not in js
    assert "lcdArmedSlow" not in css
    assert "lcdReadyFlash" not in css
    assert "animation: lcdflash" not in css
    assert 'st === "notready"' in js
    assert "openZoneIssues" in js
    assert "panelIssues" in js
    assert '"Zone " + n + " Open"' not in js
    assert 'out.push("Power Failure")' in js
    assert "setInterval(showNextIssue, 1150)" in js
    assert "ensureIssueCycle" in js
    assert 'return "Zone Open"' not in js
    assert '"System Ready"' in js
    assert '"System Disarmed"' in js
    assert "disarmed:not(.zone-open)" in css
    assert '"System Not Ready"' in js
    assert "lcd-status-issue" in html
    assert "lcd-status-main" in html
    assert "zone-open" in js
    assert "border-radius: 8px;" in css.split(".lcd {", 1)[1].split("}", 1)[0]


def test_last_pin_digit_beeps_then_welcome_tune_waits():
    js = (Path(__file__).resolve().parent / "app.js").read_text(encoding="utf-8")
    assert "willAccept" not in js
    assert 'key !== "LOGOUT" && key !== "UP") beep()' in js
    assert "setTimeout(pinAccepted, 1000)" in js
    assert "armWelcomeTune" not in js
    assert "loadPinOkBuffer" in js


def test_first_key_beep_plays_inside_pointerdown_gesture():
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    assert (root / "key-beep.wav").is_file()
    assert (root / "key-reject.wav").is_file()
    assert 'id="key-beep"' in html
    assert 'id="key-reject"' in html
    assert "key-beep.wav" in html
    assert "key-reject.wav" in html
    assert "function loadRejectBuffer()" in js
    assert "playHtmlBeep" in js
    assert "unlockAudio();" in js
    assert "onKey(btn.getAttribute(\"data-key\"));" in js
    assert "unlockAudio().then(function () {\n            onKey(key);" not in js


def test_up_arrow_is_logout_when_logged_in():
    root = Path(__file__).resolve().parent
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "arial.css").read_text(encoding="utf-8")
    assert 'id="logout-btn"' not in html
    assert "logout-link" not in html
    assert "logout-link" not in css
    assert 'data-key="UP"' in html
    assert 'class="logout-label"' not in html
    assert ">Log<" not in html
    assert 'key === "UP"' in js
    assert "logOut();" in js
    assert "logoutBeep();" in js
    assert "up.hidden = !on" in js
    assert ".pad-wrap.compact .hot[data-key=\"UP\"]" in css


def test_tuya_catalog_unique_ids_and_mains_meter():
    import json

    catalog = json.loads((Path(__file__).resolve().parent / "tuya_catalog.json").read_text(encoding="utf-8"))
    ids = [d["id"] for d in catalog["devices"]]
    assert len(ids) == len(set(ids))
    assert len(ids) == 30
    meter = next(d for d in catalog["devices"] if d.get("role") == "mains-meter")
    assert meter["id"] == "bf90676b1341ecb34dse39"
    assert meter["name"] == "HSK Mains Meter"
    assert catalog["openapiBase"] == "https://openapi.tuyaeu.com"
    assert "IoT Core" in catalog["selfServe"]["likelyCause"]


FAKE_TUYA = {
    "client_id": "cid",
    "secret": "sec",
    "endpoint": "https://openapi.tuyaeu.com",
    "device_id": "bf90676b1341ecb34dse39",
}
TOKEN_OK = {
    "success": True,
    "t": 1_700_000_000_000,
    "result": {
        "access_token": "tok-abc",
        "refresh_token": "ref-xyz",
        "expire_time": 7200,
        "uid": "eu123",
    },
}


def _assert_no_tuya_secrets(payload):
    blob = json.dumps(payload)
    assert "tok-abc" not in blob
    assert "ref-xyz" not in blob
    assert FAKE_TUYA["secret"] not in blob


def test_tuya_token_paths_omit_access_token_from_hmac():
    assert arial_api.tuya_sign_access_token("/v1.0/token", "DEAD") == ""
    assert arial_api.tuya_sign_access_token("/v1.0/token/ref-xyz", "DEAD") == ""
    assert arial_api.tuya_sign_access_token("/v1.0/devices/x/status", "LIVE") == "LIVE"
    t = 1588925778000
    path = "/v1.0/token"
    str_to_sign = arial_api.tuya_str_to_sign("GET", path, {"grant_type": 1})
    with_dead = arial_api.tuya_sign("sec", "cid", t, str_to_sign, access_token="DEAD")
    without = arial_api.tuya_sign("sec", "cid", t, str_to_sign, access_token="")
    assert with_dead != without
    assert "grant_type=1" in str_to_sign
    assert str_to_sign.startswith("GET\n")


def test_tuya_refresh_signs_without_dead_access_token(monkeypatch):
    captured = []

    def send(method, endpoint, path, headers, params=None):
        captured.append({"path": path, "access_token": headers.get("access_token"), "params": params})
        return TOKEN_OK

    monkeypatch.setattr(arial_api, "_tuya_send", send)
    arial_api._tuya_token = {
        "access_token": "DEAD",
        "refresh_token": "ref-xyz",
        "uid": "u",
        "expire_at_ms": 0,
    }
    arial_api._tuya_ensure_token(FAKE_TUYA)
    assert captured[0]["path"] == "/v1.0/token/ref-xyz"
    assert captured[0]["access_token"] == ""


def test_tuya_probe_unconfigured(monkeypatch):
    monkeypatch.setattr(
        arial_api,
        "_tuya_creds",
        lambda: {
            "client_id": "",
            "secret": "",
            "endpoint": "https://openapi.tuyaeu.com",
            "device_id": arial_api.TUYA_MAINS_METER_ID,
        },
    )
    out = arial_api.tuya_probe()
    assert out["configured"] is False
    assert out["paused"] is True
    assert out["ok"] is False
    assert "TUYA_CLIENT_ID" in out["hint"]


def test_tuya_probe_token_ok_status_1010_is_iot_core_hint(monkeypatch):
    monkeypatch.setattr(arial_api, "_tuya_creds", lambda: dict(FAKE_TUYA))

    def send(method, endpoint, path, headers, params=None):
        if "/token" in path:
            return TOKEN_OK
        return {"success": False, "code": 1010, "msg": "token invalid"}

    monkeypatch.setattr(arial_api, "_tuya_send", send)
    out = arial_api.tuya_probe()
    _assert_no_tuya_secrets(out)
    assert out["configured"] is True
    assert out["paused"] is True
    assert out["tokenOk"] is True
    assert out["deviceOk"] is False
    assert out["ok"] is False
    assert out["tuyaCode"] == 1010
    assert "IoT Core" in out["hint"]
    assert "apply-extension" in out["hint"]


def test_tuya_probe_retries_status_after_fresh_token(monkeypatch):
    monkeypatch.setattr(arial_api, "_tuya_creds", lambda: dict(FAKE_TUYA))
    status_hits = {"n": 0}

    def send(method, endpoint, path, headers, params=None):
        if path.startswith("/v1.0/token"):
            return TOKEN_OK
        status_hits["n"] += 1
        if status_hits["n"] == 1:
            return {"success": False, "code": 1010, "msg": "token invalid"}
        return {"success": True, "result": [{"code": "cur_current", "value": 12}]}

    monkeypatch.setattr(arial_api, "_tuya_send", send)
    out = arial_api.tuya_probe()
    _assert_no_tuya_secrets(out)
    assert status_hits["n"] == 2
    assert out["ok"] is True
    assert out["deviceOk"] is True
    assert out["paused"] is True
    assert out["dpsCount"] == 1


def test_tuya_probe_route_and_status_flag(monkeypatch):
    monkeypatch.setattr(
        arial_api,
        "_tuya_creds",
        lambda: {
            "client_id": "",
            "secret": "",
            "endpoint": "https://openapi.tuyaeu.com",
            "device_id": arial_api.TUYA_MAINS_METER_ID,
        },
    )
    app = FastAPI()
    app.include_router(arial_api.router)
    client = TestClient(app)
    status = client.get("/api/arial/status")
    assert status.status_code == 200
    assert status.json()["tuyaConfigured"] is False
    assert status.json()["tuyaPaused"] is True
    probe = client.get("/api/arial/tuya/probe")
    assert probe.status_code == 200
    assert probe.json()["configured"] is False
    assert probe.json()["paused"] is True


def test_register_login_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(arial_api, "_USERS_PATH", tmp_path / "arial_users.json")
    monkeypatch.setattr(arial_api, "_DATA_DIR", tmp_path)
    app = FastAPI()
    app.include_router(arial_api.router)
    client = TestClient(app)

    r = client.post(
        "/api/arial/auth/register",
        json={"email": "tester@arial.co.za", "password": "secret1", "display_name": "Tester"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["me"]["display_name"] == "Tester"
    assert client.cookies.get("arial_session")

    me = client.get("/api/arial/me")
    assert me.status_code == 200
    assert me.json()["me"]["email"] == "tester@arial.co.za"

    saved = client.put("/api/arial/me", json={"phone": "0820000000", "notes": "Voelklip"})
    assert saved.status_code == 200
    assert saved.json()["me"]["phone"] == "0820000000"

    client.post("/api/arial/auth/logout")
    denied = client.get("/api/arial/me")
    assert denied.status_code == 401

    back = client.post(
        "/api/arial/auth/login",
        json={"email": "tester@arial.co.za", "password": "secret1"},
    )
    assert back.status_code == 200


if __name__ == "__main__":
    test_enrich_device_areas_and_named_zones()
    print("enrich ok")
    # pytest-style helpers without pytest
    class MP:
        def setattr(self, obj, name, val):
            setattr(obj, name, val)
    # skip login test here; run via pytest
    print(json.dumps(arial_api.enrich_device(SAMPLE)["arialAreas"]))
    print("ok", Path(__file__).name)
