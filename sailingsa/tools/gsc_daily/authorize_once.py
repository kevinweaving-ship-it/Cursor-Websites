#!/usr/bin/env python3
"""One-time Google consent on the Mac. Never run as a password prompt."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .config import GSC_OAUTH_SCOPE, SERVER_SECRET_DIR
from .server_auth import NeedGoogleConsent, authorize_loopback, load_client


STEPS = f"""
ONE-TIME HUMAN ACTION (Kevin, kevinweaving@gmail.com)

1. Google Cloud Console → create or pick a project (e.g. sailingsa-gsc).
2. Enable “Search Console API”.
3. OAuth consent screen: External, app name SailingSA GSC Monitor,
   test user kevinweaving@gmail.com.
4. Credentials → Create OAuth client ID → Desktop app.
5. Download JSON to:
     /etc/sailingsa/gsc/client_secret.json   (after scp to Ubuntu)
   and a Mac copy:
     ~/Library/Application Support/sailingsa/gsc-oauth/client_secret.json
6. Run this script so the Google consent screen opens (Allow Search Console).
7. Token is saved to the secret dir (Ubuntu: /etc/sailingsa/gsc/token.json mode 0600).

Scope: {GSC_OAUTH_SCOPE}
Never paste Google password or 2FA into chat or production logs.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secret-dir", default="")
    ap.add_argument("--print-steps", action="store_true")
    args = ap.parse_args(argv)
    print(STEPS.strip())
    if args.print_steps:
        return 0
    secret = Path(args.secret_dir) if args.secret_dir else Path.home() / "Library/Application Support/sailingsa/gsc-oauth"
    secret.mkdir(parents=True, exist_ok=True)
    client = secret / "client_secret.json"
    if not client.is_file():
        print(f"STOP: put Desktop OAuth JSON at {client}", file=sys.stderr)
        return 2
    try:
        load_client(secret)
        path = authorize_loopback(secret)
    except NeedGoogleConsent as e:
        print("STOP_NEED_KEVIN_GOOGLE_APPROVAL", e)
        return 3
    print("SAVED", path)
    print("Next: scp to Ubuntu", SERVER_SECRET_DIR / "token.json")
    print("Also copy client_secret.json to", SERVER_SECRET_DIR / "client_secret.json")
    if shutil.which("scp"):
        print(
            "scp -i ~/.ssh/sailingsa_live_key "
            f"'{secret / 'client_secret.json'}' '{path}' "
            "root@102.218.215.253:/etc/sailingsa/gsc/"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
