# -*- coding: utf-8 -*-
"""Stable project keys shared by filtering and history."""
import re

REPO_RE = re.compile(r"https?://github\.com/([^/\s#?]+)/([^/\s#?]+)", re.IGNORECASE)


def repo_key(url):
    match = REPO_RE.search(url or "")
    if not match:
        return ""
    owner, name = match.group(1).lower(), match.group(2).lower()
    if name.endswith(".git"):
        name = name[:-4]
    return f"repo:{owner}/{name}"


def bvid_key(bvid):
    return f"bvid:{(bvid or '').upper()}"


def item_key(item, source=""):
    for url in item.get("github") or []:
        key = repo_key(url)
        if key:
            return key
    key = repo_key(item.get("url") or "")
    if key:
        return key
    if item.get("bvid"):
        return bvid_key(item["bvid"])
    if item.get("full_name"):
        return "repo:" + item["full_name"].lower()
    return "url:" + (item.get("url") or "")
