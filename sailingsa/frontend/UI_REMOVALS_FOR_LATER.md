# UI removals — for later re-introduction

Notes for copy/UI that was removed and can be re-done elsewhere without affecting behaviour.

---

## "Welcome Back!" heading

**Removed:** `<h1 id="sailor-welcome-title">Welcome Back!</h1>` from inside `#sailor-view` (signed-in sailor view).

**Effect of removal:** None. No JS or CSS in `index.html` references `#sailor-welcome-title`. The element was static text only.

**To re-introduce later:** Add the heading anywhere inside `#sailor-view` (or elsewhere on the page). Example:

```html
<h1 id="sailor-welcome-title">Welcome Back!</h1>
```

Optional: JS can later set `welcomeTitle.textContent = 'Welcome Back ' + firstName + '!';` if you have the user's first name. The id is free to reuse.

**Where it was:** Directly after `<div id="sailor-view" style="display: none;">`, before the Congratulations section.
