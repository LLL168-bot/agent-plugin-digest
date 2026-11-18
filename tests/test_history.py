#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test: the second batch continues the ranking and never repeats the first."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins" / "agent-plugin-digest" / "skills" / "agent-plugin-digest" / "scripts" / "history.py"


def run(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise SystemExit(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_items(batch):
    payload = json.loads((batch).read_text(encoding="utf-8"))
    sections = []
    for title, key in (("GitHub", "github"), ("Bilibili", "bilibili")):
        items = []
        for entry in payload[key]["items"]:
            url = (entry.get("github") or [entry.get("url")])[0]
            items.append({
                "name": entry.get("full_name") or entry.get("bvid"),
                "intro": "test introduction long enough to avoid the length warning threshold.",
                "url": url,
            })
        sections.append({"title": title, "items": items})
    return {"title": "test", "batch": payload["batch"], "sections": sections}


def main():
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        state = temp / "history.json"
        config = {
            "github": {"topics": ["x"], "candidate_limit": 10, "final_count": 2},
            "bilibili": {"keywords": ["agent 插件"], "candidate_limit": 10,
                         "video_info_limit": 10, "final_count": 2},
            "history": {"enabled": True, "state_file": str(state)},
            "output": {"dir": str(temp / "out")},
        }
        config_path = temp / "config.json"
        dump(config_path, config)

        gh = {"items": [
            {"full_name": f"a/repo{i}", "url": f"https://github.com/a/repo{i}",
             "stars": 100 - i, "pushed_at": "2026-11-01", "description": "x"}
            for i in range(5)
        ]}
        bi = {"items": [
            {"bvid": f"BV{i}", "url": f"https://www.bilibili.com/video/BV{i}/",
             "title": f"item {i}", "pubdate": f"2026-11-1{9-i}T00:00",
             "github": [f"https://github.com/b/p{i}"] if i != 2
                       else ["https://github.com/a/repo0"]}
            for i in range(5)
        ]}
        gh_path, bi_path = temp / "gh.json", temp / "bi.json"
        dump(gh_path, gh)
        dump(bi_path, bi)

        first_path = temp / "first.json"
        run("select", "--github", str(gh_path), "--bilibili", str(bi_path),
            "--config", str(config_path), "--out", str(first_path))
        first = json.loads(first_path.read_text(encoding="utf-8"))
        assert first["batch"] == 1
        assert first["github"]["selected_count"] == 2
        assert first["bilibili"]["selected_count"] == 2

        items_path = temp / "items.json"
        dump(items_path, make_items(first_path))
        run("record", "--input", str(items_path), "--batch", "1", "--config", str(config_path))

        second_path = temp / "second.json"
        run("select", "--github", str(gh_path), "--bilibili", str(bi_path),
            "--config", str(config_path), "--out", str(second_path))
        second = json.loads(second_path.read_text(encoding="utf-8"))
        assert second["batch"] == 2
        first_keys = {item["key"] for item in first["github"]["items"] + first["bilibili"]["items"]}
        second_keys = {item["key"] for item in second["github"]["items"] + second["bilibili"]["items"]}
        assert not (first_keys & second_keys), "batch 2 repeated a batch 1 item"
        assert second["github"]["selected_count"] == 2
        assert second["bilibili"]["selected_count"] == 2

        print("history continuation test passed")


if __name__ == "__main__":
    main()
