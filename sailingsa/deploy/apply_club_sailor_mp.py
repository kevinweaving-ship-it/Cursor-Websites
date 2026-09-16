#!/usr/bin/env python3
"""Club sailors on MP: landing-style card — name/club/province on one row, claim full width below."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_SAILOR_MP_v1"

CSS_OLD = (
    '        ".club-home-sailor-slot .sa-approved-sailor-card{margin:0;}"\n'
    '        "@media (max-width:768px){"\n'
    '        ".club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}"\n'
    '        ".club-home-sailor-slot .sa-approved-sailor-header{display:flex !important;flex-direction:column !important;align-items:stretch !important;gap:10px !important;}"\n'
    '        ".club-home-sailor-slot .sa-claim-banner,.club-home-sailor-slot .sa-header-mid-slot{width:100% !important;max-width:100% !important;}"\n'
    '        ".club-dev1-fallback{grid-template-columns:76px minmax(0,1fr);}"\n'
    '        "}"\n'
)

CSS_NEW = (
    '        ".club-home-sailor-slot .sa-approved-sailor-card{margin:0;overflow:hidden;}"\n'
    '        ".club-home-sailor-slot main,.club-home-sailor-slot .main-column,.club-home-sailor-slot .container{"\n'
    '        "width:100%!important;max-width:100%!important;margin:0!important;padding:0!important;}"\n'
    '        "@media (max-width:768px){"\n'
    '        ".club-home-cards-stack{max-width:100%;padding-left:10px;padding-right:10px;}"\n'
    '        ".club-home-sailor-slot .sa-approved-sailor-header{display:grid!important;"\n'
    '        "grid-template-columns:76px minmax(0,1fr) 64px!important;"\n'
    '        "grid-template-areas:\\"av main prov\\" \\"claim claim claim\\"!important;"\n'
    '        "column-gap:8px!important;row-gap:8px!important;align-items:start!important;}"\n'
    '        ".club-home-sailor-slot .sa-approved-sailor-avatar-col{grid-area:av!important;}"\n'
    '        ".club-home-sailor-slot .sa-approved-sailor-mid{grid-area:main!important;display:flex!important;"\n'
    '        "flex-direction:column!important;align-items:flex-start!important;width:100%!important;min-width:0!important;}"\n'
    '        ".club-home-sailor-slot .sa-province-pin-wrap,.club-home-sailor-slot .sa-province-pin-col{grid-area:prov!important;}"\n'
    '        ".club-home-sailor-slot .sa-header-mid-slot{grid-area:claim!important;width:100%!important;max-width:100%!important;"\n'
    '        "height:auto!important;max-height:none!important;align-self:stretch!important;}"\n'
    '        ".club-home-sailor-slot .sa-claim-banner,.club-home-sailor-slot .sa-claim-banner--landing{"\n'
    '        "width:100%!important;max-width:100%!important;height:auto!important;transform:none!important;}"\n'
    '        ".club-dev1-fallback{grid-template-columns:76px minmax(0,1fr);}"\n'
    '        "}"\n'
)

MOUNT_OLD = (
    '        "function mount(slot,html){"\n'
    '        "var box=document.createElement(\'div\');box.innerHTML=html;"\n'
    '        "var lock=box.querySelector(\'#dev1-viewport-locks\');"\n'
    '        "if(lock){if(!document.getElementById(\'dev1-viewport-locks\'))document.head.appendChild(lock);"\n'
    '        "else if(lock.parentNode)lock.parentNode.removeChild(lock);}"\n'
    '        "box.querySelectorAll(\'script\').forEach(function(sc){if(sc.parentNode)sc.parentNode.removeChild(sc);});"\n'
    '        "slot.innerHTML=\'\';while(box.firstChild)slot.appendChild(box.firstChild);"\n'
    '        "var href=slot.getAttribute(\'data-href\')||\'\';"\n'
    '        "var sid=slot.getAttribute(\'data-sas-id\')||\'\';"\n'
    '        "slot.querySelectorAll(\'a.sa-claim-banner\').forEach(function(a){"\n'
    '        "var u=\'/signup.html?signup=1\';if(sid)u+=\'&sas_id=\'+encodeURIComponent(sid);"\n'
    '        "a.setAttribute(\'href\',u);});"\n'
    '        "var card=slot.querySelector(\'.sa-approved-sailor-card\');"\n'
    '        "if(card&&href){card.style.cursor=\'pointer\';card.addEventListener(\'click\',function(ev){"\n'
    '        "if(ev.target.closest(\'a\'))return;location.href=href;});}"\n'
    '        "}"\n'
)

MOUNT_NEW = (
    '        "function scopedDoc(root){return{getElementById:function(id){try{return root.querySelector(\'[id=\"\'+String(id).replace(/\"/g,\'\')+\'\"]\');}catch(e){return null;}},"\n'
    '        "querySelector:function(s){return root.querySelector(s);},querySelectorAll:function(s){return root.querySelectorAll(s);},"\n'
    '        "createElement:function(t){return document.createElement(t);},createTextNode:function(t){return document.createTextNode(t);},"\n'
    '        "addEventListener:function(t,fn,o){return document.addEventListener(t,fn,o);},removeEventListener:function(t,fn,o){return document.removeEventListener(t,fn,o);},"\n'
    '        "get body(){return document.body;},get documentElement(){return document.documentElement;},get head(){return document.head;}};}"\n'
    '        "function layoutMp(slot){"\n'
    '        "if(!slot||!window.matchMedia(\'(max-width:768px)\').matches)return;"\n'
    '        "var head=slot.querySelector(\'.sa-approved-sailor-header\');if(!head)return;"\n'
    '        "var mid=slot.querySelector(\'.sa-approved-sailor-mid\');"\n'
    '        "var claim=slot.querySelector(\'.sa-header-mid-slot\');"\n'
    '        "var av=slot.querySelector(\'.sa-approved-sailor-avatar-col\');"\n'
    '        "var prov=slot.querySelector(\'.sa-province-pin-wrap\')||slot.querySelector(\'.sa-province-pin-col\');"\n'
    '        "head.style.setProperty(\'display\',\'grid\',\'important\');"\n'
    '        "head.style.setProperty(\'grid-template-columns\',\'76px minmax(0,1fr) 64px\',\'important\');"\n'
    '        "head.style.setProperty(\'grid-template-areas\',\'\\\"av main prov\\\" \\\"claim claim claim\\\"\',\'important\');"\n'
    '        "head.style.setProperty(\'row-gap\',\'8px\',\'important\');"\n'
    '        "if(av)av.style.setProperty(\'grid-area\',\'av\',\'important\');"\n'
    '        "if(mid)mid.style.setProperty(\'grid-area\',\'main\',\'important\');"\n'
    '        "if(prov)prov.style.setProperty(\'grid-area\',\'prov\',\'important\');"\n'
    '        "if(claim){if(claim.parentElement!==head)head.appendChild(claim);"\n'
    '        "claim.style.setProperty(\'grid-area\',\'claim\',\'important\');"\n'
    '        "claim.style.setProperty(\'width\',\'100%\',\'important\');"\n'
    '        "claim.style.setProperty(\'height\',\'auto\',\'important\');"\n'
    '        "claim.style.setProperty(\'max-height\',\'none\',\'important\');}"\n'
    '        "var ban=slot.querySelector(\'.sa-claim-banner\');"\n'
    '        "if(ban){ban.style.setProperty(\'width\',\'100%\',\'important\');ban.style.setProperty(\'height\',\'auto\',\'important\');ban.style.transform=\'none\';}"\n'
    '        "}"\n'
    '        "function mount(slot,html){"\n'
    '        "var box=document.createElement(\'div\');box.innerHTML=html;"\n'
    '        "var lock=box.querySelector(\'#dev1-viewport-locks\');"\n'
    '        "if(lock){if(!document.getElementById(\'dev1-viewport-locks\'))document.head.appendChild(lock);"\n'
    '        "else if(lock.parentNode)lock.parentNode.removeChild(lock);}"\n'
    '        "var codes=[];box.querySelectorAll(\'script\').forEach(function(sc){if(!sc.src)codes.push(sc.textContent||\'\');if(sc.parentNode)sc.parentNode.removeChild(sc);});"\n'
    '        "slot.innerHTML=\'\';while(box.firstChild)slot.appendChild(box.firstChild);"\n'
    '        "var scoped=scopedDoc(slot);codes.forEach(function(code){if(!code||!String(code).trim())return;try{(new Function(\'document\',\'window\',code))(scoped,window);}catch(e){}});"\n'
    '        "layoutMp(slot);"\n'
    '        "var href=slot.getAttribute(\'data-href\')||\'\';"\n'
    '        "var sid=slot.getAttribute(\'data-sas-id\')||\'\';"\n'
    '        "slot.querySelectorAll(\'a.sa-claim-banner\').forEach(function(a){"\n'
    '        "var u=\'/signup.html?signup=1\';if(sid)u+=\'&sas_id=\'+encodeURIComponent(sid);"\n'
    '        "a.setAttribute(\'href\',u);});"\n'
    '        "var card=slot.querySelector(\'.sa-approved-sailor-card\');"\n'
    '        "if(card&&href){card.style.cursor=\'pointer\';card.addEventListener(\'click\',function(ev){"\n'
    '        "if(ev.target.closest(\'a\'))return;location.href=href;});}"\n'
    '        "}"\n'
)


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    missing = []
    if CSS_OLD not in api:
        missing.append("CSS")
    if MOUNT_OLD not in api:
        missing.append("MOUNT")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.club_sailor_mp." + ts)
    shutil.copy2(API, bak)
    api = api.replace(CSS_OLD, CSS_NEW.replace("CLUB_SAILOR_MP", MARK), 1)
    # stamp mark into css comment via a unique token in CSS_NEW
    if MARK not in CSS_NEW:
        api = api.replace(
            '".club-home-sailor-slot .sa-approved-sailor-card{margin:0;overflow:hidden;}"',
            '".club-home-sailor-slot .sa-approved-sailor-card{margin:0;overflow:hidden;}"/* ' + MARK + " */",
            1,
        )
    api = api.replace(MOUNT_OLD, MOUNT_NEW, 1)
    if MARK not in api:
        api = api.replace("function layoutMp(slot){", "function layoutMp(slot){/* " + MARK + " */", 1)
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
