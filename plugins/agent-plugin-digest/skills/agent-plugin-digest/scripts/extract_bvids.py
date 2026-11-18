#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract and merge BVIDs/titles from one or more Firecrawl Bilibili search pages."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import utf8_stdio  # noqa: E402

LINK_RE = re.compile(
    r"\[([^\]\n]{1,200})\]\((https?://[^)\s]*?/video/(BV[0-9A-Za-z]{10})[^)\s]*)\)"
)
BVID_RE = re.compile(r"BV[0-9A-Za-z]{10}")


def clean_title(text):
    text = text.replace("\\", "")
    text = re.sub(r"^#+\s*", "", text)
    text = text.replace("_", "").replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


def extract(text):
    items, seen = [], set()
    for title, _url, bvid in LINK_RE.findall(text):
        if bvid in seen:
            continue
        seen.add(bvid)
        items.append({
            "bvid": bvid,
            "title": clean_title(title),
            "url": f"https://www.bilibili.com/video/{bvid}/",
        })
    if not items:
        for bvid in BVID_RE.findall(text):
            if bvid in seen:
                continue
            seen.add(bvid)
            items.append({
                "bvid": bvid,
                "title": "",
                "url": f"https://www.bilibili.com/video/{bvid}/",
            })
    return items


def merge(groups):
    """Round-robin merge so no single keyword fills the whole candidate pool."""
    merged, order = {}, []
    index = 0
    while any(index < len(group) for group in groups):
        for group in groups:
            if index >= len(group):
                continue
            item = group[index]
            bvid = item["bvid"]
            if bvid not in merged:
                merged[bvid] = item
                order.append(bvid)
            elif not merged[bvid].get("title") and item.get("title"):
                merged[bvid]["title"] = item["title"]
        index += 1
    return [merged[bvid] for bvid in order]


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Extract BVIDs from Bilibili search markdown")
    parser.add_argument("inputs", nargs="*", help="markdown files; omit to read stdin")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    if args.inputs:
        groups = [extract(Path(path).read_text(encoding="utf-8")) for path in args.inputs]
    else:
        groups = [extract(sys.stdin.read())]

    items = merge(groups)
    payload = {"count": len(items), "items": items}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"extracted {len(items)} videos -> {args.out}")
    else:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
