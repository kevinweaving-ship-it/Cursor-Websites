_TSC_CAPE_CLASSIC_RID = "2026-11-28-tsc-cape-classic"
_TSC_LIVE_CAM_PAGE = (
    "https://www.skylinewebcams.com/en/webcam/south-africa/"
    "western-cape/villiersdorp/watersports-western-cape.html"
)
_TSC_CAM_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": _TSC_LIVE_CAM_PAGE,
    "Accept": "*/*",
}
_TSC_GRAB_LOCK = threading.Lock()
_TSC_GRAB_MEM = {"tok": "", "tok_t": 0.0, "live": False, "probe_t": 0.0, "probe_reason": ""}
_TSC_CAM_PROBE_TTL_SEC = 12.0
_TSC_CAM_STATE_PATH = "/var/www/sailingsa/api/data/tsc_cam_stamp.json"
_TSC_HTML_MIN_INTERVAL_SEC = 120.0
_TSC_HTML_BACKOFF_CAP_SEC = 900.0


def _tsc_cam_rid_ok(regatta_id: str) -> bool:
    rid = str(regatta_id or "").strip().lower()
    if not rid:
        return False
    if rid == _TSC_CAPE_CLASSIC_RID:
        return True
    return rid.endswith("-tsc-cape-classic")


