# Compare live vs local index.html (read-only)

Live content was fetched via **expect** using SSH_LIVE.md auth: `expect sailingsa/deploy/read-live-index.exp`. Output saved to `sailingsa/deploy/live-index-sections.txt`.

---

## Where local differs from live (exact diff)

| Location | Live (sailingsa.co.za) | Local (your repo) |
|----------|------------------------|-------------------|
| **CSS** ~line 907 | `z-index: 3000;` | `z-index: 4000;` |
| **JS** after `closeRegattaChoiceModal();` ~4541 | Goes straight to `// Show modal` | Extra 4 lines: comment + get `popupOverlay` + `if (popup) popup.style.display = 'none';` then `// Show modal` |

So **local** has two edits that **live** does not:
1. Result-sheet modal z-index raised from 3000 to 4000.
2. When opening the result sheet modal, local explicitly hides the login popup overlay.

---

## Re-fetch live (read-only)

```bash
expect sailingsa/deploy/read-live-index.exp
```
Output is also written to `sailingsa/deploy/live-index-sections.txt`.

---

## Roll back local to match live

In `sailingsa/frontend/index.html`:
- Change `z-index: 4000` back to `z-index: 3000` for `.regatta-result-sheet-modal`.
- Remove the 4 lines that hide `popupOverlay` in `openResultPageInModal` (the comment + `const popup = ...` + `if (popup) popup.style.display = 'none';`).
