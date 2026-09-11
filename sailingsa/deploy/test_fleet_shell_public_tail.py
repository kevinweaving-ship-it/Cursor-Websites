#!/usr/bin/env python3
"""Unit tests for canonical fleet-shell public tails."""
from fleet_shell_public_tail import fleet_shell_public_slug, fleet_shell_public_tail

PARENT = "2026-09-13-zvyc-cape-classic"


def check(got, want, label):
    if got != want:
        raise SystemExit(f"FAIL {label}: got {got!r} want {want!r}")
    print("ok", label, got)


def main() -> int:
    check(
        fleet_shell_public_tail(
            f"{PARENT}:ilca-4-fleet",
            class_canonical="Ilca 4.7",
        ),
        "ilca-4.7-fleet",
        "truncated ILCA 4.7 block tail upgrades",
    )
    check(
        fleet_shell_public_tail(f"{PARENT}:ilca-4-fleet"),
        "ilca-4.7-fleet",
        "alias map upgrades ILCA 4.7 without labels",
    )
    check(
        fleet_shell_public_tail(
            f"{PARENT}:ilca-6-fleet",
            class_canonical="Ilca 6",
        ),
        "ilca-6-fleet",
        "ILCA 6 unchanged",
    )
    check(
        fleet_shell_public_tail(
            f"{PARENT}:optimist-a-fleet",
            class_canonical="Optimist",
        ),
        "optimist-a-fleet",
        "Optimist A keeps specific tail",
    )
    check(
        fleet_shell_public_tail(f"{PARENT}:open", class_canonical="Open", class_name="Fireball"),
        "open",
        "mixed Open not rewritten to fireball",
    )
    check(
        fleet_shell_public_tail(f"{PARENT}:extra-fleet", class_canonical="Extra"),
        "extra-fleet",
        "Extra keeps extra-fleet",
    )
    check(
        fleet_shell_public_tail(f"{PARENT}:420-fleet", class_canonical="420"),
        "420-fleet",
        "420 unchanged",
    )
    check(
        fleet_shell_public_slug(PARENT, f"{PARENT}:ilca-4-fleet", class_canonical="Ilca 4.7"),
        f"{PARENT}-ilca-4.7-fleet",
        "public slug",
    )
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
