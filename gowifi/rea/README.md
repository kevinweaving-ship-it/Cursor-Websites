# Isolated REA on the GoWifi box

[REA (Reverse Engineer Anything)](https://github.com/morluto/rea) is installed on **box.gowifi.co.za** (`102.209.119.186`) so Cursor can inspect **our own** application trees without using SailingSA live CPU or touching GoWifi production.

Official sources used for this install:

- [morluto/rea](https://github.com/morluto/rea)
- [docs/installation.md](https://github.com/morluto/rea/blob/main/docs/installation.md)
- [rea.tools/get-started](https://rea.tools/get-started/)
- npm package `rea-agents@6.4.0` (registry id `io.github.morluto/rea`)

## Isolation (do not break production)

| Item | Location / rule |
| --- | --- |
| OS user | `rea` — no password, no sudo, not in production groups |
| Prefix | `/opt/rea` only (Node 24.21.0 + `rea-agents` + samples) |
| CLI / MCP | `/opt/rea/bin/rea` → `/opt/rea/.local/bin/rea mcp` |
| Not used | `/opt/arial-whatsapp-poc/node`, Playwright’s Node, system Node |
| Never read/write | `/root/secrets`, `/root/gowifi-upp`, `/home/user-data`, `/opt/aerialnet-arial`, `/etc/nginx`, MariaDB |
| No new listeners | REA is stdio MCP only. No nginx, no systemd public service |
| Native engines | Hopper / Ghidra / IDA **not** installed |

Copy a target into `/opt/rea/work/…` (create as `rea`) before analysis. Do not point REA at live dash, Dolibarr, UniFi, Mail-in-a-Box, or secret files.

## What was verified on the box (2026-10-14)

- `rea --version` → **6.4.0**
- Isolated Node → **v24.21.0**
- `rea mcp doctor --json` → **healthy: true** (170/170 tools, 6/6 prompts, initialize + request-flow OK)
- Official `rea setup --client cursor --skill=false --yes` → wrote `/opt/rea/.cursor/mcp.json` only
- `rea doctor --client cursor --json` → Cursor registration **healthy**
- Sample JS analysis of `/opt/rea/samples/demo-app` recovered `greet` and `add`
- `rea` cannot read `/root/secrets` or `/root/gowifi-upp`, cannot write nginx / Aerialnet / MIAB web root
- nginx, Mail-in-a-Box, MariaDB, GoWifi APIs, and Aerialnet keypad APIs stayed **active**; no new listen ports

`rea doctor` without a client still reports `unsupported_host` for **Ubuntu 22.04** (official floor is 24.04+) and missing Hopper/Ghidra/IDA. That does **not** block JavaScript / .NET / web inspection. Native PE/ELF decompile needs a later Ghidra install under `/opt/rea` only, if we choose to add it.

## Connect Cursor (Mac / desktop)

REA’s MCP server is **stdio**. Cursor on your Mac launches it over SSH as the isolated `rea` user — not as root, and not via a public HTTP port.

1. Create a key on the Mac if you do not already have one:

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/rea_gowifi -N "" -C "cursor-rea@$(hostname)"
   ```

2. Install the **public** key on the box (existing root SSH). From this repo:

   ```bash
   REA_SSH_PUBKEY="$(cat ~/.ssh/rea_gowifi.pub)" \
     ssh root@box.gowifi.co.za "REA_SSH_PUBKEY='$REA_SSH_PUBKEY' bash -s" \
     < gowifi/rea/add-cursor-pubkey.sh
   ```

3. On the Mac Mini only, run [register-rea-gowifi-on-mac.sh](register-rea-gowifi-on-mac.sh). It merges `rea-gowifi` into `~/.cursor/mcp.json` and keeps every other server. Do **not** run `npx rea-agents setup --client cursor` on the Mac if you want this box — that would register a second, local REA. See [usefulness-trial.md](usefulness-trial.md).

4. Fully quit and restart Cursor. Confirm **rea** is connected under Settings → MCP.

5. Optional investigation skill (Mac only, no extra MCP):

   ```bash
   npx -y rea-agents@6.4.0 setup --skill-client cursor --yes
   ```

On-box registration (already applied, official shape):

```json
{
  "mcpServers": {
    "rea": {
      "command": "/opt/rea/.local/bin/rea",
      "args": ["mcp"]
    }
  }
}
```

## How Cursor should use REA across projects

Once the MCP server is connected, give Cursor an **absolute path on the box** and a specific question. Official starting prompt (from rea.tools):

> Look at `/absolute/path/to/app` and find how it exports data. Show the entry points, calls and dependencies involved, with the source locations for your findings.

### Workflow

1. Copy or rsync **our** unpacked app / asar / JS tree to `/opt/rea/work/<project>/` as user `rea`.
2. Ask Cursor to call REA tools rather than guessing from source alone.
3. Prefer these MCP tools first (no native engine required):
   - `analyze_javascript_application` — Electron / Node / web app graph
   - `recover_javascript_sources` — unpack / reconstruct JS
   - `trace_javascript_semantics` — follow a feature through modules
   - `compare_javascript_export_shapes` — compare two builds
   - `analyze_web_bundle` / `trace_web_module_imports` — bundled frontends
   - `inspect_managed_artifact` — .NET assemblies
4. Native binaries (`open_binary`, `analyze_function`, `procedure_pseudo_code`) need Ghidra/Hopper/IDA. Those are **not** on this box yet.
5. CLI equivalent (SSH as `rea`):

   ```bash
   ssh -i ~/.ssh/rea_gowifi rea@box.gowifi.co.za \
     /opt/rea/bin/rea analyze-javascript-application /opt/rea/work/PROJECT --json
   ```

### Project mapping (suggested drop folders)

| Project | Copy to (on the box) | Typical REA entry |
| --- | --- | --- |
| SailingSA frontend / Event URL JS | `/opt/rea/work/sailingsa/` | `analyze_javascript_application` |
| GoWifi dash (exported copy, not live `/home/user-data`) | `/opt/rea/work/gowifi-dash/` | `analyze_javascript_application` |
| Aerialnet keypad UI (exported copy) | `/opt/rea/work/aerialnet/` | `analyze_javascript_application` / `analyze_web_bundle` |
| Electron / asar we own | `/opt/rea/work/<name>/` or the `.asar` path | `analyze_javascript_application` |

Stay on copies. Live `/home/user-data/www`, `/opt/aerialnet-arial`, and `/root/gowifi-upp` are production.

## Reinstall / health

```bash
# on the box as root
bash /path/to/gowifi/rea/install-isolated-on-box.sh

# as user rea
/opt/rea/bin/rea --version
/opt/rea/bin/rea mcp doctor --json
/opt/rea/bin/rea doctor --client cursor --json
```

Do not pipe a random third-party installer. Official installer is only:

`https://raw.githubusercontent.com/morluto/rea/main/install.sh`
