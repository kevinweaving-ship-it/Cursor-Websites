# /dev1/ landing-roundup-cards.js — lead override

Live file: `https://sailingsa.co.za/dev1/landing-roundup-cards.js`

Today it fetches `/sailing-roundup/feed.json` then **hardcodes Ullman as the 2026-10-26 lead**:

```js
// DEV1-only editorial correction: lead with Ullman Day 2, not Tour de Vlei.
if (rows[0] && /2026-10-26/.test(rows[0].url || "")) {
  rows[0] = Object.assign({}, rows[0], {
    image: "https://sailingsa.co.za/sailing-roundup/issues/2026-10-26/media/2026-10-24-ullman-sails-womens-series-day-2-hero.jpg",
    image_caption: "Ullman Sails Women's Series — Day 2.",
    headline: "Ullman Sails Women's Series — Day 2, Tour de Vlei, Dam Bottle Sprints, 2026 DF 95 Global Championship and NW Youth Regionals Regatta 2026"
  });
}
```

Do **not** add another hardcoded event list. After `feed.json` is updated from `artifacts/roundup/sailing-roundup/feed.2026-10-26.json`, **delete this block** so the card overlay uses the rebuilt DF95 headline.

The navy carousel, dots, arrows, engagement row, and READ FULL ROUNDUP stay as they are.
