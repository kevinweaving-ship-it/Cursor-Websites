# SailingSA — PERMANENT MICRO-EDIT WORKFLOW LOCK (2026-08-10)

## HARD ENFORCED RULES FOR ALL sailingsa.co.za /dev-1 production→dev match edits.

## 📱 **MOBILE IS THE SINGLE SOURCE OF TRUTH — PERMANENT LAYOUT RULE (2026-08-10 V29)**
1. **Build every component mobile portrait first and only once.** No separate desktop design pass.
2. **Desktop/PC MUST render the mobile components unchanged:** exact same dimensions, typography, spacing, alignment, styling and behavior.
   - **NEVER resize, re-style, re-layout, or zoom mobile components on PC.** Do not add `@media (min-width:768px)` rules that alter the rendered size/typography/alignment/spacing/behavior of any element written for mobile.
   - **NEVER duplicate content or code for desktop.** One source block renders on every viewport.
3. **Wider screens EXTRA width usage rule:** The ONLY legal use of extra screen width beyond ~414px is to place mobile sections (that would stack below each other on mobile) **side-by-side left→right** on a responsive grid (`display:grid; grid-template-columns: repeat(auto-fill, minmax(414px, 1fr))` style). Content inside each mobile-width module remains identical to mobile rendering.
4. The **mobile width lock**: The profile UI shell on PC viewports MUST keep the exact mobile portrait max-width (414px default) with `margin:0 auto` horizontal centering. No `@media` enlargements ever.

## 🔳 **COMPACT UI RULE — PERMANENT (2026-08-10 V29)**
Every SailingSA component MUST use the smallest practical container and the MINIMUM padding / gaps. No decorative whitespace. Mobile SSOT rule applies simultaneously.

Specific applications:
1. **Avatar tight to card**: `.sa-approved-sailor-avatar` sits tight to the card `.sa-approved-sailor-card` top/left/bottom edges. No outer margins, no decorative spacing around avatar unless functionally required.
2. **Identity block tight pack**: Sailor identity block (`.sa-approved-sailor-main` → Name First / Name Last / Club Logo / Club Abbreviation) is itself tightly packed internally with MINIMUM practical line-heights, gap, padding, margins. No decorative whitespace between name, club, logo lines.
3. **Gap between avatar and identity block**: Minimal (the smallest practical consistent pixel value that avoids visual overlap / crush — no decorative gap).
4. **General**: No oversized boxes, no padding margins on wrappers "for breathing room", no whitespace added unless required to prevent element overlap or preserve required interactive hitbox size.
5. **Production match on tightness**: If `/sailor/{slug}` production components are tight, dev1 copies EXACT tight spacing verbatim. If production spacing = Xpx, dev1 = Xpx, never X+Npx.

### ⛔ **PERMANENT BANS (VIOLATION = FAIL)**
- ❌ NO perl, sed, regex patch mechanisms via SSH.
- ❌ NO generated patch / deploy / helper scripts — ever.
- ❌ NO `/tmp/*.py` files locally or remotely.
- ❌ NO SCP of scripts — SCP ALLOWED ONLY for edited `api.py` (or another exact source file) itself.
- ❌ NO new override `<style>` blocks, NO appended lock rules. Edit existing rules in place ONLY.
- ❌ NO browser `getBoundingClientRect` / `outerHTML` / computed-style reverse engineering.
- ❌ NO broad searches, diff matrices, geometry reports, audit side-quests.
- ❌ NO edits outside the EXACT element requested ("zero-addition principle").

### ✅ **4-STEP LEGAL WORKFLOW (only path allowed)**

#### STEP 1 — READ EXACT SOURCE (≤ ~5s)
- SSH + `sed` / `grep -F` **only the requested element literal**.
- Output: production source block + dev source block for that element ONLY.
- If source not found within ~5s → FAIL blocker → STOP, do not proceed.

#### STEP 2 — LOCAL EDITOR EDIT IN PLACE (~2–5s)
- Use Trae local Write/Edit tools on the checked-out local copy
  `$WORKDIR/api.py.V26_EDIT_SOURCE_COPY.py` (or the exact source file).
- Copy the PRODUCTION source literal block VERBATIM over the dev equivalent.
- Change **only required data bindings** (variable concatenations: `safe_foo`,
  `_dev1_*_html`, `is_sailor_verified` ternaries, `sas_id`, etc.) to re-connect dev logic.
- Never "interpret" the visual design — copy the literal source.

#### STEP 3 — DEPLOY SCP COMPLETE FILE (~10s)
```bash
scp local_file root@sailingsa.co.za:/var/www/sailingsa/api/api.py
ssh root@sailingsa.co.za '\
  chown www-data:www-data /var/www/sailingsa/api/api.py && \
  chmod 644 /var/www/sailingsa/api/api.py && \
  /var/www/sailingsa/api/venv/bin/python3 -m py_compile /var/www/sailingsa/api/api.py && \
  systemctl restart sailingsa-api.service'
```
- py_compile FAIL → ROLLBACK → cp the backup → STOP → report 1-sentence fail.
- NO service restart before py_compile OK.

#### STEP 4 — VISUAL COMPARE MATCH OR STOP (~5s)
- Integrated browser open both URLs same viewport.
- `browser_take_screenshot ref=".EXACT_SELECTOR"` on each.
- Read screenshots. PASS = MATCH. MISMATCH = revert if required, STOP, report 1-sentence visible difference.

### ⏱️ **OVERALL ≤30s BUDGET. STOP IF EXCEEDED.**
No artificial per-step time limit. Timer starts on receipt of each task command. TOTAL >30s → immediate FAIL + blocker sentence.

### ✋ **VALIDATION GATE: NO DEPLOY UNTIL PRE-LOCAL-CHECK OK**
If step 2 produces an edit that would not (visually / source-wise) match → stop before SCP. Do not deploy known-broken edits. Server file is production; deploy only when the local diff contains the intended literal swap.
