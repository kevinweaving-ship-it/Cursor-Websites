"""Dry-run write-back: Roundup media belongs on the event URL pool, not only the card."""

from __future__ import annotations

import json
from pathlib import Path


def write_pool(payload: dict, out_root: Path) -> Path:
    week = payload["week"]
    dest = out_root / "sailing-roundup" / "issues" / week / "media_pool"
    dest.mkdir(parents=True, exist_ok=True)
    for sheet in payload["sheets"]:
        attachments = []
        image = sheet.get("image") or {}
        if image.get("src"):
            attachments.append(
                {
                    "src": image["src"],
                    "credit": image.get("credit"),
                    "role": "hero",
                    "kind": image.get("kind"),
                }
            )
        for src in sheet.get("sources") or []:
            if src.get("kind") == "gallery":
                attachments.append({"src": src["url"], "credit": src.get("label"), "role": "gallery"})
        record = {
            "event_id": sheet["event_id"],
            "event_url": sheet.get("event_url"),
            "dry_run": True,
            "proposed_attachments": attachments,
            "note": "Write these back onto the SailingSA event page media pool. Do not PATCH live from this job.",
        }
        (dest / f"{sheet['event_id']}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return dest
