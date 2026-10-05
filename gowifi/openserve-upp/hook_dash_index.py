#!/usr/bin/env python3
"""Idempotent hook: Fibre accounts + incoming fibre on the existing GoWiFi dash."""
from pathlib import Path
import os
import shutil
from datetime import datetime

INDEX = Path(os.environ.get("GOWIFI_DASH_INDEX", "/home/user-data/www/default/dash/index.html"))
ACCOUNTS_MARKER = "gowifi-fibre-accounts-hook"
INCOMING_MARKER = "gowifi-incoming-fibre-hook"

INCOMING_JS = f"""function paintIncomingFibre(sel, siteName){{ /* {INCOMING_MARKER} */
  const el=document.querySelector(sel);
  if(!el) return;
  fetch("/dash/accounts.json?v="+Date.now(),{{credentials:"same-origin",cache:"no-store"}})
    .then(r=>r.ok?r.json():null)
    .then(data=>{{
      const rows=(data&&data.incoming_fibre)||[];
      const want=(siteName||"").trim().toLowerCase();
      const list=rows.filter(r=>!want || (r.uisp_site||"").trim().toLowerCase()===want);
      if(!list.length){{ el.remove(); return; }}
      const items=list.map(r=>`<div class="item"><div class="row"><span class="name">${{r.incoming_label||r.incoming_role}}</span>${{pill(r.line_status)}}</div><div class="meta">${{r.service_number}} · ${{r.speed}} · ${{r.product}}${{r.cost!=null?` · cost ${{Number(r.cost).toFixed(2)}}`:""}}</div>${{r.address?`<div class="meta">${{r.address}}</div>`:""}}${{r.story_label?`<div class="meta">${{r.story_label}}</div>`:""}}</div>`).join("");
      const cost=list.reduce((s,r)=>s+Number(r.cost||0),0);
      el.outerHTML=`<a class="card tap" href="#/accounts" style="display:block;margin-bottom:10px">
        <div class="row"><span class="name">Incoming fibre · ${{list[0].uisp_site||"VK Pop"}}</span><span class="pill warn">not a client</span></div>
        <div class="meta">Cost of wireless · backhaul WiFi income has to cover${{cost?` · ${{cost.toFixed(2)}} / month`:""}}</div>
        <div class="list">${{items}}</div>
      </a>`;
    }}).catch(()=>{{ el.remove(); }});
}}
"""


def _backup(path: Path) -> None:
    bak = path.with_name(f"index.html.bak-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, bak)
    print(f"backup {bak}")


def _ensure_accounts(text: str) -> str:
    if ACCOUNTS_MARKER in text:
        return text
    text = text.replace(
        '<div class="sub">NMS sites + devices · audit</div>`;',
        '<div class="sub">NMS sites + devices · <a href="#/accounts" style="color:var(--acc)">fibre accounts</a></div>`;',
        1,
    )
    text = text.replace(
        "    <h2>Network health</h2>\n    <div class=\"grid\">",
        "    <a class=\"card tap\" href=\"#/accounts\" style=\"display:block;margin-bottom:10px\">\n"
        "      <div class=\"row\"><span class=\"name\">Fibre accounts</span><span class=\"pill ok\">audit</span></div>\n"
        "      <div class=\"meta\">Active Openserve lines · join dates · cancellations</div>\n"
        "    </a>\n"
        "    <h2>Network health</h2>\n    <div class=\"grid\">",
        1,
    )
    text = text.replace(
        "    if(!DATA) DATA=await load();\n    const h=hash();",
        "    const h=hash();\n"
        "    if(h===\"/accounts\"){ accountsPage(); return; }\n"
        "    if(!DATA) DATA=await load();",
        1,
    )
    hook = (
        f"function accountsPage(){{ /* {ACCOUNTS_MARKER} */\n"
        '  location.replace("/dash/accounts.html");\n'
        "}\n"
    )
    return text.replace("let DATA=null;", hook + "let DATA=null;", 1)


def _strip_block(text: str, start_needle: str) -> str:
    start = text.find(start_needle)
    if start < 0:
        return text
    end = text.find("\nfunction ", start + 1)
    if end < 0:
        end = text.find("\nlet DATA", start + 1)
    if end < 0:
        return text
    return text[:start] + text[end + 1 :]


def _ensure_incoming(text: str) -> str:
    text = _strip_block(text, "function paintIncomingFibre")
    if "function accountsPage" in text:
        text = text.replace("function accountsPage", INCOMING_JS + "function accountsPage", 1)
    else:
        text = text.replace("let DATA=null;", INCOMING_JS + "let DATA=null;", 1)

    if 'id="incoming-fibre-slot"' not in text:
        text = text.replace(
            "    <h2>Network health</h2>",
            '    <div id="incoming-fibre-slot"></div>\n    <h2>Network health</h2>',
            1,
        )
    home_end = "    }).join(\"\") : `<div class=\"meta\">None</div>`}</div>\n  `;"
    if 'paintIncomingFibre("#incoming-fibre-slot")' not in text and home_end in text:
        text = text.replace(home_end, home_end + '\n  paintIncomingFibre("#incoming-fibre-slot");', 1)

    if 'id="incoming-fibre-site-slot"' not in text:
        text = text.replace(
            "    <h2>Customers per sector</h2>",
            '    <div id="incoming-fibre-site-slot"></div>\n    <h2>Customers per sector</h2>',
            1,
        )
    site_end = (
        "      <div class=\"meta\">${ident(d).type} · ${ident(d).role} · ${ident(d).modelName}</div></div>`"
        ").join(\"\"):`<div class=\"meta\">None</div>`}</div>\n  `;"
    )
    if 'paintIncomingFibre("#incoming-fibre-site-slot"' not in text and site_end in text:
        text = text.replace(
            site_end,
            site_end + '\n  paintIncomingFibre("#incoming-fibre-site-slot", ident(s).name);',
            1,
        )
    return text


def main() -> int:
    text = INDEX.read_text()
    original = text
    text = _ensure_accounts(text)
    text = _ensure_incoming(text)
    if text == original:
        print("already hooked")
        return 0
    if INDEX.parent.exists() and str(INDEX).startswith("/home/user-data"):
        _backup(INDEX)
    INDEX.write_text(text)
    print(f"hooked {INDEX}")
    missing = [m for m in (ACCOUNTS_MARKER, INCOMING_MARKER) if m not in text]
    if missing:
        print("WARN missing", missing)
        return 1
    if 'id="incoming-fibre-slot"' not in text or 'id="incoming-fibre-site-slot"' not in text:
        print("WARN missing incoming slots")
        return 1
    if 'paintIncomingFibre("#incoming-fibre-slot")' not in text:
        print("WARN missing home paint")
        return 1
    if 'paintIncomingFibre("#incoming-fibre-site-slot"' not in text:
        print("WARN missing site paint")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
