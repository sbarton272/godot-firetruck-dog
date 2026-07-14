#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Regenerate site/index.html from site/versions.json."""
import html
import json
import pathlib
import subprocess
import sys


def repo_root() -> pathlib.Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return pathlib.Path(out.stdout.strip())


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Firetruck Dog</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }}
  h1 {{ margin-bottom: 4px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }}
  .version {{ font-weight: bold; }}
  .date {{ color: #666; font-size: 0.9em; }}
  a.play {{ display: inline-block; margin-top: 8px; }}
</style>
</head>
<body>
<h1>Firetruck Dog</h1>
<p>Published versions, newest first.</p>
<ul>
{entries}
</ul>
</body>
</html>
"""

ENTRY_TEMPLATE = """  <li>
    <div class="version">{version}</div>
    <div class="date">{date}</div>
    <p>{summary}</p>
    <a class="play" href="{dir}/index.html">Play {version}</a>
  </li>"""


def render(versions: list[dict]) -> str:
    entries = [
        ENTRY_TEMPLATE.format(
            version=html.escape(v["version"]),
            date=html.escape(v["date"]),
            summary=html.escape(v["summary"]),
            dir=html.escape(v["dir"]),
        )
        for v in reversed(versions)
    ]
    return PAGE_TEMPLATE.format(entries="\n".join(entries))


def main(argv: list[str]) -> int:
    root = repo_root()
    versions_path = pathlib.Path(argv[0]) if len(argv) > 0 else root / "site" / "versions.json"
    output_path = pathlib.Path(argv[1]) if len(argv) > 1 else root / "site" / "index.html"

    versions = json.loads(versions_path.read_text()) if versions_path.exists() else []
    output_path.write_text(render(versions))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
