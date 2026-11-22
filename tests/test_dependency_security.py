"""Regression guard for soupsieve security advisories.

CVE-2026-126191 (selector-compilation ReDoS, fixed in 3.0.2) and
CVE-2026-126190 (descendant-combinator DoS, fixed in 4.0.0) both affect
soupsieve < 4.0.0. The resolved lockfile must never pin a vulnerable version.
"""

import tomllib
from pathlib import Path

MIN_SOUPSIEVE = (4, 0, 0)


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def test_lockfile_pins_only_patched_soupsieve() -> None:
    lockfile = Path(__file__).resolve().parents[1] / "uv.lock"
    with lockfile.open("rb") as handle:
        lock = tomllib.load(handle)

    versions = [
        package["version"]
        for package in lock["package"]
        if package["name"] == "soupsieve"
    ]

    assert versions, "uv.lock does not pin soupsieve at all"
    vulnerable = [v for v in versions if _version_tuple(v) < MIN_SOUPSIEVE]
    assert not vulnerable, (
        f"uv.lock pins vulnerable soupsieve versions: {vulnerable}; "
        f"all pins must be >= {'.'.join(map(str, MIN_SOUPSIEVE))}"
    )
