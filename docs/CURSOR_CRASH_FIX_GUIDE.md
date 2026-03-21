# Cursor Extension Host Crash Fix Guide

Extension Host crash loop makes Cursor unusable (no IntelliSense, extensions fail). Based on community fixes and testing. **Try in order.**

---

## 1. Workspace Storage Reset (~70% success rate)

Corrupted workspace metadata is a common cause.

**On Mac:**
1. Quit Cursor fully (Cmd+Q; check Activity Monitor for any Cursor processes)
2. Open Finder → Go → Go to Folder (Cmd+Shift+G)
3. Paste: `~/Library/Application Support/Cursor/User/workspaceStorage`
4. Select all folders → Move to Trash (or delete permanently)
5. Restart Cursor

---

## 2. Launch from Terminal (shell workaround)

Bypasses GUI-related init issues; often fixes Extension Bisect and startup crashes.

1. Install shell command: Cursor menu → **Shell Command: Install 'cursor' command in PATH**
2. Close Cursor
3. In Terminal: `cd /Users/kevinweaving/Desktop/MyProjects_Local/Project\ 6`
4. Run: `cursor .`
5. Use this workflow instead of opening via Dock/GUI

---

## 3. Check for Process Conflicts

If you run Python scripts, `pkill -f python` can kill Cursor's extension host (it runs Node/Python).

- **Don't** blindly run `pkill -f python` while Cursor is open
- Check first: `pgrep -lf python` — if you see Cursor-related entries, avoid killing those

---

## 4. Project Size / File Watcher Overload

Large projects (10k+ files) can overwhelm Cursor's file watcher and trigger crashes.

**Your project:** Many backup folders, archives, and nested dirs — likely high file count.

**Actions:**
- Add `.cursorignore` / `.gitignore` for heavy dirs (e.g. `ARCHIVE_BACKUPS_*`, `BU_PROOF_*`, `BACKUP_*`, `node_modules`, `.cursor`)
- Open a **smaller subfolder** as the workspace (e.g. `sailingsa/` only) instead of the whole project root
- Consider: `find . -type f | wc -l` to see file count — aim to keep watched files under ~8–10k

---

## 5. Disable Extensions (diagnostic)

Test if extensions cause the crash:

- Launch: `cursor --disable-extensions` (from Terminal)
- Or: Cmd+Shift+P → **Developer: Reload with Extensions Disabled**

If it stops crashing, use **Help → Start Extension Bisect** to find the bad extension.

---

## 6. Update Cursor

Several users reported crashes fixed after updating, especially around 1.76.0.

- Cursor menu → **Check for Updates**
- Or: https://cursor.com/download

---

## Priority Order

| Order | Fix | Risk |
|-------|-----|------|
| 1 | Workspace storage reset | Low (you may lose workspace-specific state) |
| 2 | Launch from terminal | None |
| 3 | Reduce project scope / add ignores | Low |
| 4 | Disable extensions (test) | None |
| 5 | Update Cursor | Low |

---

## References

- [Extension Host Crashes in Cursor – Dre Dyson](https://dredyson.com/extension-host-crashes-in-cursor-i-compared-every-fix-to-find-the-real-solution/)
- [3 Proven Methods – Dre Dyson](https://dredyson.com/fix-extension-host-terminated-unexpectedly-in-cursor-ide-a-beginners-step-by-step-guide-3-proven-methods/)
- Cursor Forum: [Extension host crashing on large projects](https://forum.cursor.com/t/cursor-extension-host-crashing-on-large-projects/116603)
