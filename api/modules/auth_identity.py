"""
SailingSA signup/login identity, challenges, and remembered devices.

No browser-posted provider IDs. Proofs and PINs live in a shared store so any
worker can verify them. Link landings require an explicit confirm click.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

PROOF_TTL_SEC = 15 * 60
CHALLENGE_TTL_SEC = 10 * 60
LINK_TTL_SEC = 30 * 60
REMEMBER_TTL_SEC = 30 * 24 * 3600
MAX_ATTEMPTS = 5
MAX_RESENDS = 3
RESEND_COOLDOWN_SEC = 45
PIN_LEN = 6
CLAIM_PIN_LEN = 4
MIN_PASSWORD_LEN = 7
PUBLIC_SAS_PREFIX = "PUB_"
ALLOWED_RETURN_HOSTS = {
    "sailingsa.co.za",
    "www.sailingsa.co.za",
    "timadvisor.co.za",
    "www.timadvisor.co.za",
}

OWNERSHIP_SELF = "self"
OWNERSHIP_GUARDIAN = "guardian"
OWNERSHIP_PUBLIC = "general_public"
OWNERSHIP_PENDING = "pending_match"


def _now() -> float:
    return time.time()


def _secret() -> bytes:
    return (os.getenv("AUTH_IDENTITY_SECRET") or os.getenv("SECRET_KEY") or "sailingsa-auth-identity").encode(
        "utf-8"
    )


def hash_secret(value: str) -> str:
    return hmac.new(_secret(), str(value).encode("utf-8"), hashlib.sha256).hexdigest()


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def normalize_phone(raw: Any) -> str:
    """Optional phone: empty stays empty. Else SA local 10 digits starting with 0."""
    if raw is None:
        return ""
    d = re.sub(r"\D", "", str(raw).strip())
    if not d:
        return ""
    if d.startswith("27") and len(d) >= 11:
        d = "0" + d[2:]
    if d.startswith("27") and len(d) == 10:
        d = "0" + d[1:]
    return d[:10]


def phone_valid_or_empty(raw: Any) -> Tuple[bool, str]:
    local = normalize_phone(raw)
    if local == "":
        return True, ""
    if len(local) == 10 and local.startswith("0"):
        return True, local
    return False, local


def phone_intl(local10: str) -> str:
    if local10.startswith("0") and len(local10) == 10:
        return "27" + local10[1:]
    return local10


def is_real_sas_id(sas_id: Any) -> bool:
    s = str(sas_id or "").strip()
    if not s or s.startswith("FB_") or s.startswith("TMP_") or s.startswith(PUBLIC_SAS_PREFIX):
        return False
    return s.isdigit()


def new_public_sas_id() -> str:
    """Placeholder key for a general-public account. Not a sailor SAS ID."""
    return PUBLIC_SAS_PREFIX + secrets.token_hex(8)


def valid_new_password(password: Any) -> Tuple[bool, str]:
    raw = str(password or "")
    if len(raw) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters"
    return True, raw


def classify_ownership(relationship: Any, sas_id: Any) -> str:
    rel = str(relationship or "self").strip().lower()
    if rel in {"not_me", "unknown", "pending"}:
        return OWNERSHIP_PENDING
    if rel in {"guardian", "parent", "child"}:
        return OWNERSHIP_GUARDIAN
    if rel in {"public", "general_public", "member"}:
        return OWNERSHIP_PUBLIC
    if sas_id and is_real_sas_id(sas_id):
        return OWNERSHIP_SELF
    return OWNERSHIP_PENDING


def refuse_fabricated_sas(sas_id: Any) -> None:
    if sas_id and not is_real_sas_id(sas_id) and str(sas_id).strip():
        raise ValueError("Cannot use a temporary or fabricated SAS ID")


@dataclass
class IdentityProof:
    token_hash: str
    provider: str
    provider_id: str
    email: str = ""
    email_verified: bool = False
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    picture: str = ""
    expires_at: float = 0.0
    used_at: float = 0.0


@dataclass
class Challenge:
    id: str
    purpose: str
    channel: str
    destination: str
    code_hash: str = ""
    link_hash: str = ""
    expires_at: float = 0.0
    attempts: int = 0
    resends: int = 0
    consumed_at: float = 0.0
    confirm_pending: bool = False
    account_hint: str = ""
    worker_id: str = ""
    created_at: float = field(default_factory=_now)


@dataclass
class RememberedDevice:
    token_hash: str
    account_id: Any
    sas_id: str = ""
    login_method: str = ""
    display_name: str = ""
    expires_at: float = 0.0
    revoked_at: float = 0.0


class MemoryStore:
    """Shared-process store for tests; SQL adapter uses the same method names."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.proofs: Dict[str, IdentityProof] = {}
        self.challenges: Dict[str, Challenge] = {}
        self.remembers: Dict[str, RememberedDevice] = {}
        self.contacts: Dict[str, Dict[str, Any]] = {}

    def put_proof(self, proof: IdentityProof) -> None:
        self.proofs[proof.token_hash] = proof

    def get_proof(self, token_hash: str) -> Optional[IdentityProof]:
        return self.proofs.get(token_hash)

    def put_challenge(self, ch: Challenge) -> None:
        self.challenges[ch.id] = ch

    def get_challenge(self, cid: str) -> Optional[Challenge]:
        return self.challenges.get(cid)

    def find_open_challenge(self, purpose: str, destination: str) -> Optional[Challenge]:
        now = _now()
        for ch in self.challenges.values():
            if (
                ch.purpose == purpose
                and ch.destination == destination
                and not ch.consumed_at
                and ch.expires_at > now
            ):
                return ch
        return None

    def find_challenge_by_link_hash(self, link_hash: str) -> Optional[Challenge]:
        for ch in self.challenges.values():
            if ch.link_hash == link_hash:
                return ch
        return None

    def put_remember(self, rem: RememberedDevice) -> None:
        self.remembers[rem.token_hash] = rem

    def get_remember(self, token_hash: str) -> Optional[RememberedDevice]:
        return self.remembers.get(token_hash)

    def save_contact(self, account_key: str, payload: Dict[str, Any]) -> None:
        self.contacts[account_key] = payload

    def get_contact(self, account_key: str) -> Optional[Dict[str, Any]]:
        return self.contacts.get(account_key)

    def consume_proof(self, token_hash: str) -> IdentityProof:
        with self._lock:
            proof = self.proofs.get(token_hash)
            if not proof:
                raise ValueError("Unknown or expired identity proof")
            if proof.used_at:
                raise ValueError("Identity proof already used")
            if proof.expires_at <= _now():
                raise ValueError("Identity proof expired")
            proof.used_at = _now()
            return proof

    def _pin_precheck(self, challenge_id: str, pin: str, worker_id: str = "", expected_purpose: str = "") -> Challenge:
        pin_hash = hash_secret(re.sub(r"\D", "", str(pin)))
        ch = self.challenges.get(challenge_id)
        if not ch:
            raise ValueError("Unknown challenge")
        if expected_purpose and ch.purpose != expected_purpose:
            raise ValueError("Wrong verification purpose")
        if ch.consumed_at:
            raise ValueError("PIN already used")
        if ch.expires_at <= _now():
            raise ValueError("PIN expired")
        if ch.attempts >= MAX_ATTEMPTS:
            raise ValueError("Too many attempts")
        if worker_id:
            ch.worker_id = worker_id
        if ch.code_hash != pin_hash:
            ch.attempts += 1
            raise ValueError("Incorrect PIN")
        return ch

    def match_pin(self, challenge_id: str, pin: str, worker_id: str = "", expected_purpose: str = "") -> Challenge:
        with self._lock:
            return self._pin_precheck(challenge_id, pin, worker_id, expected_purpose)

    def consume_matched(self, challenge_id: str) -> Challenge:
        with self._lock:
            ch = self.challenges.get(challenge_id)
            if not ch:
                raise ValueError("Unknown challenge")
            if ch.consumed_at:
                raise ValueError("PIN already used")
            ch.attempts += 1
            ch.consumed_at = _now()
            ch.confirm_pending = False
            return ch

    def consume_pin(self, challenge_id: str, pin: str, worker_id: str = "", expected_purpose: str = "") -> Challenge:
        with self._lock:
            ch = self._pin_precheck(challenge_id, pin, worker_id, expected_purpose)
            ch.attempts += 1
            ch.consumed_at = _now()
            ch.confirm_pending = False
            return ch

    def consume_link(self, raw_token: str) -> Challenge:
        link_hash = hash_secret(raw_token)
        with self._lock:
            ch = None
            for item in self.challenges.values():
                if item.link_hash == link_hash:
                    ch = item
                    break
            if not ch:
                raise ValueError("Unknown verification link")
            if ch.consumed_at:
                raise ValueError("Verification link already used")
            if ch.expires_at <= _now():
                raise ValueError("Verification link expired")
            ch.consumed_at = _now()
            ch.confirm_pending = False
            return ch


