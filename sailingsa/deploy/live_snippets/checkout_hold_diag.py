"""Temporary checkout-hold instrumentation (#123 measure).

Logs JSONL to /tmp/ssa_checkout_hold.jsonl:
  worker PID | request path | request checked-out | worker checked-out | site | duration

Disabled on live after the REUSE verify matrix (`_CHECKOUT_DIAG = False`).
Does not change pool/lifecycle behaviour.
"""
