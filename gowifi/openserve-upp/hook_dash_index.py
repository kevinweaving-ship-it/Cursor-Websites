#!/usr/bin/env python3
"""Idempotent hook: add Fibre accounts link/route to the existing GoWiFi dash."""
from pathlib import Path
import shutil
from datetime import datetime

INDEX = Path("/home/user-data/www/default/dash/index.html")
MARKER = "gowifi-fibre-accounts-hook"


def main() -> int:
    text = INDEX.read_text()
    if MARKER in text:
        print("already hooked")
        return 0
    bak = INDEX.with_name(f"index.html.bak-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(INDEX, bak)
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
        f"function accountsPage(){{ /* {MARKER} */\n"
        '  location.replace("/dash/accounts.html");\n'
        "}\n"
    )
    text = text.replace("let DATA=null;", hook + "let DATA=null;", 1)
    INDEX.write_text(text)
    print(f"hooked {INDEX} backup {bak}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
