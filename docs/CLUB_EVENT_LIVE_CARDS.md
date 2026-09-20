# Event URL preload — copy last same-club cards

When creating or preloading a **new Event URL**, do not invent a new card layout.

1. **Find the event** (SAS / club calendar) and match it.
2. **Create the Event URL** as `YYYY-MM-DD-{club}-{slug}`  
   Example: `/regatta/2026-09-24-hmyc-dart-18-nationals`
3. **Look up the last Event URL at the same host club** that already has live cards.
4. **Copy that club’s card stack** onto the new page:
   - Main header **Leader Board** (empty until scores)
   - **Weather** card (same station as that club)
   - **Media** card (**empty** on a new event)
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

```bash
export DB_URL="postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
python3 sailingsa/deploy/create_2026_hmyc_dart_18_nationals.py --apply
```
