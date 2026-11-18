#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect GitHub plugin repositories by topic, or verify explicit repositories.

Examples:
  python github_plugins.py --out github.json
  python github_plugins.py --config my-config.json --limit 20 --out github.json
  python github_plugins.py --repos owner/repo1,owner/repo2 --out repos.json
"""
import argparse
import datetime as dt
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import load, utf8_stdio  # noqa: E402

API = "https://api.github.com"
UA = "agent-plugin-digest/1.0"


def api_get(url, token=None, retries=3):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (403, 429):
                reset = exc.headers.get("X-RateLimit-Reset")
                wait = 60
                if reset:
                    try:
                        wait = max(5, int(reset) - int(time.time()) + 2)
                    except ValueError:
                        pass
                wait = min(wait, 120)
                body = exc.read().decode("utf-8", "replace")[:200]
                print(f"[rate-limit] {wait}s (attempt {attempt + 1}): {body}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(3)
        except json.JSONDecodeError:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return None


def normalize(repo):
    return {
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "url": repo.get("html_url"),
        "stars": repo.get("stargazers_count", 0),
        "created_at": (repo.get("created_at") or "")[:10],
        "updated_at": (repo.get("updated_at") or "")[:10],
        "pushed_at": (repo.get("pushed_at") or "")[:10],
        "description": repo.get("description") or "",
        "topics": repo.get("topics") or [],
        "archived": bool(repo.get("archived")),
        "fork": bool(repo.get("fork")),
    }


def keyword_ok(item, include_keywords, exclude_keywords):
    text = f"{item.get('name', '')} {item.get('description', '')}".lower()
    if include_keywords and not any(word.lower() in text for word in include_keywords):
        return False
    if exclude_keywords and any(word.lower() in text for word in exclude_keywords):
        return False
    return True


def collect_topics(cfg, limit, token):
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=cfg["updated_within_days"])
    seen = {}
    topics = cfg["topics"]
    for index, topic in enumerate(topics):
        if index and not token:
            time.sleep(7)  # unauthenticated search: 10 requests/minute
        query = urllib.parse.quote(f"topic:{topic}")
        url = f"{API}/search/repositories?q={query}&sort={cfg['sort']}&order=desc&per_page=100"
        data = api_get(url, token)
        if not data:
            print(f"[warn] no result for topic {topic}", file=sys.stderr)
            continue
        if data.get("message"):
            raise SystemExit(f"GitHub API error: {data['message']}")
        for repo in data.get("items", []):
            if cfg["exclude_forks"] and repo.get("fork"):
                continue
            if cfg["exclude_archived"] and repo.get("archived"):
                continue
            if (repo.get("stargazers_count") or 0) < cfg["min_stars"]:
                continue
            if cfg["require_description"] and not (repo.get("description") or "").strip():
                continue
            pushed = repo.get("pushed_at") or repo.get("updated_at") or ""
            try:
                if dt.datetime.fromisoformat(pushed.replace("Z", "+00:00")) < cutoff:
                    continue
            except ValueError:
                pass
            item = normalize(repo)
            if not keyword_ok(item, cfg["include_keywords"], cfg["exclude_keywords"]):
                continue
            previous = seen.get(item["full_name"])
            if not previous or item["stars"] > previous["stars"]:
                seen[item["full_name"]] = item
    items = list(seen.values())
    # Deterministic ranking used by the batch continuation logic.
    items.sort(key=lambda entry: entry["full_name"])
    if cfg["sort"] == "updated":
        items.sort(key=lambda entry: entry.get("pushed_at") or "", reverse=True)
    else:
        items.sort(key=lambda entry: entry.get("stars", 0), reverse=True)
    return items[:limit]


def collect_repos(names, token):
    out = []
    for name in names:
        name = name.strip()
        if not name or "/" not in name:
            continue
        repo = api_get(f"{API}/repos/{name}", token)
        if repo:
            out.append(normalize(repo))
        else:
            out.append({"full_name": name, "url": f"https://github.com/{name}", "error": "not_found"})
        time.sleep(0.3)
    return out


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Collect or verify GitHub plugin repositories")
    parser.add_argument("--config", default="", help="optional JSON config overriding defaults")
    parser.add_argument("--topics", default="", help="comma separated topics; overrides config")
    parser.add_argument("--repos", default="", help="comma separated owner/repo list (verify mode)")
    parser.add_argument("--limit", type=int, default=0, help="candidate limit; overrides config")
    parser.add_argument("--min-stars", type=int, default=0)
    parser.add_argument("--updated-within-days", type=int, default=0)
    parser.add_argument("--sort", choices=["stars", "updated"], default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data = load(args.config or None)
    cfg = data["github"]
    if args.topics:
        cfg["topics"] = [part.strip() for part in args.topics.split(",") if part.strip()]
    if args.limit:
        cfg["candidate_limit"] = args.limit
    if args.min_stars:
        cfg["min_stars"] = args.min_stars
    if args.updated_within_days:
        cfg["updated_within_days"] = args.updated_within_days
    if args.sort:
        cfg["sort"] = args.sort

    token = os.environ.get("GITHUB_TOKEN") or None
    if args.repos:
        items = collect_repos(args.repos.split(","), token)
        mode = "verify"
    else:
        items = collect_topics(cfg, cfg["candidate_limit"], token)
        mode = "topics"

    result = {
        "mode": mode,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "selection": {
            "topics": cfg["topics"],
            "sort": cfg["sort"],
            "min_stars": cfg["min_stars"],
            "updated_within_days": cfg["updated_within_days"],
        },
        "count": len(items),
        "items": items,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(f"wrote {len(items)} repos -> {args.out}")


if __name__ == "__main__":
    main()
