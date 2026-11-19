# Cursor — SailingSA historical results current handoff

Updated 19 November 2026. Kevin authorized historical result ingestion and server-side archive/task management. Shared API, frontend, routing and unrelated services stay outside this task.

## Actual working REA access
Do not diagnose SSH access from this cloud VM alone. Use the installed REA connector (rea-gowifi / rea-admin / ops-mcp) and the repository SSH/Mac runbooks.
Verified from REA on GoWifi:
- capture_process_scenario executable /opt/rea/ops/bin/rea-admin, arguments ["sailingsa","--","capabilities"]
- capture_process_scenario executable /usr/bin/ssh, arguments ["-o","BatchMode=yes","sailingsa-publish","ls /var/lib/sailingsa-results-backfill/"]
This invokes the authenticated on-box route, rather than requiring a key in the cloud pod.
Read AGENTS.md, docs/REA_CHATGPT_ACCESS.md, docs/DEVELOPMENT_TOOL_ROUTER.md, gowifi/rea/ops/CATALOG.md and sailingsa/deploy/SSH_LIVE.md.
The Mac Mini route and its key remain available through the existing Mac runbooks. Never copy keys into chat or the repository.
If the particular Cursor runtime does not expose REA/Mac controls, report the missing tool binding with exact evidence; do not equate that with absent server access.

## Archive is now populated with task records on SailingSA
Root /var/lib/sailingsa-results-backfill/
- incoming/SailingSA_historical_result_audit_newest_first.zip — original 1,645,373-byte audit bundle, SHA256 75f1427131e465d40cfc0cc784d667cbd0ebf3b876340de022fc8a83d6935e3b
- input/audit_724.csv — original 724 cases
- input/all_726_decisions.csv — 724 cases plus two carried-forward cases; do not count this as 726 missing events
- input/ — complete original ZIP contents, including comparisons and extracted PDF text
- tasks/archive.sqlite3 — 724 candidates, 1,272 unique audited source URLs and case/document relations
- tasks/<case>.json — per-case source, original audit evidence, proposed/existing URLs, IDs, issues, initial rating and download results
- tasks/priority-queue.json — highest rating first, newest event dates within rating
- sources/objects/<sha256>.<ext> — retained source bytes with checksum
- sources/named/ — source/date/event/rating/case filenames pointing to retained bytes
- reports/archive-summary.json — actual current counts, fetch errors and ratings
- logs/archive.log — bounded downloader progress
- archive_worker.py — archive/task worker; no site or results DB writes
- reports/CURSOR_NEW_SOURCES_20261119.md and tasks/additional-source-discovery-20261119.json — five further source families with nine retained index/sample documents

## Archive automation installed
/etc/cron.d/sailingsa-results-backfill-archive runs every five minutes under an exclusive flock, fetching at most 60 sources per batch.
Downloads have bounded time/size, SHA256 retention, resumable task state and three attempts before manual review.
The first verified batch saved 7 source documents and recorded 1 retry. Read current summary for live counts.
The job archives and prepares tasks. It does not automatically publish results.
Initial ratings are triage only: 4 cases rated 0, 197 rated 4, 395 rated 5, 128 rated 7. None has been marked publication-ready by this worker.
Scores reflect inherited evidence/metadata and must be replaced by actual parsing/validation readiness. Missing SAS match alone must not prevent ordinary results imports.

