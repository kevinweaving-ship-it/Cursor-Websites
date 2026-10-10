#!/usr/bin/env python3
"""Dam Bottle ET + corrected-time store. Writes results.duration_time / corrected_time. Not gold api.py."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
PATHS = {"/api/hmyc-dam-bottle-et", "/api/hmyc-dam-bottle-et/"}
STORE = Path("/var/www/sailingsa/assets/hmyc-dam-bottle-et.json")
DAM = "2026-10-10-hmyc-dam-bottle-sprints"
MAX = 32 * 1024


def db_url():
    text = Path("/etc/systemd/system/sailingsa-api.service").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'Environment="DB_URL=([^"]+)"', text)
    return m.group(1) if m else ""


def parse_time_field(raw):
    s = str(raw or "").strip()
    if not s:
        return {}
    if s.startswith("{"):
        try:
            o = json.loads(s)
            return o if isinstance(o, dict) else {}
        except Exception:
            return {"R1": s}
    return {"R1": s}


def rec_of(v):
    if not v:
        return {}
    if isinstance(v, str):
        t = v.strip()
        return {"et": t} if t else {}
    return {
        "et": str(v.get("et") or "").strip(),
        "corr": str(v.get("corr") or "").strip(),
        "place": str(v.get("place") or "").strip(),
    }


def merge_store(into, extra):
    into = into if isinstance(into, dict) else {}
    extra = extra if isinstance(extra, dict) else {}
    for race, rows in extra.items():
        if not str(race).startswith("R") or not isinstance(rows, dict):
            continue
        into.setdefault(race, {})
        for rid, raw in rows.items():
            have = rec_of(into[race].get(str(rid)))
            add = rec_of(raw)
            if not have.get("et") and add.get("et"):
                into[race][str(rid)] = add
            elif have.get("et"):
                if add.get("corr") and not have.get("corr"):
                    have["corr"] = add["corr"]
                if add.get("place") and not have.get("place"):
                    have["place"] = add["place"]
                into[race][str(rid)] = have
    return into


def load_from_db():
    store = {}
    url = db_url()
    if not url:
        return store
    try:
        import psycopg2
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute(
            "SELECT result_id, duration_time, corrected_time FROM results WHERE regatta_id=%s",
            (DAM,),
        )
        for rid, dur, corr in cur.fetchall():
            dmap = parse_time_field(dur)
            cmap = parse_time_field(corr)
            for race, et in dmap.items():
                race = str(race).upper()
                if not race.startswith("R"):
                    continue
                rec = rec_of({"et": et, "corr": cmap.get(race) or cmap.get(race.lower())})
                if rec.get("et"):
                    store.setdefault(race, {})[str(rid)] = rec
        conn.close()
    except Exception:
        return {}
    return store


def save_to_db(store):
    url = db_url()
    if not url:
        return
    by_rid = {}
    for race, rows in (store or {}).items():
        if not str(race).startswith("R") or not isinstance(rows, dict):
            continue
        for rid, raw in rows.items():
            rec = rec_of(raw)
            if not rec.get("et"):
                continue
            slot = by_rid.setdefault(str(rid), {"dur": {}, "corr": {}})
            slot["dur"][race] = rec["et"]
            if rec.get("corr"):
                slot["corr"][race] = rec["corr"]
    import psycopg2
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    for rid, maps in by_rid.items():
        cur.execute(
            "UPDATE results SET duration_time=%s, corrected_time=%s "
            "WHERE result_id=%s AND regatta_id=%s",
            (json.dumps(maps["dur"]), json.dumps(maps["corr"]), int(rid), DAM),
        )
    conn.commit()
    conn.close()


def read_store():
    payload = {"store": {}, "rid": DAM}
    if STORE.is_file():
        try:
            payload = json.loads(STORE.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                payload = {"store": {}, "rid": DAM}
        except Exception:
            payload = {"store": {}, "rid": DAM}
    payload["store"] = merge_store(payload.get("store") or {}, load_from_db())
    payload["rid"] = DAM
    return payload


def write_store(payload):
    if not isinstance(payload, dict):
        raise ValueError("object required")
    payload["store"] = merge_store(payload.get("store") or {}, {})
    payload["rid"] = DAM
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(STORE)
    save_to_db(payload.get("store") or {})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "https://sailingsa.co.za")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "https://sailingsa.co.za")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] not in PATHS:
            self._send(404, '{"ok":false}')
            return
        self._send(200, json.dumps(read_store(), ensure_ascii=False))

    def do_POST(self):
        if self.path.split("?", 1)[0] not in PATHS:
            self._send(404, '{"ok":false}')
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX:
            self._send(400, '{"ok":false,"error":"size"}')
            return
        try:
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            write_store(payload)
        except Exception as exc:
            self._send(400, json.dumps({"ok": False, "error": str(exc)}))
            return
        self._send(200, '{"ok":true}')


if __name__ == "__main__":
    STORE.parent.mkdir(parents=True, exist_ok=True)
    if not STORE.is_file():
        write_store({"store": {}, "rid": DAM})
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
