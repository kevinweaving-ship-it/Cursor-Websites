"""Tests for Arial Olarm enrich + local profile auth (no live Olarm required)."""
import json
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


def test_countdown_from_numeric_detail():
    d = {
        "deviceState": {"areas": ["countdown"], "areasDetail": ["47"]},
        "deviceProfile": {"areasLimit": 1, "areasLabels": ["House"], "zonesLimit": 0},
    }
    out = arial_api.enrich_device(d)
    assert out["arialCountdown"] == 47
    assert out["arialAreas"][0]["countdown"] == 47
    assert out["arialExitDelay"] == 10


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


def test_tuya_catalog_unique_ids_and_mains_meter():
    import json

    catalog = json.loads((Path(__file__).resolve().parent / "tuya_catalog.json").read_text(encoding="utf-8"))
    ids = [d["id"] for d in catalog["devices"]]
    assert len(ids) == len(set(ids))
    assert len(ids) == 30
    meter = next(d for d in catalog["devices"] if d.get("role") == "mains-meter")
    assert meter["id"] == "bf90676b1341ecb34dse39"
    assert meter["name"] == "HSK Mains Meter"


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
