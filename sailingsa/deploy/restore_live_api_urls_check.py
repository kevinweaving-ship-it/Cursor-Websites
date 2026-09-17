#!/usr/bin/env python3
import urllib.request

def hit(path):
    class NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    o = urllib.request.build_opener(NoRedir)
    r = urllib.request.Request(
        "http://127.0.0.1:8000" + path,
        headers={"Host": "sailingsa.co.za", "X-Forwarded-Proto": "https"},
    )
    try:
        with o.open(r, timeout=25) as resp:
            return resp.status, resp.getheader("Location") or "", len(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location") or "", 0

for p in (
    "/class/420",
    "/class/7-420",
    "/class/62-optimist-a",
    "/events-logos",
    "/events-logos/lipton-challenge-cup",
    "/classes",
    "/club/hmyc",
):
    print(p, *hit(p))
