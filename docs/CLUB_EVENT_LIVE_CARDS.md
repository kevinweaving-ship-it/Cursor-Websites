# Event URL preload — copy last same-club cards

When creating or preloading a **new Event URL**, do not invent a new card layout.

1. **Find the event** (SAS / club calendar) and match it.
2. **Create the Event URL** as `YYYY-MM-DD-{club}-{slug}`  
   Example: `/regatta/2026-09-24-hmyc-dart-18-nationals`
3. **Look up the last Event URL at the same host club** that already has live cards.
4. **Copy that club’s card stack** onto the new page:
   - Main header **Leader Board** (empty until scores)
   - **Weather** card (same station as that club)
   - **Media** card (**empty** on a new event — that event’s own `/mm-clips` only, never Midmar leftovers)
   - **Fleet header** for this event’s class
   - **Live camera** if that club already has one
5. Add a fleet block so the fleet header renders before results exist.

HMYC source event: `/regatta/2026-09-19-hmyc-midmar-cup`  
Profile: Leader Board + Agromet Midmar weather + media + HMYC camera.

**When the event opens (HMYC Dart Nationals and later club preloads):**
- **Entries** — update the fleet / entry list on this Event URL; do not change the slug.
- **WhatsApp group** — add the official event group to our WhatsApp. Super-admin drop on the media card already accepts WhatsApp photos/video (`VID_…` / WhatsApp files → `/mm-clips`). Media stays empty until those clips are saved.

Code: `sailingsa/backend/club_live_cards.py` — any later date-first HMYC Event URL inherits this stack automatically. Add a new club profile only when that club’s first live Event URL is set up.

Dart 18 Nationals 2026 preload (This Mac / live DB, not Cloud):

Event URL: `/regatta/2026-09-24-hmyc-dart-18-nationals`

Landing **Regatta Search** lists `public.regattas` via `/api/regattas/with-counts`. Hub upcoming cards with “YYYY: N entries” need `events.regatta_id` **and** a series key that merges prior years (420 Nationals already does this; 2026 Dart title does not until `_yearly_event_series_key` aliases it to `dart 18 nationals`).

Landing upcoming cards and Regatta Search now attach this Event URL from
`sailingsa/backend/preloaded_event_urls.py` even before the SQL apply, so Dart
shows the same way 420 Nationals already does (`regatta_id` on the calendar row
+ a with-counts search hit). SQL apply still persists the live DB row.

```bash
export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
python3 sailingsa/deploy/create_2026_hmyc_dart_18_nationals.py --apply
```

Then deploy API per `sailingsa/deploy/SSH_LIVE.md` so the series-key alias is live.
