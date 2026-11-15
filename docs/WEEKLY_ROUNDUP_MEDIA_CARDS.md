# Weekly Roundup media cards

Grok Bot runs this. Kevin does not. He vibe-codes. He does not pick photos, approve a card, write the story, or publish an edition by hand. There is no step that waits for him.

The job is the GoWifi roundup service at `/opt/rea/work/sailing-roundup` (`sailing-roundup.timer`). One run finishes the whole edition: results, story, photos, `issue.json`, HTML, PDF, and `feed.json`.

## One event

1. Read the results URL `https://sailingsa.co.za/regatta/{event-id}`.
2. Store the facts on `week_fact`: name, club, venue, dates, fleet, entries, winner, races, wins, nett, second place, and provisional or final.
3. Write the story from those facts only. Name winners from the results. If an event has no published results, list its name and do not invent a score.
4. Search for an on-water photo of that event after the story exists. Look at the regatta page, the club Facebook post, the club site, and class or photographer pages. Match the event name, club, class, and that weekend.
5. Save the file on the issue as `issues/{edition}/media/{event-date}-{slug}-hero.jpg`. Do not hotlink. Set `url`, `caption`, `credit`, `source_url`, `role: "hero"`, `category: "on-water"`, `event_verified: true`, and `verification: "reviewed_source_and_pixels"`. The check is the job's own vision pass, not a message to Kevin.
6. Copy the lead photo into `feed.json` as `image`, `image_caption`, and `image_focus`. Leave `image` empty only when no photo matched. Do not use a burgee, pennant, ensign, club logo, event logo, or Facebook profile picture.
7. Clear `needs_external` for that event when the photo is stored and matched. Leave it set when the search found nothing.

The homepage card only reads `feed.json`. It does not search the web. The lead photo is the card. A tap opens the issue URL.

## Every card, every run

Do not stop at the latest issue. Each run checks every edition in `feed.json` and every issue folder.

Rebuild an edition when a result it covers is published, corrected, moved to another reporting week, or withdrawn. Use the event's reporting week in Africa/Johannesburg. Late results belong in the original week. Update the existing issue URL and regenerate the HTML, PDF, `issue.json`, and the `feed.json` row together. Do not create a second edition for the same week.

Also reopen any card that still has `needs_external`, an empty `image`, or `enrichment` of `degraded`, and run the photo search again. The 2 November 2026 issue is in that state: the ILCA Masters story is already written from its results URL, and the card has no photo.

If a rebuild fails, keep the last good edition. A retry must not publish a duplicate.

## Grok Bot photo manifest

Grok Bot writes `/workspace/roundup-photos/MANIFEST.md` on its own box and adds rows on Mondays at about 08:00 SAST. `sailing-roundup.timer` checks that manifest on every run, not only on Mondays.

Sync it into `/opt/rea/work/sailing-roundup/external-photos/` when `ROUNDUP_PHOTOS_RSYNC` is set (an rsync source such as `user@grok-bot:/workspace/roundup-photos/`). Then run:

```text
python3 /opt/rea/work/sailing-roundup/external_photos.py --roundup-root /opt/rea/work/sailing-roundup
```

The script in this repo is `sailing-roundup/external_photos.py`. Copy it into the live job directory with the rest of that job. Each row has edition, event id, local file, image URL, source_url, caption, and credit. A row with a cell `EXCLUDED` is skipped.

For every event in every edition that still has `needs_external` or a null `hero_image`, a matching edition and event id:

- downloads the image URL when it returns an image, otherwise uses the synced file
- saves `issues/{edition}/media/{event-id}-hero.jpg` (or the real image extension)
- adds the hero image block and sets `event_verified` true, `category` `on-water`, and `verification` `reviewed_source_and_pixels`
- copies the first new lead photo into `feed.json` as `image`, `image_caption`, and `image_focus` when that card has no image
- sets `needs_external` false

Result tables, story paragraphs, and winner lines are not edited. Logos, flags, and profile pictures are rejected. An edition that fails to match a photo is left as it was.
