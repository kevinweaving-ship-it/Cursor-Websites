#!/usr/bin/env python3
"""Public-first hang fixes (apply on live api.py).

Causes that were hanging public URLs:
1. /events rebuilt 1MB+ HTML on the request path (15–25s)
2. /classes imported outdated deploy/classes_clubs_directory.py (int(logo_url) → 500)
3. Club pages rebuilt per-worker with no disk cache (multi-second under load)
4. Lean traffic BG + traffic dash polls competed for workers

Fixes:
- Events: memory+disk cache; never rebuild on request path (placeholder/stale only)
- Classes: prefer api/ module; HTML disk cache
- Clubs: memory+disk stale-while-revalidate
- Traffic BG: disabled / noop during crisis
"""
print(__doc__)
