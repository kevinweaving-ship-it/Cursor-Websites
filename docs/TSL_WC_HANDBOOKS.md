# TSL handbooks — box search (2026-10-12)

Jacques Smit sent these on WhatsApp (MAC C…). Kevin asked: find them on the box and study them.

| File (from the chat) | Pages | Size |
| --- | --- | --- |
| `20260210 SA Sailing Team Sailing Developmental Program with Regi…` | 8 | ~3.8 MB |
| `SASS-2022-tsl-lev1_organiser-handbook_v1-PL.docx.pdf` | 17 | ~3.0 MB |
| `SASS-2022-tsl-lev1_sailor-handbook_v1-PL.docx.pdf` | 16 | ~3.0 MB |
| `SASS-2022-tsl-lev1_sailor-tactics-quick-ref_v1-PL.docx.pdf` | 7 | ~1.5 MB |
| `SASS-2022-tsl-lev1_instructor-guide_v1-…` | 33 | ~5.1 MB |

Chat note: “These are all in email? If so → those loaded into development stack already for reading.”

---

## Result: **not on the box**

Searched live (`102.218.215.253`):

- `/var/www/sailingsa` (docs, data/reference, js, media, results)
- `/var/www/timadvisor` including `sailing-2026` (“development stack”) — no PDFs
- `/opt/arial-whatsapp-poc` — Box WhatsApp media is **545 jpg + 123 mp4 + 2 mp3**, **0 pdf/docx**
- Box groups.json (this moment): HMYC media, GoWifi Tech 2022, Southern Charter Cape Classic 2026, MIDMAR CUP. **No Jacques Smit chat. No MAC Media.**
- `/root`, `/root/incoming`, `/home`, `/opt/cursor`, `/tmp`

No file named `*organiser-handbook*`, `*sailor-handbook*`, `*sailor-tactics*`, `*instructor-guide*`, `*SASS-2022-tsl*`, or `*Developmental*Program*`.

So the booklets were **not** ingested. They sat on Kevin’s phone / email, not on Box WhatsApp (076 263 9937) and not under timadvisor.

**Do not invent** organiser / sailor / instructor / reporting rules from these titles.

To study them: drop the five PDFs onto the box (e.g. `/var/www/sailingsa/data/tsl/`) or add Box to that WhatsApp chat and re-run the group fetch.

---

## What we can use now (public SAS TSL page)

https://www.sailing.org.za/what-we-do/tsl — not a substitute for the handbooks.

- TSL is team racing: two teams of **up to three** two-person boats, equally matched.
- Boat on that page is the **TSL14** (Performance Craft / North Sails). This Event URL NOR says **TSL 410**. Do not rename the class until OA confirms.
- Regions: WC, KZN, Northern. Each operator was to get **seven boats** (two teams of three + spare).
- **WC contact on SAS:** Milnerton Aquatic Club — Michael Kavanagh 083 303 2863.
- Pillars: inter-club (about monthly), inter-schools (14–24, bi-weekly), corporate, women’s TSL / gender balance.
- Goal: novices + experienced, no boat ownership required, transformation / base-building.

This matches the locked WC answers (regional league, 3v3, SAS boats rotated). It does **not** give the post-event SAS report booklet, tie-break math, or instructor syllabus.

---

## Already on the Event URL

- NOR / SI + indemnity: `/js/mac-tsl-nor.html` and `/js/2026-10-17-mac-tsl-wc-nor.docx`
- WC answers: `docs/TSL_WC_STRUCTURE.md`
