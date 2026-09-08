"""White-label Tuya OEM app session (CBI Home and other branded apps).

HA device-sharing QR (client HA_3y9q4ak7g4ephrvke / tuyaSmart--qrLogin) is
Smart Life / Tuya Smart only. Every OEM/white-label app (CBI, Ledvance,
Gosund, Konyks, …) has its own AppKey + schema + signing material.
Prefix-flipping that QR cannot make HA's client become the OEM app.

Two OEM generations share a1.tuya*.com/api.json:

  classic — HMAC-SHA256 with secret A_{bmp}_{appSecret} (Ledvance, Gosund, …)
  thing5  — Thing SDK 5+ (CBI Home): et=3 AES-GCM body, sign key SHA256(
            package_CERT_appKey_appSecret). Same algorithm as tuya-mobile /
            libthing_security.so; only the five APK constants change per brand.

Other OEM apps: set CBI_OEM_* env (app id / key / secret / package / cert / schema).
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger("cbi-oem")

# Official CBI Home Android app (public APK com.cbilv.cbihome 1.0.9).
CBI_APP_KEY = "a5vnv3q9uxe5w7fsawn5"
CBI_APP_SECRET = "8wgcacuqr4uyavm77hk5srcgak4dy4um"
CBI_CV_KEY = "h8h3y3kvpehu88wk9euu"
CBI_CV_SECRET = "94tm5nkcjrjv78m3kwfw9xknar8yw47r"
CBI_BMP_TOKEN = "n9n3wtwx8yhvea7w7nueae5k7jt5v4v4"
CBI_SCHEMA = "cbilvcbihome"
CBI_PACKAGE = "com.cbilv.cbihome"
CBI_CERT = "A19AFDFD64AFE67AFBD20993C6F4B58CA07207E5CD162417B9CEC4119C19964F"
CBI_HMAC_SECRET = f"A_{CBI_BMP_TOKEN}_{CBI_CV_SECRET}"

REGIONS = ("eu", "us", "in", "cn")
THING_SIGN_KEYS = {
    "a", "appVersion", "chKey", "clientId", "deviceId", "et", "h5",
    "h5Token", "lang", "lat", "lon", "n4h5", "os", "postData", "requestId",
    "sid", "sp", "time", "ttid", "v",
}


def _cfg(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def oem_settings() -> dict[str, str]:
    return {
        "app_key": _cfg("CBI_OEM_APP_KEY", CBI_APP_KEY),
        "hmac_secret": _cfg("CBI_OEM_HMAC_SECRET", CBI_HMAC_SECRET),
        "schema": _cfg("CBI_OEM_SCHEMA", CBI_SCHEMA),
        "country": _cfg("CBI_OEM_COUNTRY", "27"),
        "email": _cfg("CBI_LOGIN_EMAIL"),
        "password": _cfg("CBI_LOGIN_PASSWORD"),
        "region": _cfg("CBI_OEM_REGION", "eu"),
        "package": _cfg("CBI_OEM_PACKAGE", CBI_PACKAGE),
        "cert": _cfg("CBI_OEM_CERT", CBI_CERT),
        "app_secret": _cfg("CBI_OEM_APP_SECRET", CBI_APP_SECRET),
        "bmp": _cfg("CBI_OEM_BMP", CBI_BMP_TOKEN),
        "app_version": _cfg("CBI_OEM_APP_VERSION", "1.0.9"),
    }


def mobile_hash(data: str) -> str:
    prehash = hashlib.md5(data.encode("utf-8")).hexdigest()
    return prehash[8:16] + prehash[0:8] + prehash[24:32] + prehash[16:24]


def oem_sign(secret: str, data: dict[str, str]) -> str:
    parts: list[str] = []
    for key in sorted(data):
        if key in {"gid", "sign"}:
            continue
        val = mobile_hash(data[key]) if key == "postData" else data[key]
        parts.append(f"{key}={val}")
    raw = "||".join(parts)
    return hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def colon_hex(cert_sha256_hex: str) -> str:
    h = cert_sha256_hex.replace(":", "").strip()
    return ":".join(h[i : i + 2] for i in range(0, len(h), 2)).upper()


def thing_global_material(package: str, cert: str, app_key: str, app_secret: str) -> str:
    return f"{package}_{colon_hex(cert)}_{app_key}_{app_secret}"


def thing_sign(material: str, canonical: str) -> str:
    key = hashlib.sha256(material.encode("utf-8")).digest()
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def thing_channel_key(app_id: str, package: str, cert: str) -> str:
    msg = f"{package}_{colon_hex(cert)}"
    return hmac.new(app_id.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()[8:16]


def thing_derive_key(request_id: str, material: str, ecode: str | None = None) -> bytes:
    message = material if not ecode else f"{material}_{ecode}"
    digest = hmac.new(request_id.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:16].encode("ascii")


def thing_canonical(params: dict[str, str]) -> str:
    parts: list[str] = []
    for key in sorted(params):
        value = params[key]
        if key in THING_SIGN_KEYS and value:
            if key == "postData":
                value = mobile_hash(value)
            parts.append(f"{key}={value}")
    return "||".join(parts)


def thing_profiles(settings: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Candidate Thing SDK 5 identities for this OEM (CBI defaults + env)."""
    s = settings or oem_settings()
    env_id = _cfg("CBI_OEM_APP_ID")
    # Live probe: CBI AppKey + AppSecret + BMP is accepted; CV encrypt key is ILLEGAL_CLIENT_ID.
    ids = [env_id] if env_id else [s["app_key"], CBI_APP_KEY]
    secrets = [s["app_secret"], CBI_APP_SECRET]
    bmps = [s["bmp"], CBI_BMP_TOKEN]
    ets = [_cfg("CBI_OEM_ET") or "3"]
    if _cfg("CBI_OEM_TRY_ET"):
        ets.extend(x for x in _cfg("CBI_OEM_TRY_ET").split(",") if x and x not in ets)
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for app_id in ids:
        if not app_id:
            continue
        for bmp in bmps:
            for secret in secrets:
                for et in ets:
                    ttid = _cfg("CBI_OEM_TTID") or f"sdk_international@{app_id}"
                    key = (app_id, bmp, secret, et, ttid)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "app_id": app_id,
                        "app_key": bmp,
                        "app_secret": secret,
                        "package": s["package"],
                        "cert": s["cert"],
                        "et": et,
                        "ttid": ttid,
                        "app_version": s["app_version"],
                        "sdk_version": _cfg("CBI_OEM_SDK_VERSION", "5.2.0"),
                        "device_core_version": _cfg("CBI_OEM_CORE_VERSION", "5.2.0"),
                        "app_rn_version": _cfg("CBI_OEM_RN_VERSION", "5.2"),
                        "schema": s["schema"],
                    })
    return out


