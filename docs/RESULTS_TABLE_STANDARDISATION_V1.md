# Results table standardisation v1 (non-destructive)

## Rules followed

- **No** rebuild of `<table>` body logic beyond **class attributes** and wrapper/table class names.
- **No** loop, column order, or cell content changes.
- **No** `results_table.html` Jinja component; **no** JS.

## Markup

- Wrapper (in `regatta_fleet.html`): `class="table-wrapper results-table-container"`.
- Table: `class="results-table"`.
- **Column hints** (`col-*`) added on matching `<th>` and `<td>` in lockstep (e.g. `col-pos`, `col-fleet`, `col-class`, `col-sail`, `col-race`, `col-total`, `col-nett`, `col-name` on Helm, etc.). Existing classes (`rank-col`, `sail-col`, medal rows, `code` / `disc`, etc.) **preserved**.

## CSS

- Appended to `sailingsa/frontend/css/regatta.css` (cache `?v=2` on `/css/regatta.css` links).
- **Sticky first column** not applied (optional bonus skipped for v1).

## Verify

One regatta: row count, positions, names, totals unchanged vs prior HTML; mobile — horizontal scroll inside the wrapper, no page-wide overflow.
