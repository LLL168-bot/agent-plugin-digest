#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse every JSON file in the repository and fail on syntax errors."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
count = 0
for path in sorted(ROOT.rglob("*.json")):
    if ".git" in path.parts:
        continue
    try:
        with open(path, encoding="utf-8") as handle:
            json.load(handle)
        count += 1
    except Exception as exc:  # noqa: BLE001 - report and continue
        errors.append(f"{path}: {exc}")

print(f"validated {count} JSON files")
for error in errors:
    print(error, file=sys.stderr)
sys.exit(1 if errors else 0)
