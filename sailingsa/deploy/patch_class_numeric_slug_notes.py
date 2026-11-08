#!/usr/bin/env python3
"""Fix /class/420 and /class/505: _class_public_path no longer blanks digit-only class-name slugs.

Bare digits still rejected when they are only a DB class_id (not a class_name).
Legacy /class/7-420 → 301 /class/420.
"""
print(__doc__)
