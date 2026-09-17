#!/usr/bin/env python3
import urllib.request

HDRS = {"Host": "sailingsa.co.za", "X-Forwarded-Proto": "https"}

class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def fetch(path, follow=True):
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedir)
    req = urllib.request.Request("http://127.0.0.1:8000" + path, headers=HDRS)
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "")
        return e.code, loc, ""

s, url, h = fetch("/class/420", follow=True)
print("420_FOLLOW", s, url)
ok420 = s == 200 and "/class/420" in url and "/class/7-420" not in url

s2, loc, _ = fetch("/class/7-420", follow=False)
print("7_420_REDIR", s2, loc)
ok7 = s2 in (301, 302) and loc.rstrip("/").endswith("/class/420")

s3, _, h3 = fetch("/classes", follow=True)
print("CLASSES", s3, "id_links", h3.count("/class/7-420"), "slug_420", h3.count("/class/420"))
okdir = s3 == 200 and h3.count("/class/7-420") == 0 and "/class/420" in h3

print("OK420", ok420, "OK7", ok7, "OKDIR", okdir)
if not (ok420 and ok7 and okdir):
    raise SystemExit(1)
print("CLASS_URL_OK")
