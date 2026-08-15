#!/usr/bin/env python3
"""Force lean /traffic/api/top; drop junk client-side; stop middleware swallow."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-force-lean-top-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # 1) Replace legacy traffic_api_top body to always use lean
    old_legacy = '''@app.get("/traffic/api/top")
def traffic_api_top(request: Request):
    _traffic_require_super_admin(request)
    _ta, runtime = _traffic_runtime()
    audience = request.query_params.get("audience") if request.query_params else "all"
    payload = {
        "audience": audience or "all",
        "top_pages": runtime.top_pages(limit=10, audience=audience or "all"),
'''
    if old_legacy in text:
        # Find end of function - next @app.get
        start = text.find(old_legacy)
        # find next def at same level after this function starts
        rest = text[start + 20 :]
        # Replace entire legacy function with thin wrapper
        end = -1
        for m in (
            '\n@app.get("/traffic/api/visual-overview")',
            "\n@app.get('/traffic/api/visual-overview')",
            '\n@app.get("/traffic/api/live")',
            '\n@app.get("/traffic/api/live-drill")',
        ):
            end = text.find(m, start + 50)
            if end > 0:
                break
        if end < 0:
            raise SystemExit("legacy top end not found")
        wrapper = (
            '@app.get("/traffic/api/top")\n'
            "def traffic_api_top(request: Request):\n"
            '    """Legacy route — always lean filtered top (no admin/bot probe pages)."""\n'
            "    return lean_traffic_api_top(request)\n\n\n"
        )
        # FastAPI keeps the first /traffic/api/top registration; replace legacy body.
        # lean_traffic_api_top is defined later — OK at call time.
        text = text[:start] + wrapper + text[end:]
    else:
        print("WARN: legacy traffic_api_top block not found exactly")

    # 2) Middleware: don't swallow lean top errors; re-raise filter only for unexpected
    old_mw = '''        if path == "/traffic/api/top":
            return lean_traffic_api_top(request)
'''
    # Already fine if lean works. Harden except to not fall through for traffic paths:
    old_except = '''    except Exception:
        pass
    return await call_next(request)'''
    # Only replace the one in lean override - find unique context
    mw_ctx = '''        if path in (
            "/traffic/api/recent",
            "/traffic/api/visual-overview",
            "/traffic/api/live-drill",
            "/traffic/api/registered-users",
        ):
            return lean_traffic_api_gone(request)
    except Exception:
        pass
    return await call_next(request)'''
    new_mw_ctx = '''        if path in (
            "/traffic/api/recent",
            "/traffic/api/visual-overview",
            "/traffic/api/live-drill",
            "/traffic/api/registered-users",
        ):
            return lean_traffic_api_gone(request)
    except Exception as e:
        # Never fall through to legacy traffic for /traffic* — that reintroduces bot/admin pages
        try:
            path = (request.url.path or "").rstrip("/") or "/"
        except Exception:
            path = ""
        if path.startswith("/traffic"):
            return JSONResponse(
                {"ok": False, "error": f"lean traffic failed: {type(e).__name__}: {e}"[:300]},
                status_code=500,
                headers={"Cache-Control": "no-store"},
            )
    return await call_next(request)'''
    if mw_ctx in text:
        text = text.replace(mw_ctx, new_mw_ctx, 1)
    else:
        print("WARN: middleware except block not found")

    # 3) Client-side belt: filter junk paths in renderTop
    old_render = '''  function renderTop(d){
    TOP_CACHE=d;
    var html=renderEntityBlocks(d.entities||{});
    var paths=d.top_paths||[];
    html+="<p class='note' style='margin-top:12px;font-weight:800;color:#08184a'>Pages</p>";
    html+="<table><thead><tr><th>Path</th><th>Hits</th><th>Vis</th></tr></thead><tbody>";
    paths.slice(0,15).forEach(function(p){
      html+="<tr><td><a href='"+esc(p.href||p.path)+"' style='display:inline-flex;align-items:center'>"+pathLabelHtml(p)+"</a></td><td>"+p.hits+"</td><td>"+p.visitors+"</td></tr>";
    });
'''
    new_render = '''  function isJunkTrafficPath(p){
    var raw=(p&&(p.path||p.href||""))||"";
    var path=(String(raw).split("?")[0]||"/").toLowerCase();
    if(!path||path==="#") return true;
    if(/\\.json$/.test(path)) return true;
    if(/\\.(php|env|zip|sql|bak|git)$/.test(path)) return true;
    var junkExact={"/account":1,"/app":1,"/console":1,"/dashboard":1,"/login":1,"/login.html":1,"/manage":1,"/my":1,"/portal":1,"/profile":1,"/settings":1,"/signin":1,"/signup":1,"/register":1,"/user":1,"/user/login":1,"/users":1,"/graphql":1,"/v1/graphql":1,"/class":1,"/club":1,"/workspace":1,"/manifest.json":1,"/asset-manifest.json":1,"/webpack-stats.json":1};
    if(junkExact[path]) return true;
    if(path.indexOf("/admin")===0||path.indexOf("/api/")===0||path.indexOf("/auth")===0) return true;
    if(path.indexOf("/wp-")===0||path.indexOf("/traffic")===0||path.indexOf("/lean-traffic")===0) return true;
    if(path.indexOf("/assets/")===0||path.indexOf("/static/")===0||path.indexOf("/dist/")===0) return true;
    return false;
  }
  function renderTop(d){
    TOP_CACHE=d;
    var ents=d.entities||{};
    // Drop entity rows that are only bot deep-links with no real pages (boat from quarantined IPs already absent server-side)
    var html=renderEntityBlocks(ents);
    var paths=(d.top_paths||[]).filter(function(p){ return !isJunkTrafficPath(p); });
    html+="<p class='note' style='margin-top:12px;font-weight:800;color:#08184a'>Pages</p>";
    html+="<table><thead><tr><th>Path</th><th>Hits</th><th>Vis</th></tr></thead><tbody>";
    paths.slice(0,15).forEach(function(p){
      html+="<tr><td><a href='"+esc(p.href||p.path)+"' style='display:inline-flex;align-items:center'>"+pathLabelHtml(p)+"</a></td><td>"+p.hits+"</td><td>"+p.visitors+"</td></tr>";
    });
'''
    if old_render not in text:
        raise SystemExit("renderTop block not found")
    text = text.replace(old_render, new_render, 1)

    # Cache-bust: bump a query noop in fetch top if any - add Cache-Control already no-store
    # Force loadAll to not use TOP_CACHE from old junk
    old_cache = "if(TOP_CACHE&&TOP_CACHE.ok) renderTop(TOP_CACHE);"
    if old_cache in text:
        text = text.replace(
            old_cache,
            "if(TOP_CACHE&&TOP_CACHE.ok) renderTop(TOP_CACHE); /* filtered */",
            1,
        )

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK force lean top (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
