# Verified evidence fix — 19 October 2026

Scope: the existing standalone roundup only. No changes to SailingSA API, results data, navigation, database, nginx or global site styles.

## Corrected behavior
- Source labels no longer bypass event identity checks.
- Full article bodies, including Joomla articleBody, and complete cached public captions feed a verified source packet.
- Canonical URLs, platform post IDs and normalized content hashes collapse repeats/cross-shares.
- The 505 report published 13 October is retained as a delayed report only with matching class/year, venue and multiple competitor identities.
- Schools cannot become competitor names. Timothy Weaving and Hayden Miller are the under-17 champions; the NovaNews photo caption names them.
- Equal nett scores do not imply a particular tie-break mechanism. The 505 final-race explanation cites the actual class report.
- Six wins from eight is not called a clean sweep. Final-race claims are checked against the final race.
- Images must belong to an accepted source. Unverified seed-image fallback is disabled.
- The 505 collage is excluded: its photographed results sheet is labelled 2025.
- Article tables remain podium-only; full official API result snapshots are retained separately.
- Calendar-only events remain mentioned in the feature.
- Builds run in an isolated staging directory, reject missing scored events/sources/photos/PDF, and preserve the previous edition on failure.
- The existing run-monday.sh still targets the explicitly requested September reference weekend. It now invokes safe_publish.py and propagates publication failures.
- Browser layout is unchanged. Print-only image height prevents the 420 table becoming an orphan fifth page.

## Validation
Reference issue: 2026-09-28, covering 26–27 September.
Four regatta reports: 420, 505, Dabchick and Dart 18.
Two retained photographs; no substitute photo invented for the other two reports.
PDF: four A3 pages, rendered with Poppler and visually reviewed.
Final tests: 48 run, 47 passed, one optional live-photo-fixture test skipped.
Final full staged build passed with four reports and two photographs.

Run tests with the project virtualenv:
    python3 -m unittest discover -s gowifi/rea/sailing-roundup/tests

Build:
    python3 app/safe_publish.py --test-weekend

## Deployment status
Prepared and rebuilt through REA on GoWifi under:
    /opt/rea/work/sailing-roundup-fix/gowifi/rea/sailing-roundup

SailingSA live destination already exists at /opt/sailing-roundup and /var/www/sailingsa/sailing-roundup.
The user-requested audit URL is:
https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/

These fixes have NOT been installed at that URL from this session. The available rea-ro production account is read-only; root BatchMode SSH fails and the documented sailingsa_live_key is absent. Automatic approval review rejected a credential-document inspection that might expose password material. No credentials were printed and no read-only restriction was bypassed.

An authorized deployment must first snapshot the existing roundup app and published issue, then install only changed roundup files/requirements, preserve cached sources and the source registry, run safe_publish.py --test-weekend, publish only this issue, and compare the live HTML/JSON/PDF hashes with the validated build. Do not deploy api.py, global frontend files, nginx or other editions.

## Limitations
This is an independently implemented evidence workflow, not proprietary vendor code or access to licensed feeds. Caption caching can preserve an earlier successful public retrieval when a later fetch truncates it. Discovery remains dependent on public availability; inaccessible private posts are not treated as evidence.
