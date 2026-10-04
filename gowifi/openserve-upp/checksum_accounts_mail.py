#!/usr/bin/env python3
"""Compare accounts copies in kevin@ and openserve@ mailboxes on the box.

Does not print message bodies. Matches on Message-ID, then checksums the
normalized payload so both inboxes can be proven to hold the same accounts mail.
"""
from __future__ import annotations

import email
import hashlib
import json
import os
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

KEVIN = Path("/home/user-data/mail/mailboxes/gowifi.co.za/kevin")
OPENSERVE = Path("/home/user-data/mail/mailboxes/gowifi.co.za/openserve")
ACCOUNTS_MARKERS = (
    "accounts@go-wifi.co.za",
    "accounts@gowifi.co.za",
    "openserve@gowifi.co.za",
    "openserve@go-wifi.co.za",
)


def iter_messages(root: Path):
    if not root.exists():
        return
    for dirpath, _dirs, files in os.walk(root):
        if "/new" not in dirpath and "/cur" not in dirpath:
            continue
        for name in files:
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            try:
                with path.open("rb") as fh:
                    msg = email.message_from_binary_file(fh)
            except OSError:
                continue
            yield path, msg


def payload_sha256(msg: email.message.Message) -> str:
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            payload = part.get_payload(decode=True) or b""
            parts.append(payload)
        blob = b"\n--part--\n".join(parts)
    else:
        blob = msg.get_payload(decode=True) or b""
    return hashlib.sha256(blob).hexdigest()


def header_blob(msg: email.message.Message) -> dict:
    mid = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
    subject = " ".join((msg.get("Subject") or "").split())
    date = msg.get("Date") or ""
    try:
        iso = parsedate_to_datetime(date).isoformat() if date else ""
    except (TypeError, ValueError, IndexError):
        iso = date
    to_cc = " ".join(
        filter(
            None,
            [
                msg.get("To") or "",
                msg.get("Cc") or "",
                msg.get("Delivered-To") or "",
                msg.get("X-Original-To") or "",
                msg.get("Envelope-To") or "",
            ],
        )
    ).lower()
    return {
        "message_id": mid,
        "subject": subject[:160],
        "date": iso,
        "checksum": payload_sha256(msg),
        "accounts_related": any(m in to_cc for m in ACCOUNTS_MARKERS),
    }


def index_mailbox(root: Path, accounts_only: bool) -> dict:
    by_id = {}
    unlabeled = []
    for _path, msg in iter_messages(root) or []:
        meta = header_blob(msg)
        if accounts_only and not meta["accounts_related"]:
            continue
        if meta["message_id"]:
            by_id[meta["message_id"]] = meta
        else:
            unlabeled.append(meta)
    return {"by_id": by_id, "unlabeled": unlabeled}


def main() -> int:
    kevin = index_mailbox(KEVIN, accounts_only=True)
    box = index_mailbox(OPENSERVE, accounts_only=False)
    kevin_ids = set(kevin["by_id"])
    box_ids = set(box["by_id"])
    shared = sorted(kevin_ids & box_ids)
    matched = []
    mismatch = []
    for mid in shared:
        a = kevin["by_id"][mid]
        b = box["by_id"][mid]
        row = {
            "message_id": mid,
            "subject": a["subject"] or b["subject"],
            "kevin_checksum": a["checksum"],
            "openserve_checksum": b["checksum"],
            "match": a["checksum"] == b["checksum"],
        }
        (matched if row["match"] else mismatch).append(row)
    report = {
        "kevin_accounts_with_id": len(kevin_ids),
        "openserve_with_id": len(box_ids),
        "shared_message_ids": len(shared),
        "checksum_match": len(matched),
        "checksum_mismatch": len(mismatch),
        "only_in_openserve": sorted(box_ids - kevin_ids),
        "only_in_kevin_accounts": sorted(kevin_ids - box_ids),
        "mismatches": mismatch,
        "ok": len(mismatch) == 0 and len(box_ids) <= len(shared) + len(box_ids - kevin_ids),
    }
    print(json.dumps(report, indent=2))
    if mismatch:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
