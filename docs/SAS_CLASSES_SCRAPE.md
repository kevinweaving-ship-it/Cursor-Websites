# SAS classes: two-level scrape and class page data

## Overview

1. **Level 1 – SAS list**  
   Source: [sailing.org.za/what-we-do/sasclasses](https://www.sailing.org.za/what-we-do/sasclasses).  
   Stored in **`data/sas_classes_recognised.json`**: each class has name, category, URL (if any), email (if any), and `match_name` for mapping to our `classes.class_name`.

2. **Level 2 – Deep scrape**  
   For each class that has a **URL** on the SAS page, we fetch that URL and scrape useful content for class pages.  
   Script: **`sailingsa/scripts/scrape_sas_class_pages.py`**.  
   Output: **`data/sas_class_deep/<slug>.json`** per class.

## SAS categories (sas_recognition)

| Value | Label |
|-------|--------|
| `sports_pathway` | Sports Pathway Classes |
| `elective_premier` | Elective Premier Classes |
| `recreational` | Recreational Classes |
| `discipline_authority` | Sailing Discipline Authorities |

## Data stored

### From SAS page (in DB: `classes`)

- **sas_external_url** – Class association / SAS link (from SAS list).
- **sas_contact_email** – Contact email (from SAS list or from deep scrape).
- **sas_recognition** – One of the four categories above.
- **sas_deep_data** – JSONB: scraped content from the class URL (see below).

### From deep scrape (sas_deep_data JSONB and `data/sas_class_deep/*.json`)

Each deep-scrape file contains:

- **scraped_at** – ISO8601 UTC.
- **source_url** – Final URL fetched (after redirects).
- **sas_name**, **sas_category** – From SAS list.
- **title** – Page `<title>`.
- **description** – Meta description or og:description.
- **og_image** – og:image URL (if any).
- **body_excerpt** – First ~2000 chars of main content (main/article/body), stripped of scripts.
- **emails** – All mailto: + regex-found emails (deduplicated).
- **phones** – SA-style phone numbers found in text.
- **links** – Links whose href or text matches: event, result, contact, about, championship, regatta, calendar, news, class, sail, race, fixture (up to 30).

This data is intended for use on our class pages (e.g. “Class association”, “Contact”, “Events”, description).

## How to run the deep scrape

From project root:

```bash
python3 sailingsa/scripts/scrape_sas_class_pages.py
```

- Reads **`data/sas_classes_recognised.json`**.
- For each entry with a `url`, GETs that URL and parses HTML.
- Writes **`data/sas_class_deep/<slug>.json`** (slug from class name).

No DB updates in this script; use a separate step (or script) to map `match_name` → `classes.class_id` and set `sas_external_url`, `sas_contact_email`, `sas_recognition`, `sas_deep_data` from the JSON files and SAS list.

## Matching SAS classes to our `classes` table

- **sas_classes_recognised.json** has a **match_name** per entry (e.g. `"29er"`, `"Optimist A"`, `"Dabchick"`). Match to **classes.class_name** (case-sensitive or normalised per your rules).
- Classes that appear in our DB but have **no** row in the SAS list (and no `match_name` match) are “not on SAS list” – less recognised / lower priority for SAS-linked content.
- To list **classes in our DB not on SAS list**: query `classes` where `sas_recognition IS NULL` (after you’ve backfilled SAS data), or compare `classes.class_name` to the set of `match_name` values in **sas_classes_recognised.json**.

## DB migration

Run once:

```bash
psql $DATABASE_URL -f database/migrations/169_classes_sas_recognition.sql
```

Then backfill from **sas_classes_recognised.json** and **data/sas_class_deep/*.json** (manual UPDATEs or a small script that joins on `match_name` → `class_name` and sets the four columns).

## Class page usage

- Show **SAS recognition**: e.g. “Recognised by SA Sailing: Sports Pathway Classes” with a link to the SAS page or class URL.
- Show **Class association link**: use `sas_external_url` (and optional `sas_deep_data.title` or `sas_deep_data.description`).
- Show **Contact**: `sas_contact_email` and, if present, extra emails from `sas_deep_data.emails` or `sas_deep_data.phones`.
- Show **Useful links**: from `sas_deep_data.links` (events, results, contact, etc.).
- Optional: short blurb from `sas_deep_data.body_excerpt` or `sas_deep_data.description`.

API **GET /api/class/{class_id}** should return these fields so the frontend can render them without extra requests.