## Your work
Use the existing codebase and parser/publisher rules to process verified high-readiness cases, then descend through the queue. Recheck the database immediately before each write. Existing participants alone do not prove duplicate events.
Confirm edition, start/end dates, host, classes, fleets, parent-child scopes and source versions.
Retain original host scoring, scoring codes, discards, fractional values, totals, nett, ranks and checksum validation.
Resolve verified SAS IDs with canonical names and standard clickable profiles. Reuse corroborated Temp identities or create through existing workflows. Do not conflate unrelated people with incomplete names. Apply DF95 Globals RSA/ZAR verified SAS ID exception.
Store source category and actual source URL/name separately from event category and SAS sanction status.
Preserve existing stable URLs. Add missing parent/fleet/race scope through existing atomic ingestion workflows. Do not overwrite good existing results.
Rebuild affected original weekly editions with existing publisher in Africa/Johannesburg, retain last-good edition on failure and verify HTML/PDF/cards.
Install automatic publication only for cases that pass all existing gates. Record exact manual issues and continue other cases.
Report actual archived documents, audited cases, duplicates, missing event/fleet/race scopes, validated-ready cases, published results and manual cases.

## Previously published in this thread
2017 Hobie GP1 (TCC), 16–17 Sep 2017:
https://sailingsa.co.za/regatta/2017-09-16-tcc-hobie-gp1
event_id 276045, artifact_id 1481, 8 entries, 10 races, 2 discards, 7 SAS slots, 7 Temp slots. Source PDF on SailingSA /opt/rea-ops/stage/historical-results/be20c8d6dba5ed3ab7f94894087b757ab7795ec9f96401c1824ea50c0dc108b0.pdf.
Final/Provisional/as-at deliberately unspecified because absent in source. Public source label display remains unfinished; store provenance now and flag shared UI limitation rather than editing shared API.

Redhouse event 168679 /regatta/2026-10-31-ec-dinghy-regionals has 24 rows, artifact 1478, RYC host 103. 2 Nov roundup still lacks Redhouse results because scoped rebuild timed out before validated publication. Preserve the previous edition.
The daily SAS loader preservation fix for stable results_url survived the next import.

No shared API/frontend changes, existing URL rewrites or service restarts are authorized by the historical-results import task.

## Current continuation instruction — 19 November 2026
Run the ingestion task in Cursor on Kevin's Mac Mini local/Remote-SSH workspace with its existing SSH configuration, or in a runtime exposing the authenticated REA connector. A cloud pod lacking those bindings cannot gain them merely by pulling this file. Do not copy private keys, disable host checking, or broaden service privileges. Use existing Mac/SSH runbooks; do not repeatedly retry unauthenticated pod SSH.

Read the complete server handoff and parsing/scoring/identity runbooks before writes. Inspect current live task state; do not assume earlier counts mean validation or publication. Continue the 724 backlog and new-source registers, highest validated readiness then newest date, skipping blocked cases into a precise manual queue.

DATA-ONLY: use existing ingestion/result/profile/roundup workflows; no shared API/frontend/routing/service configuration changes, no URL rewrites, no service restarts. Scoped backups, atomic transactions, exclusive ingestion lock, source-version and duplicate guards, checkpoints, bounded retries, health checks before/after. Preserve source scoring and verify races/codes/discards/total/nett/rank/count. Verified SAS identities else established Temp workflow; RSA/ZAR DF95 Globals exception applies. Preserve parent/fleet scopes, stable URLs, confirmed host club metadata/logos, provenance and separate source origin from sanction status. Rebuild original affected reporting weeks (Africa/Johannesburg), preserving last-good editions on failure; verify results/profiles/HTML/PDF/cards publicly. A shared-code blocker holds that case only.

Additional discovery inputs on SailingSA:
- reports/GOOGLE_SOURCE_CLAIMS_CHECK_20261119.md
- tasks/google-source-leads-20261119.json
- tasks/further-source-discovery-20261119.json
- reports/FURTHER_SOURCE_DISCOVERY_20261119.md
All below /var/lib/sailingsa-results-backfill/. These are source leads, not a count of missing events. Validate against live data. FBYC handicap views and provisional/final snapshots must not become duplicate parent events. Official SAS 2015/2016 Youth PDFs remain SAS sources. Hunter archive needs exact event dates; ABYC 2014 Hobie summary lacks race-by-race scores, so do not fabricate them.

Report actual archived, audited, duplicates, published and manual counts separately. No blanket publication enablement before existing validation gates pass.
