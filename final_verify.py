#!/usr/bin/env python3
import re, hashlib
LIVE = "/var/www/sailingsa/index.html"
BAK  = "/var/www/sailingsa/bak_INDEX_PRE_GOLD_UNIV_20260808_143304.html"
live = open(LIVE).read()
bak  = open(BAK).read()
print("="*60)
print("FINAL VERIFY sailingsa.co.za/ (live index.html SHA", hashlib.sha256(live.encode()).hexdigest()[:16]+"...)")
print("="*60)

def ok(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}  {detail}")
    return cond

all_ok = True

# 1. ZERO banned dead code strings
for pat in ['renderLoggedIn','logout-pill-auto-login-popup-v1','padding-top: 80px','padding-top:80px','@@GOLD_HEADER_']:
    all_ok &= ok(f"ZERO dead/banned: '{pat}'", live.count(pat) == 0, f"matches={live.count(pat)}")

# 2. ZERO doc-line leakage in </header> → <main gap (render-visible zone on screenshot)
hc = live.find("</header>"); mn = live.find('<main class="main-content">')
gap = live[hc:mn]
banned_doc = ['PACKAGE SECTION','Marker:','@@GOLD_HEADER','COPY verbatim','copy verbatim',
             '[1] logo','[2] user','[3] auth','Override slots','override slots',
             '-> cfg.logoHref','-> filled by updateHeaderAuthStatus()','/ #loginBox',
             '#headerLogoLink href/title','#headerUserCenter            ->',
             '============================================================']
failed_doc = []
for b in banned_doc:
    if gap.count(b) > 0:
        failed_doc.append(f"{b}*{gap.count(b)}")
all_ok &= ok(f"ZERO render-visible doc lines between </header> & <main (gap={len(gap)} chars)", len(failed_doc) == 0, (f"FAILURES={failed_doc}" if failed_doc else ""))

# 3. Logout/alignment centering rules present
CENTER_RULES = [
    ('header.site-header > .container align-items:center !imp', 'header.site-header > .container' in live and 'align-items: center !important' in live),
    ('slots min-height 80px + inline-flex center', 'min-height:      80px !important' in live and 'display:         inline-flex !important' in live),
    ('buttons align-self:center !imp', 'align-self:       center !important' in live and 'header.site-header button' in live),
    ('GOLD_FORCED_CENTER_CSS guard block', '#loggedInStatus button,\nheader.site-header #headerAuth button' in live and 'transform: translateY(0) !important' in live),
]
for label, cond in CENTER_RULES:
    all_ok &= ok(f"CENTERING RULE: {label}", cond)

# 4. Logged-out button guard: SU=#eab308 YELLOW LEFT (FIRST CHILD) of Login white RIGHT
BGUARD = [
    ('YELLOW Sign Up BG = #eab308', live.count("SU_BG='#eab308'") > 0),
    ('WHITE Login BG = #ffffff',  live.count("SI_BG='#ffffff'")  > 0),
    ('DOM ORDER: appendChild(su) FIRST -> appendChild(si) SECOND', live.count("lb.appendChild(su); lb.appendChild(si)") > 0),
    ('edit.svg SU ICON PATH', live.count("SU_ICON='/icons/assets/iconoir/regular/edit.svg'") > 0),
    ('user-circle-gear SI ICON PATH', live.count("SI_ICON='/icons/assets/iconoir/regular/user-circle-gear-bold.svg'") > 0),
    ('FORCE_GOLD_BUTTONS_GUARD fireSignIn/Up wired to __GOLD_HEADER_CFG', live.count('_fireSu(e)') > 0 and live.count('_fireSi(e)') > 0),
]
for label, cond in BGUARD:
    all_ok &= ok(f"BUTTON GUARD: {label}", cond)

# 5. LIB-ONWARDS IDENTITY: /js/config.js through </body></html> NEVER TOUCHED
ANCHOR = '<script src="/js/config.js">'
la = live.find(ANCHOR); ba = bak.find(ANCHOR)
identical = (live[la:] == bak[ba:])
all_ok &= ok(f"LIB ONWARDS byte-identical (main tag + ALL below NEVER EDITED)", identical, f"tail_same={identical} bytes={len(live[la:])}")

# 6. IIFE count in header wiring (__GOLD_HEADER_CFG to lib anchor): 3 gold PKG3 + 1 button guard = 4 MIN
cfg_pos = live.find("window.__GOLD_HEADER_CFG")
block = live[cfg_pos:la]
noch = re.sub(r'<!--.*?-->','',block,re.DOTALL)
noch = re.sub(r'/\*.*?\*/','',noch,re.DOTALL)
noch = re.sub(r'(?m)^\s*//.*$','',noch)
iife_c = len(re.findall(r'\(function\s*\(\s*\)\s*\{', noch))
all_ok &= ok(f"IIFE count in header wiring block", iife_c >= 4, f"count={iife_c} (need >= 4)")

print()
print("="*60)
print("FINAL RESULT:", "ALL PASS ✅ (deploy complete)" if all_ok else "AT LEAST 1 FAILURE ❌")
print("Live size:", len(live), "bytes,", len(live.splitlines()), "lines")
print("Live SHA256:", hashlib.sha256(live.encode()).hexdigest())
print("="*60)
import sys; sys.exit(0 if all_ok else 3)