STORE: Any = MemoryStore()
_SQL_FACTORY: Optional[Callable] = None
_SQL_RELEASE: Optional[Callable] = None


def _as_dt(value: Any) -> Optional[datetime]:
    if value in (None, 0, 0.0, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def _from_dt(value: Any) -> float:
    if value in (None, 0, 0.0, ""):
        return 0.0
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    return float(value)


def _row_map(row: Any, cols: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return dict(zip(cols, row))


class SqlStore:
    """Postgres-backed store so gunicorn workers share proofs, PINs, and remember tokens."""

    def __init__(self, connect: Callable, release: Optional[Callable] = None) -> None:
        self.connect = connect
        self.release = release
        self._ensured = False

    def _ctx(self):
        conn = self.connect()
        cur = conn.cursor()
        if not self._ensured:
            ensure_tables(cur)
            conn.commit()
            self._ensured = True
        return conn, cur

    def _done(self, conn, cur, ok: bool = True) -> None:
        try:
            if ok:
                conn.commit()
            else:
                conn.rollback()
        except Exception:
            pass
        try:
            cur.close()
        except Exception:
            pass
        if self.release:
            self.release(conn)

    def put_proof(self, proof: IdentityProof) -> None:
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                INSERT INTO public.auth_identity_proofs
                (token_hash, provider, provider_id, email, email_verified, first_name, last_name, full_name, picture, expires_at, used_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (token_hash) DO UPDATE SET
                    used_at = EXCLUDED.used_at,
                    expires_at = EXCLUDED.expires_at
                """,
                (
                    proof.token_hash,
                    proof.provider,
                    proof.provider_id,
                    proof.email,
                    proof.email_verified,
                    proof.first_name,
                    proof.last_name,
                    proof.full_name,
                    proof.picture,
                    _as_dt(proof.expires_at),
                    _as_dt(proof.used_at),
                ),
            )
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise

    def get_proof(self, token_hash: str) -> Optional[IdentityProof]:
        cols = (
            "token_hash",
            "provider",
            "provider_id",
            "email",
            "email_verified",
            "first_name",
            "last_name",
            "full_name",
            "picture",
            "expires_at",
            "used_at",
        )
        conn, cur = self._ctx()
        try:
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_identity_proofs WHERE token_hash = %s",
                (token_hash,),
            )
            row = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        if not row:
            return None
        return IdentityProof(
            token_hash=row["token_hash"],
            provider=row["provider"],
            provider_id=row["provider_id"],
            email=row.get("email") or "",
            email_verified=bool(row.get("email_verified")),
            first_name=row.get("first_name") or "",
            last_name=row.get("last_name") or "",
            full_name=row.get("full_name") or "",
            picture=row.get("picture") or "",
            expires_at=_from_dt(row.get("expires_at")),
            used_at=_from_dt(row.get("used_at")),
        )

    def consume_proof(self, token_hash: str) -> IdentityProof:
        cols = (
            "token_hash",
            "provider",
            "provider_id",
            "email",
            "email_verified",
            "first_name",
            "last_name",
            "full_name",
            "picture",
            "expires_at",
            "used_at",
        )
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                UPDATE public.auth_identity_proofs
                SET used_at = NOW()
                WHERE token_hash = %s
                  AND used_at IS NULL
                  AND expires_at > NOW()
                RETURNING """
                + ", ".join(cols),
                (token_hash,),
            )
            row = _row_map(cur.fetchone(), cols)
            if row:
                self._done(conn, cur, True)
                return IdentityProof(
                    token_hash=row["token_hash"],
                    provider=row["provider"],
                    provider_id=row["provider_id"],
                    email=row.get("email") or "",
                    email_verified=bool(row.get("email_verified")),
                    first_name=row.get("first_name") or "",
                    last_name=row.get("last_name") or "",
                    full_name=row.get("full_name") or "",
                    picture=row.get("picture") or "",
                    expires_at=_from_dt(row.get("expires_at")),
                    used_at=_from_dt(row.get("used_at")),
                )
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_identity_proofs WHERE token_hash = %s",
                (token_hash,),
            )
            found = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        if not found:
            raise ValueError("Unknown or expired identity proof")
        if found.get("used_at"):
            raise ValueError("Identity proof already used")
        raise ValueError("Identity proof expired")

    def _challenge_from_row(self, row: Optional[Dict[str, Any]]) -> Optional[Challenge]:
        if not row:
            return None
        return Challenge(
            id=row["id"],
            purpose=row["purpose"],
            channel=row["channel"],
            destination=row["destination"],
            code_hash=row.get("code_hash") or "",
            link_hash=row.get("link_hash") or "",
            expires_at=_from_dt(row.get("expires_at")),
            attempts=int(row.get("attempts") or 0),
            resends=int(row.get("resends") or 0),
            consumed_at=_from_dt(row.get("consumed_at")),
            confirm_pending=bool(row.get("confirm_pending")),
            account_hint=row.get("account_hint") or "",
            worker_id=row.get("worker_id") or "",
            created_at=_from_dt(row.get("created_at")) or _now(),
        )

    _CH_COLS = (
        "id",
        "purpose",
        "channel",
        "destination",
        "code_hash",
        "link_hash",
        "expires_at",
        "attempts",
        "resends",
        "consumed_at",
        "confirm_pending",
        "account_hint",
        "worker_id",
        "created_at",
    )

    def put_challenge(self, ch: Challenge) -> None:
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                INSERT INTO public.auth_challenges
                (id, purpose, channel, destination, code_hash, link_hash, expires_at, attempts, resends,
                 consumed_at, confirm_pending, account_hint, worker_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    code_hash = EXCLUDED.code_hash,
                    link_hash = EXCLUDED.link_hash,
                    expires_at = EXCLUDED.expires_at,
                    attempts = EXCLUDED.attempts,
                    resends = EXCLUDED.resends,
                    consumed_at = EXCLUDED.consumed_at,
                    confirm_pending = EXCLUDED.confirm_pending,
                    worker_id = EXCLUDED.worker_id
                """,
                (
                    ch.id,
                    ch.purpose,
                    ch.channel,
                    ch.destination,
                    ch.code_hash,
                    ch.link_hash,
                    _as_dt(ch.expires_at),
                    ch.attempts,
                    ch.resends,
                    _as_dt(ch.consumed_at),
                    ch.confirm_pending,
                    ch.account_hint,
                    ch.worker_id,
                    _as_dt(ch.created_at),
                ),
            )
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise

    def get_challenge(self, cid: str) -> Optional[Challenge]:
        conn, cur = self._ctx()
        try:
            cur.execute(
                "SELECT " + ", ".join(self._CH_COLS) + " FROM public.auth_challenges WHERE id = %s",
                (cid,),
            )
            row = _row_map(cur.fetchone(), self._CH_COLS)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        return self._challenge_from_row(row)

    def find_open_challenge(self, purpose: str, destination: str) -> Optional[Challenge]:
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                SELECT """
                + ", ".join(self._CH_COLS)
                + """
                FROM public.auth_challenges
                WHERE purpose = %s AND destination = %s AND consumed_at IS NULL AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (purpose, destination),
            )
            row = _row_map(cur.fetchone(), self._CH_COLS)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        return self._challenge_from_row(row)

    def find_challenge_by_link_hash(self, link_hash: str) -> Optional[Challenge]:
        conn, cur = self._ctx()
        try:
            cur.execute(
                "SELECT " + ", ".join(self._CH_COLS) + " FROM public.auth_challenges WHERE link_hash = %s LIMIT 1",
                (link_hash,),
            )
            row = _row_map(cur.fetchone(), self._CH_COLS)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        return self._challenge_from_row(row)

    def put_remember(self, rem: RememberedDevice) -> None:
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                INSERT INTO public.auth_remembered_devices
                (token_hash, account_id, sas_id, login_method, display_name, expires_at, revoked_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (token_hash) DO UPDATE SET revoked_at = EXCLUDED.revoked_at
                """,
                (
                    rem.token_hash,
                    rem.account_id,
                    rem.sas_id,
                    rem.login_method,
                    rem.display_name,
                    _as_dt(rem.expires_at),
                    _as_dt(rem.revoked_at),
                ),
            )
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise

    def get_remember(self, token_hash: str) -> Optional[RememberedDevice]:
        cols = ("token_hash", "account_id", "sas_id", "login_method", "display_name", "expires_at", "revoked_at")
        conn, cur = self._ctx()
        try:
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_remembered_devices WHERE token_hash = %s",
                (token_hash,),
            )
            row = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        if not row:
            return None
        return RememberedDevice(
            token_hash=row["token_hash"],
            account_id=row.get("account_id"),
            sas_id=row.get("sas_id") or "",
            login_method=row.get("login_method") or "",
            display_name=row.get("display_name") or "",
            expires_at=_from_dt(row.get("expires_at")),
            revoked_at=_from_dt(row.get("revoked_at")),
        )

    def save_contact(self, account_key: str, payload: Dict[str, Any]) -> None:
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                INSERT INTO public.auth_verified_contacts
                (account_key, email, phone, provenance, ownership, sas_id, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_key) DO UPDATE SET
                    email = EXCLUDED.email,
                    phone = EXCLUDED.phone,
                    provenance = EXCLUDED.provenance,
                    ownership = EXCLUDED.ownership,
                    sas_id = EXCLUDED.sas_id,
                    verified_at = EXCLUDED.verified_at
                """,
                (
                    account_key,
                    payload.get("email") or "",
                    payload.get("phone") or "",
                    payload.get("provenance") or "",
                    payload.get("ownership") or "",
                    payload.get("sas_id") or "",
                    _as_dt(payload.get("verified_at")),
                ),
            )
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise

    def get_contact(self, account_key: str) -> Optional[Dict[str, Any]]:
        cols = ("account_key", "email", "phone", "provenance", "ownership", "sas_id", "verified_at")
        conn, cur = self._ctx()
        try:
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_verified_contacts WHERE account_key = %s",
                (account_key,),
            )
            row = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        return row

    def match_pin(self, challenge_id: str, pin: str, worker_id: str = "", expected_purpose: str = "") -> Challenge:
        pin_hash = hash_secret(re.sub(r"\D", "", str(pin)))
        cols = self._CH_COLS
        conn, cur = self._ctx()
        try:
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_challenges WHERE id = %s",
                (challenge_id,),
            )
            found = _row_map(cur.fetchone(), cols)
            if not found:
                self._done(conn, cur, True)
                raise ValueError("Unknown challenge")
            ch = self._challenge_from_row(found)
            if expected_purpose and ch.purpose != expected_purpose:
                self._done(conn, cur, True)
                raise ValueError("Wrong verification purpose")
            if ch.consumed_at:
                self._done(conn, cur, True)
                raise ValueError("PIN already used")
            if ch.expires_at <= _now():
                self._done(conn, cur, True)
                raise ValueError("PIN expired")
            if ch.attempts >= MAX_ATTEMPTS:
                self._done(conn, cur, True)
                raise ValueError("Too many attempts")
            if ch.code_hash != pin_hash:
                cur.execute(
                    """
                    UPDATE public.auth_challenges
                    SET attempts = attempts + 1,
                        worker_id = COALESCE(NULLIF(%s, ''), worker_id)
                    WHERE id = %s AND consumed_at IS NULL
                    """,
                    (worker_id, challenge_id),
                )
                self._done(conn, cur, True)
                raise ValueError("Incorrect PIN")
            if worker_id:
                cur.execute(
                    "UPDATE public.auth_challenges SET worker_id = %s WHERE id = %s",
                    (worker_id, challenge_id),
                )
                ch.worker_id = worker_id
            self._done(conn, cur, True)
            return ch
        except ValueError:
            raise
        except Exception:
            self._done(conn, cur, False)
            raise

    def consume_matched(self, challenge_id: str) -> Challenge:
        cols = self._CH_COLS
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                UPDATE public.auth_challenges
                SET consumed_at = NOW(), confirm_pending = FALSE, attempts = attempts + 1
                WHERE id = %s AND consumed_at IS NULL AND expires_at > NOW()
                RETURNING """
                + ", ".join(cols),
                (challenge_id,),
            )
            row = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        if not row:
            raise ValueError("PIN already used")
        return self._challenge_from_row(row)

    def consume_pin(self, challenge_id: str, pin: str, worker_id: str = "", expected_purpose: str = "") -> Challenge:
        pin_hash = hash_secret(re.sub(r"\D", "", str(pin)))
        cols = self._CH_COLS
        purpose_sql = " AND purpose = %s" if expected_purpose else ""
        purpose_args = (expected_purpose,) if expected_purpose else ()
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                UPDATE public.auth_challenges
                SET consumed_at = NOW(), confirm_pending = FALSE,
                    attempts = attempts + 1,
                    worker_id = COALESCE(NULLIF(%s, ''), worker_id)
                WHERE id = %s
                  AND consumed_at IS NULL
                  AND expires_at > NOW()
                  AND attempts < %s
                  AND code_hash = %s"""
                + purpose_sql
                + """
                RETURNING """
                + ", ".join(cols),
                (worker_id, challenge_id, MAX_ATTEMPTS, pin_hash) + purpose_args,
            )
            row = _row_map(cur.fetchone(), cols)
            if row:
                self._done(conn, cur, True)
                return self._challenge_from_row(row)
            if expected_purpose:
                cur.execute(
                    "SELECT " + ", ".join(cols) + " FROM public.auth_challenges WHERE id = %s",
                    (challenge_id,),
                )
                maybe = _row_map(cur.fetchone(), cols)
                if maybe and str(maybe.get("purpose") or "") != expected_purpose:
                    self._done(conn, cur, True)
                    raise ValueError("Wrong verification purpose")
            cur.execute(
                """
                UPDATE public.auth_challenges
                SET attempts = attempts + 1,
                    worker_id = COALESCE(NULLIF(%s, ''), worker_id)
                WHERE id = %s
                  AND consumed_at IS NULL
                  AND expires_at > NOW()
                  AND attempts < %s
                RETURNING """
                + ", ".join(cols),
                (worker_id, challenge_id, MAX_ATTEMPTS),
            )
            fail = _row_map(cur.fetchone(), cols)
            if fail:
                self._done(conn, cur, True)
                raise ValueError("Incorrect PIN")
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_challenges WHERE id = %s",
                (challenge_id,),
            )
            found = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except ValueError:
            raise
        except Exception:
            self._done(conn, cur, False)
            raise
        if not found:
            raise ValueError("Unknown challenge")
        ch = self._challenge_from_row(found)
        if ch.consumed_at:
            raise ValueError("PIN already used")
        if ch.expires_at <= _now():
            raise ValueError("PIN expired")
        if ch.attempts >= MAX_ATTEMPTS:
            raise ValueError("Too many attempts")
        raise ValueError("Incorrect PIN")

    def consume_link(self, raw_token: str) -> Challenge:
        cols = self._CH_COLS
        conn, cur = self._ctx()
        try:
            cur.execute(
                """
                UPDATE public.auth_challenges
                SET consumed_at = NOW(), confirm_pending = FALSE
                WHERE link_hash = %s
                  AND consumed_at IS NULL
                  AND expires_at > NOW()
                RETURNING """
                + ", ".join(cols),
                (hash_secret(raw_token),),
            )
            row = _row_map(cur.fetchone(), cols)
            if row:
                self._done(conn, cur, True)
                return self._challenge_from_row(row)
            cur.execute(
                "SELECT " + ", ".join(cols) + " FROM public.auth_challenges WHERE link_hash = %s LIMIT 1",
                (hash_secret(raw_token),),
            )
            found = _row_map(cur.fetchone(), cols)
            self._done(conn, cur, True)
        except Exception:
            self._done(conn, cur, False)
            raise
        if not found:
            raise ValueError("Unknown verification link")
        ch = self._challenge_from_row(found)
        if ch.consumed_at:
            raise ValueError("Verification link already used")
        if ch.expires_at <= _now():
            raise ValueError("Verification link expired")
        raise ValueError("Verification link already used")


def bind_sql_factory(connect: Callable, release: Optional[Callable] = None) -> SqlStore:
    """Point STORE at Postgres so proofs/PINs survive worker hops."""
    global STORE, _SQL_FACTORY, _SQL_RELEASE
    _SQL_FACTORY = connect
    _SQL_RELEASE = release
    STORE = SqlStore(connect, release)
    return STORE


def get_store() -> Any:
    return STORE


def resolve_signup_identity(relationship: Any, sas_id: Any) -> Tuple[str, str]:
    """Separate contact/login from sailor ownership. Never invent a SAS ID."""
    ownership = classify_ownership(relationship, sas_id)
    sid = str(sas_id or "").strip()
    refuse_fabricated_sas(sid)
    if ownership == OWNERSHIP_SELF:
        if not is_real_sas_id(sid):
            raise ValueError("Self ownership requires a real SAS ID")
        return ownership, sid
    if ownership == OWNERSHIP_GUARDIAN:
        if sid and not is_real_sas_id(sid):
            raise ValueError("Guardian link requires a real SAS ID or none")
        return ownership, sid
    if ownership == OWNERSHIP_PUBLIC:
        return ownership, ""
    return ownership, sid if is_real_sas_id(sid) else ""


def account_writes_sas(ownership: str) -> bool:
    return ownership == OWNERSHIP_SELF


def refuse_silent_sas_overwrite(existing_sas: Any, new_sas: Any) -> None:
    old = str(existing_sas or "").strip()
    new = str(new_sas or "").strip()
    if old and is_real_sas_id(old) and new and old != new:
        raise ValueError("This login is already linked to another sailor")


def issue_identity_proof(store: Any, provider: str, profile: Dict[str, Any]) -> str:
    token = new_token()
    proof = IdentityProof(
        token_hash=hash_secret(token),
        provider=str(provider),
        provider_id=str(profile.get("provider_id") or "").strip(),
        email=str(profile.get("email") or "").strip(),
        email_verified=bool(profile.get("email_verified")),
        first_name=str(profile.get("first_name") or "").strip(),
        last_name=str(profile.get("last_name") or "").strip(),
        full_name=str(profile.get("full_name") or "").strip(),
        picture=str(profile.get("picture") or "").strip(),
        expires_at=_now() + PROOF_TTL_SEC,
    )
    if not proof.provider_id:
        raise ValueError("provider_id required")
    store.put_proof(proof)
    return token


def consume_identity_proof(store: Any, token: str) -> IdentityProof:
    if not token:
        raise ValueError("Missing identity proof")
    token_hash = hash_secret(token)
    if hasattr(store, "consume_proof"):
        return store.consume_proof(token_hash)
    proof = store.get_proof(token_hash)
    if not proof:
        raise ValueError("Unknown or expired identity proof")
    if proof.used_at:
        raise ValueError("Identity proof already used")
    if proof.expires_at <= _now():
        raise ValueError("Identity proof expired")
    proof.used_at = _now()
    store.put_proof(proof)
    return proof


def peek_identity_proof(store: Any, token: str) -> Optional[IdentityProof]:
    if not token:
        return None
    proof = store.get_proof(hash_secret(token))
    if not proof or proof.used_at or proof.expires_at <= _now():
        return None
    return proof


def issue_pin_challenge(
    store: Any,
    *,
    purpose: str,
    channel: str,
    destination: str,
    account_hint: str = "",
    worker_id: str = "",
    pin_len: int = PIN_LEN,
) -> Tuple[str, str]:
    dest = destination.strip().lower() if channel == "email" else normalize_phone(destination)
    if channel == "email" and "@" not in dest:
        raise ValueError("Valid email required")
    if channel == "whatsapp":
        ok, dest = phone_valid_or_empty(destination)
        if not ok or not dest:
            raise ValueError("Enter a 10-digit WhatsApp number starting with 0")
    existing = store.find_open_challenge(purpose, dest)
    if existing and _now() - existing.created_at < RESEND_COOLDOWN_SEC:
        raise ValueError("Wait a moment before sending another code")
    if existing and existing.resends >= MAX_RESENDS:
        raise ValueError("Too many resends")
    digits = int(pin_len) if pin_len else PIN_LEN
    if digits < 4:
        digits = 4
    if digits > 8:
        digits = 8
    pin = f"{secrets.randbelow(10 ** digits):0{digits}d}"
    cid = new_token(12)
    if existing:
        existing.resends += 1
        existing.code_hash = hash_secret(pin)
        existing.expires_at = _now() + CHALLENGE_TTL_SEC
        existing.attempts = 0
        existing.worker_id = worker_id or existing.worker_id
        store.put_challenge(existing)
        return existing.id, pin
    ch = Challenge(
        id=cid,
        purpose=purpose,
        channel=channel,
        destination=dest,
        code_hash=hash_secret(pin),
        expires_at=_now() + CHALLENGE_TTL_SEC,
        account_hint=account_hint,
        worker_id=worker_id,
    )
    store.put_challenge(ch)
    return cid, pin


def issue_link_challenge(
    store: Any,
    *,
    purpose: str,
    channel: str,
    destination: str,
    account_hint: str = "",
) -> Tuple[str, str]:
    dest = destination.strip().lower() if channel == "email" else normalize_phone(destination)
    raw = new_token()
    ch = Challenge(
        id=new_token(12),
        purpose=purpose,
        channel=channel,
        destination=dest,
        link_hash=hash_secret(raw),
        expires_at=_now() + LINK_TTL_SEC,
        confirm_pending=True,
        account_hint=account_hint,
    )
    store.put_challenge(ch)
    return ch.id, raw


def preview_link_challenge(store: Any, raw_token: str) -> Challenge:
    ch = store.find_challenge_by_link_hash(hash_secret(raw_token))
    if not ch:
        raise ValueError("Unknown verification link")
    if ch.consumed_at:
        raise ValueError("Verification link already used")
    if ch.expires_at <= _now():
        raise ValueError("Verification link expired")
    return ch


def confirm_link_challenge(store: Any, raw_token: str) -> Challenge:
    if hasattr(store, "consume_link"):
        return store.consume_link(raw_token)
    ch = preview_link_challenge(store, raw_token)
    ch.consumed_at = _now()
    ch.confirm_pending = False
    store.put_challenge(ch)
    return ch


def _resolve_challenge_id(store: Any, challenge_id: str, purpose: str, destination: str) -> str:
    cid = str(challenge_id or "").strip()
    if cid:
        return cid
    if purpose and destination:
        dest = destination.strip().lower() if "@" in str(destination) else normalize_phone(destination)
        if "@" in str(destination):
            dest = str(destination).strip().lower()
        open_ch = store.find_open_challenge(purpose, dest)
        if not open_ch:
            raise ValueError("Unknown challenge")
        return open_ch.id
    raise ValueError("Unknown challenge")


def match_pin(
    store: Any,
    challenge_id: str,
    pin: str,
    worker_id: str = "",
    purpose: str = "",
    destination: str = "",
    expected_purpose: str = "",
) -> Challenge:
    cid = _resolve_challenge_id(store, challenge_id, purpose or expected_purpose, destination)
    want = expected_purpose or purpose
    if hasattr(store, "match_pin"):
        return store.match_pin(cid, pin, worker_id, expected_purpose=want)
    if hasattr(store, "consume_pin"):
        ch = store.get_challenge(cid)
        if not ch:
            raise ValueError("Unknown challenge")
        if want and ch.purpose != want:
            raise ValueError("Wrong verification purpose")
        if ch.consumed_at:
            raise ValueError("PIN already used")
        if hash_secret(re.sub(r"\D", "", str(pin))) != ch.code_hash:
            ch.attempts += 1
            store.put_challenge(ch)
            raise ValueError("Incorrect PIN")
        return ch
    raise ValueError("Unknown challenge")


def consume_matched(store: Any, challenge_id: str) -> Challenge:
    if hasattr(store, "consume_matched"):
        return store.consume_matched(challenge_id)
    ch = store.get_challenge(challenge_id)
    if not ch:
        raise ValueError("Unknown challenge")
    if ch.consumed_at:
        raise ValueError("PIN already used")
    ch.consumed_at = _now()
    store.put_challenge(ch)
    return ch


def verify_pin(
    store: Any,
    challenge_id: str,
    pin: str,
    worker_id: str = "",
    purpose: str = "",
    destination: str = "",
    expected_purpose: str = "",
) -> Challenge:
    cid = _resolve_challenge_id(store, challenge_id, purpose or expected_purpose, destination)
    want = expected_purpose or purpose
    if hasattr(store, "consume_pin"):
        return store.consume_pin(cid, pin, worker_id, expected_purpose=want)
    ch = store.get_challenge(cid)
    if not ch:
        raise ValueError("Unknown challenge")
    if want and ch.purpose != want:
        raise ValueError("Wrong verification purpose")
    if ch.consumed_at:
        raise ValueError("PIN already used")
    if ch.expires_at <= _now():
        raise ValueError("PIN expired")
    if ch.attempts >= MAX_ATTEMPTS:
        raise ValueError("Too many attempts")
    ch.attempts += 1
    if worker_id:
        ch.worker_id = worker_id
    if hash_secret(re.sub(r"\D", "", str(pin))) != ch.code_hash:
        store.put_challenge(ch)
        raise ValueError("Incorrect PIN")
    ch.consumed_at = _now()
    store.put_challenge(ch)
    return ch


def bind_recovery_account(ch: Challenge, account_id: Any, destination: str) -> None:
    if str(ch.purpose or "") != "recovery":
        raise ValueError("Wrong verification purpose")
    dest = str(destination or "").strip().lower()
    if ch.channel == "email":
        dest = dest.lower()
    if str(ch.destination or "") != dest:
        raise ValueError("Recovery code is not for this account")
    hint = str(ch.account_hint or "").strip()
    if hint and str(account_id) != hint:
        raise ValueError("Recovery code is not for this account")


def safe_return_url(value: Any, default: str = "/") -> str:
    raw = str(value or "").strip()
    if not raw:
        return default
    if raw.startswith("/") and not raw.startswith("//"):
        return raw
    try:
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        if parsed.scheme in {"http", "https"} and host in ALLOWED_RETURN_HOSTS:
            return raw
    except Exception:
        return default
    return default


@dataclass
class CompletionIntent:
    purpose: str
    channel: str
    destination: str
    ownership: str
    sailor_sas_id: str
    attach_sailor: bool
    create_session: bool
    save_contact: bool
    find_existing_only: bool
    create_public_account: bool
    login_method: str
    return_to: str
    provenance: str


def completion_intent(
    ch: Challenge,
    *,
    relationship: Any = "",
    sas_id: Any = "",
    return_to: Any = "",
) -> CompletionIntent:
    purpose = str(ch.purpose or "").strip() or "login"
    if purpose == "claim":
        rel = relationship or "self"
    elif purpose in {"login", "recovery"}:
        rel = relationship or "pending"
    else:
        rel = relationship or "pending"
    ownership, sid = resolve_signup_identity(rel, sas_id or ch.account_hint)
    attach = purpose == "claim" and account_writes_sas(ownership)
    method = "whatsapp" if ch.channel == "whatsapp" else "email"
    if purpose == "recovery":
        method = method
    default_return = "/"
    if attach and sid:
        default_return = f"/sailor/s-{sid}"
    return CompletionIntent(
        purpose=purpose,
        channel=ch.channel,
        destination=ch.destination,
        ownership=ownership,
        sailor_sas_id=sid if purpose == "claim" else "",
        attach_sailor=attach,
        create_session=True,
        save_contact=True,
        find_existing_only=purpose in {"login", "recovery"},
        create_public_account=ownership == OWNERSHIP_PUBLIC and purpose not in {"login", "recovery", "claim"},
        login_method=method,
        return_to=safe_return_url(return_to, default_return),
        provenance=f"{purpose}_{ch.channel}",
    )


def issue_remembered_device(
    store: Any,
    account_id: Any,
    sas_id: str = "",
    login_method: str = "",
    display_name: str = "",
) -> str:
    raw = new_token()
    rem = RememberedDevice(
        token_hash=hash_secret(raw),
        account_id=account_id,
        sas_id=str(sas_id or ""),
        login_method=str(login_method or ""),
        display_name=str(display_name or ""),
        expires_at=_now() + REMEMBER_TTL_SEC,
    )
    store.put_remember(rem)
    return raw


def recognise_remembered_device(store: Any, raw: str) -> RememberedDevice:
    rem = store.get_remember(hash_secret(raw or ""))
    if not rem:
        raise ValueError("Not recognised")
    if rem.revoked_at:
        raise ValueError("Remembered access was cleared")
    if rem.expires_at <= _now():
        raise ValueError("Remembered access expired")
    return rem


def revoke_remembered_device(store: Any, raw: str) -> None:
    rem = store.get_remember(hash_secret(raw or ""))
    if rem and not rem.revoked_at:
        rem.revoked_at = _now()
        store.put_remember(rem)


def logout_choice(store: Any, remember_raw: str, keep_remember: bool) -> str:
    """Yes keeps remember token (no session). No revokes it."""
    if keep_remember:
        if remember_raw:
            try:
                recognise_remembered_device(store, remember_raw)
            except ValueError:
                pass
        return "kept"
    if remember_raw:
        revoke_remembered_device(store, remember_raw)
    return "cleared"


def save_verified_contact(
    store: Any,
    account_key: str,
    *,
    email: str = "",
    phone: str = "",
    provenance: str,
    ownership: str,
    sas_id: str = "",
) -> Dict[str, Any]:
    refuse_fabricated_sas(sas_id)
    ok, local = phone_valid_or_empty(phone)
    if not ok:
        raise ValueError("Invalid phone")
    if ownership == OWNERSHIP_SELF and sas_id and not is_real_sas_id(sas_id):
        raise ValueError("Self ownership requires a real SAS ID")
    row = {
        "account_key": account_key,
        "email": (email or "").strip().lower(),
        "phone": local,
        "provenance": provenance,
        "ownership": ownership,
        "sas_id": str(sas_id or ""),
        "verified_at": _now(),
    }
    store.save_contact(account_key, row)
    return row


def recovery_destination(raw: Any) -> Tuple[str, str]:
    """Return (channel, destination) for email or WhatsApp recovery."""
    text = str(raw or "").strip()
    if "@" in text:
        return "email", text.lower()
    ok, local = phone_valid_or_empty(text)
    if ok and local:
        return "whatsapp", local
    raise ValueError("Enter the email or 10-digit WhatsApp number on the account")


def merge_login_methods(existing_methods: list, new_method: str, sas_id: str) -> list:
    """Attach another login method to one person. No duplicate people."""
    refuse_fabricated_sas(sas_id)
    methods = list(existing_methods or [])
    if new_method and new_method not in methods:
        methods.append(new_method)
    return methods


def session_insert_values(
    session_token: str,
    account_id: Any,
    sas_id: Any,
    login_method: str,
    expires_at: Any,
    client_ip: Any,
    user_agent: Any,
    device_type: Any = None,
) -> Tuple[list, list]:
    cols = ["session_id", "account_id", "sas_id", "login_method", "expires_at", "ip_address", "user_agent"]
    vals = [session_token, account_id, sas_id, login_method, expires_at, client_ip, user_agent]
    if device_type is not None:
        cols.append("device_type")
        vals.append(device_type)
    if len(cols) != len(vals):
        raise ValueError("session insert column/value mismatch")
    return cols, vals


SQL_ENSURE_TABLES = """
CREATE TABLE IF NOT EXISTS public.auth_identity_proofs (
    token_hash TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    email TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    picture TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS public.auth_challenges (
    id TEXT PRIMARY KEY,
    purpose TEXT NOT NULL,
    channel TEXT NOT NULL,
    destination TEXT NOT NULL,
    code_hash TEXT,
    link_hash TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INT DEFAULT 0,
    resends INT DEFAULT 0,
    consumed_at TIMESTAMPTZ,
    confirm_pending BOOLEAN DEFAULT FALSE,
    account_hint TEXT,
    worker_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS auth_challenges_dest ON public.auth_challenges (purpose, destination);
CREATE TABLE IF NOT EXISTS public.auth_remembered_devices (
    token_hash TEXT PRIMARY KEY,
    account_id BIGINT,
    sas_id TEXT,
    login_method TEXT,
    display_name TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS public.auth_verified_contacts (
    account_key TEXT PRIMARY KEY,
    email TEXT,
    phone TEXT,
    provenance TEXT,
    ownership TEXT,
    sas_id TEXT,
    verified_at TIMESTAMPTZ
);
"""


def ensure_tables(cur) -> None:
    cur.execute(SQL_ENSURE_TABLES)
