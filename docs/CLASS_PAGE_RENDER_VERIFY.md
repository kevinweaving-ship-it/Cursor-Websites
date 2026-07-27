# Class page render path verification

## 1. renderClassPage() calls buildMasterPageLayout()

**index.html** (line ~2041): `buildMasterPageLayout(cv, { backLink, titleCard, statsCard, dataCards });`
**public/index.html** (line ~1966): same.

No direct `cv.innerHTML` or `heroCard` in renderClassPage. Only `buildMasterPageLayout(cv, ...)` writes the DOM.

## 2. Which index.html is loaded for /class/62-optimist-a?

Deploy extracts the frontend zip into `/var/www/sailingsa`. The zip is built from `sailingsa/frontend/`, so:
- **Root:** `sailingsa/frontend/index.html` → deployed as `/var/www/sailingsa/index.html`
- **Public:** `sailingsa/frontend/public/index.html` → deployed as `/var/www/sailingsa/public/index.html`

For `https://sailingsa.co.za/class/62-optimist-a` the server typically serves the **root** index.html (SPA fallback). So the file that runs is the **root** index.html (our updated one). If your site serves the app from a path that uses `public/`, then `public/index.html` would be used instead. Both files have been updated identically.

## 3. Browser console check

Open https://sailingsa.co.za/class/62-optimist-a → F12 → Console. Run:
```js
typeof window.renderClassPage
```
Expected: `"function"`. Then run:
```js
document.querySelector('.master-page-layout')
```
If the new layout is active, this returns the wrapper element. If it returns `null`, the old bundle or cached HTML is still in use.

## 4. Old wrapper removed

Grep confirms: no `class-page-component`, no `cv.innerHTML` in renderClassPage, no `heroCard` string. Old layout HTML has been removed; only `buildMasterPageLayout()` sets container content.

## 5. If old layout still appears

- Hard refresh: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Windows).
- Or open in a private/incognito window.
- Then redeploy frontend so the server has the latest files: `bash sailingsa/deploy/auto-dr.sh`

---

## 6. DevTools verification (stats links vs plain text)

### A. Confirm what file the browser actually loaded

1. Open **DevTools** → **Network** tab.
2. Reload the page (e.g. https://sailingsa.co.za/class/62-optimist-a).
3. Click the **index.html** (or main document) entry.
4. Check **Headers** or **Response** – verify timestamp/size matches the deployed file (e.g. compare with local `sailingsa/frontend/index.html` size / last-modified after deploy).

For `/class/...` the server serves the **root** document: `index.html` from `/var/www/sailingsa/` (built from `sailingsa/frontend/index.html`). If the app is under a path that uses `public/`, the loaded file may be `public/index.html` instead.

### B. Confirm the stats links exist in the loaded file

1. **DevTools** → **Elements** tab.
2. Find the stats card (e.g. search for `stats-card` or `class-stats`).
3. Inspect the contents of `.class-stats`:
   - **Correct (new frontend):** There are **`<a>` elements** with `href="#regattas"`, `href="#clubs"`, `href="#sailors"`, and labels like "Regattas 5", "Clubs 3", etc.
   - **Wrong (old/cached):** Only **text nodes** (no `<a>` tags); stats look like plain text.

### C. If it’s still text

The browser is using an older frontend than the one edited in Cursor. The server may not have the latest deploy, or the response is cached (browser or CDN).

### D. Quick isolation test

Open the site in a **new private/incognito** window and load the same URL (e.g. https://sailingsa.co.za/class/62-optimist-a). That forces a fresh load from the server with no local cache. If stats are `<a>` links in incognito but plain text in the normal window, the issue is cache; if still text in incognito, redeploy so the server has the latest `index.html` (and `public/index.html` if that path is used).
