#!/usr/bin/env python3
import sys, re, os, hashlib, subprocess

GOLD = "/var/www/sailingsa/header/index.html"
LND  = "/var/www/sailingsa/bak_INDEX_PRE_GOLD_UNIV_20260808_143304.html"
OUT  = "/var/www/sailingsa/index.html.new"
LIVE = "/var/www/sailingsa/index.html"

def sha(p):
    return hashlib.sha256(open(p,"rb").read()).hexdigest()

with open(GOLD) as f: gold = f.read()
with open(LND)  as f: lnd  = f.read()

print("GOLD SHA256 :", sha(GOLD), os.path.getsize(GOLD), "bytes")
print("BACKUP SHA256:", sha(LND),  os.path.getsize(LND),  "bytes")
print("LIVE SHA256  :", sha(LIVE), os.path.getsize(LIVE), "bytes")

JS_FUNCTIONAL_TOKENS = [
    'function(){', 'function (){', '(function(', '()=>',
    'addEventListener', 'createElement', 'appendChild', 'removeChild', 'insertBefore',
    'MutationObserver', 'setInterval', 'setTimeout', 'clearInterval', 'clearTimeout',
    'OVERLAY_MAX_Z', 'HDR_MAX_Z', 'PROTECTED_TOP', 'scheduleDemoteOverlaps',
    'updateHeaderAuthStatus',
    'innerText', 'innerHTML', 'textContent', 'className', 'classList',
    'style.setProperty', 'style.', 'getElementById', 'querySelector', 'querySelectorAll',
    'getAttribute', 'setAttribute', 'dataset.',
    'Promise.', '.then(', '.catch(', 'async ', 'await ',
    'window.__GOLD_HEADER', 'fireLogout', 'fireSignIn', 'fireSignUp', 'safeFire',
    'Object.keys', 'Object.assign', 'applyLogoCfg',
    'pageshow', 'DOMContentLoaded', 'bfcache',
    'loginBox', 'loggedInStatus', 'headerAuth', 'headerUserCenter', 'headerLogoLink',
    'signUpBtn', 'signInBtn', 'logoutBtn',
    'appendChild(signUpBtn)', 'appendChild(signInBtn)',
    'dispatchEvent', 'new Event', 'CustomEvent',
    'if(', 'for(', 'while(', 'return ', 'throw ', 'try{', '}catch',
    'const ', 'let ', 'var '
]

def extract_between_markers(text, name):
    s = f"@@GOLD_HEADER_{name}_START@@"
    e = f"@@GOLD_HEADER_{name}_END@@"
    si = text.rfind(s)
    ei = text.rfind(e)
    assert si > 0 and ei > si, f"marker pair missing for {name}: s={si} e={ei}"
    line_start = text.rfind("\n", 0, si)
    if line_start == -1: line_start = 0
    else: line_start += 1
    line_end = text.find("\n", ei)
    if line_end == -1: line_end = len(text)
    chunk = text[line_start:line_end]
    print(f"  PKG {name} RAW: {len(chunk.splitlines())} lines, {len(chunk)} chars")
    return chunk

def count_iifes(label, txt):
    noch = re.sub(r'<!--.*?-->','',txt,re.DOTALL)
    noch = re.sub(r'/\*.*?\*/','',noch,re.DOTALL)
    # skip single-line comments
    noch = re.sub(r'(?m)^\s*//.*$','',noch)
    iifes = re.findall(r'\(function\s*\(\s*\)\s*\{', noch)
    print(f"    [{label}] IIFE count = {len(iifes)}")
    return len(iifes)

PKG_STAGE = {}

def _strip_html_tags(s):
    tags = ['style','/style','head','/head','body','/body','html','/html','meta','link','title','script','/script','main','/main','noscript','/noscript']
    pat = re.compile(r'<\s*(?:' + '|'.join(re.escape(t) for t in tags) + r')(?:\s[^>]*)?\s*>', re.IGNORECASE)
    return pat.sub('', s)

