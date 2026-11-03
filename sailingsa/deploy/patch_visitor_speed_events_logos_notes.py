#!/usr/bin/env python3
"""Visitor speed (live): cache /events-logos (+ slug) + nginx /artwork/ long-cache.

Keep public up: nginx reload first (no downtime), one short API restart, warm caches.
"""
print(__doc__)
