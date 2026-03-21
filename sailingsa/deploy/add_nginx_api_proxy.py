#!/usr/bin/env python3
"""Add location /api proxy to sailingsa server block. Backend on port 8000."""
import sys

NGINX_FILE = "/etc/nginx/sites-available/timadvisor"
API_INSERT = '''    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
    }

'''

def main():
    with open(NGINX_FILE, "r") as f:
        content = f.read()

    sailingsa_start = content.find("# SailingSA Configuration")
    if sailingsa_start == -1:
        print("Could not find sailingsa block")
        sys.exit(1)

    if "location /api" in content[sailingsa_start:]:
        print("Already has /api proxy")
        sys.exit(0)

    loc_slash = content.find("    location / {", sailingsa_start)
    if loc_slash == -1:
        print("Could not find location / in sailingsa block")
        sys.exit(1)

    new_content = content[:loc_slash] + API_INSERT + content[loc_slash:]
    with open(NGINX_FILE, "w") as f:
        f.write(new_content)
    print("Inserted /api proxy -> 127.0.0.1:8000")

if __name__ == "__main__":
    main()
