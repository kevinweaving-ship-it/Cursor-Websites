#!/usr/bin/env python3
"""Replace /dev-1 countdown claim advert with the landing sailor-search claim card."""
from pathlib import Path
import shutil
import time

API = Path("/var/www/sailingsa/api/api.py")
MARK = "DEV1_CLAIM_LANDING_v1"

START = (
    "    # Mid-banner advert (claim profile) — only for unclaimed (no green verified tick). "
    "Live countdown vs fixed deadline.\n"
)
END = '    _dev1_claim_fit_js = (\'<script id="dev1-align-fit">(function(){'

NEW = r'''    # DEV1_CLAIM_LANDING_v1 — landing sailor-search claim only (no countdown advert)
    _dev1_claim_banner_html = ""
    _dev1_claim_banner_js = ""
    _dev1_claim_fit_js = ""
    if not is_sailor_verified:
        from urllib.parse import quote as _claim_urlquote
        _claim_sas = str(final_sas or "").strip()
        _claim_name = " ".join(x for x in [(sailor_first or "").strip(), (sailor_last or "").strip()] if x)
        _claim_href = "/signup.html?signup=1"
        if _claim_sas:
            _claim_href += "&sas_id=" + _claim_urlquote(_claim_sas)
        if _claim_name:
            _claim_href += "&name=" + _claim_urlquote(_claim_name)
        _safe_claim_href = _html_escape.escape(_claim_href, quote=True)
        _dev1_claim_banner_html = (
            '<div class="sa-claim-slot" id="dev1-claim-slot">'
            + '<a class="sa-claim-banner sa-claim-banner--landing" id="dev1-claim-banner" href="'
            + _safe_claim_href
            + '">'
            + '<span class="sa-claim-landing-copy">'
            + "<strong>Is this your sailing profile?</strong>"
            + "<span>Unlock your full results and stats</span>"
            + "</span>"
            + '<span class="sa-claim-landing-cta">CLAIM MY PROFILE</span>'
            + "</a></div>"
            + "<style>"
            + "#dev1-claim-slot{display:flex;justify-content:stretch;align-items:stretch;width:100%;height:100%;"
            + "min-width:0;min-height:0;align-self:stretch;box-sizing:border-box;}"
            + ".sa-claim-banner.sa-claim-banner--landing{display:flex!important;flex-direction:column!important;"
            + "width:100%!important;max-width:100%!important;height:100%!important;min-height:44px;margin:0;padding:0;"
            + "text-decoration:none;color:inherit;box-sizing:border-box;overflow:hidden!important;"
            + "border:1px solid #e5e7eb;border-radius:12px;background:#fff;transform:none!important;}"
            + ".sa-claim-landing-copy{display:flex;flex-direction:column;justify-content:center;gap:2px;flex:1 1 auto;"
            + "padding:6px 10px;color:#111827;font-size:12px;line-height:1.25;min-height:0;overflow:hidden;}"
            + ".sa-claim-landing-copy strong{display:block;font-size:13px;font-weight:800;color:#111827;}"
            + ".sa-claim-landing-cta{display:flex;align-items:center;justify-content:center;flex:0 0 auto;"
            + "min-height:44px;background:#001f3f;color:#fff;font-size:12px;font-weight:800;letter-spacing:.04em;}"
            + "</style>"
        )

'''

FIT_OLD = (
    '        + \'if(slot&&ban){\'\n'
    '        + \'  ban.style.transform="none";ban.style.transformOrigin="top center";\'\n'
)
FIT_NEW = (
    '        + \'if(slot&&ban){\'\n'
    '        + \'  if(ban.classList&&ban.classList.contains("sa-claim-banner--landing")){'
    'ban.style.transform="none";ban.style.width="100%";ban.style.maxWidth="100%";ban.style.height="100%";}\'\n'
    '        + \'  else {\'\n'
    '        + \'  ban.style.transform="none";ban.style.transformOrigin="top center";\'\n'
)

FIT_CLOSE_OLD = (
    '        + \'  ban.style.transform=(dy?("translateY("+dy+"px) scale("+s+")"):("scale("+s+")"));\'\n'
    '        + \'}\'\n'
)
FIT_CLOSE_NEW = (
    '        + \'  ban.style.transform=(dy?("translateY("+dy+"px) scale("+s+")"):("scale("+s+")"));\'\n'
    '        + \'}}\'\n'
)

CSS_OLD = (
    "        '.sa-claim-banner{overflow:visible !important;max-width:none !important;"
    "width:max-content !important;height:auto !important;}'\n"
)
CSS_NEW = (
    "        '.sa-claim-banner:not(.sa-claim-banner--landing){overflow:visible !important;"
    "max-width:none !important;width:max-content !important;height:auto !important;}'\n"
)


def main() -> None:
    api = API.read_text()
    if MARK in api:
        print("ALREADY")
        return
    missing = []
    if START not in api:
        missing.append("START")
    if END not in api:
        missing.append("END")
    if FIT_OLD not in api:
        missing.append("FIT")
    if FIT_CLOSE_OLD not in api:
        missing.append("FIT_CLOSE")
    if CSS_OLD not in api:
        missing.append("CSS")
    if "CLAIM YOUR PROFILE NOW" not in api:
        missing.append("OLD_CLAIM")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    start = api.find(START)
    end = api.find(END, start)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit("MISSING:RANGE")
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = API.with_name("api.py.bak.dev1_claim_landing." + ts)
    shutil.copy2(API, bak)
    api = api[:start] + NEW + api[end:]
    api = api.replace(FIT_OLD, FIT_NEW, 1)
    api = api.replace(FIT_CLOSE_OLD, FIT_CLOSE_NEW, 1)
    api = api.replace(CSS_OLD, CSS_NEW, 1)
    if "CLAIM YOUR PROFILE NOW" in api or "PUBLIC ACCESS ENDS IN" in api:
        raise SystemExit("OLD_CLAIM_STILL_PRESENT")
    if MARK not in api:
        raise SystemExit("MARK_MISSING")
    API.write_text(api)
    print("API_OK", MARK, "BAK", str(bak))


if __name__ == "__main__":
    main()
