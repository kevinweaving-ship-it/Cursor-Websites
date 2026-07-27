# Regatta Phase 2 — safe component extraction (zero-break)

## What changed

| Piece | Location |
|-------|----------|
| Header block | `templates/components/regatta_header.html` via `_render_regatta_header_html()` |
| Fleet wrapper | `templates/components/regatta_fleet.html` via `_render_regatta_fleet_wrapper_html()` |
| Result sheet CSS | `sailingsa/frontend/css/regatta.css` (migrated from removed `api._RESULT_SHEET_CSS`) |

## Python

- **No** changes to row loops, fleet data assembly, or `<table>` / `<tr>` generation in `_render_result_sheet_fleet`.
- **Outer HTML only** moved to Jinja; `table_html` string unchanged.
- **`Markup`** used for pre-built HTML fragments (back link, host, status line, fleet title, table).

## Back link variants

The spec used `back_url` only; full regatta and class pages use **different** anchor text and `href`, so the partial accepts **`back_link`** (full `<a>...</a>` string) plus `event_name`, `host_club_html`, `status_line_text` — same output as before.

## CSS loading

- **`/css/regatta.css?v=1`** is linked from:
  - `templates/pages/regatta.html` (`extra_head`), and
  - `serve_regatta_class_standalone` full-document `<head>`.
- **Not** added to `base_app.html` globally: the stylesheet includes global `html,body` and `table` rules that would affect About/Stats/Events.

## Class pages

- `/regatta/{slug}/class-{class_slug}` still returns a **full HTML document** (not `base_app`); only the `<style>` block was replaced with `<link href="/css/regatta.css?v=1">`.

## Manual test (step 6)

Same regatta slug before/after: compare fleet count, row counts, sailor names; mobile — table scroll only, no full-page horizontal scroll.
