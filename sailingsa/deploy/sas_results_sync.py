#!/usr/bin/env python3
"""Stage recent SAS result sheets and retain revisions for review."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

INDEX = "https://www.sailing.org.za/what-we-do/event-results"
FILE = re.compile(r"/(?:file|site)/([a-z0-9]{16})(?:\.(pdf|jpe?g|png))?/?$", re.I)
HOSTS = {"www.sailing.org.za", "sailing.org.za", "cdn.revolutionise.com.au"}
SIGNATURES = {b"%PDF-": "pdf", b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}
RECENT_COUNT = 20
MAX_BYTES = 30 * 1024 * 1024


class ResultsLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.rows = {}
        self.link = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        url = urljoin(INDEX, dict(attrs).get("href") or "")
        parts = urlsplit(url)
        match = FILE.fullmatch(parts.path)
        if parts.scheme == "https" and parts.hostname in HOSTS and match:
            file_id, ext = match.groups()
            self.link = (file_id, ext, url, [])

    def handle_data(self, data):
        if self.link:
            self.link[3].append(data)

    def handle_endtag(self, tag):
        if tag != "a" or self.link is None:
            return
        file_id, ext, url, chunks = self.link
        self.link = None
        title = " ".join(" ".join(chunks).split())
        if title:
            self.rows.setdefault(file_id, dict(title=title, url=url, extension=ext))


def fetch(url, validators=None):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SailingSA Results Sync)",
               "Referer": INDEX}
    headers.update(validators or {})
    try:
        with urlopen(Request(url, headers=headers), timeout=25) as response:
            destination = urlsplit(response.geturl())
            if destination.scheme != "https" or destination.hostname not in HOSTS:
                raise ValueError("unexpected redirect destination")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("response exceeded size limit")
            return data, response.headers
    except HTTPError as error:
        if error.code == 304 and validators:
            return None, error.headers
        raise


def index_rows(render_command):
    try:
        data, _ = fetch(INDEX)
        rows = ResultsLinks(data.decode("utf-8", "replace")).rows
        if len(rows) >= RECENT_COUNT:
            return rows
        raise ValueError(f"only {len(rows)} result links in SAS index")
    except (OSError, ValueError) as error:
        if not render_command:
            raise
        print(f"Direct SAS index fetch failed ({error}). Trying browser.", flush=True)
        html = subprocess.check_output(
            [render_command, "--headless", "--disable-gpu",
             "--virtual-time-budget=10000", "--dump-dom", INDEX],
            text=True, timeout=60,
        )
        rows = ResultsLinks(html).rows
        if len(rows) < RECENT_COUNT:
            raise ValueError(f"browser found only {len(rows)} result links")
        return rows


def write_atomic(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def stage(directory, file_id, row, previous):
    validators = {}
    if previous.get("url") == row["url"] and (directory / previous["file"]).is_file():
        validators = previous.get("validators", {})
    data, headers = fetch(row["url"], validators)
    if data is None:
        return {**previous, **row}
    extension = next((ext for signature, ext in SIGNATURES.items()
                      if data.startswith(signature)), None)
    if extension is None:
        raise ValueError("download did not contain a PDF, JPEG or PNG")
    digest = hashlib.sha256(data).hexdigest()
    name = f"{file_id}-{digest}.{extension}"
    if not (directory / name).exists():
        write_atomic(directory / name, data)
    validators = {request: headers[response] for request, response in
                  (("If-None-Match", "ETag"), ("If-Modified-Since", "Last-Modified"))
                  if response in headers}
    return {**row, "file": name, "sha256": digest, "validators": validators}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--browser", help="Optional Chromium executable for rendered index")
    args = parser.parse_args()
    directory = args.state_dir
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "manifest.json"
    previous = json.loads(manifest.read_text()) if manifest.exists() else {}
    rows = index_rows(args.browser)
    files = previous.get("files", {})
    errors = {}
    changed = 0
    # Start with the newest sheets, retry failures and recheck staged sheets.
    new_ids = rows.keys() - previous["index"].keys() if previous else set()
    targets = dict.fromkeys([*list(rows)[:RECENT_COUNT],
                             *(file_id for file_id in rows if file_id in new_ids),
                             *previous.get("errors", {}), *files])
    for file_id in targets:
        if file_id not in rows:
            continue
        prior = files.get(file_id, {})
        try:
            result = stage(directory, file_id, rows[file_id], prior)
            changed += result["sha256"] != prior.get("sha256")
            files[file_id] = result
        except (OSError, ValueError) as error:
            errors[file_id] = str(error)
            print(f'{rows[file_id]["title"]}: {error}', flush=True)
    state = {"checked_at": datetime.now(timezone.utc).isoformat(),
             "index": rows, "files": files, "errors": errors}
    write_atomic(manifest, json.dumps(state, indent=2).encode())
    print(f"SAS results: {len(rows)} listed, {changed} new/revised, {len(errors)} failed")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
