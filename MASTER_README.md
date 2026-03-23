# SailingSA — Master README

Single entry point for **roles**, **chat discipline**, **rules**, **enforcement**, **core enforced rules (Git + backup + deploy/rollback)**, **bans**, and **controlled build tasks**.  
Detail lives in linked docs; this file is the contract — **not** optional guidance for Git, backup, or rollback.

---

## 1. Roles

| Role | Responsibility |
|------|------------------|
| **Kevin** | Product owner, approvals, live impact, commits, deploy triggers, and explicit “apply” for repo/production changes. |
| **ChatGPT** | Advisory only unless Kevin runs or pastes output; no direct repo or server access. |
| **Cursor (agent)** | Implements tasks in-repo; runs read/diagnostic commands freely; **asks before applying** edits, deploy, or commits unless Kevin already requested that change. Follows this README and linked rules. |

**Run vs apply:** Agents may **run** commands (diagnostics, SSH read-only, `git status`, builds/tests when asked). They must **confirm with Kevin** before **applying** edits, deploying, or committing. See `.cursor/rules/run-vs-apply.mdc`.

---

## 2. Chat discipline rules (NON-NEGOTIABLE)

How assistants and tooling communicate with **Kevin**. **Mandatory** for ChatGPT-in-chat and for any handoff to Cursor.

- **Max 3 lines to Kevin** — default reply length; no preambles, no sign-off filler.
- **No chatter / no explanations unless asked** — do not narrate process, justify choices, or teach unless Kevin requests detail.
- **Only ONE `For Cursor:` block when needed** — if instructions must go to Cursor, put them in a **single** fenced or clearly delimited block; do not scatter duplicate directives.
- **No code outside Cursor block** — do not paste implementation code in the general reply; code belongs only inside the `For Cursor:` block (or Kevin’s editor), never as casual inline examples unless Kevin asked for a snippet.
- **Never break rules A, B, 1–6 under any condition** — theme/layout (Rule A), design system (Rule B), and hard UI rules 1–6 in **`docs/UI_COMPONENTS_README.md`**; no exceptions for speed or convenience.
- **If uncertain → STOP and ask Kevin** — do not guess, defer, or “pick a sensible default”; one short question, then wait.

---

## 3. Rules A & B (foundation)

### Rule A — Theme & layout (mandatory)

- All pages use the SailingSA layout: **global header** + **main** content.
- **Header (`.site-header`):** Dark background `#001f3f`. **All links in the header and mobile overlay must stay white** (readable on dark). Enforced in CSS: `.site-header a`, `.nav-menu-overlay a` (see `sailingsa/frontend/css/main.css`).
- **Locked master template:** Regatta, Sailor, Class, Club pages use **`buildMasterPageLayout(container, opts)`** in `index.html` / `public/index.html`. **Do not** change the order: Back → Title card → Stats card → Data cards; **do not** remove `.table-container` from the master pattern.
- **Class page section order:** HEADER → CLASS HERO → REGATTAS → CLUBS SAILING THIS CLASS → SAILORS.
- **Page background:** Same as landing; **no** dark page backgrounds outside the global header; **cards are white**.
- **Mobile-first:** Base styles for mobile; breakpoints for larger screens; **min 44px** touch targets for buttons and table headers.
- **URLs:** Follow `docs/URL_STANDARD_ALL_PAGES.md` and `.cursor/rules/url-canonical-and-redirects.mdc` (canonical `https://sailingsa.co.za`, no `www`, HTTPS, sensible slug encoding).

Full text: `.cursor/rules/theme-layout-mandatory.mdc`.

### Rule B — Design system & components

- **No new CSS frameworks** and **no ad-hoc global styles.** Use **`docs/design_system.md`** and **`sailingsa/frontend/css/main.css`** only.
- **Reuse components:** `.container`, `.card`, `.table`, `.table-container`, `.section-title`, `.section`, `.tabs`.
- **Allowed classes** (page chrome): `container`, `card`, `table`, `tabs`, `section`.
- **Footer:** Do not change footer structure without explicit approval.

