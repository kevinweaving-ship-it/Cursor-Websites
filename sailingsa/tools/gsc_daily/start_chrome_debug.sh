#!/bin/bash
# Optional: relaunch the EXISTING Chrome profile with remote debugging.
# Use only if AppleScript cannot drive the tab. Quit Chrome first.
# Does not copy cookies into git or /var/www.
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "STOP: Mac only."
  exit 2
fi
if pgrep -x "Google Chrome" >/dev/null; then
  echo "Quit Google Chrome first, then re-run this script."
  echo "It will reopen YOUR existing profile with --remote-debugging-port=9222."
  exit 1
fi
open -a "Google Chrome" --args --remote-debugging-port=9222
echo "Chrome started with CDP on 9222. Existing Google login stays in this profile."
