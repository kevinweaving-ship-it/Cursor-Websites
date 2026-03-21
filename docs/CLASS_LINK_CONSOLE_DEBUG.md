# classLink(7,"420") returns plain text — which file to patch

## Steps for Cursor / developer

1. **Open DevTools** on the regatta page.
2. **Check frame context**: Console frame selector — **top** vs **iframe**. The document in that frame is the one that defines the `classLink` you’re calling.
3. **View Source** of that exact document (e.g. right‑click → View Page Source, or Sources tab and select the document).
4. **Inspect `function classLink`** in that source (search for `function classLink`). That code lives in one of the HTML files below.
5. **Fix that file**: ensure when `classId` is null/empty but `displayName` is set, it returns a link to `/class/{slug}` with `target="_top"`, not plain text.
6. **Redeploy frontend only**: `bash sailingsa/deploy/deploy-with-key.sh`.

## Quick console check

```js
classLink(7,"420")
```

**If it returns plain text** (e.g. `"420"`) instead of a link, the `classLink` in the **current document** is wrong. Patch that document’s file (see table below), not necessarily `index.html`.

## There is no separate JS file

`classLink` is **only** defined in **inline scripts inside HTML**. There is no `classLink` in any `.js` file under `sailingsa/frontend`. So “the loaded script file” is the **HTML document** that’s currently the console’s execution context.

## Which HTML file is in context?

1. **DevTools → Console**  
   The console runs in the **top frame** by default. If you didn’t select another frame, you’re in the main document.

2. **Check the document:**
   - Run `window.location.pathname` (or look at the address bar).
   - If the regatta results are in an **iframe**, use the frame selector in DevTools (Console or Elements) to switch context to that iframe, then run `classLink(7,"420")` again.

3. **Map context → file to patch** (View Source shows which document; patch the corresponding file(s)):

   | Frame / document | File(s) to patch |
   |------------------|------------------|
   | **Top** (main window, path like `/regatta/371-...`) | `sailingsa/frontend/index.html`, `sailingsa/frontend/public/index.html` |
   | **Iframe**: regatta results (`/regatta/results.html?regatta_id=...`) | `sailingsa/frontend/regatta/results.html`, `sailingsa/frontend/public/regatta/results.html` |
   | **Iframe**: class results (`/regatta/class/class-results.html?...)` | `sailingsa/frontend/regatta/class/class-results.html`, `sailingsa/frontend/public/regatta/class/class-results.html` |

4. **Network tab**  
   “Network → JS” only shows separate script requests (e.g. `api.js`, `session.js`). None of those define `classLink`. The definition is in the **HTML document** that was loaded (index.html, results.html, or class-results.html). So use the mapping above; don’t patch a random .js file.

## Required behavior for classLink

In the file you identified, `classLink(classId, displayName)` must:

- If `classId` is set and `displayName` is set: return a link to `/class/{classId}-{slug}` with `target="_top"`.
- If `classId` is null/empty but `displayName` is set: return a link to `/class/{slug}` with `target="_top"` (fallback so class name is always clickable).
- If there’s no usable display name/slug: return escaped text (e.g. `—`).

Patch the **inline** `function classLink(...)` in that HTML file (and its public copy if it exists).
