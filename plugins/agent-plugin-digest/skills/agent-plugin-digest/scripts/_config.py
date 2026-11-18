# -*- coding: utf-8 -*-
"""Config loader shared by the digest scripts (portable across Windows/macOS/Linux)."""
import copy
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_ROOT / "config" / "default.json"


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load(path=None):
    if not DEFAULT_CONFIG.is_file():
        raise SystemExit(f"default config not found: {DEFAULT_CONFIG}")
    with open(DEFAULT_CONFIG, encoding="utf-8") as handle:
        data = json.load(handle)
    if path:
        with open(path, encoding="utf-8") as handle:
            data = _merge(data, json.load(handle))
    return data


def utf8_stdio():
    """Keep Chinese output readable on Windows consoles with legacy code pages."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
