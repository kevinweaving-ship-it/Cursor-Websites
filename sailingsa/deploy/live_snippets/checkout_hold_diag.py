"""Temporary checkout-hold instrumentation (#123 measure).

Logs JSONL to /tmp/ssa_checkout_hold.jsonl:
  worker PID | request path | request checked-out | worker checked-out | site | duration

Do NOT leave this on after verification.
Does not change pool/lifecycle behaviour.
"""
