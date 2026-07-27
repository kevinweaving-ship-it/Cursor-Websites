# Regatta page safe refactor — Phase 1 (identification log)

## Target URL

`/regatta/{slug}` → `serve_regatta_standalone` in **`api.py`** (no Jinja template before this phase).

## Template files (before → after)

| Before | After (Phase 1 shell only) |
|--------|------------------------------|
| None | `sailingsa/frontend/templates/pages/regatta.html` extends `base_app.html` |

## Inline HTML vs includes (approximate)

| Metric | Value |
|--------|--------|
| **Jinja / includes** | **0%** of body HTML pre-refactor; post-refactor: layout shell only (`base_app` + components includes). |
| **Python-built HTML** | **~100%** of regatta body: `header_html` + `_render_result_sheet_fleet()` per fleet + print button. |
| **Inline CSS** | **Was** `_RESULT_SHEET_CSS` in Python; **Phase 2** → `css/regatta.css` (see `REGATTA_PHASE_2_SAFE_COMPONENT_EXTRACTION.md`). |
| **Inline HTML attributes** | **Yes** — e.g. `class-header` uses `style="font-size:20px;..."` inside `_render_result_sheet_fleet` (not modified in Phase 1). |

## Section map (logical)

| Section | Source |
|---------|--------|
| **Header block** | `header_html`: back link + `.header` + `.regatta-name` / `.host-club` / `.status-line` |
| **Stats / meta** | Status line + per-fleet `sailed-line` (entries, discards, etc.) inside each `fleet-section` |
| **Results table** | `<div class="table-wrapper"><table>...</table></div>` per fleet (not `.table-container`; CSS safety via `app.css` on `.table-wrapper` under `.app-container`) |

## Rules observed (Phase 1)

- No route path changes; no DB/query changes.
- No `components/results_table.html` integration.
- No restructuring of table rows or fleet renderer.

## Phase 2 prep

Future extraction markers live in `pages/regatta.html` (comments only).

## Implementation (Phase 1 wrap)

- **`pages/regatta.html`** extends `base_app.html`; `regatta_body_html` is the same string as before (inside `.regatta-page`), built in `serve_regatta_standalone`.
- **Header isolation:** Legacy page had no `.site-header` duplicate — only event `.header`. That block is **unchanged** inside `regatta_body_html`.
- **`/regatta/{slug}/class-...`** is **not** migrated in this phase (still full `HTMLResponse` document).
