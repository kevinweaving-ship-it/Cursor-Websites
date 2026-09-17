#!/usr/bin/env python3
"""Surgical live api.py patch: shared db_connection() + adopt in proven helpers."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/api.py.patchwork")
raw = SRC.read_text(encoding="utf-8", errors="replace")
lines = raw.splitlines(keepends=True)
nchg = 0


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def find_unique(substr: str) -> int:
    hits = [i for i, l in enumerate(lines) if substr in l]
    if len(hits) != 1:
        fail(f"unique {substr!r} hits={len(hits)} {hits[:8]}")
    return hits[0]


def find_line_eq(exact: str, start: int = 0, end: int | None = None) -> int:
    end = len(lines) if end is None else end
    hits = [i for i in range(start, end) if lines[i].rstrip("\n") == exact]
    if len(hits) != 1:
        fail(f"eq {exact!r} in [{start},{end}) hits={len(hits)}")
    return hits[0]


def indent_of(i: int) -> int:
    s = lines[i].replace("\t", "    ")
    return len(s) - len(s.lstrip(" "))


def replace_span(i0: int, i1: int, new_lines: list[str], label: str) -> None:
    global nchg
    lines[i0:i1] = new_lines
    nchg += 1
    print(f"OK {label} lines {i0+1}-{i1} -> {len(new_lines)} lines")


# ---------------------------------------------------------------------------
# 1) import
# ---------------------------------------------------------------------------
i = find_unique("import contextvars")
if "from contextlib import contextmanager" not in "".join(lines[i : i + 3]):
    lines[i] = lines[i].rstrip("\n") + "\nfrom contextlib import contextmanager\n"
    nchg += 1
    print("OK import-contextmanager")
else:
    print("SKIP import-contextmanager")

# ---------------------------------------------------------------------------
# 2) tag borrow site on get_db
# ---------------------------------------------------------------------------
i = find_unique("        wrapped = _ConnectionWrapper(conn)")
if "_borrowed_from" not in lines[i + 1]:
    ins = [
        "        wrapped = _ConnectionWrapper(conn)\n",
        "        try:\n",
        "            wrapped._borrowed_from = _borrow_site()\n",
        "        except Exception:\n",
        '            wrapped._borrowed_from = "?"\n',
    ]
    replace_span(i, i + 1, ins, "tag-borrow-site")
else:
    print("SKIP tag-borrow-site")

# ---------------------------------------------------------------------------
# 3) helpers after return_db_connection
# ---------------------------------------------------------------------------
marker = "# ============================================================================\n# QUERY PROFILING\n"
join = "".join(lines)
if "def db_connection(" not in join:
    i = None
    for idx, l in enumerate(lines):
        if l.startswith("# ============================================================================") and idx + 1 < len(lines) and "QUERY PROFILING" in lines[idx + 1]:
            i = idx
            break
    if i is None:
        fail("QUERY PROFILING marker")
    block = '''
def _borrow_site() -> str:
    """Best-effort helper names that called get_db_connection (no GC/weakref)."""
    try:
        fr = sys._getframe(2)
        parts = []
        skip = {
            "get_db_connection", "db_connection", "_db_connection",
            "__enter__", "__exit__", "_release",
        }
        while fr is not None and len(parts) < 4:
            name = fr.f_code.co_name
            if name not in skip:
                parts.append(f"{name}:{fr.f_lineno}")
            fr = fr.f_back
        return " < ".join(parts) if parts else "?"
    except Exception:
        return "?"

@contextmanager
def db_connection(request_id: str = None):
    """Borrow a pooled connection and always return it."""
    conn = get_db_connection(request_id)
    try:
        yield conn
    finally:
        return_db_connection(conn)

'''
    lines[i:i] = [block]
    nchg += 1
    print("OK add-db-connection-cm")
else:
    print("SKIP add-db-connection-cm")

# ---------------------------------------------------------------------------
# 4) reclaim log
# ---------------------------------------------------------------------------
i = find_unique('print(f"[DB] reclaiming {len(leaked)} leaked conn(s) after {endpoint}"')
if "from=" not in lines[i]:
    replace_span(
        i,
        i + 1,
        [
            "            sites = [getattr(c, \"_borrowed_from\", \"?\") for c in leaked]\n",
            '            print(f"[DB] reclaiming {len(leaked)} leaked conn(s) after {endpoint} from={sites}", flush=True)\n',
        ],
        "reclaim-from-sites",
    )
else:
    print("SKIP reclaim-from-sites")


def func_span(name: str) -> tuple[int, int]:
    start = None
    for i, l in enumerate(lines):
        if l.startswith(f"def {name}(") or l.startswith(f"def {name}("):
            start = i
            break
        if re.match(rf"def {re.escape(name)}\(", l):
            start = i
            break
    if start is None:
        fail(f"def {name}")
    # end: next top-level def/class or decorator at col 0
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("def ") or lines[j].startswith("class ") or lines[j].startswith("@app.") or lines[j].startswith("@app."):
            # allow nested? top-level only
            if not lines[j].startswith(" "):
                end = j
                break
        if lines[j].startswith("@") and j + 1 < len(lines) and lines[j + 1].startswith("def "):
            end = j
            break
    return start, end


def replace_func_prefix_get_try_finally(name: str, conn_var: str = "conn") -> None:
    """Inside function, convert first
        conn = get_db_connection(...)
        cur = conn.cursor(...)
        try:
            ...
        finally:
            cur.close()
            return_db_connection(conn)
    into with db_connection() as conn.
    """
    start, end = func_span(name)
    body = lines[start:end]
    get_i = None
    for k, l in enumerate(body):
        if re.search(rf"{conn_var}\s*=\s*get_db_connection\(", l) and not l.lstrip().startswith("#"):
            get_i = k
            break
    if get_i is None:
        fail(f"{name}: no get_db")
    abs_get = start + get_i
    ind = indent_of(abs_get)
    # find finally at same indent after get
    fin_i = None
    for k in range(abs_get + 1, end):
        if lines[k].rstrip("\n") == (" " * ind) + "finally:":
            fin_i = k
            break
    if fin_i is None:
        fail(f"{name}: no finally at indent {ind} after get")
    # finally body until dedent
    fin_end = fin_i + 1
    while fin_end < end and (not lines[fin_end].strip() or indent_of(fin_end) > ind):
        fin_end += 1
    fin_block = "".join(lines[fin_i:fin_end])
    if "return_db_connection" not in fin_block and "conn.close()" not in fin_block:
        fail(f"{name}: finally has no return/close: {fin_block!r}")
    # rewrite get line
    get_line = lines[abs_get]
    req = ""
    m = re.search(r"get_db_connection\((.*)\)", get_line)
    args = (m.group(1) if m else "").strip()
    new_get = (" " * ind) + (f"with db_connection({args}) as {conn_var}:\n" if args else f"with db_connection() as {conn_var}:\n")
    # indent get+1 .. fin_end-1 by +4, drop return_db/conn.close in finally
    new_mid = []
    for k in range(abs_get + 1, fin_end):
        ln = lines[k]
        if re.search(r"return_db_connection\(\s*" + conn_var + r"\s*\)", ln):
            continue
        if re.search(rf"{conn_var}\.close\(\)", ln) and "cur" not in ln:
            continue
        if ln.strip() == "":
            new_mid.append(ln)
        else:
            new_mid.append("    " + ln)
    replace_span(abs_get, fin_end, [new_get] + new_mid, f"wrap-{name}")


def replace_q_style(name: str) -> None:
    """try/finally only (no except): become a bare with db_connection()."""
    start, end = func_span(name)
    body = "".join(lines[start:end])
    if "with db_connection()" in body:
        print(f"SKIP {name} already wrapped")
        return
    old = body
    new = old.replace(
        "    conn = None\n    try:\n        conn = get_db_connection()\n",
        "    with db_connection() as conn:\n",
    )
    new = re.sub(
        r"\n    finally:\n        if conn:\n            return_db_connection\(conn\)\n",
        "\n",
        new,
        count=1,
    )
    if new == old:
        fail(f"{name}: q-style replace no-op")
    new_lines = new.splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"
    replace_span(start, end, new_lines, f"qstyle-{name}")


def replace_try_except_finally(name: str) -> None:
    """Keep try/except; swap get+finally-return for with db_connection()."""
    start, end = func_span(name)
    body_lines = lines[start:end]
    body = "".join(body_lines)
    if body.count("with db_connection()") >= 1 and "conn = get_db_connection()" not in body:
        print(f"SKIP {name} already wrapped")
        return
    get_k = next((k for k, l in enumerate(body_lines) if re.search(r"conn\s*=\s*get_db_connection\(", l)), None)
    if get_k is None:
        fail(f"{name}: no get_db")
    # expect `    try:` immediately before, optionally after `    conn = None`
    # find matching except/finally at indent 4 after get
    abs_get = start + get_k
    try_k = None
    for k in range(get_k - 1, -1, -1):
        if body_lines[k].rstrip("\n") == "    try:":
            try_k = k
            break
        if body_lines[k].strip() and not body_lines[k].rstrip().endswith("= None"):
            break
    if try_k is None:
        fail(f"{name}: no try before get")
    close_k = None
    for k in range(get_k + 1, len(body_lines)):
        s = body_lines[k].rstrip("\n")
        if s in ("    except Exception:", "    except Exception as e:", "    finally:"):
            close_k = k
            break
    if close_k is None:
        fail(f"{name}: no except/finally after get")
    # drop `conn = None` immediately above try
    drop_none = try_k > 0 and body_lines[try_k - 1].rstrip("\n") == "    conn = None"
    new_chunk = []
    if drop_none:
        prefix = body_lines[: try_k - 1]
    else:
        prefix = body_lines[:try_k]
    new_chunk.extend(prefix)
    new_chunk.append("    try:\n")
    new_chunk.append("        with db_connection() as conn:\n")
    for l in body_lines[get_k + 1 : close_k]:
        if l.strip() == "":
            new_chunk.append(l if l.endswith("\n") else l + "\n")
        else:
            new_chunk.append("    " + (l if l.endswith("\n") else l + "\n"))
    # keep except; drop 4-space finally that only returns conn
    tail = body_lines[close_k:]
    tail_s = "".join(tail)
    tail_s = re.sub(
        r"\n    finally:\n        if conn:\n            return_db_connection\(conn\)\n",
        "\n",
        tail_s,
        count=1,
    )
    tail_s = re.sub(
        r"\n    finally:\n        if conn:\n            try:\n                return_db_connection\(conn\)\n            except Exception:\n                pass\n",
        "\n",
        tail_s,
        count=1,
    )
    new_lines = new_chunk + tail_s.splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"
    replace_span(start, end, new_lines, f"tryex-{name}")


# q / one / qf
for fn in ("q", "one", "qf"):
    replace_q_style(fn)

# get+cursor+try+finally helpers
for fn in (
    "_directory_sailors",
    "_directory_regattas",
    "_directory_clubs",
    "_directory_classes",
    "_batch_sailor_slugs_for_sas_ids",
    "_get_club_slug_by_id",
    "_get_sailor_bio_data",
    "_gold_infer_event_host",
):
    replace_func_prefix_get_try_finally(fn)

replace_func_prefix_get_try_finally("_seo_discovery_pairs_fetch")

replace_try_except_finally("_get_site_stats")
replace_try_except_finally("_get_yearly_event_series")
replace_try_except_finally("_touch_request_session_path")
replace_try_except_finally("_log_analytics_event")

# ---------------------------------------------------------------------------
# upcoming second conn
# ---------------------------------------------------------------------------
start, end = func_span("_get_upcoming_events")
body = "".join(lines[start:end])
old = """                _econn = get_db_connection()
                try:
                    _ecur = _econn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    _attach_event_card_display_sort_fields(
                        _ecur, past_need, series_max_entries_by_key=_series_max_map
                    )
                    _ecur.close()
                finally:
                    return_db_connection(_econn)