Full text: `.cursor/rules/design-system-and-components.mdc`, `docs/UI_COMPONENTS_README.md`.

---

## 4. Rules 1–6 (hard UI rules)

From **`docs/UI_COMPONENTS_README.md`** — do not break pages:

1. **Never modify the header or navigation layout.** Header lives in `sailingsa/frontend/index.html` and `public/index.html` (and aligned copies, e.g. About). Nav items and mobile menu structure stay as-is; links stay **white** on `#001f3f`.
2. **Never modify the footer structure** without explicit approval.
3. **Always reuse existing components and classes** (see Rule B). Use **`buildMasterPageLayout`** for Regatta, Sailor, Class, Club — do not replace with a different layout system.
4. **Do not invent new CSS frameworks or new global styles.** Follow the design system and `main.css`.
5. **UI changes only in components or page sections** — not global layout. No extra wrappers that break the master order; no standalone pages that bypass the theme layout.
6. **Allowed classes** (theme): `container`, `card`, `table`, `tabs`, `section`. **Forbidden:** raw `<ol>`/`<ul>` for results, inline CSS, custom page-level fonts or colours.

---

## 5. Enforcement plan (locks, zones, `/app`)

### 5.1 Locked files (header + index)

| Lock | Files / scope |
|------|----------------|
| **Header & global nav** | **`sailingsa/frontend/index.html`** — the `<header class="site-header">` block through `</header>` (including overlay nav). |
| **SPA shell** | **`sailingsa/frontend/index.html`** — single bootstrap for the app (base, script order, `buildMasterPageLayout` contract). |
| **Deployed index** | **`/var/www/sailingsa/index.html`** must match deploy output; **`api.py`** uses `STATIC_DIR` / `_INDEX_HTML_PATH` for the same file. |
| **Mirror** | **`sailingsa/frontend/public/index.html`** — treat as **duplicate** of the root SPA: no independent product divergences until consolidation. |
| **Header parity** | **`about.html`** (header block); **header strings** in **`api.py`** for server-rendered pages (`/stats`, `/events`, …) must stay aligned with the canonical header rules. |

### 5.2 Allowed edit zones

- **`index.html`:** Inside **`<main class="main-content">`** — views, cards, tables, search, profile panels; data passed into `buildMasterPageLayout` only as allowed opts.
- **JS:** `sailingsa/frontend/js/` and inline scripts that power the SPA — logic and table builders, not replacing the master template.
- **CSS:** `sailingsa/frontend/css/main.css` — design-system-aligned; no new layout that replaces `.site-header` / `.main-content`.
- **Standalone pages:** `about.html` body, `login.html`, `facebook-confirm.html`, `site-stats.html`, `regatta/**/*.html` — content and below-header markup; iframe internals.
- **`api.py`:** Body HTML for directory/stats/events pages — not a second divergent nav spec.

### 5.3 `/app` (new system only)

- **Purpose:** All **new** application modules after consolidation live under a **single tree** so the codebase does not sprawl.
- **Source root (when created):** **`sailingsa/frontend/app/`** — new features, modules, optional future bundler inputs.
- **Integration:** **`index.html` remains the only shell** (header + main). Code under `app/` **imports into** or **bundles into** the existing SPA — no second competing `index.html` product.
- **URL prefix:** If public routes become **`/app/...`**, implement them only from this tree and one routing story (document in deploy notes).
- **Deploy:** **`bash sailingsa/deploy/deploy-with-key.sh`** stays the supported path to `/var/www/sailingsa/` unless explicitly superseded.

---

## 6. Core enforced rules — Git, backup, deploy & rollback

**These rules are mandatory.** They sit alongside **§8 Absolute bans** as non-negotiable project law. Treating them as optional notes is a process failure.

### 6.1 Key lock (why this exists)

Together, the rules below achieve:

