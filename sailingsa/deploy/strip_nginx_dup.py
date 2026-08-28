#!/usr/bin/env python3
"""Strip nested duplicate server block from broken live nginx config."""
from pathlib import Path

p = Path("/etc/nginx/sites-enabled/sailingsa")
lines = p.read_text().splitlines(True)
fixed = lines[:11] + lines[130:]
p.write_text("".join(fixed))
print("wrote", p, "bytes", p.stat().st_size, "lines", len(fixed))