def _tsc_cam_load_state() -> dict:
    try:
        with open(_TSC_CAM_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _tsc_cam_save_state(**kwargs) -> None:
    st = _tsc_cam_load_state()
    st.update(kwargs)
    path = _TSC_CAM_STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(tmp, path)


def _tsc_token_url(tok: str) -> str:
    return "https://hd-auth.skylinewebcams.com/live.m3u8?a=" + tok


def _tsc_remember_token(tok: str) -> str:
    tok = _zvyc_normalize_cam_token(tok)
    if not tok:
        return ""
    now = time.time()
    with _TSC_GRAB_LOCK:
        _TSC_GRAB_MEM["tok"] = tok
        _TSC_GRAB_MEM["tok_t"] = now
    try:
        _tsc_cam_save_state(tok=tok, tok_t=now)
    except Exception as e:
        print(f"[tsc_live_cam] save token failed: {e}", flush=True)
    return tok


def _tsc_known_token() -> str:
    with _TSC_GRAB_LOCK:
        tok = _zvyc_normalize_cam_token(str(_TSC_GRAB_MEM.get("tok") or ""))
        if tok:
            return tok
    st = _tsc_cam_load_state()
    tok = _zvyc_normalize_cam_token(str(st.get("tok") or ""))
    if tok:
        with _TSC_GRAB_LOCK:
            _TSC_GRAB_MEM["tok"] = tok
            _TSC_GRAB_MEM["tok_t"] = float(st.get("tok_t") or 0)
    return tok


def _tsc_html_backoff_ok() -> bool:
    st = _tsc_cam_load_state()
    now = time.time()
    until = float(st.get("html_backoff_until") or 0)
    last = float(st.get("html_fetch_t") or 0)
    if until and now < until:
        return False
    if last and now - last < _TSC_HTML_MIN_INTERVAL_SEC:
        return False
    return True


def _tsc_scrape_token() -> str:
    """Pull the current Skyline player token. Back off hard on 429."""
    if not _tsc_html_backoff_ok():
        return ""
    now = time.time()
    try:
        _tsc_cam_save_state(html_fetch_t=now)
    except Exception:
        pass
    html_headers = dict(_TSC_CAM_FETCH_HEADERS)
    html_headers["Accept"] = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
    html_headers["Accept-Language"] = "en-US,en;q=0.9"
    html_headers.pop("Accept-Encoding", None)
    try:
        with httpx.Client(
            timeout=8.0, follow_redirects=True, headers=html_headers
        ) as client:
            resp = client.get(_TSC_LIVE_CAM_PAGE)
        if int(resp.status_code) == 429:
            raw = str(resp.headers.get("retry-after") or "300").strip()
            try:
                wait = float(raw)
            except Exception:
                wait = 300.0
            wait = min(max(wait, 60.0), _TSC_HTML_BACKOFF_CAP_SEC)
            try:
                _tsc_cam_save_state(
                    html_backoff_until=time.time() + wait, html_status=429
                )
            except Exception:
                pass
            print(f"[tsc_live_cam] html 429 backoff {wait}s", flush=True)
            return ""
        html = resp.text or ""
        m = _ZVYC_LIVE_M3U8_RE.search(html)
        if m:
            return _tsc_remember_token(m.group(1))
    except Exception as e:
        print(f"[tsc_live_cam] resolve failed: {e}", flush=True)
        try:
            _tsc_cam_save_state(html_backoff_until=time.time() + 60)
        except Exception:
            pass
    return ""


def _tsc_cam_proxy_url(dest: str) -> str:
    return (
        f"/api/regatta/{_TSC_CAPE_CLASSIC_RID}/tsc-live-cam-seg?u="
        + quote(dest, safe="")
    )


def _tsc_rewrite_playlist(text: str, base_url: str) -> str:
    """Point playlist URIs at our pass-through. Do not store the feed."""
    lines = []
    for line in str(text or "").splitlines():
        stripped = line.strip()

        def _rewrite_uri(match):
            dest = urljoin(base_url, match.group(1))
            if _zvyc_allowed_cam_url(dest):
                return 'URI="' + _tsc_cam_proxy_url(dest) + '"'
            return match.group(0)

        if stripped.startswith("#") and "URI=" in stripped:
            lines.append(re.sub(r'URI="([^"]+)"', _rewrite_uri, line))
        elif stripped and not stripped.startswith("#"):
            dest = urljoin(base_url, stripped)
            if _zvyc_allowed_cam_url(dest):
                lines.append(_tsc_cam_proxy_url(dest))
            else:
                lines.append(line)
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def _tsc_live_cam_stream_url(explicit_token: str = "") -> str:
    """Resolve the current TSC Skyline HLS URL. Prefer a saved token over HTML scrape."""
    tok = _zvyc_normalize_cam_token(explicit_token)
    if tok:
        _tsc_remember_token(tok)
        return _tsc_token_url(tok)
    tok = _tsc_known_token()
    if tok:
        return _tsc_token_url(tok)
    tok = _tsc_scrape_token()
    if tok:
        return _tsc_token_url(tok)
    tok = _tsc_known_token()
    if tok:
        return _tsc_token_url(tok)
    return ""


def _tsc_fetch_playlist(url: str):
    with httpx.Client(
        timeout=8.0, follow_redirects=True, headers=_TSC_CAM_FETCH_HEADERS
    ) as client:
        resp = client.get(url)
    return int(resp.status_code), (resp.text or ""), str(resp.url)


def _tsc_cam_probe_live(explicit_token: str = "") -> bool:
    now = time.time()
    with _TSC_GRAB_LOCK:
        probe_t = float(_TSC_GRAB_MEM.get("probe_t") or 0)
        if probe_t and now - probe_t < _TSC_CAM_PROBE_TTL_SEC:
            return bool(_TSC_GRAB_MEM.get("live"))
    url = _tsc_live_cam_stream_url(explicit_token)
    live = False
    reason = "no_url"
    body = ""
    status_code = 0
    if url:
        try:
            status_code, body, _final = _tsc_fetch_playlist(url)
            live = status_code < 400 and _zvyc_cam_playlist_is_live(body)
            reason = "hls" if live else "not_live"
            if (not live) and (not explicit_token):
                scraped = _tsc_scrape_token()
                if scraped:
                    status_code, body, _final = _tsc_fetch_playlist(_tsc_token_url(scraped))
                    live = status_code < 400 and _zvyc_cam_playlist_is_live(body)
                    reason = "hls" if live else "not_live"
        except Exception as e:
            reason = f"err:{e}"
    with _TSC_GRAB_LOCK:
        _TSC_GRAB_MEM["live"] = live
        _TSC_GRAB_MEM["probe_t"] = now
        _TSC_GRAB_MEM["probe_reason"] = reason
        if live:
            _TSC_GRAB_MEM["tok_t"] = now
    if not live:
        print(
            f"[tsc_live_cam] probe live={live} status={status_code} reason={reason}",
            flush=True,
        )
    return live


@app.get("/api/regatta/{regatta_id}/tsc-live-cam-status")
def api_tsc_live_cam_status(regatta_id: str, a: str = Query("")):
    if not _tsc_cam_rid_ok(regatta_id):
        raise HTTPException(status_code=404, detail="not found")
    live = _tsc_cam_probe_live(a)
    with _TSC_GRAB_LOCK:
        reason = str(_TSC_GRAB_MEM.get("probe_reason") or "")
    return {"live": bool(live), "reason": reason}


@app.get("/api/regatta/{regatta_id}/tsc-live-cam")
async def api_tsc_live_cam(regatta_id: str, a: str = Query("")):
    """Pass through the current TSC Skyline HLS playlist. Do not store the feed."""
    if not _tsc_cam_rid_ok(regatta_id):
        raise HTTPException(status_code=404, detail="not found")
    url = _tsc_live_cam_stream_url(a)
    if not url:
        return Response(status_code=204, headers={"Cache-Control": "no-store"})
    try:
        status_code, body, final_url = _tsc_fetch_playlist(url)
        if status_code >= 400 or "#EXTM3U" not in body:
            scraped = _tsc_scrape_token()
            if scraped:
                status_code, body, final_url = _tsc_fetch_playlist(_tsc_token_url(scraped))
        if status_code >= 400 or "#EXTM3U" not in body:
            return Response(status_code=204, headers={"Cache-Control": "no-store"})
        playlist = _tsc_rewrite_playlist(body, final_url)
        return Response(
            content=playlist,
            media_type="application/vnd.apple.mpegurl",
            headers={"Cache-Control": "no-store"},
        )
    except Exception as e:
        print(f"[tsc_live_cam] playlist failed: {e}", flush=True)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})


@app.get("/api/regatta/{regatta_id}/tsc-live-cam-seg")
async def api_tsc_live_cam_seg(regatta_id: str, u: str = Query("")):
    """Pass through one TSC Skyline HLS segment or key. Do not store the feed."""
    if not _tsc_cam_rid_ok(regatta_id):
        raise HTTPException(status_code=404, detail="not found")
    dest = str(u or "").strip()
    if not _zvyc_allowed_cam_url(dest):
        raise HTTPException(status_code=400, detail="invalid cam url")
    try:
        with httpx.Client(
            timeout=15.0, follow_redirects=True, headers=_TSC_CAM_FETCH_HEADERS
        ) as client:
            resp = client.get(dest)
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail="cam segment failed")
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
        if not ctype or ctype in ("text/html", "application/octet-stream"):
            ctype = "video/MP2T" if dest.endswith(".ts") else (ctype or "application/octet-stream")
        return Response(
            content=resp.content,
            media_type=ctype,
            headers={"Cache-Control": "no-store"},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[tsc_live_cam] segment failed: {e}", flush=True)
        raise HTTPException(status_code=502, detail="cam segment failed")


