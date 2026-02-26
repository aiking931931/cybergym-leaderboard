#!/usr/bin/env python3
"""Inline http_entrypoint.py into cybergym-executor.json5 as a python3 -c entrypoint."""
import json
from pathlib import Path

here = Path(__file__).parent
script = (here / "http_entrypoint.py").read_text()

if "${" in script:
    raise ValueError("http_entrypoint.py contains '${' which would be interpreted as amber interpolation syntax")

template = (here / "cybergym-executor.json5.template").read_text()
manifest_path = here / "cybergym-executor.json5"

manifest = template.replace('"@@HTTP_ENTRYPOINT@@"', json.dumps(script))
manifest_path.write_text(manifest)
print(f"Updated {manifest_path}")
