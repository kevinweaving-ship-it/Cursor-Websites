# OpenCode server (not purchased)

Evaluated as a GLM/MiniMax host with Mac/phone **browser** access. Keys would live on the server, so Cursor iPhone custom-key limits do not apply.

**Not live.** No GLM/MiniMax purchase this turn. Do not bind `0.0.0.0` on a public IP. Use Tailscale or an SSH tunnel, plus `OPENCODE_SERVER_PASSWORD`.

One default model in `opencode.json` — no `/models`. Stock OpenCode does not escalate by difficulty.

Separate projects: one working directory per `opencode web --port …` (or `--dir`). SSH/deploy: same `sailingsa/deploy/deploy-with-key.sh` if that checkout has the key. REA: `audit_*` only via the existing isolated box user, not `analyze_*`.

Cursor CLI on this Linux host still bills Cursor. That is not this path.
