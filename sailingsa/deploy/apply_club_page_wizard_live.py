#!/usr/bin/env python3
"""Surgically patch live 83k api.py with Phase A club-page wizard endpoints.
Never overwrite the whole file. Run on the live server after snapshot + chattr -i.
"""
from __future__ import annotations

import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path


def func_span(src: str, name: str):
    tree = ast.parse(src)
    lines = src.splitlines(True)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            start = (node.decorator_list[0].lineno - 1) if node.decorator_list else (node.lineno - 1)
            end = node.end_lineno
            return start, end, "".join(lines[start:end])
    return None


def replace_func(dst: str, src: str, name: str) -> str:
    dspan = func_span(dst, name)
    sspan = func_span(src, name)
    if not sspan:
        raise SystemExit("workspace missing %s" % name)
    if not dspan:
        raise SystemExit("live missing %s" % name)
    dlines = dst.splitlines(True)
    slines = src.splitlines(True)
    return "".join(dlines[: dspan[0]] + slines[sspan[0] : sspan[1]] + dlines[dspan[1] :])


def insert_after_func(dst: str, src: str, after_name: str, new_name: str) -> str:
    if func_span(dst, new_name):
        return dst
    sspan = func_span(src, new_name)
    dspan = func_span(dst, after_name)
    if not sspan or not dspan:
        raise SystemExit("cannot insert %s after %s" % (new_name, after_name))
    slines = src.splitlines(True)
    dlines = dst.splitlines(True)
    block = "\n\n" + "".join(slines[sspan[0] : sspan[1]]) + "\n"
    return "".join(dlines[: dspan[1]] + [block] + dlines[dspan[1] :])


def insert_helpers(dst: str, src: str) -> str:
    helpers = [
        "_phase2_lookup_club_id",
        "_resolve_managed_club_id",
        "_phase2_bool",
        "_upsert_season_item",
        "_norm_club_kind",
        "_kind_allows_regatta",
        "_year_stripped_event_name",
        "_host_display_name",
    ]
    after = "_require_club_host_club_id"
    for name in helpers:
        if func_span(dst, name):
            continue
        dst = insert_after_func(dst, src, after, name)
        after = name
    if "_NO_REGATTA_KINDS" not in dst:
        needle = "def _norm_club_kind"
        const = (
            "\n_NO_REGATTA_KINDS = frozenset({\"training\", \"external\", \"informal\", \"cruise\", \"ops\", \"duty\"})\n"
            "_VALID_CLUB_KINDS = frozenset({\"race\"}) | _NO_REGATTA_KINDS\n\n"
        )
        if needle in dst:
            dst = dst.replace(needle, const + needle, 1)
    return dst


def patch_html(dst: str) -> str:
    old_div = 'f"<div class=\\"club-page\\">{body}</div>{_seo_discovery_block_html()}"'
    new_div = (
        'f"<div class=\\"club-page\\" data-club-abbrev=\\"{(club_code or slug or \'\').strip()}\\" '
        'data-club-id=\\"{int(club_id)}\\">{body}</div>{_seo_discovery_block_html()}"'
    )
    if old_div in dst:
        dst = dst.replace(old_div, new_div, 1)
    old = '<div class="club-page">{body}</div>'
    new = (
        '<div class="club-page" data-club-abbrev="{(club_code or slug or \'\').strip()}" '
        'data-club-id="{int(club_id)}">{body}</div>'
    )
    if old in dst and "data-club-abbrev" not in dst:
        dst = dst.replace(old, new, 1)
    live_js = '"<script src=\\"/js/club-page-std.js?v=clubstd2\\" defer></script>"'
    live_tag = live_js + '\n        "<script src=\\"/js/club-page-wizard.js?v=clubwz1\\"></script>"'
    if "club-page-wizard.js" not in dst and live_js in dst:
        dst = dst.replace(live_js, live_tag, 1)
    tag = '<script src="/js/club-page-wizard.js?v=clubwz1"></script>'
    needle = '<script src="/js/club-page-std.js?v=clubstd2" defer></script>'
    if tag not in dst and needle in dst:
        dst = dst.replace(needle, needle + "\n        " + tag, 1)
    return dst


def main():
    live = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
    workspace = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/club-wizard-workspace-api.py")
    dst = live.read_text(encoding="utf-8")
    src = workspace.read_text(encoding="utf-8")
    ast.parse(src)
    if dst.count("\n") < 40000:
        raise SystemExit("refusing to patch a short api.py (%s lines)" % dst.count("\n"))
    bak = live.with_name(live.name + "." + datetime.now().strftime("%Y%m%d_%H%M%S") + ".applywizard.bak")
    shutil.copy2(live, bak)
    dst = insert_helpers(dst, src)
    for name in (
        "api_club_me",
        "_ensure_phase2_columns",
        "_phase2_host_is_claimable",
        "api_club_me_events",
        "api_club_create_event",
        "api_club_claim_event",
    ):
        dst = replace_func(dst, src, name)
    if not func_span(dst, "api_club_events_match"):
        dst = insert_after_func(dst, src, "api_club_create_event", "api_club_events_match")
    if not func_span(dst, "api_club_season_item"):
        dst = insert_after_func(dst, src, "api_club_events_match", "api_club_season_item")
    dst = patch_html(dst)
    ast.parse(dst)
    live.write_text(dst, encoding="utf-8")
    print("patched", live, "backup", bak, "lines", dst.count("\n"))


if __name__ == "__main__":
    main()
