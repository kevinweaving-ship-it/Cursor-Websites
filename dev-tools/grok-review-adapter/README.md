# Grok reviewer — isolated adapter

**Status:** implemented and offline-tested. **Not connected/billable** until an xAI API key is configured and `--execute` is explicitly supplied. No changes to SailingSA production or to the REA tools server.

## Architecture

GitHub / REA (existing, read access) → human-checked, bounded code diff → local Python adapter → xAI Responses API → independent review → ChatGPT / Cursor / REA verify findings → **normal audited change workflow**.

Grok receives only the content of the file passed in, not a GitHub credential, repository token, SSH session, or production access. The adapter cannot push commits, change files, or call execution tools. By default it makes **no network request**. One paid request requires both `XAI_API_KEY` and `--execute`. It uses `store: false` and limits model output to 1,200 tokens. Input is capped at 80 KB with best-effort secret redaction; **do not upload private configurations, customer data, or secrets**.

## Offline verification

`python3 -m unittest discover -s tests -v`

## Dry run

`python3 grok_review.py --input-file /path/to/review-safe-diff.txt`

## Enable paid model review when explicitly approved

1. Get an xAI API key at https://console.x.ai (separate from SuperGrok subscription).
2. Store it in your local secret manager / environment as `XAI_API_KEY`, **not in Git or application code**.
3. `python3 grok_review.py --input-file /path/to/review-safe-diff.txt --execute`

Model defaults to `grok-build-0.1`; override with `--model` only after checking current xAI model availability and pricing. Requests use `https://api.x.ai/v1/responses` and standard-library HTTPS, without external Python dependencies.

## Cursor / REA integration boundaries

Keep this as a **developer-side utility only**. Do not add it to SailingSA's FastAPI production process, `/dev1/`, user search, or Roundup publication. Do not install an MCP server on production or grant Grok GitHub write access. Cursor may invoke the tool locally on a curated diff, collect the review, and verify findings against source and tests before proposing changes.

## This checkout

Installed at `dev-tools/grok-review-adapter/` in the Cursor-Websites workflow repo. `api.py` does not import it. The SailingSA frontend zip is built from `sailingsa/frontend/` only, so this directory is not part of that deploy. The REA mux under `gowifi/rea/` is unchanged.

Prepare a bounded diff and dry-run (no API call):

```text
python3 prepare_review_diff.py --input-file tests/example-safe-diff.txt
```

`prepare_review_diff.py` accepts a patch already saved from `git diff` or `gh pr diff`, or a read-only `git diff` of explicit paths. See `INTEGRATION.md`.

## Limitations

- Not a native ChatGPT plugin or a directly callable REA MCP tool. This package is an isolated adapter that the existing tool workflow can run after setup.
- No API call or model-quality validation was possible without the key; offline unit tests use a fake HTTP response.
- Does not automatically fetch repository contents (deliberately); use the **existing** GitHub and REA tools and pass only the code you intend to share externally.
- Secret redaction is heuristic, not a data-loss prevention guarantee.
