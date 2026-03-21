# Homepage search boxes — design (sailingsa.co.za)

**Rollback (if the page breaks):** Restore from the backup taken before this change. From your machine:
```bash
ssh -i ~/.ssh/sailingsa_live_key root@102.218.215.253 'rm -rf /var/www/sailingsa/* ; cp -a /root/backups/sailingsa_frontend_BEFORE_BIO_20260306_150545/* /var/www/sailingsa/ ; chown -R www-data:www-data /var/www/sailingsa ; systemctl restart sailingsa-api'
```
Or use the path printed when you last ran `bash sailingsa/deploy/backup-live-frontend-before-bio.sh`. See **`sailingsa/deploy/BIO_BACKUP_RESTORE.md`**.

---

## Goal

- **Separate** Sailor and Regatta into **two distinct search boxes** (no shared bar, no mode toggle).
- **Same / identical style** as current: same box look, input height, borders, pill shape where used, spacing.
- **Extensible:** add **Club Search** and **Class Search** below later, each with the same style.

## Order (top to bottom)

1. **Sailor** (top)
2. **Regatta**
3. **Club** (planned)
4. **Class** (planned)

## Style to keep (identical)

- Reuse current **sailor** row styling for the Sailor row:
  - Label (visually or screen-reader) + input wrap with **search icon** (magnifying glass), **pill-shaped input** (`border-radius: 999px`), **orange border** (`#cc4400` / `#FF6600`), placeholder colour, focus ring.
- Reuse same **box/row pattern** for Regatta (and later Club, Class):
  - Same container pattern: label + input; same font sizes, padding, heights as current `.sailor-search-input` / `.regatta-search-input` so all rows look like one family.
- Existing CSS to align with:
  - `.search-header-container`, `.sailor-search-section`, `.sailor-search-form`, `.sailor-search-input-wrap`, `.sailor-search-input`, `.regatta-search-form`, `.regatta-search-input`, and media queries for 768px / 480px.

So: **same boxes, same style** — only the label and placeholder (and which API/list they drive) change per row.

## Row pattern (for all four)

Each row:

- One **container** (e.g. section or div) with same margin/gap as current.
- **Label** (e.g. "Sailor Search", "Regatta Search", "Club Search", "Class Search") — same class/style as now.
- **Input** in a wrap (optional search icon for consistency): same height, border, radius, padding as current sailor/regatta inputs.
- **Results** area below that row (sailor results, regatta list, club list, class list) in the same visual style as today.

No toggle buttons: each row has one purpose. Same look and feel across all rows so adding Club and Class is just another row with the same markup/CSS pattern.

## Implementation notes (when building)

- **Sailor:** keep `#sailor-search-input`, `#sailor-search-form`; remove mode toggle; sailor input only runs sailor search.
- **Regatta:** add `#regatta-search-input` (and optional `#regatta-search-form`); `applyRegattaFilter()` reads only from this input.
- **Club / Class:** add `#club-search-input` and `#class-search-input` (and forms if desired); same HTML/CSS structure as Sailor/Regatta rows; wire to their own APIs/lists later.
