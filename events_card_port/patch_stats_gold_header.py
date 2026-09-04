#!/usr/bin/env python3
"""Switch /stats page shell to std gold header (_html_with_gold_header)."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

m = re.search(r"\ndef _stats_page_html\(data: dict\) -> str:\n", t)
if not m:
    raise SystemExit("_stats_page_html not found")
start = m.start() + 1
m2 = re.search(r"\n\ndef [a-zA-Z_]", t[start + 20 :])
if not m2:
    raise SystemExit("end anchor not found")
end = start + 20 + m2.start()
fn = t[start:end]

if "_html_with_gold_header" in fn and "site-header" not in fn:
    print("already gold")
    sys.exit(0)

old_open = '''    header = f"""<!DOCTYPE html>
<html lang="en-US">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html_module.escape(title)}</title>
<meta name="description" content="{html_module.escape(desc)}">
<link rel="canonical" href="https://sailingsa.co.za/stats">
<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png"><link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/css/main.css?v=13">
<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">
<style>
'''

new_open = '''    extra_head = (
        f"""<meta name="description" content="{html_module.escape(desc)}">
<link rel="canonical" href="https://sailingsa.co.za/stats">
<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">
<style>
'''

old_mid = '''</style>
</head>
<body>
<header class="site-header"><div class="container" style="display:flex;align-items:center;flex-wrap:wrap;gap:0.75rem;">
<a href="/" class="logo js-go-home" title="Home"><img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo"></a>
<nav class="nav-inline" aria-label="Main" style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin-right:auto;"><a href="/">Home</a><a href="/sailors">Sailors</a><a href="/regattas">Regattas</a><a href="/classes">Classes</a><a href="/clubs">Clubs</a><a href="https://sailingsa.co.za/events">Events</a><a href="/about">About</a></nav>
<div class="header-auth" style="margin-left:auto;"></div>
</div></header>
<main class="main-content" id="stats-dashboard"><div class="container">
"""
    card_links'''

new_mid = '''</style>
"""
    )
    inner = (
        """<div class="container" id="stats-dashboard">
"""
    )
    card_links'''

old_close = '''    footer = """</div></main><footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer>
<script>
document.getElementById("year").textContent = new Date().getFullYear();
(function(){
'''

new_close = '''    footer = """</div><footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer>
<script>
document.getElementById("year").textContent = new Date().getFullYear();
(function(){
'''

old_return = '''})();
</script></body></html>"""
    return header + body + _seo_discovery_block_html() + footer
'''

new_return = '''})();
</script>"""
    inner = inner + body + _seo_discovery_block_html() + footer
    resp = _html_with_gold_header(title, inner, extra_head)
    body_bytes = resp.body
    if isinstance(body_bytes, memoryview):
        body_bytes = body_bytes.tobytes()
    if isinstance(body_bytes, (bytes, bytearray)):
        return body_bytes.decode("utf-8")
    return str(body_bytes)
'''

for label, old, new in [
    ("open", old_open, new_open),
    ("mid", old_mid, new_mid),
    ("close", old_close, new_close),
    ("return", old_return, new_return),
]:
    if old not in fn:
        # try without favicon block (thin api)
        if label == "open":
            old_alt = old_open.replace(
                '<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png"><link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png"><link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">\n',
                '<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">\n',
            ).replace(
                '<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">\n',
                "",
            )
            if old_alt in fn:
                new_alt = new_open.replace(
                    '<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">\n',
                    "",
                )
                fn = fn.replace(old_alt, new_alt, 1)
                continue
        raise SystemExit(f"{label} anchor missing")
    fn = fn.replace(old, new, 1)

t = t[:start] + fn + t[end:]
path.write_text(t, encoding="utf-8")
print("patched", path)
