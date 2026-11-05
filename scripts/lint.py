#!/usr/bin/env python3
"""Repository rules that recipe-check cannot see from a single recipe.

Usage: python3 scripts/lint.py   (from the repository root; Python 3.11+, no dependencies)
"""

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIONS = ROOT / "stations"
FIXTURES = ROOT / "fixtures"
SCHEMA_LINE = "#:schema ../recipe.schema.json"
ID = re.compile(r"^[a-z0-9_-]{1,64}$")
MAX_FIXTURE = 64 * 1024

errors: list[str] = []


def error(path: Path, message: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def stream_key(pattern: str) -> str:
    return pattern.strip().lower().rstrip("/")


used_fixtures: set[Path] = set()
streams: dict[str, Path] = {}
stations: dict[str, Path] = {}

for path in sorted(STATIONS.iterdir()):
    if path.suffix != ".toml":
        error(path, "only <id>.toml files belong in stations/")
        continue
    if not ID.match(path.stem):
        error(path, "file names are lowercase letters, digits, `-` and `_` (at most 64)")
    text = path.read_text(encoding="utf-8")
    if text.splitlines()[:1] != [SCHEMA_LINE]:
        error(path, f"the first line must be `{SCHEMA_LINE}`")
    try:
        recipe = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        error(path, f"not valid TOML: {e}")
        continue

    tests = recipe.get("test", [])
    if not tests:
        error(path, "add at least one [[test]] with a saved page (see README)")
    for test in tests:
        page = (path.parent / test.get("page", "")).resolve()
        if page.parent != FIXTURES:
            error(path, f"test page {test.get('page')!r} must be in fixtures/ (`../fixtures/<file>`)")
            continue
        if not page.is_file():
            error(path, f"test page {test.get('page')!r} does not exist")
            continue
        used_fixtures.add(page)
        if page.stat().st_size > MAX_FIXTURE:
            error(page, f"{page.stat().st_size} bytes: keep only the part of the page the recipe reads (max {MAX_FIXTURE})")
        if "at" not in test:
            error(path, f"test {test.get('page')!r}: add `at`, when the page was saved (its HTTP Date)")

    match = recipe.get("match", {})
    for stream in match.get("streams", []):
        key = stream_key(stream)
        if key in streams:
            error(path, f"stream {stream!r} is already matched by {streams[key].name}")
        streams[key] = path
    for station in match.get("stations", []):
        key = station.strip().lower()
        if key in stations:
            error(path, f"station {station!r} is already matched by {stations[key].name}")
        stations[key] = path

for path in sorted(FIXTURES.iterdir()):
    if path.name.startswith("."):
        continue
    if path.resolve() not in used_fixtures:
        error(path, "not used by any recipe's [[test]]")

if errors:
    print("\n".join(f"FAIL  {e}" for e in errors))
    sys.exit(1)
print(f"ok    {len(list(STATIONS.glob('*.toml')))} recipe(s), {len(used_fixtures)} fixture(s)")
