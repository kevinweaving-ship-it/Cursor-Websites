#!/usr/bin/env python3
"""Cleanup password-rule labels after easy signup form patch."""
from pathlib import Path

p = Path("/var/www/sailingsa/signup.html")
s = p.read_text(encoding="utf-8", errors="replace")
old = """            try { refreshRegFieldStatuses(); } catch (eTickP) {}
            // keep legacy special/number colour updates below
            if (false && ruleCapital) ruleCapital.style.color = rules.capital ? '#28a745' : '#999';
            if (ruleSpecial) ruleSpecial.style.color = rules.special ? '#28a745' : '#999';
            if (ruleNumber) ruleNumber.style.color = rules.number ? '#28a745' : '#999';"""
new = """            if (ruleSpecial) {
                ruleSpecial.style.color = rules.special ? '#28a745' : '#999';
                ruleSpecial.textContent = (rules.special ? '✓' : '○') + ' Special character (nice to have)';
            }
            if (ruleNumber) {
                ruleNumber.style.color = rules.number ? '#28a745' : '#999';
                ruleNumber.textContent = (rules.number ? '✓' : '○') + ' A number (nice to have)';
            }
            try { refreshRegFieldStatuses(); } catch (eTickP) {}"""
if old not in s:
    raise SystemExit("missing password rule cleanup anchor")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("OK password rule labels")