| Lock | Meaning |
|------|--------|
| **Git = source of truth** | Committed history and the repo define what the software **is**. Live is an **artifact** of repo + deploy — never the canonical copy of logic or assets. |
| **Backup = mandatory before ANY change** | Uncommitted work and files without rollback copies can be lost in seconds. **Every** substantive edit session assumes a recoverable state **before** the first line changes. |
| **Deploy tied to rollback** | No deploy overwrites production **without** a pre-deploy snapshot and a known restore path. |

This removes the **“lose weeks of work”** risk: work lives in **git + dated backups + pre-deploy archives**, not only in a single working tree or one server directory.

### 6.2 Git (enforced)

- **Repo = single source of truth.** Application code, frontend, and deployable assets are defined by **git commits**. **Live** must be reproducible from **repo + documented deploy steps** — not edited into shape only on the server.
- **Commit before change.** **MUST** start from a **known committed baseline** (or explicit stash with a recorded message) **before** beginning new work. No long-lived uncommitted multi-file edits without checkpoints.
- **One change = one commit.** **MUST** keep each commit to a **single logical change** with a **clear message** (what and why). No mixing unrelated features, drive-by refactors, and bugfixes in one commit.
- **No direct production edits without repo first.** **MUST NOT** treat **`/var/www/sailingsa`** (or other production paths) as the primary place to fix behaviour. **Change the repo → commit → deploy.** If an emergency edit is made on the server, it **MUST** be back-ported and committed **immediately**.
- **Before every commit:** Run **`git status`** and **`git diff`** (or **`git diff --staged`**) so what is committed is visible and reversible. Use **`bash sailingsa/deploy/backup-before-commit.sh`** before commits per **`.cursor/rules/git-before-commit-rollback.mdc`** (copies modified files to **`backups/pre_commit_*/`**).

### 6.3 Backup (enforced)

- **Before ANY file edit:** **MUST** create a **`.bak_YYYYMMDD`** copy of each file about to change (e.g. `index.html.bak_20260321` beside the original, or equivalent path containing **`.bak_YYYYMMDD`**). This is **in addition to** git — instant single-file rollback.
- **Daily full project backup:** **MUST** maintain a **daily** full backup of the project — **local** (archive of repo/workspace) and **server** (snapshot of **`/var/www/sailingsa`** and, per your ops routine, DB/config). Gaps in the backup chain are **not** acceptable for production work.
- **Pre-deploy backup:** **MUST** create a **zip or tarball of the current live** **`/var/www/sailingsa`** on the server **before** any deploy that overwrites that tree. Name with date/time (e.g. `sailingsa_predeploy_YYYYMMDD_HHMM.zip`).
- **Rollback rule:** **MUST NOT** overwrite production files, databases, or nginx config **without** a retrievable previous copy (pre-deploy archive, git tag, or documented restore procedure). **Never** deploy on the assumption that “we can fix it live.”

### 6.4 Deploy tied to rollback

- **Deploy** is only allowed when **§6.2–6.3** are satisfied for that change set (committed, reviewed, pre-deploy live snapshot taken where deploy touches **`/var/www/sailingsa`**).
- **`sailingsa/deploy/SSH_LIVE.md`** is the authoritative runbook for commands, paths, and verification.
- **Production URL:** **`https://sailingsa.co.za`** — local changes do not affect users until deploy completes successfully.

---

## 7. Deploy + SSH (operations)

**Primary reference:** **`sailingsa/deploy/SSH_LIVE.md`** — always use it; do not guess paths.

| Item | Value / command |
|------|------------------|
| **Server** | `102.218.215.253`, user `root` |
| **SSH key** | `~/.ssh/sailingsa_live_key` (preferred) |
| **Web root** | `/var/www/sailingsa` |
| **Frontend deploy** | `bash sailingsa/deploy/deploy-with-key.sh` (from project root) |
| **API deploy** | `scp api.py … /root/incoming/api.py` then `/root/deploy_api_verified.sh` on server (see SSH_LIVE.md) |
| **After API/frontend/CSS affecting live** | Restart/verify **`sailingsa-api`**; audit per SSH_LIVE / `auto-dr` where applicable |
| **Regatta 385 sync** | `bash sailingsa/deploy/sync-385-local-to-live.sh` when required |
| **Canonical site** | `https://sailingsa.co.za` — Rule A / URL rules |

