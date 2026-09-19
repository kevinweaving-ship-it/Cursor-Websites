#!/usr/bin/env python3
from pathlib import Path

t = Path("/var/www/sailingsa/api/api.py").read_text()
i = t.find('cell_class = " ".join(inner_cls)')
print("==== CELL -2800 ====")
print(t[i - 2800 : i + 120])

print("==== RKEY LOOPS ====")
start = 0
n = 0
while True:
    p = t.find("for rkey in race_columns", start)
    if p < 0:
        break
    n += 1
    print("--- loop", n, p, "---")
    print(t[p : p + 180])
    start = p + 1

print("==== RACE_SCORES GET ====")
start = 0
n = 0
while True:
    p = t.find("race_scores.get(rkey", start)
    if p < 0:
        break
    n += 1
    print("--- get", n, p, "---")
    print(t[p - 120 : p + 200])
    start = p + 1

print("==== DISCARD BUILD ====")
a = t.find("res_scores_list = []")
print(t[a - 250 : a + 250])
