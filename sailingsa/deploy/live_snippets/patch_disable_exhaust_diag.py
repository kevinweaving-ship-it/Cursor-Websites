#!/usr/bin/env python3
"""Turn off temporary pool-exhaustion / checkout jsonl after verification."""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = p.read_text(encoding="utf-8", errors="replace")
n = 0
if "_EXHAUST_DIAG = True" in text:
    text = text.replace("_EXHAUST_DIAG = True", "_EXHAUST_DIAG = False", 1)
    n += 1
if "_CHECKOUT_DIAG = True" in text:
    text = text.replace("_CHECKOUT_DIAG = True", "_CHECKOUT_DIAG = False", 1)
    n += 1
if n == 0:
    raise SystemExit("no diag flags to disable")
p.write_text(text, encoding="utf-8")
print(f"disabled {n} diag flag(s) in {p}")
