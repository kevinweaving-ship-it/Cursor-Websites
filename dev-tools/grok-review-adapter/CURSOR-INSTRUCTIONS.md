# Cursor Bot — ONE-TIME SAFE GROK REVIEW SETUP

Implement the supplied `grok-review-adapter/` **as a standalone development-only tool**, NOT inside the SailingSA application, Roundup pipeline or production server.

1. Audit existing ChatGPT/REA/GitHub/Cursor tooling and report any existing Grok/xAI integrations. Do not duplicate a working integration.
2. Place the adapter in a separate local developer-tools directory. Do not deploy to `/var/www/sailingsa`, import it in `api.py`, or expose a web endpoint.
3. Run `python3 -m unittest discover -s tests -v`, then test `python3 grok_review.py --input-file <a locally created harmless test diff>`. Confirm dry run makes ZERO API requests.
4. Do **not** request, paste or store an API key in the repository or chat. When an xAI key is available in a secure secret store/environment, verify that `XAI_API_KEY` exists **without printing its value**. Do not make a paid request without user approval.
5. Connect the existing GitHub diff/audit workflow to this optional reviewer by passing only pre-screened diffs of at most 80 KB. The reviewer is read-only and cannot commit, deploy, SSH, modify production or authorize actions.
6. On the first explicitly approved paid call, verify model availability and costs and review a harmless test diff. Report API success/failure, request cost or token usage if available, and any mismatch against the original diff.
7. Final report: files installed, tests passed/failed, dry-run proof, credentials present yes/no (never reveal), paid call executed yes/no, GitHub/REA workflows affected, and exact remaining blockers.

STRICT: no application UI changes, no production or Roundup feed changes, no extra JS/CSS patches. Do not silently run expensive requests.