def _strip_all_comments(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
    return s

def _strip_packaging_lines(s):
    out = []
    for raw in s.splitlines():
        t = raw.rstrip()
        stripped = t.strip()
        if not stripped:
            out.append(raw.rstrip())
            continue
        # =============================================================
        # KILL LIST FIRST: run most-obvious packaging kills BEFORE
        # any "functional token exemption" checks, because packaging
        # doc lines sometimes CONTAIN substrings like "window.__GOLD_HEADER"
        # that trigger exemption falsely (doc refs, not actual code).
        # =============================================================
        if '@@GOLD_HEADER_' in stripped:
            continue
        if 'PACKAGE SECTION' in stripped.upper():
            continue
        if stripped.startswith('Marker:') or stripped.startswith('Marker :'):
            continue
        # pure separator / comment shell
        pure_sym = re.sub(r'[\s<>\-*/=|#+]','', stripped)
        if pure_sym == '':
            continue
        # slot-index doc lines: [1] [2] [3] anything after
        if re.match(r'^\s*\[\s*\d+\s*\]\s*', stripped):
            continue
        # slot id doc lines: "#<id> ... -> cfg.xxx" / "#<id> ... -> filled by ..." (anywhere in line, even with bullet)
        if re.search(r'#[a-zA-Z][a-zA-Z0-9_-]*\s+[^#\n]*?(?:->|—|–|:)\s*(?:cfg\.|filled by)', stripped):
            continue
        # slot id doc (start of line, hash id + arrow/colon)
        if re.match(r'^\s*#[a-zA-Z][a-zA-Z0-9_-]*\s*(?:->|—|–|:)', stripped):
            continue
        # dual slot doc: "loggedInStatus / #loginBox ->"
        if re.search(r'#(?:loggedInStatus|loginBox|headerAuth|headerUserCenter|headerLogoLink).*?(/\s*#|->|—|–|:)', stripped):
            continue
        if stripped.startswith('Slot ') and ('(' in stripped or '->' in stripped):
            continue
        # COPY VERBATIM header layout lines
        low_stripped = stripped.lower()
        if re.match(r'^\s*\(\s*copy\s+verbatim\s*:', low_stripped):
            continue
        if 'copy verbatim' in low_stripped and ('grid slots' in low_stripped or '80px sticky' in low_stripped or 'navy band' in low_stripped):
            continue
        if '80px sticky navy band' in stripped:
            continue
        # override/slot-edit-advice lines (case insensitive substring)
        if ('override slots' in low_stripped) or ('no edit needed' in stripped) or ('use window.__GOLD_HEADER_CFG' in stripped) or ('use window.__GOLD_HEADER_CFG instead' in stripped):
            continue
        # packaging labels (=== BLAH / --- BLAH / EXTRACTION / PACKAGE / WRAP / BOUNDARY)
        if re.match(r'^=+\s*[A-Z]', stripped) or re.match(r'^-{3,}\s*[A-Z]', stripped):
            continue
        _su = stripped.upper()
        if _su.startswith('EXTRACTION') or _su.startswith('WRAP') or _su.startswith('BOUNDARY') or _su.startswith('PACKAGING'):
            continue
        # partial comment shells (unpaired)
        if stripped in ('<!--', '-->', '/*', '*/'):
            continue
        if (stripped.startswith('/*') or stripped.endswith('*/')) and len(pure_sym) < 8:
            continue
        # start-of-line doc partial comment shells (no functional calls inside)
        if stripped.startswith('<!--') or stripped.endswith('-->'):
            if not any(c in stripped for c in JS_FUNCTIONAL_TOKENS) and not re.search(r'[a-zA-Z_]\([^)]*\)', stripped):
                continue
        # asterisk / dash bullet pure doc lines: no JS function call syntax inside
        if (re.match(r'^\s*\*\s+', stripped) or re.match(r'^\s*-\s+', stripped)):
            # only kill if it's a pure doc bullet; keep if it has real code
            if ('function' not in stripped) and ('()' not in stripped) and (not re.search(r'[a-zA-Z_]\s*\(\s*\)', stripped)):
                continue

        # =============================================================
        # SURVIVED KILL LIST → now exemptions: keep if it's REAL code / markup
        # =============================================================
        # NEVER STRIP lines containing functional JS/CSS/HTML tokens
        low = stripped
        if any(tok in low for tok in JS_FUNCTIONAL_TOKENS):
            out.append(raw.rstrip())
            continue
        # also protect CSS selectors/rules
        if ('{' in stripped and '}' in stripped) or stripped.endswith('{') or stripped.startswith('}'):
            out.append(raw.rstrip())
            continue
        if stripped.startswith('.') or stripped.startswith('#') or stripped.startswith('@') or stripped.startswith('body') or stripped.startswith('header') or stripped.startswith('html') or stripped.startswith('main'):
            if ':' in stripped or '{' in stripped:
                out.append(raw.rstrip())
                continue
        # PROTECT HTML ELEMENT TAGS (actual tags, not doc lines)
        tag_match = re.match(r'^\s*</?[a-zA-Z][a-zA-Z0-9-]*(?:\s[^>]*)?>\s*$', stripped)
        if tag_match:
            out.append(raw.rstrip())
            continue
        if '<a ' in stripped or '</a>' in stripped or '<img ' in stripped or '<div' in stripped or '</div>' in stripped or '<header' in stripped or '</header>' in stripped or '<nav' in stripped or '</nav>' in stripped:
            out.append(raw.rstrip())
            continue
        out.append(raw.rstrip())
    return "\n".join(out)

def _strip_script_tags(s):
    s = re.sub(r'<\s*script(?:\s[^>]*)?\s*>', '', s, flags=re.IGNORECASE)
    s = re.sub(r'<\s*/\s*script\s*>', '', s, flags=re.IGNORECASE)
    return s

def clean_package(raw, pkg_name, strip_style_wrap=False):
    print(f"\n=== CLEANING PKG {pkg_name} ===")
    count_iifes(f"{pkg_name} pre-strip raw", raw)
    c = raw
    c = _strip_html_tags(c)
    count_iifes(f"{pkg_name} after strip_html_tags", c)
    c = _strip_all_comments(c)
    count_iifes(f"{pkg_name} after strip_all_comments", c)
    c = _strip_packaging_lines(c)
    count_iifes(f"{pkg_name} after strip_packaging_lines", c)
    if pkg_name == 'SCRIPTS':
        c = _strip_script_tags(c)
    # collapse >2 blank lines to max 2
    c = re.sub(r'\n{3,}', '\n\n', c)
    c = c.strip()
    count_iifes(f"{pkg_name} FINAL cleaned", c)
    PKG_STAGE[pkg_name] = len(c.splitlines())
    return c

# ===== EXTRACT 3 PACKAGES from GOLD =====
print("\n=== EXTRACT PACKAGES FROM GOLD ===")
raw_styles  = extract_between_markers(gold, 'STYLES')
raw_html    = extract_between_markers(gold, 'HTML')
raw_scripts = extract_between_markers(gold, 'SCRIPTS')

PKG1_STYLES  = clean_package(raw_styles,  'STYLES')
PKG2_HTML    = clean_package(raw_html,    'HTML')
PKG3_SCRIPTS = clean_package(raw_scripts, 'SCRIPTS')

# =============================================================================
# POST-CLEAN NUCLEAR DOC-LINE PURGE PASS (run AFTER clean_package 7-stage)
# Catches ANYTHING that slipped through (unpaired partial comment blocks etc.)
# =============================================================================
_AGGRO_DOC_KILL_SUBSTRINGS = [
    'PACKAGE SECTION 1 of 3', 'PACKAGE SECTION 2 of 3', 'PACKAGE SECTION 3 of 3',
    'GOLD_HEADER_STYLES START', 'GOLD_HEADER_STYLES END',
    'GOLD_HEADER_HTML START',   'GOLD_HEADER_HTML END',
    'GOLD_HEADER_SCRIPTS START','GOLD_HEADER_SCRIPTS END',
    'Marker: @@GOLD_HEADER', 'Marker : @@GOLD_HEADER',
    '@@GOLD_HEADER_STYLES', '@@GOLD_HEADER_HTML', '@@GOLD_HEADER_SCRIPTS',
    'COPY verbatim: 80px sticky navy band',
    'copy verbatim: 80px sticky navy band',
    '(COPY verbatim:', '(copy verbatim:',
    '80px sticky navy band with 3 grid slots',
    'Override slots (no edit needed',
    'override slots (no edit needed',
    'no edit needed, use window.__GOLD_HEADER_CFG',
    'use window.__GOLD_HEADER_CFG instead',
    '#headerLogoLink href/title   -> cfg.logoHref',
    '#headerLogoLink href/title  -> cfg.logoHref',
    '#headerLogoLink href/title -> cfg.logoHref',
    '#headerLogoLink href/title',
    '-> cfg.logoHref / cfg.logoTitle',
    '-> cfg.logoHref',
    '#headerUserCenter            -> filled by updateHeaderAuthStatus()',
    '#headerUserCenter -> filled by updateHeaderAuthStatus()',
    '#loggedInStatus / #loginBox  -> filled by updateHeaderAuthStatus() + buttons',
    '#loggedInStatus / #loginBox -> filled by updateHeaderAuthStatus() + buttons',
    '#loggedInStatus / #loginBox  -> filled by updateHeaderAuthStatus()',
    '#loggedInStatus / #loginBox -> filled by updateHeaderAuthStatus()',
    '/ #loginBox  ->', '/ #loginBox ->',
    '-> filled by updateHeaderAuthStatus()',
    '[1] logo left, [2] user center',
    '[1] logo left',
    '[2] user center (centered name/SAS), [3] auth right',
    '[2] user center',
    '[3] auth right',
    '============================================================ -->',
    '============================================================  -->',
    '==== MARKER-LINE', '=== PACKAGE',
    'GOLD_HEADER_STYLES START', 'GOLD_HEADER_STYLES END',
    'GOLD_HEADER_HTML START',   'GOLD_HEADER_HTML END',
    'GOLD_HEADER_SCRIPTS START','GOLD_HEADER_SCRIPTS END',
]
def _nuke_doc_lines(chunk, pkg_label):
    lines = chunk.splitlines()
    before = len(lines)
    kept = []
    for raw in lines:
        s = raw.strip()
        if not s:
            kept.append(raw)
            continue
        low = s.lower()
        kill = False
        for ks in _AGGRO_DOC_KILL_SUBSTRINGS:
            if ks.lower() in low:
                kill = True
                break
        if kill:
            # NEVER kill if line contains any CSS selector/rule/props syntax or real HTML/JS
            is_css_like = (
                ((':' in s or '{' in s or ';' in s) and ('.' in s or '#' in s or s[0].isalpha()))
                or s.endswith('{') or s.startswith('}') or '!important' in s
            )
            is_html_like = bool(re.search(r'</?[a-zA-Z][a-zA-Z0-9-]*', s))
            is_js_like = any(tok in s for tok in JS_FUNCTIONAL_TOKENS) or bool(re.search(r'[a-zA-Z_]\s*\(', s))
            if is_css_like or is_html_like or is_js_like:
                kept.append(raw)
                continue
            print(f"    [{pkg_label}] NUKED SLIP-THROUGH DOC LINE: {s!r}")
            continue
        kept.append(raw)
    after = len(kept)
    if before != after:
        print(f"    [{pkg_label}] post-nuke: removed {before-after} slip-through doc lines")
    return "\n".join(kept)

PKG1_STYLES  = _nuke_doc_lines(PKG1_STYLES,  'STYLES')
PKG2_HTML    = _nuke_doc_lines(PKG2_HTML,    'HTML')
PKG3_SCRIPTS = _nuke_doc_lines(PKG3_SCRIPTS, 'SCRIPTS')

# =============================================================================
# GOLD FORCED LOGOUT + AUTH BUTTON CENTERING (ensures slots align when
# landing legacy CSS overrides the gold grid rules). Appended to cleaned
# PKG1_CSS at end so always last wins.
#
# CRITICAL: NEVER force display:inline-flex !important on #loginBox or
# #loggedInStatus — updateHeaderAuthStatus() uses inline style.display=
# "none"/"flex" to control auth state, and a forced display would override
# it (causing BOTH SU/Login + Logout pills to show stacked).
# =============================================================================
GOLD_FORCED_CENTER_CSS = """
header.site-header > .container,
header.site-header .container {
    align-items: center !important;
    justify-items: stretch !important;
}
header.site-header #headerLogoLink,
header.site-header #headerUserCenter,
header.site-header #headerAuth {
    display:         inline-flex !important;
    align-items:     center !important;
    justify-content: center !important;
    align-self:      center !important;
    margin:          0 !important;
    padding:         0 !important;
    height:          100% !important;
    min-height:      80px !important;
}
header.site-header #loggedInStatus,
header.site-header #loginBox {
    align-items:     center !important;
    justify-content: center !important;
    align-self:      center !important;
    margin:          0 !important;
    padding:         0 !important;
    height:          100% !important;
    min-height:      80px !important;
    /* display: NEVER force — controlled by updateHeaderAuthStatus() inline style */
}
header.site-header #headerUserCenter > * {
    text-align: center !important;
}
header.site-header button,
header.site-header .btn-logout,
header.site-header [id*="Btn"],
header.site-header #goldHeaderSignUpBtn,
header.site-header #goldHeaderSignInBtn {
    display:          inline-flex !important;
    align-items:      center !important;
    justify-content:  center !important;
    align-self:       center !important;
    vertical-align:   middle !important;
    margin:           0 !important;
    padding-top:      0 !important;
    padding-bottom:   0 !important;
    line-height:      1 !important;
}
header.site-header #loggedInStatus button,
header.site-header #headerAuth button {
    transform: translateY(0) !important;
    top: auto !important;
    bottom: auto !important;
}
"""
PKG1_STYLES = (PKG1_STYLES + "\n" + GOLD_FORCED_CENTER_CSS).strip()

PKG1_STYLES = PKG1_STYLES.strip()
PKG2_HTML   = PKG2_HTML.strip()
PKG3_SCRIPTS= PKG3_SCRIPTS.strip()

# ===== FIND LANDING WHITELIST REPLACE RANGES =====
# R1: from start of .site-header { style block up to LAST </style> before </head>
r1_start = lnd.find('.site-header {')
# fallback: find first site-header rule if the above misses
if r1_start == -1:
    r1_start = lnd.find('.site-header')
    # walk back to start of line or beginning of style block
    nl = lnd.rfind('\n', 0, r1_start)
    r1_start = nl+1 if nl!=-1 else 0
print(f"\nR1 start: pos {r1_start}, snippet: ...{repr(lnd[r1_start:r1_start+40])}...")
# find last </style> BEFORE </head>
head_end = lnd.find('</head>')
assert head_end > 0, "no </head> in landing"
r1_end = lnd.rfind('</style>', 0, head_end)
assert r1_end > r1_start, "no </style> before </head>"
print(f"R1 end: pos {r1_end}, snippet: ...{repr(lnd[r1_end:r1_end+20])}...")

# R2: from line after <body> to line BEFORE <main class="main-content">
body_tag = lnd.find('<body')
assert body_tag > 0, "no <body"
r2_start = lnd.find('\n', body_tag)
assert r2_start > body_tag
r2_start += 1
main_line = lnd.find('<main class="main-content">')
assert main_line > r2_start, "no main-content"
r2_end = lnd.rfind('\n', 0, main_line)
assert r2_end > r2_start, "cannot find newline before main"
print(f"R2 start: pos {r2_start}, end: pos {r2_end} (main at {main_line})")

# R3: INSERT between end of landing inline scripts/news BEFORE <script src="/js/config.js">
r3_anchor = '<script src="/js/config.js">'
r3_insert_point = lnd.find(r3_anchor)
assert r3_insert_point > r2_end, "no /js/config.js lib anchor"
print(f"R3 insert point: pos {r3_insert_point}, snippet: {repr(lnd[r3_insert_point:r3_insert_point+60])}")

# ===== LANDING SPECIFIC REWIRING CFG =====
LANDING_CFG = r"""    <script>
    window.__GOLD_HEADER_CFG = {
      onLogout: async function(){ if(typeof handleLogout==="function"){try{await handleLogout();}catch(_hl){} } try{window.location.reload();}catch(_){} },
      onSignIn:  function(){ try{ return sailingHandleHeaderSignIn.apply(this, arguments); }catch(_){} },
      onSignUp:  function(){ try{ return sailingHandleHeaderSignUp.apply(this, arguments); }catch(_){} },
      logoHref:  "/",
      logoTitle: "Home – clear search and return to sailingsa.co.za"
    };
    </script>
"""

# =============================================================================
# FORCE GOLD BUTTONS (only when NOT logged in). Last-write-wins over
# session.js sailingRenderLoggedOutAuthButtons which overwrites gold buttons
# with legacy GRAY pair on landing. GUARANTEE no stacked 3-button state when
# user IS logged in by checking loggedInStatus.style.display !== 'none'
# before touching loginBox/loggedInStatus.
# =============================================================================
FORCE_GOLD_BUTTONS_GUARD = r"""    <script>
    (function(){
      function _gc2(){ try{return window.__GOLD_HEADER_CFG||{};}catch(_){return {};} }
      function _fireSu(e){try{var x=_gc2();if(typeof x.onSignUp==="function"){x.onSignUp(e);return;}if(typeof sailingHandleHeaderSignUp==="function"){sailingHandleHeaderSignUp(e);}}catch(_){}}
      function _fireSi(e){try{var x=_gc2();if(typeof x.onSignIn==="function"){x.onSignIn(e);return;}if(typeof sailingHandleHeaderSignIn==="function"){sailingHandleHeaderSignIn(e);}}catch(_){}}
      function forceGoldLoggedOutButtons(){
        try{
          var lid = document.getElementById('loggedInStatus');
          // DO NOT TOUCH loginBox when user IS logged in (prevents stacking 3 buttons).
          if (lid && lid.style && lid.style.display !== 'none' && window.getComputedStyle(lid).display !== 'none') {
            // Logged in: ensure SU/Login loginBox hidden (matches updateHeaderAuthStatus).
            try{ var lb=document.getElementById('loginBox'); if(lb){lb.style.display='none';} }catch(_z){}
            return;
          }
          var lb = document.getElementById('loginBox');
          if(!lb) return;
          var SU_ICON='/icons/assets/iconoir/regular/edit.svg';
          var SU_TEXT='Sign Up'; var SU_BG='#eab308'; var SU_FG='#000000'; var SU_BORDER='#eab308';
          var SI_ICON='/icons/assets/iconoir/regular/user-circle-gear-bold.svg';
          var SI_TEXT='Login';  var SI_BG='#ffffff';  var SI_FG='#001f3f'; var SI_BORDER='#f1f5f9';
          var BTN='display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:0 16px;height:32px;min-width:96px;border-radius:9999px;font-size:14px;font-weight:600;cursor:pointer;box-sizing:border-box;white-space:nowrap;line-height:1;';
          var IMG='width:16px;height:16px;display:inline-block;vertical-align:middle;';
          lb.innerHTML='';
          var su=document.createElement('button'); su.setAttribute('type','button'); su.id='goldHeaderSignUpBtn';
          su.style.cssText=BTN+'border:1px solid '+SU_BORDER+';background:'+SU_BG+';color:'+SU_FG+';';
          var sui=document.createElement('img'); sui.src=SU_ICON; sui.alt=SU_TEXT; sui.setAttribute('aria-hidden','true'); sui.style.cssText=IMG;
          su.appendChild(sui); su.appendChild(document.createTextNode('\u00A0'+SU_TEXT));
          su.addEventListener('click',function(e){if(e&&e.preventDefault)e.preventDefault();_fireSu(e);},false);
          var si=document.createElement('button'); si.setAttribute('type','button'); si.id='goldHeaderSignInBtn';
          si.style.cssText=BTN+'border:1px solid '+SI_BORDER+';background:'+SI_BG+';color:'+SI_FG+';';
          var sii=document.createElement('img'); sii.src=SI_ICON; sii.alt=SI_TEXT; sii.setAttribute('aria-hidden','true'); sii.style.cssText=IMG;
          si.appendChild(sii); si.appendChild(document.createTextNode('\u00A0'+SI_TEXT));
          si.addEventListener('click',function(e){if(e&&e.preventDefault)e.preventDefault();_fireSi(e);},false);
          // DOM ORDER MATCH GOLD: Sign Up YELLOW LEFT (first child) -> Login WHITE RIGHT (second child)
          lb.appendChild(su); lb.appendChild(si);
          lb.style.alignItems='center'; lb.style.justifyContent='flex-end'; lb.style.gap='12px';
          // Only set display:flex if NOT already hidden (prevents accidentally showing
          // loginBox alongside visible Logout pill if auth check just ran).
          var lbComp = window.getComputedStyle(lb);
          if (lbComp.display !== 'none' && lb.style.display !== 'none') {
            lb.style.display='inline-flex';
          }
        }catch(e){}
      }
      function _runAll(){
        try{if(typeof updateHeaderAuthStatus==="function"){updateHeaderAuthStatus();}}catch(_){}
        forceGoldLoggedOutButtons();
      }
      if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",_runAll,{once:true});}else{setTimeout(_runAll,0);}
      setTimeout(_runAll, 100); setTimeout(_runAll, 300); setTimeout(_runAll, 800); setTimeout(_runAll, 2000);
      try{if(typeof window.addEventListener==="function"){window.addEventListener("pageshow",function(pse){try{if(pse&&pse.persisted){setTimeout(_runAll,0);setTimeout(_runAll,80);setTimeout(_runAll,700);}}catch(_){}},false);}}catch(_){}
      try{if(typeof window.__GOLD_HEADER_CALL!=="undefined"&&window.__GOLD_HEADER_CALL){window.__GOLD_HEADER_CALL.__forceGoldButtons=forceGoldLoggedOutButtons;}}catch(_){}
    })();
    </script>
"""

# ===== ASSEMBLE =====
print("\n=== ASSEMBLE NEW LANDING ===")
result = (
    lnd[0:r1_start]
    + PKG1_STYLES + "\n</style>\n"
    + lnd[r1_end:r2_start]
    + PKG2_HTML + "\n"
    + lnd[r2_end:r3_insert_point]
    + LANDING_CFG
    + "\n    <script>\n" + PKG3_SCRIPTS.strip() + "\n    </script>\n"
    + FORCE_GOLD_BUTTONS_GUARD
    + lnd[r3_insert_point:]
)

# ===== VALIDATION =====
print("\n=== POST-ASSEMBLY VALIDATION ===")
# 1. ZERO dead markers
for m in ['@@GOLD_HEADER_STYLES_START@@','@@GOLD_HEADER_STYLES_END@@',
          '@@GOLD_HEADER_HTML_START@@','@@GOLD_HEADER_HTML_END@@',
          '@@GOLD_HEADER_SCRIPTS_START@@','@@GOLD_HEADER_SCRIPTS_END@@',
          '@@GOLD_HEADER']:
    c = result.count(m)
    print(f"  marker '{m}' count = {c}")
    assert c == 0, f"dead marker remains: {m}={c}"
# 2. Banned dead code strings
for banned in ['renderLoggedIn', 'logout-pill-auto-login-popup-v1', 'padding-top: 80px', 'padding-top:80px']:
    c = result.count(banned)
    print(f"  BANNED '{banned}' count = {c}")
    assert c == 0, f"banned dead code: {banned}={c}"
# 2b. LEAKED DOC LINES MUST BE ZERO — only in the gap between </header> and <main (where they render as visible page text)
#     AND also inside each cleaned PACKAGE chunk itself (never allow packaging doc in cleaned chunks)
PROBLEMATIC_DOC_STRINGS = [
    'COPY verbatim', 'copy verbatim', '80px sticky navy band',
    'Override slots', 'override slots', 'no edit needed, use window.__GOLD_HEADER_CFG',
    '#headerLogoLink href/title', '-> cfg.logoHref', '-> cfg.logoTitle',
    '-> filled by updateHeaderAuthStatus()', '/ #loginBox  ->',
    '[1] logo left', '[2] user center', '[3] auth right',
    'Override slots (no edit needed', 'no edit needed', 'use window.__GOLD_HEADER_CFG instead',
    '  * #headerLogoLink', '  * #headerUserCenter', '  * #loggedInStatus / #loginBox',
    '============================================================ -->',
    'PACKAGE SECTION'
]
# Never inside cleaned package chunks
for pkg_name, pkg_chunk in [('PKG1_STYLES', PKG1_STYLES), ('PKG2_HTML', PKG2_HTML), ('PKG3_SCRIPTS', PKG3_SCRIPTS)]:
    for ds in PROBLEMATIC_DOC_STRINGS:
        c = pkg_chunk.count(ds)
        if c != 0:
            print(f"  DOC-LEAK inside cleaned {pkg_name}: '{ds}' count = {c}  KILL!")
            assert c == 0, f"cleaned {pkg_name} still has packaging doc: '{ds}'={c}"
print("  [OK] Cleaned PKG1/PKG2/PKG3 have ZERO packaging doc strings (1/2)")
# Never in header→main gap (<- this is the render leak zone on screenshot)
header_close = result.find('</header>')
main_tag     = result.find('<main class="main-content">')
assert header_close > 0 and main_tag > header_close, f"header/main order wrong hc={header_close} main={main_tag}"
gap = result[header_close : main_tag]
for ds in PROBLEMATIC_DOC_STRINGS:
    c = gap.count(ds)
    if c != 0:
        # show 120 chars around
        pi = gap.find(ds)
        snippet = gap[max(0, pi-60):pi+len(ds)+60]
        print(f"  DOC-LEAK in HEADER→MAIN gap (renderable zone!): '{ds}' @ gap-idx {pi}  around >>>{snippet!r}<<<")
        assert c == 0, f"DOC LEAK between </header> and <main: '{ds}'={c}"
print("  [OK] HEADER→MAIN render gap has ZERO packaging doc strings (2/2)")
# benign check: any other doc-string occurrences elsewhere are landing legacy comments (not rendered, OK)
# 3. Lib onwards IDENTITY (config.js through </body></html> = untouched)
lib_in_result = result.find(r3_anchor)
print(f"  lib anchor in new result at pos {lib_in_result}")
orig_tail = lnd[r3_insert_point:]
new_tail  = result[lib_in_result:]
tail_ok = orig_tail == new_tail
print(f"  LIB-ONWARDS IDENTITY (backup tail == result tail): {tail_ok}  ({len(orig_tail)} bytes)")
assert tail_ok, "TOUCHED BELOW HEADER: lib onwards tail mismatch"
# 4. IIFE count in result script section
iife_in_result = count_iifes("ASSEMBLED RESULT total", result)
print(f"  Total IIFE count in result (should be 8+ from PKG3 + landing inline prior) = {iife_in_result}")
# 5. PKG3 embedded IIFE count inside result (between landing cfg end and config.js start)
cfg_end = result.find(LANDING_CFG) + len(LANDING_CFG)
pkg3_block = result[cfg_end : lib_in_result]
pkg3_iifes = count_iifes("ASSEMBLED PKG3+GUARD embedded", pkg3_block)
print(f"  PKG3 + FORCE_GUARD embedded IIFE count = {pkg3_iifes} (EXPECT = 4: 3 gold PKG3 IIFEs + 1 button guard IIFE)")
assert pkg3_iifes >= 4, f"TOO FEW IIFEs in PKG3+GUARD block: {pkg3_iifes} (need >= 4)"
# 6. HTML comment balance (after stripping)
def tag_balance_check(html, name):
    stripped = re.sub(r'<!--.*?-->','',html,re.DOTALL)
    for tag in ['style','script','div','header','nav','main']:
        o = len(re.findall(rf'<{tag}(?:\s[^>]*)?>', stripped, re.IGNORECASE))
        c = len(re.findall(rf'</{tag}\s*>', stripped, re.IGNORECASE))
        print(f"    {name} <{tag}> open={o} close={c} delta={o-c}")
tag_balance_check(result, "RESULT")
# 7. size
print(f"\n  ASSEMBLED RESULT SIZE: {len(result)} bytes ({len(result.splitlines())} lines)")

# ===== WRITE + CHOWN + CHMOD =====
print(f"\n=== WRITING {OUT} ===")
with open(OUT, "w") as f:
    f.write(result)
os.chmod(OUT, 0o644)
try:
    os.chown(OUT, 33, 33)
    print("  chown 33:33 OK")
except Exception as e:
    try:
        subprocess.run(['chown','www-data:www-data', OUT], check=True)
        print("  chown www-data OK")
    except Exception as e2:
        print(f"  chown skipped (run later as root): {e} / {e2}")

new_sha = sha(OUT)
print(f"  OUT SHA256  : {new_sha}")
print(f"  LIVE SHA256 : {sha(LIVE)}")

# ================================================================
# ATOMIC SWAP — AUTO APPLY when (and ONLY when) ALL assertions passed
# ================================================================
print(f"\n=== AUTOMATIC ATOMIC SWAP (all validations passed) ===")
import shutil
# double safety: mv via atomic syscall path (same filesystem always true → /var/www ext4)
shutil.move(OUT, LIVE)
# chown + chmod guarantee
try:
    os.chmod(LIVE, 0o644)
    try:
        os.chown(LIVE, 33, 33)
    except Exception as _c1:
        try:
            subprocess.run(['chown','www-data:www-data', LIVE], check=True, timeout=15)
        except Exception as _c2:
            print(f"  WARN chown failed but mv OK: {_c2}")
except Exception as _m:
    print(f"  [FATAL] post-mv permission fix FAILED: {_m}")
    raise

final_sha = sha(LIVE)
print(f"  POST-SWAP LIVE SHA256 : {final_sha}")
print(f"  EXPECTED (from build)  : {new_sha}")
assert final_sha == new_sha, f"ATOMIC SWAP INTEGRITY FAILURE: final={final_sha} != expected_build={new_sha}"
print(f"\n=== DEPLOY SUCCESS — sailingsa.co.za/ LIVE UPDATED ===")
print(f"  Live file: {LIVE}")
print(f"  Final SHA256: {final_sha}")
print(f"  Size: {os.path.getsize(LIVE)} bytes, {len(open(LIVE).read().splitlines())} lines")
print(f"  Verify browser: https://sailingsa.co.za/?v=CB_FORCE_{int(__import__('time').time()*1000)}")