"""
new = """                with db_connection() as _econn:
                    _ecur = _econn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    try:
                        _attach_event_card_display_sort_fields(
                            _ecur, past_need, series_max_entries_by_key=_series_max_map
                        )
                    finally:
                        _ecur.close()
"""
if old not in body:
    fail("upcoming _econn block missing")
body2 = body.replace(old, new, 1)
new_lines = body2.splitlines(keepends=True)
if new_lines and not new_lines[-1].endswith("\n"):
    new_lines[-1] += "\n"
replace_span(start, end, new_lines, "upcoming-econn")

# ---------------------------------------------------------------------------
# events_by_type: column_exists BEFORE get; wrap get..except with db_connection
# ---------------------------------------------------------------------------
start, end = func_span("_get_events_by_type_slug")
if "with db_connection() as conn:" not in "".join(lines[start:end]):
    old = """        if not table_exists("events"):
            return out
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        has_regatta_id = column_exists("events", "regatta_id")
        has_host_club_id = column_exists("events", "host_club_id")
        has_map_url = column_exists("events", "map_url")
        has_image_url = column_exists("events", "image_url")
        has_address = column_exists("events", "address")
        has_start_time = column_exists("events", "start_time")
        has_end_time = column_exists("events", "end_time")
        has_source = column_exists("events", "source")
