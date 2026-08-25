#!/usr/bin/env python3
"""Clear Year / Month / Day format hint on date of birth field."""
from pathlib import Path
import shutil
import time

SIGNUP = Path("/var/www/sailingsa/signup.html")
ts = time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(SIGNUP, Path(f"/root/backups/signup_dob_format_{ts}.html"))
print("BACKUP", ts)
html = SIGNUP.read_text(encoding="utf-8", errors="replace")

CSS = """
            .reg-dob-format {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.35rem;
                margin: 0.45rem 0 0.55rem;
                flex-wrap: wrap;
            }
            .reg-dob-format-part {
                display: flex;
                flex-direction: column;
                align-items: center;
                min-width: 4.5rem;
            }
            .reg-dob-format-part span:first-child {
                font-size: 0.68rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #475569;
            }
            .reg-dob-format-part span:last-child {
                margin-top: 0.2rem;
                padding: 0.35rem 0.55rem;
                min-width: 4.2rem;
                text-align: center;
                border: 2px solid #cbd5e1;
                border-radius: 8px;
                background: #f8fafc;
                font-size: 0.95rem;
                font-weight: 700;
                color: #0f172a;
            }
            .reg-dob-format-sep {
                font-size: 1.25rem;
                font-weight: 900;
                color: #64748b;
                margin-top: 0.85rem;
            }
            #regDobHelp {
                font-size: 0.88rem !important;
                color: #334155 !important;
                font-weight: 600;
            }
"""

if "    </style>" not in html:
    raise SystemExit("missing style end")
html = html.replace("    </style>", CSS + "    </style>", 1)
print("ok css dob format")

OLD = """                        <label for="regDob">Date of birth <span style="color: red;">*</span></label>
                        <div class="reg-field-row">
                            <input type="date" id="regDob" name="bday" autocomplete="bday" required
                                   enterkeyhint="done" tabindex="6"
                                   oninput="refreshRegFieldStatuses()" onchange="refreshRegFieldStatuses()">
                            <span class="reg-tick" id="tick-regDob" aria-hidden="true">✓</span>
                        </div>
                        <div id="regDobHelp" style="margin-top: 0.4rem; font-size: 0.75rem; color: #666; line-height: 1.4;">
                            Required — tap to pick <b>Year</b>, then <b>Month</b>, then <b>Day</b> (e.g. 1998 / March / 15).
                        </div>"""

NEW = """                        <label for="regDob">Date of birth <span style="color: red;">*</span></label>
                        <div class="reg-dob-format" aria-hidden="true">
                            <div class="reg-dob-format-part"><span>Year</span><span>1998</span></div>
                            <div class="reg-dob-format-sep">/</div>
                            <div class="reg-dob-format-part"><span>Month</span><span>03</span></div>
                            <div class="reg-dob-format-sep">/</div>
                            <div class="reg-dob-format-part"><span>Day</span><span>15</span></div>
                        </div>
                        <div class="reg-field-row">
                            <input type="date" id="regDob" name="bday" autocomplete="bday" required
                                   enterkeyhint="done" tabindex="6"
                                   title="Year, then Month, then Day"
                                   oninput="refreshRegFieldStatuses()" onchange="refreshRegFieldStatuses()">
                            <span class="reg-tick" id="tick-regDob" aria-hidden="true">✓</span>
                        </div>
                        <div id="regDobHelp" style="margin-top: 0.4rem; line-height: 1.45;">
                            Tap the field above, then choose <b>Year</b> → <b>Month</b> → <b>Day</b>.
                            Example: <b>1998 / 03 / 15</b> (15 March 1998).
                        </div>"""

if OLD not in html:
    raise SystemExit("missing dob block")
html = html.replace(OLD, NEW, 1)

# Update validation message to match format
html = html.replace(
    "issues.push({ id: 'regDob', msg: 'Enter date of birth — Year, then Month, then Day' });",
    "issues.push({ id: 'regDob', msg: 'Enter date of birth — Year / Month / Day (e.g. 1998 / 03 / 15)' });",
    1,
)

SIGNUP.write_text(html, encoding="utf-8")
assert "reg-dob-format" in html and "Year</span><span>1998" in html
print("WROTE", len(html))
