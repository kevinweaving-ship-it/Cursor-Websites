# FORBIDDEN: deploy watchdogs / URL fight loops

**Hard ban for all Cursor agents (Cloud, Mac, Mobile).**

## What you have been doing wrong

When a live page “won’t stick” or “the old page keeps coming back”, it is usually **not** nginx being mysterious.

Agents previously “fixed” deploys by installing **permanent enforcers** on the server:

- systemd services with `Restart=always` (`*-url-hold`, `*-public-watch`, `*-ngx-restore`)
- cron every minute rewriting nginx
- `while true` bash loops spawning `lw-g*.py`
- `chattr +i` on scripts so they can’t be deleted
- a “gold” copy (e.g. `/usr/local/share/sailingsa-lipton/watch.py`) that **reinstalls** units + scripts after delete

One agent installs “keep public on API proxy”.  
Another installs “keep public on playback alias”.  
Both run forever. **That is the fight.** Old page vs new page forever.

That is **shit coding**. It wastes days. It is **forbidden**.

## Why you did it (and why it is wrong)

Agents invent watchdogs when:

1. A change flipped back once → agent thinks “I need a loop to enforce my version”
2. Two intents exist (`-dev` vs public) → agent “protects” one with a daemon
3. Multiple agents run at once → each installs its own enforcer
4. `chattr +i` is used to “lock” a bad decision in place

**Correct deploy:** copy file / patch nginx **once**, reload, verify. Stop.  
**Wrong deploy:** install a daemon that rewrites config every 15–60 seconds.

## Hard rules (do not break)

1. **Never** create/install systemd services, timers, cron jobs, or `while true` loops whose job is to rewrite nginx, HTML, or “hold” a URL.
2. **Never** create `force_*`, `*_watch`, `*_hold`, `*_restore`, `lw-g*`, `keep-*-playback` scripts for live pages.
3. **Never** use `chattr +i` on revert/enforce scripts. Only temporary lock of a **finished** config is allowed, and only after the user asked for that lock.
4. **Never** run two agents against the same live server URL at the same time.
5. If a deploy flips back: **find and delete the enforcer** — do **not** install a second enforcer that fights it.
6. When user intent changes (e.g. promote `-dev` → public): **remove** any prior enforcer for the old intent first, then deploy once.
7. Do **not** claim fixed until external check **and** a recheck after ≥60 seconds both show the new page.

## Allowed

- One-shot `cp`, nginx edit, `nginx -t && reload`
- One-shot backup tarball before change
- Disabling/removing **existing** bad watchdogs (cleanup only)

## Lipton example (2026-08-28)

Agents built `lipton_ngx_public_restore`, `lw-g17`…`lw-g22`, `sailingsa-lipton-*-watch/hold/restore` services, and gold `watch.py` that said “public MUST proxy to API; only -dev may alias”. When the user asked to promote `-dev` to public, those enforcers undid every fix. That pattern must never be repeated for any page.