"""
    new = """        if not table_exists("events"):
            return out
        has_regatta_id = column_exists("events", "regatta_id")
        has_host_club_id = column_exists("events", "host_club_id")
        has_map_url = column_exists("events", "map_url")
        has_image_url = column_exists("events", "image_url")
        has_address = column_exists("events", "address")
        has_start_time = column_exists("events", "start_time")
        has_end_time = column_exists("events", "end_time")
        has_source = column_exists("events", "source")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
"""
    text_fn = "".join(lines[start:end])
    if old not in text_fn:
        fail("events_by_type open block")
    text_fn = text_fn.replace(old, new, 1)
    tmp = text_fn.splitlines(keepends=True)
    # find get line inside this temp function
    g = next(i for i, l in enumerate(tmp) if "conn = get_db_connection()" in l)
    # find matching except at 4 spaces
    ex = next(i for i in range(g + 1, len(tmp)) if tmp[i].rstrip("\n") == "    except Exception:")
    # replace get with with, indent g+1 .. ex-1, drop return_db
    ind_get = len(tmp[g]) - len(tmp[g].lstrip(" "))
    new_mid = []
    new_mid.append(" " * ind_get + "with db_connection() as conn:\n")
    for l in tmp[g + 1 : ex]:
        if "return_db_connection(conn)" in l:
            continue
        if l.strip() == "":
            new_mid.append(l)
        else:
            new_mid.append("    " + l)
    # except: with already returned — drop conn rollback/return
    rest = tmp[ex:]
    rest_s = "".join(rest)
    rest_s = rest_s.replace(
        """    except Exception:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            return_db_connection(conn)
