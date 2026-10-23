"""Database-backed auth tests (sqlite, same atomic consume rules as Postgres)."""
from __future__ import annotations

import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from modules import auth_identity as auth


def _connect():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE auth_identity_proofs (
            token_hash TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            email TEXT,
            email_verified INTEGER DEFAULT 0,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            picture TEXT,
            expires_at REAL NOT NULL,
            used_at REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE auth_challenges (
            id TEXT PRIMARY KEY,
            purpose TEXT NOT NULL,
            channel TEXT NOT NULL,
            destination TEXT NOT NULL,
            code_hash TEXT,
            link_hash TEXT,
            expires_at REAL NOT NULL,
            attempts INTEGER DEFAULT 0,
            resends INTEGER DEFAULT 0,
            consumed_at REAL,
            confirm_pending INTEGER DEFAULT 0,
            account_hint TEXT,
            worker_id TEXT,
            created_at REAL
        )
        """
    )
    conn.commit()
    return conn


class SqliteAuthStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._lock = threading.Lock()

    def put_proof(self, proof: auth.IdentityProof) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO auth_identity_proofs
                (token_hash, provider, provider_id, email, email_verified, first_name, last_name, full_name, picture, expires_at, used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_hash) DO UPDATE SET used_at=excluded.used_at, expires_at=excluded.expires_at
                """,
                (
                    proof.token_hash,
                    proof.provider,
                    proof.provider_id,
                    proof.email,
                    int(proof.email_verified),
                    proof.first_name,
                    proof.last_name,
                    proof.full_name,
                    proof.picture,
                    proof.expires_at,
                    proof.used_at or None,
                ),
            )
            self.conn.commit()

    def get_proof(self, token_hash: str):
        cur = self.conn.execute("SELECT * FROM auth_identity_proofs WHERE token_hash=?", (token_hash,))
        row = cur.fetchone()
        if not row:
            return None
        return auth.IdentityProof(
            token_hash=row["token_hash"],
            provider=row["provider"],
            provider_id=row["provider_id"],
            email=row["email"] or "",
            email_verified=bool(row["email_verified"]),
            first_name=row["first_name"] or "",
            last_name=row["last_name"] or "",
            full_name=row["full_name"] or "",
            picture=row["picture"] or "",
            expires_at=float(row["expires_at"] or 0),
            used_at=float(row["used_at"] or 0),
        )

    def consume_proof(self, token_hash: str) -> auth.IdentityProof:
        with self._lock:
            now = time.time()
            cur = self.conn.execute(
                """
                UPDATE auth_identity_proofs
                SET used_at=?
                WHERE token_hash=? AND used_at IS NULL AND expires_at > ?
                RETURNING *
                """,
                (now, token_hash, now),
            )
            row = cur.fetchone()
            self.conn.commit()
            if not row:
                found = self.get_proof(token_hash)
                if not found:
                    raise ValueError("Unknown or expired identity proof")
                if found.used_at:
                    raise ValueError("Identity proof already used")
                raise ValueError("Identity proof expired")
            return auth.IdentityProof(
                token_hash=row["token_hash"],
                provider=row["provider"],
                provider_id=row["provider_id"],
                email=row["email"] or "",
                email_verified=bool(row["email_verified"]),
                first_name=row["first_name"] or "",
                last_name=row["last_name"] or "",
                full_name=row["full_name"] or "",
                picture=row["picture"] or "",
                expires_at=float(row["expires_at"] or 0),
                used_at=float(row["used_at"] or 0),
            )

    def put_challenge(self, ch: auth.Challenge) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO auth_challenges
                (id, purpose, channel, destination, code_hash, link_hash, expires_at, attempts, resends,
                 consumed_at, confirm_pending, account_hint, worker_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    code_hash=excluded.code_hash, attempts=excluded.attempts,
                    consumed_at=excluded.consumed_at, worker_id=excluded.worker_id
                """,
                (
                    ch.id,
                    ch.purpose,
                    ch.channel,
                    ch.destination,
                    ch.code_hash,
                    ch.link_hash,
                    ch.expires_at,
                    ch.attempts,
                    ch.resends,
                    ch.consumed_at or None,
                    int(ch.confirm_pending),
                    ch.account_hint,
                    ch.worker_id,
                    ch.created_at,
                ),
            )
            self.conn.commit()

    def get_challenge(self, cid: str):
        row = self.conn.execute("SELECT * FROM auth_challenges WHERE id=?", (cid,)).fetchone()
        if not row:
            return None
        return auth.Challenge(
            id=row["id"],
            purpose=row["purpose"],
            channel=row["channel"],
            destination=row["destination"],
            code_hash=row["code_hash"] or "",
            link_hash=row["link_hash"] or "",
            expires_at=float(row["expires_at"] or 0),
            attempts=int(row["attempts"] or 0),
            resends=int(row["resends"] or 0),
            consumed_at=float(row["consumed_at"] or 0),
            confirm_pending=bool(row["confirm_pending"]),
            account_hint=row["account_hint"] or "",
            worker_id=row["worker_id"] or "",
            created_at=float(row["created_at"] or 0),
        )

    def find_open_challenge(self, purpose: str, destination: str):
        now = time.time()
        row = self.conn.execute(
            """
            SELECT * FROM auth_challenges
            WHERE purpose=? AND destination=? AND consumed_at IS NULL AND expires_at > ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (purpose, destination, now),
        ).fetchone()
        return self.get_challenge(row["id"]) if row else None

    def match_pin(self, challenge_id: str, pin: str, worker_id: str = "", expected_purpose: str = "") -> auth.Challenge:
        with self._lock:
            ch = self.get_challenge(challenge_id)
            if not ch:
                raise ValueError("Unknown challenge")
            if expected_purpose and ch.purpose != expected_purpose:
                raise ValueError("Wrong verification purpose")
            if ch.consumed_at:
                raise ValueError("PIN already used")
            if ch.expires_at <= time.time():
                raise ValueError("PIN expired")
            pin_hash = auth.hash_secret("".join(c for c in str(pin) if c.isdigit()))
            if ch.code_hash != pin_hash:
                ch.attempts += 1
                self.put_challenge(ch)
                raise ValueError("Incorrect PIN")
            return ch

    def consume_matched(self, challenge_id: str) -> auth.Challenge:
        with self._lock:
            now = time.time()
            row = self.conn.execute(
                """
                UPDATE auth_challenges
                SET consumed_at=?, confirm_pending=0, attempts=attempts+1
                WHERE id=? AND consumed_at IS NULL AND expires_at > ?
                RETURNING id
                """,
                (now, challenge_id, now),
            ).fetchone()
            self.conn.commit()
            if not row:
                raise ValueError("PIN already used")
            return self.get_challenge(challenge_id)


