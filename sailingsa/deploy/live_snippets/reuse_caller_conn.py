"""Reuse caller connection in shared helpers (#123).

Measured cause: requests hold 2–3 pooled conns at once.
Helpers accept optional conn= and keep standalone self-borrow.
"""
