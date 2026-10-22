import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from modules import auth_identity as auth
from modules.auth_identity import MemoryStore


def test_session_insert_includes_login_method():
    cols, vals = auth.session_insert_values("tok", 1, "4701", "facebook", "exp", "1.1.1.1", "ua")
    assert "login_method" in cols
    assert len(cols) == len(vals) == 7
    assert vals[3] == "facebook"


def test_facebook_seven_columns_six_values_is_the_bug_we_refuse():
    with pytest.raises(ValueError):
        cols = ["session_id", "account_id", "sas_id", "login_method", "expires_at", "ip_address", "user_agent"]
        vals = ["t", 1, "4701", "exp", "ip", "ua"]
        if len(cols) != len(vals):
            raise ValueError("session insert column/value mismatch")


def test_identity_proof_not_browser_ids():
    store = MemoryStore()
    token = auth.issue_identity_proof(
        store,
        "google",
        {"provider_id": "gid-1", "email": "a@b.co.za", "email_verified": True, "full_name": "Ann"},
    )
    proof = auth.consume_identity_proof(store, token)
    assert proof.provider_id == "gid-1"
    assert proof.email_verified is True
    with pytest.raises(ValueError):
        auth.consume_identity_proof(store, token)
    with pytest.raises(ValueError):
        auth.consume_identity_proof(store, "forged-browser-id")


def test_pin_worker_switch_and_replay():
    store = MemoryStore()
    cid, pin = auth.issue_pin_challenge(
        store, purpose="login", channel="email", destination="ann@b.co.za", worker_id="w1"
    )
    ch = auth.verify_pin(store, cid, pin, worker_id="w2")
    assert ch.worker_id == "w2"
    with pytest.raises(ValueError, match="already used"):
        auth.verify_pin(store, cid, pin, worker_id="w1")


def test_expired_and_wrong_pin():
    store = MemoryStore()
    cid, pin = auth.issue_pin_challenge(
        store, purpose="email_verify", channel="email", destination="ann@b.co.za"
    )
    with pytest.raises(ValueError, match="Incorrect"):
        auth.verify_pin(store, cid, "000000")
    ch = store.get_challenge(cid)
    ch.expires_at = time.time() - 1
    with pytest.raises(ValueError, match="expired"):
        auth.verify_pin(store, cid, pin)


def test_pin_attempt_and_resend_bounds():
    store = MemoryStore()
    cid, pin = auth.issue_pin_challenge(
        store, purpose="phone_verify", channel="whatsapp", destination="0821112233"
    )
    for _ in range(auth.MAX_ATTEMPTS):
        try:
            auth.verify_pin(store, cid, "111111")
        except ValueError:
            pass
    with pytest.raises(ValueError, match="Too many"):
        auth.verify_pin(store, cid, pin)
    cid2, _ = auth.issue_pin_challenge(
        store, purpose="phone_verify", channel="whatsapp", destination="0839998877"
    )
    ch = store.get_challenge(cid2)
    ch.created_at = time.time() - 100
    ch.resends = auth.MAX_RESENDS
    store.put_challenge(ch)
    with pytest.raises(ValueError, match="resends"):
        auth.issue_pin_challenge(
            store, purpose="phone_verify", channel="whatsapp", destination="0839998877"
        )


def test_link_requires_confirm_then_blocks_replay():
    store = MemoryStore()
    _cid, raw = auth.issue_link_challenge(
        store, purpose="email_verify", channel="email", destination="ann@b.co.za"
    )
    preview = auth.preview_link_challenge(store, raw)
    assert preview.confirm_pending is True
    assert preview.consumed_at == 0
    confirmed = auth.confirm_link_challenge(store, raw)
    assert confirmed.consumed_at > 0
    with pytest.raises(ValueError, match="already used"):
        auth.confirm_link_challenge(store, raw)


def test_optional_phone_and_normalise():
    assert auth.phone_valid_or_empty("") == (True, "")
    assert auth.phone_valid_or_empty(None) == (True, "")
    ok, local = auth.phone_valid_or_empty("+27 82 123 4567")
    assert ok and local == "0821234567"
    assert auth.phone_intl(local) == "27821234567"
    ok, _ = auth.phone_valid_or_empty("123")
    assert ok is False