@pytest.fixture
def sql_store():
    conn = _connect()
    try:
        yield SqliteAuthStore(conn)
    finally:
        conn.close()


def test_sql_public_signup_creates_placeholder_not_sailor():
    pub = auth.new_public_sas_id()
    assert pub.startswith("PUB_")
    assert auth.is_real_sas_id(pub) is False
    store = auth.MemoryStore()
    cid, pin = auth.issue_pin_challenge(
        store, purpose="signup", channel="email", destination="public@b.co.za"
    )
    ch = auth.verify_pin(store, cid, pin)
    intent = auth.completion_intent(ch, relationship="public", return_to="/")
    assert intent.create_public_account is True
    assert intent.find_existing_only is False
    assert intent.attach_sailor is False
    assert intent.sailor_sas_id == ""
    assert intent.create_session is True


def test_sql_wrong_purpose_pin_is_not_consumed(sql_store):
    cid, pin = auth.issue_pin_challenge(
        sql_store, purpose="login", channel="email", destination="ann@b.co.za"
    )
    with pytest.raises(ValueError, match="Wrong verification purpose"):
        auth.match_pin(sql_store, cid, pin, expected_purpose="recovery")
    left = sql_store.get_challenge(cid)
    assert not left.consumed_at
    matched = auth.match_pin(sql_store, cid, pin, expected_purpose="login")
    assert matched.id == cid
    assert not matched.consumed_at


def test_sql_invalid_password_then_retry(sql_store):
    cid, pin = auth.issue_pin_challenge(
        sql_store, purpose="recovery", channel="email", destination="ann@b.co.za",
        account_hint="44",
    )
    ok, _ = auth.valid_new_password("short")
    assert ok is False
    ch = auth.match_pin(sql_store, cid, pin, expected_purpose="recovery")
    assert not ch.consumed_at
    with pytest.raises(ValueError, match="not for this account"):
        auth.bind_recovery_account(ch, "99", "ann@b.co.za")
    still = sql_store.get_challenge(cid)
    assert not still.consumed_at
    auth.bind_recovery_account(ch, "44", "ann@b.co.za")
    consumed = auth.consume_matched(sql_store, cid)
    assert consumed.consumed_at > 0
    with pytest.raises(ValueError, match="already used"):
        auth.consume_matched(sql_store, cid)


def test_sql_concurrent_proof_replay_only_one_wins(sql_store):
    token = auth.issue_identity_proof(
        sql_store, "google", {"provider_id": "gid-sql", "email": "a@b.co.za", "email_verified": True}
    )
    results = []

    def worker():
        try:
            results.append(("ok", auth.consume_identity_proof(sql_store, token)))
        except ValueError as e:
            results.append(("err", str(e)))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for r in results if r[0] == "ok") == 1
    assert sum(1 for r in results if r[0] == "err") == 7
    with pytest.raises(ValueError, match="already used"):
        auth.consume_identity_proof(sql_store, token)
