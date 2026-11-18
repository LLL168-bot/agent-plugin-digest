#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply configurable mechanical filters to Bilibili candidates.

Produces a deterministic ranked candidate list. The final N is chosen later by
history.py together with the continuation state.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import load, utf8_stdio  # noqa: E402
from _keys import item_key  # noqa: E402


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Filter and rank Bilibili candidates")
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cfg = load(args.config or None)["bilibili"]
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    limit = args.limit or cfg["candidate_limit"]

    selected, excluded, seen = [], [], set()
    for item in payload.get("items", []):
        title = (item.get("title") or "").strip()
        reason = None
        if item.get("error"):
            reason = f"fetch_error: {item['error']}"
        elif cfg.get("title_include_keywords") and not any(
            word.lower() in title.lower() for word in cfg["title_include_keywords"]
        ):
            reason = "missing_title_keyword"
        elif cfg["single_plugin_only"] and any(
            word.lower() in title.lower() for word in cfg["exclude_title_keywords"]
        ):
            reason = "compilation_or_ranking_title"
        elif cfg["require_github_repo"] and not item.get("github"):
            reason = "missing_github_repo"

        key = item_key(item, "bilibili")
        if reason is None and key in seen:
            reason = "duplicate_project"

        if reason:
            excluded.append({"bvid": item.get("bvid"), "title": title, "reason": reason})
            continue
        seen.add(key)
        selected.append(item)

    # Deterministic ranking: newest first; with prefer_github_repo, repo-backed items first.
    selected.sort(key=lambda entry: entry.get("bvid") or "")
    selected.sort(key=lambda entry: entry.get("pubdate") or "", reverse=True)
    if cfg["prefer_github_repo"]:
        selected.sort(key=lambda entry: bool(entry.get("github")), reverse=True)

    selected = selected[:limit]
    result = {
        "ranked_count": len(selected),
        "excluded_count": len(excluded),
        "selection_rules": {
            "keywords": cfg.get("keywords") or [cfg.get("keyword", "")],
            "order": cfg["order"],
            "single_plugin_only": cfg["single_plugin_only"],
            "require_github_repo": cfg["require_github_repo"],
            "prefer_github_repo": cfg["prefer_github_repo"],
            "exclude_title_keywords": cfg["exclude_title_keywords"],
            "title_include_keywords": cfg.get("title_include_keywords") or [],
            "candidate_limit": limit,
        },
        "items": selected,
        "excluded": excluded,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ranked {len(selected)}, excluded {len(excluded)} -> {args.out}")


if __name__ == "__main__":
    main()