**Mandatory link:** Every deploy that overwrites live satisfies **§6.3** (pre-deploy archive) and **§6.4**.

---

## 8. Absolute bans list

Do **not**:

- Change **header or navigation layout** (structure, link set, order) without owner approval and update of all parity copies.
- Put **non-white** link colours on **`.site-header`** / **`.nav-menu-overlay`** (breaks readability on `#001f3f`).
- Introduce **new global layout** or **replace `buildMasterPageLayout`** for Sailor/Class/Club/Regatta with a different DOM structure.
- Add **extra wrappers** or **reorder** Back / Title / Stats / Data cards in the master template.
- Use **raw `<ol>`/`<ul>` for results**; **inline CSS**; **custom page-level fonts or colours** outside the design system.
- Add **standalone HTML** that bypasses the theme layout for public site pages.
- Invent **new CSS frameworks** or duplicate **theme** in unrelated global stylesheets.
- Link user-facing or crawlable content to **`http://`**, **`www.sailingsa.co.za`**, or **`/index.html`** as the canonical home (use **`https://sailingsa.co.za`** and **`/`**).
- **Deploy** or **commit** without following **§6 Core enforced rules** (Git, backup, rollback) when the agent is performing commits or deploys.
- **Silently overwrite** live server state, baseline restores, or secrets — see SSH_LIVE.md; **never overwrite without rollback copy** (**§6.3–6.4**).

---

## 9. First controlled build task (`/app`, zero touch live)

**Goal:** Prove the **`sailingsa/frontend/app/`** pipeline with **no impact** on **https://sailingsa.co.za** until Kevin explicitly promotes it.

| Constraint | Rule |
|------------|------|
| **Scope** | Add **`sailingsa/frontend/app/`** (create directory) with a **minimal landing** — one route or one static module (e.g. “App shell placeholder” or read-only status page) **only** under the `/app` integration rules in **§5.3**. |
| **Zero touch live** | **No** `deploy-with-key.sh`, **no** nginx change, **no** public DNS/route to new code on production for this task. Work stays **local** and/or **feature branch** until a separate “go-live” step. |
| **Header / index** | **Do not** change locked header or **`index.html`** shell for this task except **optional** non-breaking import of a bundle from `app/` if required — prefer **isolated files** only under `app/` until integration is reviewed. |
| **Done when** | Directory exists, landing builds or loads locally, documented **one-line** “how to run”, and merge is **commit + backup rules** compliant — **not** when live updates. |

This task validates **controlled delivery** before any `/app` URL is exposed on production.

---

## 10. Where to read more

| Topic | File |
|-------|------|
| UI hard rules & components | `docs/UI_COMPONENTS_README.md` |
| Design tokens & patterns | `docs/design_system.md` |
| Theme layout (full) | `.cursor/rules/theme-layout-mandatory.mdc` |
| Canonical URLs | `.cursor/rules/url-canonical-and-redirects.mdc` |
| Deploy & SSH (authoritative) | `sailingsa/deploy/SSH_LIVE.md` |
| Git / backup before commit | `.cursor/rules/git-before-commit-rollback.mdc`, `sailingsa/deploy/backup-before-commit.sh` |
| Agents & splitting work | `AGENTS.md` |
| Cursor workspace rules | `.cursorrules`, `.cursor/rules/*.mdc` |

---

**§6 (Git, backup, deploy & rollback)** and **§8 (Absolute bans)** are **enforced** project rules. Other sections reference them; they are not weaker “notes.”

*If this README conflicts with a task-specific doc, resolve after **Kevin confirms** — except **§6–6.4** and **§8** remain binding unless explicitly revised here.*
