#!/usr/bin/env python3
"""Patch nginx config: www.sailingsa.co.za 301 -> https://sailingsa.co.za. Reads stdin, writes stdout."""
import re
import sys

content = sys.stdin.read()

# 1) In sailingsa HTTPS block, change server_name to apex only and insert www redirect block before it.
#    Match: "# SailingSA Configuration" then "server {" then "server_name sailingsa.co.za www.sailingsa.co.za;"
content = re.sub(
    r'(# SailingSA Configuration\n)(server \{\n)(    server_name )sailingsa\.co\.za www\.sailingsa\.co\.za;',
    r'\1# www -> 301 to apex (canonical)\n'
    r'server {\n    listen [::]:443 ssl;\n    listen 443 ssl;\n    server_name www.sailingsa.co.za;\n'
    r'    ssl_certificate /etc/letsencrypt/live/sailingsa.co.za/fullchain.pem;\n'
    r'    ssl_certificate_key /etc/letsencrypt/live/sailingsa.co.za/privkey.pem;\n'
    r'    include /etc/letsencrypt/options-ssl-nginx.conf;\n    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;\n'
    r'    return 301 https://sailingsa.co.za$request_uri;\n}\n\n\2\3sailingsa.co.za;',
    content,
    count=1
)

# 2) Replace sailingsa HTTP block with two clean blocks (www -> apex, apex -> https).
# Match from "server {" through "return 301 https:$host$request_uri" and closing "}"
old_http = (
    r'server \{\s*'
    r'if \(\$host = www\.sailingsa\.co\.za\) \{[^}]+\}.*?'
    r'if \(\$host = sailingsa\.co\.za\) \{[^}]+\}.*?'
    r'listen 80;.*?listen \[::\]:80;.*?'
    r'server_name sailingsa\.co\.za www\.sailingsa\.co\.za;.*?'
    r'return 301 https:\$host\$request_uri;[^}]*\n\s*\}\s*\n'
)
new_http = '''server {
    listen 80;
    listen [::]:80;
    server_name www.sailingsa.co.za;
    return 301 https://sailingsa.co.za$request_uri;
}
server {
    listen 80;
    listen [::]:80;
    server_name sailingsa.co.za;
    return 301 https://sailingsa.co.za$request_uri;
}
'''
content = re.sub(old_http, new_http, content, flags=re.DOTALL)

sys.stdout.write(content)
