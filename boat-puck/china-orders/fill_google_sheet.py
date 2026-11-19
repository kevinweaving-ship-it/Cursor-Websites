#!/usr/bin/env python3
"""Paste Moko / Dragino order blocks into the China Order Google Sheet."""

from playwright.sync_api import sync_playwright

SHEET = (
    "https://docs.google.com/spreadsheets/d/"
    "1vUaJjcAtC8SZOwNTbnv1Sj9A6j5VCQZ9z1zRMHDw7Tk/edit?gid=2065625820#gid=2065625820"
)
RAW = (
    "https://cdn.jsdelivr.net/gh/kevinweaving-ship-it/Cursor-Websites@"
    "d05dc31/boat-puck/china-orders/images"
)
SHOP = {
    "wsc2": "https://cdn.shopify.com/s/files/1/0724/0489/4032/files/dragino-wsc2-l-lorawan-main-process-unit-eu868-386231_2048x2048_d137778b-44ae-44ec-8583-c0406a53fa54.webp?v=1749033453",
    "se01": "https://cdn.shopify.com/s/files/1/0724/0489/4032/files/dragino-se01-lb-lorawan-soil-moisture-ec-sensor-eu868-872970_2048x2048_d4337f19-4386-4154-a613-8411d86194db.webp?v=1749029394",
    "sph01": "https://cdn.shopify.com/s/files/1/0724/0489/4032/files/dragino-sph01-lb-lorawan-soil-ph-sensor-eu868-252684_2048x2048_b877404e-642e-40ac-9563-9fe866886029.webp?v=1749033800",
    "s31b": "https://cdn.shopify.com/s/files/1/0724/0489/4032/files/dragino-lsn50v2-s31b-lorawan-outdoor-temperature-humidity-integrated-sensor-eu868-388500_2048x2048_b4dc242e-4654-42fe-b50c-4147dba6ac3b.webp?v=1749556327",
    "lt": "https://cdn.shopify.com/s/files/1/0724/0489/4032/files/dragino-lt-22222-l-lorawan-io-controller-eu868-remote-control-monitoring-for-industrial-systems-726789_2048x2048_0bd94da1-86fe-4282-9e45-0fbc7d41f006.webp?v=1749557076",
    "la66": "https://cdn.shopify.com/s/files/1/0724/0489/4032/files/dragino-la66-lorawan-module-eu868-compact-versatile-wireless-connectivity-for-iot-projects-330473_2048x2048_9cdd8f16-3b90-4e05-8c6f-46e48b30ab76.webp?v=1749556745",
}


def img(url: str) -> str:
    return f'=IMAGE("{url}")'


HDR = "Use\tSKU\tDescription\tQty\tBand\tProduct URL\tImage\tStatus\tNotes"

MOKO_ROWS = [
    HDR,
    "Dev\tLW014\tWearable / wrist panic button\t20\tEU868\thttps://store.mokosmart.com/product/lw014-lorawan-wearable-button/\t"
    + img(f"{RAW}/lw014.png")
    + "\tSEND PI\tRichard 10 Sep — qty 20",
    "Dev\tLW013\tSmart button\t10\tEU868\thttps://www.mokosmart.com/lw013-sb-lorawan-smart-button/\t\tSEND PI\tMinimum 10",
    "Dev\tLW006\tSmart badge\t4\tEU868\thttps://store.mokosmart.com/product/lw006-sb-lorawan-smart-badge/\t"
    + img(f"{RAW}/lw006.png")
    + "\tSEND PI\tDev list",
    "Farm\t—\tnone on this order\t\t\t\t\t\tMoko is personnel / Dev kit",
]

