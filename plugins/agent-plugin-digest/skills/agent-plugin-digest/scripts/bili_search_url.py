#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print the Bilibili search URL(s) derived from config.

Supports multiple keywords so the report is not limited to DSH plugins.
"""
import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import load, utf8_stdio  # noqa: E402


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Build Bilibili search URLs")
    parser.add_argument("--config", default="")
    parser.add_argument("--keyword", default="", help="single keyword override")
    parser.add_argument("--order", default="", help="pubdate | click | dm | stow")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = load(args.config or None)["bilibili"]
    if args.keyword:
        keywords = [args.keyword]
    else:
        keywords = cfg.get("keywords") or []
        if not keywords and cfg.get("keyword"):
            keywords = [cfg["keyword"]]
    order = args.order or cfg["order"]

    urls = [
        "https://search.bilibili.com/all?keyword="
        + urllib.parse.quote(keyword, safe="")
        + "&order="
        + urllib.parse.quote(order, safe="")
        for keyword in keywords
    ]
    if args.json:
        print(json.dumps({"keywords": keywords, "order": order, "urls": urls}, ensure_ascii=False))
    else:
        for url in urls:
            print(url)


if __name__ == "__main__":
    main()
