#!/usr/bin/env python3
"""Class URL redirects (live):
- Valid name slugs work: /class/420, /class/505, /class/ilca-6
- Bare DB id → name slug: /class/7 → /class/420
- Unknown → /classes: /class/99999, /class/not-a-real-class
- /class and /class/ → /classes (unblocked from probe list)
"""
print(__doc__)