""",
        """    except Exception:
        pass
""",
        1,
    )
    new_fn = tmp[:g] + new_mid + rest_s.splitlines(keepends=True)
    if new_fn and not new_fn[-1].endswith("\n"):
        new_fn[-1] += "\n"
    replace_span(start, end, new_fn, "events-by-type")
else:
    print("SKIP events-by-type")

# ---------------------------------------------------------------------------
# full_page: load boat map AFTER releasing the page conn
# ---------------------------------------------------------------------------
start, end = func_span("_get_regatta_full_page_data")
fn = "".join(lines[start:end])
old = """            print(f"REGATTA_DATA: step=after_dup_names time={time.time() - t0:.3f}", flush=True)
            boat_norm_slug_map = _load_boat_norm_slug_map()
        finally:
"""
new = """            print(f"REGATTA_DATA: step=after_dup_names time={time.time() - t0:.3f}", flush=True)
        finally:
"""
if old not in fn:
    fail("full_page boat map before finally")
fn = fn.replace(old, new, 1)
old2 = """        return None
    print(f"REGATTA_DATA: step=after_db_calls time={time.time() - t0:.3f}", flush=True)
"""
new2 = """        return None
    boat_norm_slug_map = _load_boat_norm_slug_map()
    print(f"REGATTA_DATA: step=after_db_calls time={time.time() - t0:.3f}", flush=True)
"""
if old2 not in fn:
    fail("full_page after_db_calls")
fn = fn.replace(old2, new2, 1)
new_lines = fn.splitlines(keepends=True)
if new_lines and not new_lines[-1].endswith("\n"):
    new_lines[-1] += "\n"
replace_span(start, end, new_lines, "full-page-boat-map")

# ---------------------------------------------------------------------------
# gold_infer: slug lookup after with (if wrap left it inside)
# After wrap, _get_club_slug_by_id is still inside the with body.
# Move it out by assigning cid then looking up after the with — only if still inside.
# Safer: leave it; wrap of _get_club_slug_by_id itself guarantees that nested
# borrow returns. Nested hold remains 2-deep only for the slug query.
# ---------------------------------------------------------------------------

# seo: table_exists still inside with (they were already inside before wrap).
# Move table_exists before the with by rewriting the start of the function.
start, end = func_span("_seo_discovery_pairs_fetch")
fn = "".join(lines[start:end])
old = '''    pairs = []
    conn = None
    try:
        with db_connection() as conn:
'''
# wrap may have produced slightly different opening
if "with db_connection() as conn:" in fn and "has_regattas = table_exists" not in fn:
    old = """    pairs = []
    conn = None
    try:
"""
    if old not in fn:
        # maybe wrap removed conn = None
        old = """    pairs = []
    try:
"""
    if old not in fn:
        fail(f"seo open: {fn[:400]!r}")
    new = """    pairs = []
    has_regattas = table_exists("regattas")
    has_results_sailors = table_exists("results") and table_exists("sas_id_personal")
    has_clubs = table_exists("clubs")
    has_classes = table_exists("classes")
    try:
"""
    fn = fn.replace(old, new, 1)
    fn = fn.replace('if table_exists("regattas"):', "if has_regattas:")
    fn = fn.replace('if table_exists("results") and table_exists("sas_id_personal"):', "if has_results_sailors:")
    fn = fn.replace('if table_exists("clubs"):', "if has_clubs:")
    fn = fn.replace('if table_exists("classes"):', "if has_classes:")
    # batch slugs: still inside with. Pull after by splitting — keep SQL order.
    # Leave batch inside if rewrite is too risky; batch itself is now wrapped.
    new_lines = fn.splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"
    replace_span(start, end, new_lines, "seo-table-exists-before")
else:
    print("SKIP seo-table-exists-before")

out = "".join(lines)
if out == raw:
    fail("no changes produced")
SRC.write_text(out, encoding="utf-8")
print(f"WROTE {SRC} changes={nchg} lines={out.count(chr(10))}")
