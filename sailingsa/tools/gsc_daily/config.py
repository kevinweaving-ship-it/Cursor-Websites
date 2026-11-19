"""GSC daily workflow — constants. No secrets."""

from __future__ import annotations

from pathlib import Path

SITE = "https://sailingsa.co.za"
SITE_SLASH = "https://sailingsa.co.za/"
GSC_HOME = "https://search.google.com/search-console"
GSC_PAGES = (
    "https://search.google.com/search-console/index"
    "?resource_id=https%3A%2F%2Fsailingsa.co.za%2F"
)
GSC_PAGES_DOMAIN = (
    "https://search.google.com/search-console/index"
    "?resource_id=sc-domain%3Asailingsa.co.za"
)

UA = "SailingSA-GSC-Daily/1.0"

# Official GSC Page Indexing labels + aliases Kevin used.
# Order = first-run priority (small cohorts first).
ISSUES = [
    {
        "key": "redirect_error",
        "label": "Redirect error",
        "aliases": ["Redirect error"],
    },
    {
        "key": "other_4xx",
        "label": "Blocked due to other 4xx issue",
        "aliases": [
            "Blocked due to other 4xx issue",
            "Blocked due to other 4xx",
            "Other 4xx",
        ],
    },
    {
        "key": "soft_404",
        "label": "Soft 404",
        "aliases": ["Soft 404"],
    },
    {
        "key": "forbidden_403",
        "label": "Blocked due to access forbidden (403)",
        "aliases": [
            "Blocked due to access forbidden (403)",
            "Blocked due to access forbidden",
            "403",
        ],
    },
    {
        "key": "server_error_5xx",
        "label": "Server error (5xx)",
        "aliases": ["Server error (5xx)", "5xx"],
    },
    {
        "key": "page_with_redirect",
        "label": "Page with redirect",
        "aliases": ["Page with redirect"],
    },
    {
        "key": "not_found_404",
        "label": "Not found (404)",
        "aliases": ["Not found (404)", "404"],
    },
    {
        "key": "excluded_noindex",
        "label": "Excluded by ‘noindex’ tag",
        "aliases": [
            "Excluded by ‘noindex’ tag",
            "Excluded by 'noindex' tag",
            "Excluded by noindex",
            "noindex",
        ],
    },
    {
        "key": "duplicate_no_canonical",
        "label": "Duplicate without user-selected canonical",
        "aliases": [
            "Duplicate without user-selected canonical",
            "Duplicate without canonical",
        ],
    },
    {
        "key": "alternative_canonical",
        "label": "Alternate page with proper canonical tag",
        "aliases": [
            "Alternate page with proper canonical tag",
            "Alternative page with proper canonical",
            "Alternative canonical",
        ],
    },
]


def default_data_root() -> Path:
    home = Path.home()
    return home / "Library" / "Application Support" / "sailingsa" / "gsc-daily"


def run_dir(day: str, root: Path | None = None) -> Path:
    return (root or default_data_root()) / day
