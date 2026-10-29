"""GSC Page Indexing snapshot contract (gitignore-safe name)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sailingsa.tools.gsc_daily.page_indexing_test import (
    test_every_family_has_a_bucket_in_the_snapshot,
    test_probe_families_uses_injected_hit,
    test_redirect_helper,
    test_snapshot_is_the_pasted_gsc_table,
)

if __name__ == "__main__":
    test_snapshot_is_the_pasted_gsc_table()
    test_redirect_helper()
    test_probe_families_uses_injected_hit()
    test_every_family_has_a_bucket_in_the_snapshot()
    print("ok")
