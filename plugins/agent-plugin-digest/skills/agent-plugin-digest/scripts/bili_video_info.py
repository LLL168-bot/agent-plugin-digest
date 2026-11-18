#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch Bilibili video titles/descriptions and extract GitHub links.

Uses a cookie bootstrap and paced retries for the 412 anti-bot response.
If the error rate is still high, the caller should fall back to
firecrawl_scrape for individual video pages.
"""
import argparse
import datetime as dt
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import load, utf8_stdio  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
VIEW_API = "https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
GH_RE = re.compile(r"https?://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+")


def build_opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def bootstrap(opener):
    request = urllib.request.Request("https://www.bilibili.com/", headers={"User-Agent": UA})
    try:
        opener.open(request, timeout=20).read(2048)
    except Exception:
        pass


def fetch(opener, bvid, retries):
    url = VIEW_API.format(bvid=bvid)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Referer": f"https://www.bilibili.com/video/{bvid}/"},
    )
    for attempt in range(retries):
        try:
            with opener.open(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 412 and attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
                bootstrap(opener)
                continue
            raise
        except urllib.error.URLError:
            if attempt == retries - 1:
                raise
            time.sleep(3)
    return None


def to_item(bvid, data):
    video = data.get("data") or {}
    desc = video.get("desc") or ""
    links = []
    for link in GH_RE.findall(desc):
        link = link.rstrip(".,;:)]}'\"")
        if link not in links:
            links.append(link)
    published = video.get("pubdate")
    return {
        "bvid": bvid,
        "url": f"https://www.bilibili.com/video/{bvid}/",
        "title": video.get("title") or "",
        "desc": desc,
        "pubdate": dt.datetime.fromtimestamp(published).isoformat(timespec="minutes") if published else "",
        "owner": (video.get("owner") or {}).get("name") or "",
        "github": links,
        "error": None,
    }


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Fetch Bilibili video info and GitHub links")
    parser.add_argument("--config", default="")
    parser.add_argument("--input", help="JSON from extract_bvids.py")
    parser.add_argument("--bvids", default="", help="comma separated BVIDs (alternative to --input)")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0)
    parser.add_argument("--retries", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cfg = load(args.config or None)["bilibili"]
    limit = args.limit or cfg["video_info_limit"]
    delay = args.delay or cfg["request_delay_seconds"]
    retries = args.retries or cfg["retries"]

    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        bvids = [entry["bvid"] for entry in payload.get("items", [])]
    else:
        bvids = [part.strip() for part in args.bvids.split(",") if part.strip()]
    bvids = bvids[:limit]

    opener = build_opener()
    bootstrap(opener)
    results = []
    for index, bvid in enumerate(bvids):
        if index:
            time.sleep(delay)
        try:
            data = fetch(opener, bvid, retries)
            item = to_item(bvid, data or {})
            if not item["title"]:
                item["error"] = "empty_response"
        except Exception as exc:
            item = {
                "bvid": bvid,
                "url": f"https://www.bilibili.com/video/{bvid}/",
                "title": "",
                "desc": "",
                "pubdate": "",
                "owner": "",
                "github": [],
                "error": str(exc),
            }
        results.append(item)
        status = "ok" if not item["error"] else f"error: {item['error']}"
        print(f"[{index + 1}/{len(bvids)}] {bvid} {status}", file=sys.stderr)

    errors = sum(1 for entry in results if entry["error"])
    payload = {"count": len(results), "errors": errors, "items": results}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(results)} videos ({errors} errors) -> {args.out}")
    if results and errors / len(results) > cfg["fallback_error_rate"]:
        print("WARN: error rate above threshold; fall back to firecrawl_scrape per video", file=sys.stderr)


if __name__ == "__main__":
    main()
