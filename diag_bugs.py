#!/usr/bin/env python3
import re
GOLD = "/var/www/sailingsa/header/index.html"
LND  = "/var/www/sailingsa/bak_INDEX_PRE_GOLD_UNIV_20260808_143304.html"
with open(GOLD) as f: gold = f.read()
with open(LND) as f: lnd = f.read()

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
    return text[line_start:line_end]

print("="*72)
print("GOLD PKG2 HTML RAW LINES (every line, numbered):")
print("="*72)
for i, line in enumerate(extract_between_markers(gold,"HTML").splitlines(), 1):
    print(f"{i:3}| {repr(line)}")
print()
print("="*72)
print("GOLD PKG3 SCRIPTS RAW LINES (first 3 of each IIFE, numbered):")
print("="*72)
lines = extract_between_markers(gold,"SCRIPTS").splitlines()
iife_starts = []
for i,l in enumerate(lines):
    if re.match(r'\s*\(\s*function\s*\(\s*\)\s*\{', l):
        iife_starts.append(i)
print(f"  IIFE start line indices (0-based): {iife_starts}, count = {len(iife_starts)}")
for idx, start_i in enumerate(iife_starts, 1):
    print(f"\n  --- IIFE #{idx} starts at line {start_i+1} (1-based), first 5 lines:")
    for j in range(start_i, min(start_i+5, len(lines))):
        print(f"    {j+1:3}| {repr(lines[j])}")

print()
print("="*72)
print("LANDING inline scripts BEFORE /js/config.js (R3 insert point range):")
print("="*72)
anchor = '<script src="/js/config.js">'
r3 = lnd.find(anchor)
# go back ~20k chars from r3 and look for logged-out button render patterns
tail_before = lnd[max(0, r3-30000):r3]
for pattern in ['signUpBtn', 'signInBtn', 'sailingRenderLoggedOutAuthButtons', 'loginBox', 'appendChild(signIn', 'appendChild(signUp', '#eab308', 'Sign Up', '#ffffff']:
    pos = tail_before.find(pattern)
    if pos != -1:
        realpos = max(0, r3-30000) + pos
        surrounding = lnd[max(0, realpos-120):realpos+len(pattern)+120]
        print(f"\n  FOUND '{pattern}' at global pos {realpos} (r3={r3}), surrounding 240 chars:")
        for sline in surrounding.splitlines():
            print(f"    >> {repr(sline)[:200]}")
