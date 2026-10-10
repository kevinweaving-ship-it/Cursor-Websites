# PY numbers and SailRSA reference

Reference-only scrape so club PY events and class URLs can reuse published numbers and SA history. **Does not write gold `classes`.**

## Sources

- RYA scheme: https://www.rya.org.uk/racing/portsmouth-yardstick/
- RYA 2026 PN list + limited-data list (Asset Bank tiles on that page)
- SA Sailing dinghy/cat PY-LA (2019): https://cdn.revolutionise.com.au/cups/sas/files/ruou7obyk3wzgeqf.pdf
- SailRSA archive: https://sailrsa.org.za/index.htm — classes, clubs, results by year, news, links

## Where it lives

- **Box:** `/var/www/sailingsa/data/reference/` (full HTML/PDF crawl + JSON)
- **Repo compact index:** `sailingsa/reference/py/` (`portsmouth-numbers.json` = SAS 2019 first, then RYA 2026)

## Refresh

```bash
python3 sailingsa/scripts/ingest_py_and_sailrsa.py /var/www/sailingsa/data/reference sailingsa/reference/py
```

Use SA PY-LA for local boats (Dabchick, Sprog, Sonnet, Gypsy, Mosquito). Use RYA 2026 for international classes (ILCA, 420, 505, Optimist). Club may still adjust.
