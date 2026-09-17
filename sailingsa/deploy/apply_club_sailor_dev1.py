#!/usr/bin/env python3
"""Club sailors list: use the landing /dev-1 approved sailor card."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_SAILOR_DEV1_v1"

NEW_FN = r'''def _club_sailors_table_section_html(sailors: list, club_abbrev: str = "") -> str:
    # CLUB_SAILOR_DEV1_v1
    n = len(sailors or [])
    if n == 0:
        return (
            '<div class="club-home-cards-stack"><div class="card stats-section club-sailors-section">'
            '<h2 class="section-title">Sailors (0)</h2><p>No sailors found.</p></div></div>'
        )
    esc = html_module.escape
    club_code = (club_abbrev or "").strip()
    try:
        club_logo = _club_logo_public_url(club_code) if club_code else ""
    except Exception:
        club_logo = ""
    slots = []
    for row in sailors or []:
        name = row[0] if row else ""
        sslug = row[1] if len(row) > 1 else ""
        sas = str(row[2] or "").strip() if len(row) > 2 else ""
        fn = str(row[3] or "").strip() if len(row) > 3 else ""
        ln = str(row[4] or "").strip() if len(row) > 4 else ""
        full = str(row[5] or "").strip() if len(row) > 5 else name
        if not fn and "," in str(name):
            fn = str(name).split(",", 1)[0].strip()
            ln = str(name).split(",", 1)[1].strip()
        first = fn or (full.split(" ", 1)[0] if full else name) or "Sailor"
        last = ln or (" ".join(full.split(" ")[1:]) if full and " " in full else "")
        href = ("/sailor/" + sslug) if sslug else ""
        hay = esc(" ".join([name, first, last, sas]).lower(), quote=True)
        try:
            av_src = _users_avatar_url(sas, fn, ln, full)
        except Exception:
            av_src = "/assets/avatars/default-youth.png"
        fallback = (
            '<a class="club-dev1-fallback" href="%s">'
            '<img class="club-dev1-fallback-av" src="%s" alt="" loading="lazy" decoding="async">'
            '<span class="club-dev1-fallback-name"><b>%s</b><span>%s</span></span>'
            "</a>"
        ) % (
            esc(href or "#", quote=True),
            esc(av_src, quote=True),
            esc(first),
            esc(last),
        )
        if club_logo or club_code:
            fallback = fallback[:-4] + (
                '<span class="club-dev1-fallback-club">'
                + (
                    '<img src="%s" alt="" loading="lazy" decoding="async">' % esc(club_logo, quote=True)
                    if club_logo
                    else ""
                )
                + ("<span>%s</span>" % esc(club_code) if club_code else "")
                + "</span></a>"
            )
        slots.append(
            '<div class="ssa-dev1-inject club-home-sailor-slot" data-search="%s" data-sas-id="%s" data-href="%s">%s</div>'
            % (hay, esc(sas, quote=True), esc(href, quote=True), fallback)
        )
    css = (
        '<style id="club-home-sailor-dev1-style">'
        ".club-home-cards-stack{width:100%;max-width:52rem;margin:0 auto 1.5rem;box-sizing:border-box;padding-left:10px;padding-right:10px;}"
        ".club-home-cards-stack .card.stats-section,.club-home-sailor-slot,.club-home-sailor-slot .sa-approved-sailor-card{width:100%;max-width:100%;box-sizing:border-box;}"
        ".club-home-sailor-list{display:flex;flex-direction:column;gap:10px;width:100%;}"
        ".club-home-card-filter{min-height:44px;width:100%;max-width:100%;box-sizing:border-box;font-size:16px;padding:8px 12px;margin:0 0 0.75rem 0;}"
        ".club-dev1-fallback{display:grid;grid-template-columns:76px minmax(0,1fr) auto;gap:10px;align-items:center;min-height:76px;padding:8px 10px;border:3px solid #6c8ebd;border-radius:22px;text-decoration:none;color:#142b5f;background:#fff;box-sizing:border-box;}"
        ".club-dev1-fallback-av{width:76px;height:76px;border-radius:999px;object-fit:cover;background:#eef4fb;}"
        ".club-dev1-fallback-name{display:flex;flex-direction:column;min-width:0;overflow-wrap:anywhere;}"
        ".club-dev1-fallback-name b{font-size:1.05rem;}"
        ".club-dev1-fallback-club{display:inline-flex;flex-direction:column;align-items:center;gap:3px;}"
        ".club-dev1-fallback-club img{height:34px;width:auto;max-width:56px;object-fit:contain;}"
        ".club-home-sailor-slot .sa-approved-sailor-card{margin:0;}"
        "@media (max-width:768px){"
        ".club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}"
        ".club-home-sailor-slot .sa-approved-sailor-header{display:flex !important;flex-direction:column !important;align-items:stretch !important;gap:10px !important;}"
        ".club-home-sailor-slot .sa-claim-banner,.club-home-sailor-slot .sa-header-mid-slot{width:100% !important;max-width:100% !important;}"
        ".club-dev1-fallback{grid-template-columns:76px minmax(0,1fr);}"
        "}"
        "</style>"
    )
    js = (
        "<script>(function(){"
        "var list=document.getElementById('club-home-sailors-list');"
        "var inp=document.getElementById('club-sailors-home-filter');"
        "if(inp&&list){inp.addEventListener('input',function(){var q=(inp.value||'').toLowerCase();var n=0;"
        "list.querySelectorAll('.club-home-sailor-slot').forEach(function(c){"
        "var ok=((c.getAttribute('data-search')||'').indexOf(q)>=0);c.style.display=ok?'':'none';if(ok)n++;});"
        "var empty=document.getElementById('club-home-sailors-empty');if(empty)empty.style.display=n?'none':'block';});}"
        "if(!list)return;"
        "function mount(slot,html){"
        "var box=document.createElement('div');box.innerHTML=html;"
        "var lock=box.querySelector('#dev1-viewport-locks');"
        "if(lock){if(!document.getElementById('dev1-viewport-locks'))document.head.appendChild(lock);"
        "else if(lock.parentNode)lock.parentNode.removeChild(lock);}"
        "box.querySelectorAll('script').forEach(function(sc){if(sc.parentNode)sc.parentNode.removeChild(sc);});"
        "slot.innerHTML='';while(box.firstChild)slot.appendChild(box.firstChild);"
        "var href=slot.getAttribute('data-href')||'';"
        "var sid=slot.getAttribute('data-sas-id')||'';"
        "slot.querySelectorAll('a.sa-claim-banner').forEach(function(a){"
        "var u='/signup.html?signup=1';if(sid)u+='&sas_id='+encodeURIComponent(sid);"
        "a.setAttribute('href',u);});"
        "var card=slot.querySelector('.sa-approved-sailor-card');"
        "if(card&&href){card.style.cursor='pointer';card.addEventListener('click',function(ev){"
        "if(ev.target.closest('a'))return;location.href=href;});}"
        "}"
        "function load(slot){"
        "if(!slot||slot.getAttribute('data-card-loaded')==='1')return;"
        "slot.setAttribute('data-card-loaded','1');"
        "var sid=slot.getAttribute('data-sas-id')||'';"
        "if(!sid)return;"
        "fetch('/dev-1?embed=1&sas_id='+encodeURIComponent(sid),{credentials:'same-origin'})"
        ".then(function(r){if(!r.ok)throw new Error('x');return r.text();})"
        ".then(function(html){if(html&&html.charAt(0)!=='{')mount(slot,html);})"
        ".catch(function(){});"
        "}"
        "var slots=[].slice.call(list.querySelectorAll('.club-home-sailor-slot[data-sas-id]'));"
        "slots.slice(0,3).forEach(load);"
        "if(typeof IntersectionObserver==='function'){"
        "var io=new IntersectionObserver(function(entries){entries.forEach(function(en){"
        "if(!en.isIntersecting)return;io.unobserve(en.target);load(en.target);});}"
        ",{root:null,rootMargin:'500px 0px',threshold:0.01});"
        "slots.slice(3).forEach(function(s){io.observe(s);});"
        "}else{slots.slice(3).forEach(load);}"
        "})();</script>"
    )
    return (
        '<div class="club-home-cards-stack">'
        + css
        + '<div class="card stats-section club-sailors-section">'
        '<h2 class="section-title">Sailors (%d)</h2>'
        '<input type="search" id="club-sailors-home-filter" class="club-home-card-filter" placeholder="Search sailors name…" autocomplete="off">'
        '<div class="club-home-sailor-list" id="club-home-sailors-list">%s</div>'
        '<p id="club-home-sailors-empty" role="status" style="display:none">No sailors match your search.</p>'
        "</div></div>"
        % (n, "".join(slots))
        + js
    )


'''


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    start = api.find("def _club_sailors_table_section_html")
    if start < 0:
        raise SystemExit("MISSING:FN")
    nxt = api.find("\ndef ", start + 1)
    if nxt < 0:
        raise SystemExit("MISSING:NEXT")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.club_sailor_dev1." + ts)
    shutil.copy2(API, bak)
    api = api[:start] + NEW_FN + api[nxt + 1 :]
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