DRAGINO_ROWS = [
    HDR,
    "Farm\tWSC2-L kit\tLoRaWAN weather station kit\t1\tEU868\thttps://www.dragino.com/products/agriculture-weather-station/item/339-wsc2-l.html\t"
    + img(SHOP["wsc2"])
    + "\tSEND PI\tAsk for working kit / sensors",
    "Farm\tSE01-LB\tSoil moisture & EC\t1\tEU868\thttps://www.dragino.com/products/agriculture-weather-station/item/277-se01-lb-ls.html\t"
    + img(SHOP["se01"])
    + "\tSEND PI\tRichard SE01 / SE OX",
    "Farm\tSPH01-LB\tSoil pH\t1\tEU868\thttps://www.dragino.com/products/agriculture-weather-station/item/279-sph01-lb.html\t"
    + img(SHOP["sph01"])
    + "\tSEND PI\t",
    "Farm\tS31B-LB\tOutdoor temp & humidity\t1\tEU868\thttps://www.dragino.com/products/temperature-humidity-sensor/item/265-s31b-lb.html\t"
    + img(SHOP["s31b"])
    + "\tSEND PI\tVineyard humidity — not S31-CB",
    "Farm\tLT-22222-L\tLoRaWAN I/O controller\t1\tEU868\thttps://www.dragino.com/products/lora-lorawan-end-node/item/156-lt-22222-l.html\t"
    + img(SHOP["lt"])
    + "\tSEND PI\tValve + open/closed feedback",
    "Dev\tLA66\tLoRaWAN module\t1\tEU868\thttps://www.dragino.com/products/lora/item/230-la66-lorawan-module.html\t"
    + img(SHOP["la66"])
    + "\tSEND PI\tDevelop",
]


def block(title: str, rows: list[str]) -> str:
    head = [
        title,
        "Ship to Eric: 深圳市福田区华强北友谊路上步工业区404栋2楼212号 吴建军 18680660780 kevin",
        "EU868 · SEND PI · updated 2026-09-15 · Lucas follows (not on this tab)",
        "",
    ]
    return "\n".join(head + rows)


COMBINED = "\n".join(
    [
        "MOKO + DRAGINO — ship to Eric (PIs first)",
        "深圳市福田区华强北友谊路上步工业区404栋2楼212号 吴建军 18680660780 kevin",
        "EU868 · SEND PI · 2026-09-15 · Lucas / OTW later",
        "",
        "MOKO",
        *MOKO_ROWS,
        "",
        "DRAGINO",
        *DRAGINO_ROWS,
    ]
)
MOKO_ONLY = block("MOKO", MOKO_ROWS)
DRAGINO_ONLY = block("DRAGINO", DRAGINO_ROWS)


def goto_a1(page):
    box = page.locator("#t-name-box")
    box.click()
    page.keyboard.press("Control+A")
    page.keyboard.type("A1")
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)


def paste(page, text: str):
    goto_a1(page)
    page.evaluate(
        """async (text) => { await navigator.clipboard.writeText(text); }""",
        text,
    )
    page.keyboard.press("Control+V")
    page.wait_for_timeout(2500)


def click_tab(page, name: str):
    page.locator(".docs-sheet-tab-name").filter(has_text=name).first.click()
    page.wait_for_timeout(2000)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.goto(SHEET, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(7000)
        print("title", page.title())

        click_tab(page, "Moko / Dragino Orders")
        paste(page, COMBINED)
        page.screenshot(path="/tmp/sheet-combined.png")

        click_tab(page, "Moko")
        # avoid matching "Moko / Dragino Orders"
        tabs = page.locator(".docs-sheet-tab-name")
        for i in range(tabs.count()):
            if tabs.nth(i).inner_text().strip() == "Moko":
                tabs.nth(i).click()
                break
        page.wait_for_timeout(2000)
        paste(page, MOKO_ONLY)
        page.screenshot(path="/tmp/sheet-moko.png")

        for i in range(tabs.count()):
            if tabs.nth(i).inner_text().strip() == "Dragino":
                tabs.nth(i).click()
                break
        page.wait_for_timeout(2000)
        paste(page, DRAGINO_ONLY)
        page.screenshot(path="/tmp/sheet-dragino.png")

        print("done")
        browser.close()


if __name__ == "__main__":
    main()
