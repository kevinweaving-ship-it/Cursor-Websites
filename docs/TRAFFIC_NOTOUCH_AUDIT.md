# Traffic Real visitors ▶ — audit report (no-touch)

## What you see (matches the code)

1. Empty “No real visitors…” appears  
2. Later a list with ▶ shows  
3. ~3s later list vanishes / collapses back to ▶ or empty  
4. ▶ never becomes teal ▼  
5. Tap does nothing useful  

URL refresh is a red herring for (4)/(5). The break is **in-page poll + click handlers**.

---

## Bug A — dead ▶ / ▼ never sticks (double toggle)

Live code had **two** handlers on the same tap:

1. Inline `onclick="return window.__ssaTrailToggle(...)"` on the button  
2. `document` click listener also calling `trailToggle(k)`

One tap → open → immediately close.  
Result: always looks like ▶, never teal ▼, feels “not clickable”.

**No-touch never helps** here: `LIVE_TRAIL_OPEN` never stays true, so `trailHold` stays false and polls keep rewriting the table.

---

## Bug B — list ↔ empty flicker (empty wipe on poll)

In `renderOffline`:

- Poll every 3s calls `/traffic/api/live`
- If that response has `offline: []` (timeout / aborted txn / slow query), code did:

```js
box.innerHTML = "No real visitors since reset yet…"
```

That **destroys** a good list that was already on screen. Next successful poll paints the list again → your loop.

“No touch” only skips rewrite when a trail is open. Because Bug A prevents open state, **no-touch never engages**, so every poll can wipe/rebuild.

---

## How no-touch is supposed to work (and why it never did for you)

| Step | Intended | What actually happened |
|------|----------|-------------------------|
| Tap ▶ | `LIVE_TRAIL_OPEN[k]=true`, show ▼ | Double toggle cleared it instantly |
| Poll 3s | `trailHold` true → skip `renderLive`/`renderOffline` | `trailHold` false → full rewrite |
| URL refresh | Memory cleared; refetch API | Correct — open state never survives URL reload by design |

So no-touch was written, but **unreachable** while taps self-cancel.

---

## Fix applied on live (this pass)

1. Remove inline `onclick` — **one** document listener only  
2. Do not replace Real visitors with empty message if a table is already shown  
3. `stopImmediatePropagation` on the trail click  

Hard-refresh `/traffic` after deploy. This report stands even if UX still fails — next check is whether `/traffic/api/live` still returns empty `offline` under load.
