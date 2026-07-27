# Cursor web dev & Cursor Browser (noted from Cursor Docs)

**Source:** Cursor Docs → Web Development guide. Use this when verifying or testing the frontend.

---

## Cursor Browser (built-in)

**Cursor Browser** is a built-in browser tool so Cursor can interact with the site directly: navigate pages, fill forms, click elements, inspect console logs, monitor network requests — without leaving Cursor.

**Use it when:** Verifying changes, debugging, or iterating on the web app (e.g. https://sailingsa.co.za or localhost).

**How:** Reference the browser in prompts, e.g.:

- "Open the app in the browser and check for console errors"
- "Navigate to the login page and test the form submission"
- "Take a screenshot of the current page"
- "Open https://sailingsa.co.za/class/62-optimist-a in the browser and confirm the boxes and layout"

**Details:** See Cursor’s **Browser** documentation (capabilities, security, advanced features).

---

## MCP pattern (from docs)

MCP servers go in **`mcp.json`** (global: `~/.cursor/mcp.json` or project: `.cursor/mcp.json`). Example pattern:

```json
{
  "mcpServers": {
    "Linear": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.linear.app/mcp"]
    },
    "Figma": {
      "url": "http://127.0.0.1:3845/sse"
    }
  }
}
```

Then enable the server from **Cursor Settings → Tools & MCP**.

---

## Web dev takeaways (from Cursor Docs)

- Tight feedback loops: use Cursor with Figma, Linear, and the **browser** to move quickly.
- MCP servers reduce context switching.
- Reuse components and design systems; reference them in rules (e.g. `.cursor/rules/*.mdc`).
- Clear, scoped tasks lead to better results.
- Extend context with runtime info: console logs, network requests, UI element data.
- Cursor as co-pilot, not autopilot.

---

## This project

- **Frontend:** `sailingsa/frontend/`; live: https://sailingsa.co.za
- **Verify:** Use Cursor Browser when asked to “check the site”, “verify deploy”, or “test the class page”.
- **Deploy:** See `sailingsa/deploy/SSH_LIVE.md`; D/R = backup + deploy-with-key.sh + API restart.
