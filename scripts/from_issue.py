#!/usr/bin/env python3
"""Writes the recipe and fixture of a "Share a recipe" issue into stations/ and fixtures/.

Usage: python3 scripts/from_issue.py <event.json>   (from the repository root)

Prints `id=<id>` for $GITHUB_OUTPUT. Exits 1 with the reason on stderr when the issue cannot be
used. The issue body is untrusted: it is only ever written to these two files.
"""

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID = re.compile(r"^[a-z0-9_-]{1,64}$")
EXTENSIONS = {"html": "html", "json": "json", "text": "txt"}
SCHEMA_LINE = "#:schema ../recipe.schema.json"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def sections(body: str) -> dict[str, str]:
    """`### Heading` → content, as GitHub renders issue forms."""
    found: dict[str, str] = {}
    parts = re.split(r"^### (.+)$", body.replace("\r\n", "\n"), flags=re.M)
    for heading, content in zip(parts[1::2], parts[2::2]):
        found[heading.strip()] = unfence(content.strip("\n"))
    return found


def unfence(content: str) -> str:
    """Removes the outer code fence added by `render:`, if any."""
    lines = content.strip("\n").split("\n")
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
        lines = lines[1:-1]
    text = "\n".join(lines).strip("\n")
    return "" if text == "_No response_" else text


event = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
fields = sections(event["issue"].get("body") or "")
recipe_id = fields.get("Recipe id", "").strip()
recipe_text = fields.get("Recipe", "")
fixture_text = fields.get("Fixture", "")

if not ID.match(recipe_id):
    fail(f"The recipe id {recipe_id!r} is not valid: lowercase letters, digits, `-` and `_`.")
if not recipe_text:
    fail("The Recipe field is empty.")
if not fixture_text:
    fail("The Fixture field is empty: paste the excerpt Soundfolk copied to your clipboard.")

try:
    recipe = tomllib.loads(recipe_text)
except tomllib.TOMLDecodeError as e:
    fail(f"The recipe is not valid TOML: {e}")
kind = recipe.get("extract", {}).get("type")
if kind not in EXTENSIONS:
    fail(f"Unknown `extract.type` {kind!r}.")
fixture_file = f"{recipe_id}.{EXTENSIONS[kind]}"

# The fixture always goes to fixtures/<id>.<ext>, whatever the test said.
lines = [line for line in recipe_text.split("\n") if not line.lstrip().startswith("#:schema")]
text = SCHEMA_LINE + "\n" + "\n".join(lines).strip("\n") + "\n"
text = re.sub(r'^(\s*page\s*=\s*)"[^"\n]*"', rf'\1"../fixtures/{fixture_file}"', text, flags=re.M)

(ROOT / "stations" / f"{recipe_id}.toml").write_text(text, encoding="utf-8")
(ROOT / "fixtures" / fixture_file).write_text(fixture_text.rstrip("\n") + "\n", encoding="utf-8")
print(f"id={recipe_id}")
