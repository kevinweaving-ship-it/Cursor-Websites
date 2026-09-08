from oem import (
    _enc_password,
    colon_hex,
    device_to_snapshot,
    mobile_hash,
    oem_sign,
    thing_canonical,
    thing_channel_key,
    thing_global_material,
    thing_profiles,
    thing_sign,
)


def test_mobile_hash_rearranges_md5():
    assert mobile_hash('{"x":1}') == mobile_hash('{"x":1}')
    h = mobile_hash("abc")
    assert len(h) == 32
    import hashlib
    raw = hashlib.md5(b"abc").hexdigest()
    assert h == raw[8:16] + raw[0:8] + raw[24:32] + raw[16:24]


def test_oem_sign_stable():
    secret = "A_armptsqyfpxa4ftvtc739ardncett3uy_cgqx3ku34mh5qdesd7fcaru3gx7tyurr"
    data = {
        "a": "tuya.m.user.email.token.create",
        "clientId": "fx3fvkvusmw45d7jn8xh",
        "v": "1.0",
        "time": "1000",
        "postData": '{"countryCode":"","email":"a@b.c"}',
    }
    sig = oem_sign(secret, data)
    assert len(sig) == 64
    assert sig == oem_sign(secret, data)


def test_device_to_snapshot_dps_and_status():
    row = device_to_snapshot(
        {"devId": "d1", "name": "Plug", "category": "cz", "dps": {"1": True}, "productId": "p"},
        "HH",
        "99",
    )
    assert row["id"] == "d1"
    assert row["home"] == "HH"
    assert row["home_id"] == "99"
    assert row["status"]["1"] is True
    row2 = device_to_snapshot(
        {"id": "d2", "name": "Lamp", "status": [{"code": "switch_1", "value": False}]},
        "HH",
        "99",
    )
    assert row2["status"]["switch_1"] is False


def test_thing5_sign_matches_tuya_mobile():
    from tuya_mobile.client import canonical_string
    from tuya_mobile.signer import PurePythonTuyaSigner

    package = "com.cbilv.cbihome"
    cert = "A19AFDFD64AFE67AFBD20993C6F4B58CA07207E5CD162417B9CEC4119C19964F"
    app_key = "n9n3wtwx8yhvea7w7nueae5k7jt5v4v4"
    app_secret = "94tm5nkcjrjv78m3kwfw9xknar8yw47r"
    app_id = "h8h3y3kvpehu88wk9euu"
    params = {
        "a": "thing.m.user.username.token.get",
        "v": "2.0",
        "clientId": app_id,
        "os": "Android",
        "et": "3",
        "time": "1000",
        "requestId": "rid",
        "postData": "cipher",
        "channel": "sdk",
    }
    assert thing_canonical(params) == canonical_string(params)
    material = thing_global_material(package, cert, app_key, app_secret)
    signer = PurePythonTuyaSigner(app_id, app_secret, cert, app_key, package)
    assert thing_sign(material, thing_canonical(params)) == signer.sign(canonical_string(params))
    assert thing_channel_key(app_id, package, cert) == signer.channel_key()
    assert colon_hex(cert) == signer.cert_msg().split("_", 1)[1]


def test_cbi_profiles_cover_both_app_ids():
    ids = {p["app_id"] for p in thing_profiles()}
    assert "h8h3y3kvpehu88wk9euu" in ids
    assert "a5vnv3q9uxe5w7fsawn5" in ids


def test_enc_password_decimal_modulus():
    # 256-bit-ish toy modulus so textbook RSA still produces hex
    n = str(2 ** 1024 + 13)
    out = _enc_password(n, "3", "secret")
    assert len(out) >= 64
    assert all(c in "0123456789abcdef" for c in out)
