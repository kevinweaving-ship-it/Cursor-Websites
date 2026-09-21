"""
Boats Audit Routes for SailingSA API

Add this to api.py after existing admin routes.

Endpoints:
- /admin/boats-audit - HTML page
- /admin/api/boats-audit - JSON data
- /boat/{boat_id} - Individual boat page
"""

# =============================================================================
# BOATS AUDIT DATA ENDPOINT
# =============================================================================

@app.get("/admin/api/boats-audit")
def admin_api_boats_audit(
    q: str = Query(None, description="Search query"),
    class_id: int = Query(None, description="Filter by class"),
    family: str = Query(None, description="Filter by hull family"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500)
):
    """Get boats audit data with statistics."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get summary stats
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM boats) as total_boats,
                (SELECT COUNT(*) FROM boat_identifiers) as total_identifiers,
                (SELECT COUNT(*) FROM boat_names) as total_names,
                (SELECT COUNT(*) FROM results WHERE boat_id IS NOT NULL) as results_linked,
                (SELECT COUNT(*) FROM results WHERE boat_id IS NULL AND sail_number IS NOT NULL AND sail_number != '') as results_unlinked
        """)
        stats = dict(cur.fetchone())
        
        # Get hull families
        cur.execute("""
            SELECT cf.family_id, cf.family_name, cf.share_sail_identity,
                   COUNT(DISTINCT cfm.class_id) as class_count,
                   COUNT(DISTINCT bi.boat_id) as boat_count
            FROM class_hull_families cf
            LEFT JOIN class_family_members cfm ON cf.family_id = cfm.family_id
            LEFT JOIN boat_identifiers bi ON bi.class_id = cfm.class_id AND bi.is_current = TRUE
            GROUP BY cf.family_id, cf.family_name, cf.share_sail_identity
            ORDER BY cf.family_name
        """)
        families = [dict(r) for r in cur.fetchall()]
        
        # Build boats query
        where_clauses = []
        params = []
        
        if q:
            where_clauses.append("(bi.identifier_value ILIKE %s OR bn.boat_name ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
        
        if class_id:
            where_clauses.append("bi.class_id = %s")
            params.append(class_id)
        
        if family:
            where_clauses.append("cf.family_name = %s")
            params.append(family)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
        
        # Get boats
        offset = (page - 1) * limit
        cur.execute(f"""
            SELECT DISTINCT ON (b.boat_id)
                b.boat_id,
                bi.identifier_value as sail_number,
                bn.boat_name,
                c.class_name,
                c.class_id,
                cf.family_name as hull_family,
                b.created_at,
                b.created_source,
                (SELECT COUNT(*) FROM results r WHERE r.boat_id = b.boat_id) as result_count,
                (SELECT COUNT(*) FROM boat_identifiers bi2 WHERE bi2.boat_id = b.boat_id) as identifier_count,
                (SELECT COUNT(*) FROM boat_names bn2 WHERE bn2.boat_id = b.boat_id) as name_count
            FROM boats b
            LEFT JOIN boat_identifiers bi ON bi.boat_id = b.boat_id AND bi.is_current = TRUE
            LEFT JOIN boat_names bn ON bn.boat_id = b.boat_id
            LEFT JOIN classes c ON c.class_id = bi.class_id
            LEFT JOIN class_family_members cfm ON cfm.class_id = c.class_id
            LEFT JOIN class_hull_families cf ON cf.family_id = cfm.family_id
            WHERE {where_sql}
            ORDER BY b.boat_id DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        boats = [dict(r) for r in cur.fetchall()]
        
        # Get total count for pagination
        cur.execute(f"""
            SELECT COUNT(DISTINCT b.boat_id)
            FROM boats b
            LEFT JOIN boat_identifiers bi ON bi.boat_id = b.boat_id AND bi.is_current = TRUE
            LEFT JOIN boat_names bn ON bn.boat_id = b.boat_id
            LEFT JOIN classes c ON c.class_id = bi.class_id
            LEFT JOIN class_family_members cfm ON cfm.class_id = c.class_id
            LEFT JOIN class_hull_families cf ON cf.family_id = cfm.family_id
            WHERE {where_sql}
        """, params)
        total = cur.fetchone()[0]
        
        return {
            "stats": stats,
            "families": families,
            "boats": boats,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        print(f"Error in boats audit: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)


# =============================================================================
# BOATS AUDIT HTML PAGE
# =============================================================================

@app.get("/admin/boats-audit", response_class=HTMLResponse)
def admin_boats_audit(request: Request):
    """Boats Register audit page."""
    if socket.gethostname() != ADMIN_LIVE_HOSTNAME:
        raise HTTPException(status_code=403, detail="Admin disabled on local.")
    role = _get_session_role(request)
    if not role or role not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    if not os.path.isfile(_INDEX_HTML_PATH):
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(_INDEX_HTML_PATH, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    
    boats_panel = """
<style id="boats-audit-style">
body.boats-audit-page .search-header-container, body.boats-audit-page .search-row-container, body.boats-audit-page #landing-news-embed, body.boats-audit-page #site-stats-embed, body.boats-audit-page #public-regattas-section, body.boats-audit-page .search-to-profile-separator { display: none !important; }
#boats-audit-panel { max-width: 100%; margin: 12px auto; padding: 12px; background: #fff; border-radius: 8px; border: 1px solid #001f3f; box-shadow: 0 4px 12px rgba(0,0,0,0.1); box-sizing: border-box; }
#boats-audit-panel h1 { font-size: 1.1rem; margin: 0 0 12px 0; color: #0f172a; }
#boats-audit-panel .stats-bar { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 16px; padding: 12px; background: #f0f9ff; border-radius: 8px; }
#boats-audit-panel .stat-item { text-align: center; }
#boats-audit-panel .stat-value { font-size: 1.5rem; font-weight: 700; color: #0c4a6e; }
#boats-audit-panel .stat-label { font-size: 0.75rem; color: #64748b; }
#boats-audit-panel .filters { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; align-items: center; }
#boats-audit-panel input[type="text"], #boats-audit-panel select { min-height: 44px; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
#boats-audit-panel input[type="text"] { width: 200px; }
#boats-audit-panel .table-wrap { overflow-x: auto; max-height: 70vh; overflow-y: auto; }
#boats-audit-panel table { width: 100%; border-collapse: collapse; font-size: 14px; min-width: 600px; }
#boats-audit-panel th, #boats-audit-panel td { padding: 10px 8px; text-align: left; border-top: 1px solid #e2e8f0; }
#boats-audit-panel th { background: #e2e8f0; color: #0f172a; font-weight: 700; position: sticky; top: 0; }
#boats-audit-panel tr:hover { background: #f1f5f9; }
#boats-audit-panel td a { color: #001f3f; }
#boats-audit-panel .family-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
#boats-audit-panel .family-ilca { background: #dbeafe; color: #1e40af; }
#boats-audit-panel .family-optimist { background: #dcfce7; color: #166534; }
#boats-audit-panel .family-other { background: #f3e8ff; color: #7c3aed; }
#boats-audit-panel .pagination { display: flex; gap: 8px; margin-top: 12px; align-items: center; }
#boats-audit-panel .pagination button { padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; background: #fff; }
#boats-audit-panel .pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
#boats-audit-panel .pagination button:hover:not(:disabled) { background: #f1f5f9; }
@media (min-width: 640px) { #boats-audit-panel { margin: 20px auto; padding: 20px; max-width: 1400px; } }
</style>
<div id="boats-audit-panel" style="display:block;">
<h1>Boats Register — Audit</h1>
<div id="boats-stats" class="stats-bar">Loading...</div>
<div class="filters">
<a href="/admin/dashboard-v3" style="color:#001f3f;font-weight:600;">← Dashboard</a>
<input type="text" id="boats-search" placeholder="Search sail #, boat name..." />
<select id="boats-family-filter"><option value="">All Families</option></select>
</div>
<div id="boats-list" class="table-wrap">Loading...</div>
<div id="boats-pagination" class="pagination"></div>
</div>
<script>
(function(){
 if (window.location.pathname !== '/admin/boats-audit') { var p = document.getElementById('boats-audit-panel'); if (p) p.style.display = 'none'; return; }
 if (document.body) document.body.classList.add('boats-audit-page');
 var statsEl = document.getElementById('boats-stats');
 var listEl = document.getElementById('boats-list');
 var searchEl = document.getElementById('boats-search');
 var familyEl = document.getElementById('boats-family-filter');
 var paginationEl = document.getElementById('boats-pagination');
 var page = 1;
 var limit = 100;
 var debounceTimer = null;
 function esc(s) { return s == null ? '' : String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
 function familyClass(f) {
  if (!f) return '';
  var fl = f.toLowerCase();
  if (fl.indexOf('ilca') !== -1 || fl.indexOf('laser') !== -1) return 'family-ilca';
  if (fl.indexOf('optimist') !== -1) return 'family-optimist';
  return 'family-other';
 }
 function load() {
  var q = searchEl.value.trim();
  var family = familyEl.value;
  var url = '/admin/api/boats-audit?page=' + page + '&limit=' + limit;
  if (q) url += '&q=' + encodeURIComponent(q);
  if (family) url += '&family=' + encodeURIComponent(family);
  fetch(url).then(r => r.json()).then(function(data) {
   var s = data.stats;
   statsEl.innerHTML = '<div class="stat-item"><div class="stat-value">' + s.total_boats + '</div><div class="stat-label">Boats</div></div>'
    + '<div class="stat-item"><div class="stat-value">' + s.total_identifiers + '</div><div class="stat-label">Identifiers</div></div>'
    + '<div class="stat-item"><div class="stat-value">' + s.total_names + '</div><div class="stat-label">Names</div></div>'
    + '<div class="stat-item"><div class="stat-value">' + s.results_linked + '</div><div class="stat-label">Results Linked</div></div>'
    + '<div class="stat-item"><div class="stat-value">' + s.results_unlinked + '</div><div class="stat-label">Unlinked</div></div>';
   if (familyEl.options.length <= 1 && data.families.length > 0) {
    data.families.forEach(function(f) {
     var opt = document.createElement('option');
     opt.value = f.family_name;
     opt.textContent = f.family_name + ' (' + f.boat_count + ')';
     familyEl.appendChild(opt);
    });
   }
   if (data.boats.length === 0) {
    listEl.innerHTML = '<p style="padding:20px;color:#64748b;">No boats found.</p>';
   } else {
    var html = '<table><thead><tr><th>ID</th><th>Sail #</th><th>Boat Name</th><th>Class</th><th>Family</th><th>Results</th><th>Source</th></tr></thead><tbody>';
    data.boats.forEach(function(b) {
     var familyTag = b.hull_family ? '<span class="family-tag ' + familyClass(b.hull_family) + '">' + esc(b.hull_family) + '</span>' : '-';
     html += '<tr>'
      + '<td><a href="/boat/' + b.boat_id + '">' + b.boat_id + '</a></td>'
      + '<td>' + esc(b.sail_number || '-') + '</td>'
      + '<td>' + esc(b.boat_name || '-') + '</td>'
      + '<td>' + esc(b.class_name || '-') + '</td>'
      + '<td>' + familyTag + '</td>'
      + '<td>' + (b.result_count || 0) + '</td>'
      + '<td>' + esc(b.created_source || '-') + '</td>'
      + '</tr>';
    });
    html += '</tbody></table>';
    listEl.innerHTML = html;
   }
   var p = data.pagination;
   var phtml = '<span>Page ' + p.page + ' of ' + p.pages + ' (' + p.total + ' boats)</span>';
   phtml += '<button ' + (p.page <= 1 ? 'disabled' : '') + ' onclick="window._boatsPage(' + (p.page-1) + ')">Prev</button>';
   phtml += '<button ' + (p.page >= p.pages ? 'disabled' : '') + ' onclick="window._boatsPage(' + (p.page+1) + ')">Next</button>';
   paginationEl.innerHTML = phtml;
  }).catch(function(e) {
   listEl.innerHTML = '<p style="color:red;">Error loading data: ' + e.message + '</p>';
  });
 }
 window._boatsPage = function(p) { page = p; load(); };
 searchEl.addEventListener('input', function() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(function() { page = 1; load(); }, 300);
 });
 familyEl.addEventListener('change', function() { page = 1; load(); });
 load();
})();
</script>
"""
    
    html = html.replace("</body>", boats_panel + "</body>")
    return HTMLResponse(content=html)


# =============================================================================
# INDIVIDUAL BOAT PAGE
# =============================================================================

@app.get("/boat/{boat_id}", response_class=HTMLResponse)
def boat_page(boat_id: int, request: Request):
    """Individual boat page showing history and identifiers."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get boat basic info
        cur.execute("SELECT * FROM boats WHERE boat_id = %s", (boat_id,))
        boat = cur.fetchone()
        if not boat:
            raise HTTPException(status_code=404, detail="Boat not found")
        boat = dict(boat)
        
        # Get identifiers
        cur.execute("""
            SELECT bi.*, c.class_name
            FROM boat_identifiers bi
            LEFT JOIN classes c ON c.class_id = bi.class_id
            WHERE bi.boat_id = %s
            ORDER BY bi.is_current DESC, bi.valid_from DESC
        """, (boat_id,))
        identifiers = [dict(r) for r in cur.fetchall()]
        
        # Get names
        cur.execute("""
            SELECT * FROM boat_names
            WHERE boat_id = %s
            ORDER BY last_seen_date DESC
        """, (boat_id,))
        names = [dict(r) for r in cur.fetchall()]
        
        # Get results history
        cur.execute("""
            SELECT r.result_id, r.sail_number, r.boat_name as result_boat_name, r.helm_name, r.helm_sa_sailing_id,
                   r.place_overall, r.nett_points,
                   reg.event_name, reg.start_date, reg.regatta_id,
                   c.class_name
            FROM results r
            JOIN regattas reg ON reg.regatta_id = r.regatta_id
            LEFT JOIN classes c ON c.class_id = r.class_id
            WHERE r.boat_id = %s
            ORDER BY reg.start_date DESC
            LIMIT 50
        """, (boat_id,))
        results = [dict(r) for r in cur.fetchall()]
        
        # Get hull family if applicable
        hull_family = None
        if identifiers:
            class_id = identifiers[0].get('class_id')
            if class_id:
                cur.execute("""
                    SELECT cf.family_name, cf.share_sail_identity
                    FROM class_family_members cfm
                    JOIN class_hull_families cf ON cf.family_id = cfm.family_id
                    WHERE cfm.class_id = %s
                """, (class_id,))
                row = cur.fetchone()
                if row:
                    hull_family = dict(row)
        
        # Build HTML page
        if not os.path.isfile(_INDEX_HTML_PATH):
            raise HTTPException(status_code=404, detail="index.html not found")
        with open(_INDEX_HTML_PATH, "r", encoding="utf-8", errors="replace") as f:
            base_html = f.read()
        
        # Get display values
        sail_number = identifiers[0]['identifier_value'] if identifiers else "Unknown"
        boat_name = names[0]['boat_name'] if names else ""
        class_name = identifiers[0]['class_name'] if identifiers else "Unknown"
        
        title = f"Boat {sail_number}"
        if boat_name:
            title = f"{boat_name} ({sail_number})"
        
        def esc(s):
            if s is None:
                return ""
            return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        
        # Build identifiers table
        id_rows = ""
        for i in identifiers:
            current = "✓" if i['is_current'] else ""
            id_rows += f"""<tr>
                <td>{esc(i['identifier_type'])}</td>
                <td><strong>{esc(i['identifier_value'])}</strong></td>
                <td>{esc(i['class_name'] or '-')}</td>
                <td>{esc(str(i['valid_from']) if i['valid_from'] else '-')}</td>
                <td>{current}</td>
            </tr>"""
        
        # Build names table
        name_rows = ""
        for n in names:
            name_rows += f"""<tr>
                <td><strong>{esc(n['boat_name'])}</strong></td>
                <td>{esc(str(n['first_seen_date']) if n['first_seen_date'] else '-')}</td>
                <td>{esc(str(n['last_seen_date']) if n['last_seen_date'] else '-')}</td>
            </tr>"""
        
        # Build results table
        result_rows = ""
        for r in results:
            date_str = str(r['start_date'])[:10] if r['start_date'] else "-"
            sailor_link = f'<a href="/sailor/{r["helm_sa_sailing_id"]}">{esc(r["helm_name"])}</a>' if r['helm_sa_sailing_id'] else esc(r['helm_name'] or '-')
            result_rows += f"""<tr>
                <td><a href="/regatta/{esc(r['regatta_id'])}">{esc(r['event_name'])}</a></td>
                <td>{date_str}</td>
                <td>{esc(r['class_name'] or '-')}</td>
                <td>{sailor_link}</td>
                <td>{r['place_overall'] or '-'}</td>
            </tr>"""
        
        family_badge = ""
        if hull_family:
            family_class = "family-ilca" if "ilca" in hull_family['family_name'].lower() or "laser" in hull_family['family_name'].lower() else ("family-optimist" if "optimist" in hull_family['family_name'].lower() else "family-other")
            family_badge = f'<span class="family-tag {family_class}">{esc(hull_family["family_name"])}</span>'
        
        page_content = f"""
<style>
body.boat-page .search-header-container, body.boat-page .search-row-container, body.boat-page #landing-news-embed, body.boat-page #site-stats-embed, body.boat-page #public-regattas-section, body.boat-page .search-to-profile-separator {{ display: none !important; }}
#boat-page-panel {{ max-width: 1200px; margin: 12px auto; padding: 12px; background: #fff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
#boat-page-panel h1 {{ font-size: 1.5rem; margin: 0 0 4px 0; color: #0f172a; }}
#boat-page-panel .boat-subtitle {{ color: #64748b; margin-bottom: 16px; }}
#boat-page-panel .section {{ margin-bottom: 24px; }}
#boat-page-panel .section h2 {{ font-size: 1rem; color: #334155; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 12px; }}
#boat-page-panel table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
#boat-page-panel th, #boat-page-panel td {{ padding: 10px 8px; text-align: left; border-top: 1px solid #e2e8f0; }}
#boat-page-panel th {{ background: #f8fafc; font-weight: 600; }}
#boat-page-panel tr:hover {{ background: #f8fafc; }}
#boat-page-panel a {{ color: #001f3f; }}
.family-tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 8px; }}
.family-ilca {{ background: #dbeafe; color: #1e40af; }}
.family-optimist {{ background: #dcfce7; color: #166534; }}
.family-other {{ background: #f3e8ff; color: #7c3aed; }}
.meta-info {{ display: flex; flex-wrap: wrap; gap: 16px; padding: 12px; background: #f8fafc; border-radius: 8px; margin-bottom: 16px; font-size: 13px; }}
.meta-item {{ }}
.meta-label {{ color: #64748b; }}
.meta-value {{ font-weight: 600; color: #0f172a; }}
</style>
<div id="boat-page-panel">
<div style="margin-bottom:12px;"><a href="/admin/boats-audit" style="color:#001f3f;">← Boats Audit</a></div>
<h1>{esc(title)} {family_badge}</h1>
<p class="boat-subtitle">Class: {esc(class_name)} | Boat ID: {boat_id}</p>

<div class="meta-info">
<div class="meta-item"><span class="meta-label">Created:</span> <span class="meta-value">{str(boat.get('created_at', '-'))[:19]}</span></div>
<div class="meta-item"><span class="meta-label">Source:</span> <span class="meta-value">{esc(boat.get('created_source', '-'))}</span></div>
<div class="meta-item"><span class="meta-label">Results:</span> <span class="meta-value">{len(results)}</span></div>
</div>

<div class="section">
<h2>Identifiers ({len(identifiers)})</h2>
<table>
<thead><tr><th>Type</th><th>Value</th><th>Class</th><th>Valid From</th><th>Current</th></tr></thead>
<tbody>{id_rows if id_rows else '<tr><td colspan="5">No identifiers</td></tr>'}</tbody>
</table>
</div>

<div class="section">
<h2>Names ({len(names)})</h2>
<table>
<thead><tr><th>Name</th><th>First Seen</th><th>Last Seen</th></tr></thead>
<tbody>{name_rows if name_rows else '<tr><td colspan="3">No names recorded</td></tr>'}</tbody>
</table>
</div>

<div class="section">
<h2>Results History (Latest {len(results)})</h2>
<table>
<thead><tr><th>Regatta</th><th>Date</th><th>Class</th><th>Helm</th><th>Place</th></tr></thead>
<tbody>{result_rows if result_rows else '<tr><td colspan="5">No results</td></tr>'}</tbody>
</table>
</div>
</div>
<script>
if (document.body) document.body.classList.add('boat-page');
</script>
"""
        
        html = base_html.replace("</body>", page_content + "</body>")
        return HTMLResponse(content=html)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in boat page: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)