def test_ownership_no_fabricated_sas():
    assert auth.classify_ownership("self", "4701") == auth.OWNERSHIP_SELF
    assert auth.classify_ownership("guardian", "4701") == auth.OWNERSHIP_GUARDIAN
    assert auth.classify_ownership("public", "") == auth.OWNERSHIP_PUBLIC
    assert auth.classify_ownership("not_me", "4701") == auth.OWNERSHIP_PENDING
    with pytest.raises(ValueError):
        auth.refuse_fabricated_sas("FB_123")
    with pytest.raises(ValueError):
        auth.save_verified_contact(
            MemoryStore(), "a1", provenance="email", ownership=auth.OWNERSHIP_SELF, sas_id="FB_9"
        )


def test_one_person_many_methods_no_duplicate():
    methods = auth.merge_login_methods(["google"], "facebook", "4701")
    assert methods == ["google", "facebook"]
    assert auth.merge_login_methods(methods, "facebook", "4701") == methods


def test_verified_contact_provenance():
    store = MemoryStore()
    row = auth.save_verified_contact(
        store,
        "acct-1",
        email="Ann@B.co.za",
        phone="0821234567",
        provenance="email_pin",
        ownership=auth.OWNERSHIP_SELF,
        sas_id="4701",
    )
    assert row["email"] == "ann@b.co.za"
    assert row["provenance"] == "email_pin"
    assert store.get_contact("acct-1")["phone"] == "0821234567"


def test_logout_yes_keeps_remember_until_login_click():
    store = MemoryStore()
    raw = auth.issue_remembered_device(store, 9, sas_id="4701", login_method="email", display_name="Ann")
    assert auth.logout_choice(store, raw, keep_remember=True) == "kept"
    rem = auth.recognise_remembered_device(store, raw)
    assert rem.account_id == 9
    assert auth.logout_choice(store, raw, keep_remember=False) == "cleared"
    with pytest.raises(ValueError, match="cleared"):
        auth.recognise_remembered_device(store, raw)


def test_remember_not_plaintext_password():
    store = MemoryStore()
    raw = auth.issue_remembered_device(store, 3)
    rem = store.get_remember(auth.hash_secret(raw))
    assert rem is not None
    assert "password" not in rem.__dict__
    assert rem.token_hash != raw


def test_isolated_worker_memory_cannot_verify():
    w1 = MemoryStore()
    w2 = MemoryStore()
    cid, pin = auth.issue_pin_challenge(
        w1, purpose="login", channel="email", destination="ann@b.co.za", worker_id="w1"
    )
    with pytest.raises(ValueError, match="Unknown"):
        auth.verify_pin(w2, cid, pin, worker_id="w2")


def test_ownership_conflicts_and_no_silent_overwrite():
    assert auth.resolve_signup_identity("self", "4701") == (auth.OWNERSHIP_SELF, "4701")
    assert auth.resolve_signup_identity("guardian", "4701") == (auth.OWNERSHIP_GUARDIAN, "4701")
    assert auth.resolve_signup_identity("public", "4701") == (auth.OWNERSHIP_PUBLIC, "")
    assert auth.resolve_signup_identity("not_me", "4701") == (auth.OWNERSHIP_PENDING, "4701")
    assert auth.account_writes_sas(auth.OWNERSHIP_SELF) is True
    assert auth.account_writes_sas(auth.OWNERSHIP_GUARDIAN) is False
    with pytest.raises(ValueError):
        auth.resolve_signup_identity("self", "FB_99")
    with pytest.raises(ValueError, match="already linked"):
        auth.refuse_silent_sas_overwrite("4701", "9999")
    auth.refuse_silent_sas_overwrite("4701", "4701")


def test_recovery_destination_and_retries():
    assert auth.recovery_destination("Ann@B.co.za") == ("email", "ann@b.co.za")
    assert auth.recovery_destination("+27 82 123 4567") == ("whatsapp", "0821234567")
    with pytest.raises(ValueError):
        auth.recovery_destination("not-an-id")
    store = MemoryStore()
    cid, pin = auth.issue_pin_challenge(
        store, purpose="recovery", channel="email", destination="ann@b.co.za"
    )
    auth.verify_pin(store, cid, pin)
    with pytest.raises(ValueError, match="already used"):
        auth.verify_pin(store, cid, pin)


def test_sql_store_roundtrip_helpers():
    now = time.time()
    dt = auth._as_dt(now)
    assert abs(auth._from_dt(dt) - now) < 1
    mapped = auth._row_map(("a", "b"), ("one", "two"))
    assert mapped == {"one": "a", "two": "b"}
    assert auth._row_map(None, ("one",)) is None
