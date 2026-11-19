# Grok review — workflow connection

Standalone developer tool. It is not part of the SailingSA application, the REA tools server, `/dev1/`, or Roundups.

## Audit before install

| Existing piece | What it already does | Grok |
| --- | --- | --- |
| ChatGPT + REA | ChatGPT uses tunnel channel `main` (`openai-rea-tunnel`). The mux exposes REA tools plus read-only `audit_*` and `ops_*`. | No xAI client, no `XAI_API_KEY`, no `api.x.ai` call. |
| `audit_*` | Read-only inspect: files, search, schema, SELECT, nginx, logs, deployment, live-vs-repo compare. | Not given to Grok. |
| `ops_git` diff | `git diff --stat` on an allowlisted checkout. Output is truncated to 4,000 characters. | Too small and too coarse to be the review body. Left unchanged. |
| GitHub | REA can HTTPS-clone this repo and `ls-remote`. Write still needs a human deploy key. Cursor can use local `git` / `gh` read access. | The adapter never receives a token, remote, or SSH key. |
| Cursor | This file lives in the Cursor-Websites checkout the agent already uses. | No earlier Grok review adapter in the repo. |

Nothing above was duplicated or rewired. `gowifi/rea/` and `api.py` are untouched, so the tunnel and the live API do not gain a Grok tool.

## How a review is prepared

1. Export a patch with the tools that already exist. Examples, run by a person on a local checkout:
   - `git diff --no-ext-diff -- path/to/file`
   - `gh pr diff <number>`
2. Save that patch somewhere that is not `/var/www`, `/opt/rea`, `/opt/rea-ops`, `/dev1/`, or a Roundups tree.
3. From this directory:

```text
python3 prepare_review_diff.py --input-file /path/to/saved.diff
```

Or, for a local checkout and an explicit path only:

```text
python3 prepare_review_diff.py --from-git --repo /path/to/Cursor-Websites -- path/to/file
```

`prepare_review_diff.py` refuses a whole-repo diff, refuses those production paths, redacts likely secrets, and rejects input over 80,000 bytes. It then runs `grok_review.py` without `--execute`.

Grok sees only that prepared file. It cannot commit, deploy, SSH, or call REA.

## Paid review

Do not pass `--execute` until an `XAI_API_KEY` is in the environment or a secret store and a person has approved one paid request. The key must not be committed or pasted into chat.
