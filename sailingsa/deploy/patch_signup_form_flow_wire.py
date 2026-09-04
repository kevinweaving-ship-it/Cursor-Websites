#!/usr/bin/env python3
"""Wire easy field-flow when registration form is shown."""
from pathlib import Path
import shutil
import time

p = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
bak = Path(f"/root/backups/signup_wire_flow_{ts}.html")
shutil.copy2(p, bak)
print("BACKUP", bak)
s = p.read_text(encoding="utf-8", errors="replace")

old = """        function showRegistrationDataForm() {
            console.log('[DEBUG] showRegistrationDataForm: Showing registration data form');
            showSection('registrationDataForm');
            try {
                trackClaimFunnel('registration_started', (currentProfile && currentProfile.sas_id) ? currentProfile.sas_id : (claimSelectedSasId || ''), true, '', {});
            } catch (e) {}
            
            // Reset form
            const form = document.getElementById('regDataForm');
            if (form) {
                form.reset();
            }"""

new = """        function showRegistrationDataForm() {
            console.log('[DEBUG] showRegistrationDataForm: Showing registration data form');
            showSection('registrationDataForm');
            try {
                trackClaimFunnel('registration_started', (currentProfile && currentProfile.sas_id) ? currentProfile.sas_id : (claimSelectedSasId || ''), true, '', {});
            } catch (e) {}
            
            // Reset form
            const form = document.getElementById('regDataForm');
            if (form) {
                form.reset();
                try { form.dataset.flowWired = ''; } catch (eRw) {}
            }
            try { setTimeout(wireRegFormFieldFlow, 30); } catch (eFlow) {}"""

if old not in s:
    raise SystemExit("missing showRegistrationDataForm anchor")
s = s.replace(old, new, 1)
print("ok showRegistrationDataForm wire")

needle = "window.addEventListener('DOMContentLoaded', async function() {"
pos = s.find(needle)
if pos >= 0 and "wireRegFormFieldFlow" not in s[pos : pos + 350]:
    s = s.replace(
        needle,
        needle + "\n            try { setTimeout(wireRegFormFieldFlow, 150); } catch (eFlow0) {}",
        1,
    )
    print("ok DOMContentLoaded wire")

s = s.replace(
    "Green tick = done. Optional fields can be left blank — tap <b>Skip</b> or press Tab.",
    "Green tick = done. Optional fields: leave blank and press Tab (or Enter) to move on.",
    1,
)
print("ok hint copy")

p.write_text(s, encoding="utf-8")
assert "setTimeout(wireRegFormFieldFlow, 30)" in s
print("WROTE", p, len(s))