def _aes_encrypt(key: bytes, payload: dict[str, Any]) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.b64encode(nonce + AESGCM(key).encrypt(nonce, body, None)).decode("ascii")


def _aes_decrypt(key: bytes, value: str) -> Any:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = base64.b64decode(value)
    plain = AESGCM(key).decrypt(raw[:12], raw[12:], None)
    try:
        plain = gzip.decompress(plain)
    except OSError:
        pass
    return json.loads(plain.decode("utf-8"))


def _status_map(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    out: dict[str, Any] = {}
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("code") is not None:
                out[str(item["code"])] = item.get("value")
    return out


def device_to_snapshot(dev: dict[str, Any], home_name: str, home_id: str) -> dict[str, Any]:
    dps = dev.get("dps") if isinstance(dev.get("dps"), dict) else None
    status = dps if dps is not None else _status_map(dev.get("status"))
    return {
        "id": str(dev.get("id") or dev.get("devId") or ""),
        "name": str(dev.get("name") or dev.get("dev_name") or "").strip(),
        "category": str(dev.get("category") or ""),
        "online": bool(dev.get("online", True) if "online" in dev else True),
        "status": status,
        "home": home_name,
        "home_id": str(home_id),
        "icon": dev.get("icon") or dev.get("iconUrl") or None,
        "product_id": dev.get("product_id") or dev.get("productId") or None,
        "product_name": (dev.get("product_name") or dev.get("productName") or "") or None,
        "units": {},
    }


def _plain_rsa_encrypt(modulus: int, exponent: int, message: bytes) -> str:
    enc = pow(int.from_bytes(message, "big"), exponent, modulus)
    return enc.to_bytes((modulus.bit_length() + 7) // 8, "big").hex()


def _rsa_params(public_key: str, exponent: str) -> tuple[int, int]:
    if public_key.isdigit():
        return int(public_key), int(exponent)
    try:
        return int(public_key, 16), int(exponent)
    except ValueError:
        pass
    der = base64.b64decode(public_key)
    try:
        from cryptography.hazmat.primitives.serialization import load_der_public_key

        key = load_der_public_key(der)
        numbers = key.public_numbers()
        return int(numbers.n), int(numbers.e)
    except Exception:
        return int.from_bytes(der, "big"), int(exponent)


def _enc_password(public_key: str, exponent: str, password: str) -> str:
    digest = hashlib.md5(password.encode("utf-8")).hexdigest().encode("utf-8")
    modulus, exp = _rsa_params(public_key, exponent)
    return _plain_rsa_encrypt(modulus, exp, digest)


def _enc_password_pkcs1(public_key: str, exponent: str, password: str) -> str:
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    digest = hashlib.md5(password.encode("utf-8")).hexdigest().encode("ascii")
    n, e = _rsa_params(public_key, exponent)
    key = rsa.RSAPublicNumbers(e, n).public_key()
    return key.encrypt(digest, padding.PKCS1v15()).hex()


class OemClient:
    """Phone-app mobile API for one OEM brand (CBI today; any white-label tomorrow)."""

    def __init__(self, settings: dict[str, str] | None = None) -> None:
        self.s = settings or oem_settings()
        self.region = self.s["region"] or "eu"
        self.session = requests.Session()
        self.sid: str | None = None
        self.uid: str = ""
        self.username: str = self.s["email"]
        self.oem_kind = "classic"
        self.ecode: str | None = None
        self.profile: dict[str, str] = {}
        self.material = ""

    @property
    def endpoint(self) -> str:
        return f"https://a1.tuya{self.region}.com/api.json"

    def _classic_api(self, action: str, payload: dict[str, Any] | None = None, extra: dict[str, str] | None = None, *, need_sid: bool = True) -> Any:
        params = {
            "a": action,
            "clientId": self.s["app_key"],
            "v": "1.0",
            "time": str(int(time.time())),
        }
        if extra:
            params.update(extra)
        if need_sid:
            if not self.sid:
                raise RuntimeError("OEM login required")
            params["sid"] = self.sid
        data: dict[str, str] = {}
        if payload is not None:
            data["postData"] = json.dumps(payload, separators=(",", ":"))
        params["sign"] = oem_sign(self.s["hmac_secret"], {**params, **data})
        r = self.session.post(
            self.endpoint,
            params=params,
            data=data,
            headers={"User-Agent": "TY-UA=APP/Android/1.0.9/SDK/null"},
            timeout=30,
        )
        body = r.json()
        if body.get("success"):
            return body.get("result")
        code = body.get("errorCode") or body.get("code")
        msg = body.get("errorMsg") or body.get("msg") or body
        raise RuntimeError(f"{action}: {code} {msg}")

    def _thing_api(self, action: str, payload: dict[str, Any] | None = None, *, version: str = "1.0", need_sid: bool = True) -> Any:
        if need_sid and not self.sid:
            raise RuntimeError("OEM login required")
        profile = self.profile
        request_id = str(uuid.uuid4())
        key = thing_derive_key(request_id, self.material, self.ecode)
        et = profile.get("et") or "3"
        if et == "3":
            post = _aes_encrypt(key, payload or {})
        else:
            post = json.dumps(payload or {}, separators=(",", ":"), ensure_ascii=False)
        device_id = hashlib.sha256(
            f"{profile.get('package')}|{profile.get('app_id')}|{self.username}".encode()
        ).hexdigest()[:44]
        params: dict[str, str] = {
            "a": action,
            "v": version,
            "clientId": profile["app_id"],
            "os": "Android",
            "appVersion": profile.get("app_version") or "1.0.9",
            "channel": "sdk",
            "osSystem": "14",
            "sdkVersion": profile.get("sdk_version") or "5.2.0",
            "deviceCoreVersion": profile.get("device_core_version") or "5.2.0",
            "platform": "Android",
            "lang": "en",
            "ttid": profile.get("ttid") or f"sdk_international@{profile['app_id']}",
            "et": et,
            "chKey": thing_channel_key(profile["app_id"], profile["package"], profile["cert"]),
            "deviceId": device_id,
            "time": str(int(time.time())),
            "requestId": request_id,
            "postData": post,
        }
        if profile.get("app_rn_version"):
            params["appRnVersion"] = profile["app_rn_version"]
        if self.sid:
            params["sid"] = self.sid
        params["sign"] = thing_sign(self.material, thing_canonical(params))
        gid = str((payload or {}).get("gid") or "")
        # Classic OEM device APIs read gid from the query string, not the body.
        q = {"gid": gid} if gid else None
        r = self.session.post(self.endpoint, params=q, data=params, timeout=30)
        body = r.json()
        if not body.get("success") and "result" not in body:
            code = body.get("errorCode") or body.get("code")
            msg = body.get("errorMsg") or body.get("msg") or body
            raise RuntimeError(f"{action}: {code} {msg}")
        result = body.get("result")
        if et == "3" and isinstance(result, str):
            result = _aes_decrypt(key, result)
        if isinstance(result, dict) and result.get("success") is False:
            code = result.get("errorCode") or result.get("code")
            msg = result.get("errorMsg") or result.get("msg") or result
            raise RuntimeError(f"{action}: {code} {msg}")
        if isinstance(result, dict) and "result" in result and result.get("success") is True:
            return result.get("result")
        return result

    def _api(self, action: str, payload: dict[str, Any] | None = None, extra: dict[str, str] | None = None, *, need_sid: bool = True, version: str = "1.0") -> Any:
        if self.oem_kind == "thing5":
            if extra and extra.get("gid") and payload is not None:
                payload = {**payload, "gid": extra["gid"]}
            elif extra and extra.get("gid"):
                payload = {"gid": extra["gid"]}
            return self._thing_api(action, payload, version=version, need_sid=need_sid)
        return self._classic_api(action, payload, extra, need_sid=need_sid)

    def apply_profile(self, profile: dict[str, str]) -> None:
        self.profile = profile
        self.oem_kind = "thing5"
        self.material = thing_global_material(
            profile["package"], profile["cert"], profile["app_key"], profile["app_secret"]
        )
        self.s["app_key"] = profile["app_id"]

    def probe_token(self, profile: dict[str, str], email: str, country: str) -> str:
        """Hit token.get only — used to find a working white-label identity."""
        self.apply_profile(profile)
        try:
            token = self._thing_api(
                "thing.m.user.username.token.get",
                {"countryCode": country, "username": email, "isUid": False},
                version="2.0",
                need_sid=False,
            )
        except Exception as exc:
            return str(exc)[:180]
        if isinstance(token, dict) and (token.get("publicKey") or token.get("pbKey")):
            return "OK"
        return f"unexpected {type(token).__name__}"

    def _login_thing5(self, profile: dict[str, str], country: str) -> dict[str, Any]:
        self.apply_profile(profile)
        token = None
        last: Exception | None = None
        for action, version, payload in (
            ("thing.m.user.username.token.get", "2.0", {"countryCode": country, "username": self.s["email"], "isUid": False}),
            ("thing.m.user.email.token.create", "1.0", {"countryCode": country, "email": self.s["email"]}),
            ("tuya.m.user.email.token.create", "1.0", {"countryCode": country, "email": self.s["email"]}),
        ):
            try:
                token = self._thing_api(action, payload, version=version, need_sid=False)
                break
            except Exception as exc:
                last = exc
        if not isinstance(token, dict):
            raise RuntimeError(f"thing5 token failed: {last}")
        pub = str(token.get("publicKey") or token.get("pbKey") or "")
        exp = str(token.get("exponent") or "3")
        if not pub or not token.get("token"):
            raise RuntimeError(f"thing5 token missing key fields: {last}")
        try:
            passwd = _enc_password_pkcs1(pub, exp, self.s["password"])
        except Exception:
            passwd = _enc_password(pub, exp, self.s["password"])
        login = None
        for action, version in (
            ("thing.m.user.email.password.login", "3.0"),
            ("thing.m.user.email.password.login", "1.0"),
            ("tuya.m.user.email.password.login", "1.0"),
        ):
            try:
                login = self._thing_api(
                    action,
                    {
                        "countryCode": country,
                        "email": self.s["email"],
                        "ifencrypt": 1,
                        "options": '{"group":1,"mfaCode":""}',
                        "passwd": passwd,
                        "token": token["token"],
                    },
                    version=version,
                    need_sid=False,
                )
                break
            except Exception as exc:
                last = exc
        if not isinstance(login, dict):
            raise RuntimeError(f"thing5 login failed: {last}")
        self.sid = str(login.get("sid") or "")
        self.uid = str(login.get("uid") or login.get("euid") or login.get("userId") or "")
        self.ecode = str(login.get("ecode") or login.get("eCode") or login.get("encryptCode") or "") or None
        domain = login.get("domain") if isinstance(login.get("domain"), dict) else {}
        region = str(domain.get("regionCode") or "").lower()
        if region in REGIONS:
            self.region = region
        if not self.sid:
            raise RuntimeError("thing5 login returned no sid")
        log.info("OEM thing5 login ok region=%s uid=%s app_id=%s et=%s", self.region, self.uid, profile["app_id"], profile.get("et"))
        return login

    def _login_classic(self) -> dict[str, Any]:
        self.oem_kind = "classic"
        self.profile = {}
        self.material = ""
        regions = [self.region] if self.s.get("region") else list(REGIONS)
        actions = (
            ("thing.m.user.email.token.create", "thing.m.user.email.password.login"),
            ("tuya.m.user.email.token.create", "tuya.m.user.email.password.login"),
        )
        last: Exception | None = None
        for region in regions:
            self.region = region
            for token_a, login_a in actions:
                for country in (self.s["country"], ""):
                    try:
                        token = self._classic_api(token_a, {"countryCode": country, "email": self.s["email"]}, need_sid=False)
                        pub = token.get("publicKey") or token.get("pbKey")
                        exp = str(token.get("exponent") or "3")
                        login = self._classic_api(
                            login_a,
                            {
                                "countryCode": country,
                                "email": self.s["email"],
                                "ifencrypt": 1,
                                "options": '{"group": 1}',
                                "passwd": _enc_password(str(pub), exp, self.s["password"]),
                                "token": token["token"],
                            },
                            need_sid=False,
                        )
                        self.sid = str(login.get("sid") or "")
                        self.uid = str(login.get("uid") or login.get("euid") or "")
                        if not self.sid:
                            raise RuntimeError(f"{login_a} returned no sid")
                        log.info("OEM classic login ok region=%s action=%s uid=%s", region, login_a, self.uid)
                        return login
                    except Exception as exc:
                        last = exc
                        log.warning("OEM classic %s %s cc=%r: %s", region, token_a, country, exc)
        raise RuntimeError(f"OEM classic login failed for schema {self.s['schema']}: {last}")

    def login(self) -> dict[str, Any]:
        if not self.s["email"] or not self.s["password"]:
            raise RuntimeError("CBI_LOGIN_EMAIL / CBI_LOGIN_PASSWORD required for OEM login")
        last: Exception | None = None
        countries = []
        for country in (self.s["country"], "27", ""):
            if country not in countries:
                countries.append(country)
        # Token-only first: find a Thing SDK 5 identity that the OEM cloud accepts,
        # then submit the password once for that identity (do not spray logins).
        accepted: list[tuple[dict[str, str], str]] = []
        for profile in thing_profiles(self.s):
            for country in countries:
                result = self.probe_token(profile, self.s["email"], country)
                if result == "OK":
                    accepted.append((profile, country))
                    break
                last = RuntimeError(result)
                log.warning(
                    "OEM thing5 token app=%s et=%s cc=%r: %s",
                    profile["app_id"][-4:],
                    profile.get("et"),
                    country,
                    result,
                )
        for profile, country in accepted:
            try:
                return self._login_thing5(profile, country)
            except Exception as exc:
                last = exc
                log.warning("OEM thing5 login app=%s et=%s: %s", profile["app_id"][-4:], profile.get("et"), exc)
        if _cfg("CBI_OEM_CLASSIC") == "1":
            try:
                return self._login_classic()
            except Exception as exc:
                last = exc
        raise RuntimeError(f"OEM login failed for schema {self.s['schema']}: {last}")

    def list_homes(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for action in ("tuya.m.location.list", "thing.m.location.list", "m.life.home.space.list"):
            try:
                result = self._api(action, {} if self.oem_kind == "thing5" else None)
            except Exception as exc:
                log.warning("OEM %s: %s", action, exc)
                continue
            homes = result if isinstance(result, list) else []
            if isinstance(result, dict):
                homes = result.get("list") or result.get("homes") or result.get("result") or []
            for h in homes if isinstance(homes, list) else []:
                if not isinstance(h, dict):
                    continue
                hid = str(h.get("groupId") or h.get("homeId") or h.get("gid") or h.get("id") or "")
                if hid:
                    out.append({"id": hid, "name": str(h.get("name") or h.get("group") or "").strip(), "role": h.get("role")})
            if out:
                return out
        return out

    def list_devices(self, home_id: str) -> list[dict[str, Any]]:
        extra = {"gid": str(home_id)}
        for action, version in (
            ("tuya.m.my.group.device.list", "1.0"),
            ("thing.m.my.group.device.list", "1.0"),
            ("m.life.my.group.device.list", "2.2"),
        ):
            try:
                result = self._api(action, extra=extra, version=version)
                if isinstance(result, list):
                    return [d for d in result if isinstance(d, dict)]
                if isinstance(result, dict):
                    devices = result.get("devices") or result.get("list") or []
                    if isinstance(devices, list):
                        return [d for d in devices if isinstance(d, dict)]
            except Exception as exc:
                log.warning("OEM %s home=%s: %s", action, home_id, exc)
        return []

    def send_dps(self, device_id: str, home_id: str, dps: dict[str, Any]) -> Any:
        payload = {"devId": device_id, "gwId": device_id, "dps": dps}
        extra = {"gid": str(home_id)}
        last: Exception | None = None
        for action in ("tuya.m.device.dp.publish", "thing.m.device.dp.publish"):
            try:
                return self._api(action, payload, extra)
            except Exception as exc:
                last = exc
        raise RuntimeError(f"OEM command failed: {last}")

    def snapshot_devices(self, mapped: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        seen: list[dict[str, Any]] = []
        out: list[dict[str, Any]] = []
        homes = self.list_homes()
        watch_all = not mapped
        for h in homes:
            devices = self.list_devices(h["id"])
            seen.append({"id": h["id"], "name": h["name"], "devices": len(devices), "role": h.get("role")})
            if not watch_all and h["id"] not in mapped:
                log.warning("unmapped OEM home %s %r", h["id"], h["name"])
                continue
            for d in devices:
                row = device_to_snapshot(d, h["name"], h["id"])
                if row["id"]:
                    out.append(row)
        return seen, out


def connect_oem(settings: dict[str, str] | None = None) -> OemClient:
    client = OemClient(settings)
    client.login()
    return client


def session_record(client: OemClient) -> dict[str, Any]:
    return {
        "kind": "oem",
        "oem_kind": client.oem_kind,
        "schema": client.s["schema"],
        "username": client.username,
        "uid": client.uid,
        "sid": client.sid,
        "ecode": client.ecode,
        "endpoint": client.endpoint,
        "region": client.region,
        "app_key": client.s["app_key"],
        "app_id": client.profile.get("app_id") or client.s["app_key"],
        "et": client.profile.get("et") or "",
        "ttid": client.profile.get("ttid") or "",
        "at": int(time.time()),
    }


def write_session(path: Path, client: OemClient) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(session_record(client), separators=(",", ":")), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def client_from_session(path: Path, settings: dict[str, str] | None = None) -> OemClient:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("kind") != "oem" or not raw.get("sid"):
        raise RuntimeError("session.json is not an OEM app session")
    client = OemClient(settings)
    client.sid = str(raw["sid"])
    client.uid = str(raw.get("uid") or "")
    client.username = str(raw.get("username") or client.username)
    client.ecode = str(raw["ecode"]) if raw.get("ecode") else None
    if raw.get("region"):
        client.region = str(raw["region"])
    if raw.get("app_key"):
        client.s["app_key"] = str(raw["app_key"])
    if raw.get("oem_kind") == "thing5":
        app_id = str(raw.get("app_id") or raw.get("app_key") or CBI_CV_KEY)
        match = next((p for p in thing_profiles(client.s) if p["app_id"] == app_id and (not raw.get("et") or p["et"] == raw.get("et"))), None)
        client.apply_profile(match or {
            "app_id": app_id,
            "app_key": client.s["bmp"],
            "app_secret": client.s["app_secret"],
            "package": client.s["package"],
            "cert": client.s["cert"],
            "et": str(raw.get("et") or "3"),
            "ttid": str(raw.get("ttid") or f"sdk_international@{app_id}"),
            "app_version": client.s["app_version"],
            "sdk_version": "5.2.0",
            "device_core_version": "5.2.0",
            "app_rn_version": "5.2",
            "schema": client.s["schema"],
        })
    return client
