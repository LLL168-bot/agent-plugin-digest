#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch continuation state: select the next ranked items and record delivered ones.

Commands:
  select  -- filter ranked candidates against history and return the next batch
  record  -- mark a successfully generated batch as delivered
  status  -- show the current state
  reset   -- clear the state (requires --yes)
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import load, utf8_stdio  # noqa: E402
from _keys import item_key  # noqa: E402


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def resolve_state(args, data):
    raw = args.state or data["history"]["state_file"]
    return Path(raw).expanduser()


def load_state(path):
    if path.is_file():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid history state {path}: {exc}")
    else:
        state = {}
    state.setdefault("version", 1)
    state.setdefault("batch_count", 0)
    state.setdefault("seen", {})
    state.setdefault("updated_at", "")
    return state


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def rank_github(items, cfg):
    ranked = list(items)
    ranked.sort(key=lambda entry: entry.get("full_name") or "")
    if cfg["github"]["sort"] == "updated":
        ranked.sort(key=lambda entry: entry.get("pushed_at") or "", reverse=True)
    else:
        ranked.sort(key=lambda entry: entry.get("stars", 0), reverse=True)
    return ranked


def rank_bilibili(items, cfg):
    ranked = list(items)
    ranked.sort(key=lambda entry: entry.get("bvid") or "")
    ranked.sort(key=lambda entry: entry.get("pubdate") or "", reverse=True)
    if cfg["bilibili"]["prefer_github_repo"]:
        ranked.sort(key=lambda entry: bool(entry.get("github")), reverse=True)
    return ranked


def dedupe(items, source):
    out, seen = [], set()
    for item in items:
        key = item_key(item, source)
        if key in seen:
            continue
        seen.add(key)
        copy = dict(item)
        copy["key"] = key
        out.append(copy)
    return out


def cmd_select(args, data):
    cfg = data
    history_cfg = cfg["history"]
    state_path = resolve_state(args, cfg)
    state = load_state(state_path)
    enabled = history_cfg.get("enabled", True) and not args.no_history
    seen = set(state.get("seen", {})) if enabled else set()

    gh_payload = json.loads(Path(args.github).read_text(encoding="utf-8"))
    bi_payload = json.loads(Path(args.bilibili).read_text(encoding="utf-8"))

    gh_ranked = dedupe(rank_github(gh_payload.get("items", []), cfg), "github")
    bi_ranked = dedupe(rank_bilibili(bi_payload.get("items", []), cfg), "bilibili")

    gh_fresh = [item for item in gh_ranked if item["key"] not in seen]
    gh_final = cfg["github"]["final_count"]
    gh_selected = gh_fresh[:gh_final]
    gh_keys = {item["key"] for item in gh_selected}

    bi_fresh = [
        item for item in bi_ranked
        if item["key"] not in seen and item["key"] not in gh_keys
    ]
    bi_final = cfg["bilibili"]["final_count"]
    bi_selected = bi_fresh[:bi_final]

    batch = state["batch_count"] + 1 if enabled else 1
    result = {
        "batch": batch,
        "history_enabled": enabled,
        "state_file": str(state_path),
        "github": {
            "requested": gh_final,
            "selected_count": len(gh_selected),
            "remaining": max(0, len(gh_fresh) - len(gh_selected)),
            "exhausted": len(gh_selected) < gh_final,
            "items": gh_selected,
        },
        "bilibili": {
            "requested": bi_final,
            "selected_count": len(bi_selected),
            "remaining": max(0, len(bi_fresh) - len(bi_selected)),
            "exhausted": len(bi_selected) < bi_final,
            "items": bi_selected,
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"batch {batch}: github {len(gh_selected)}/{gh_final} "
        f"(remaining {result['github']['remaining']}), "
        f"bilibili {len(bi_selected)}/{bi_final} "
        f"(remaining {result['bilibili']['remaining']}) -> {args.out}"
    )
    if result["github"]["exhausted"] or result["bilibili"]["exhausted"]:
        print("WARN: candidate pool exhausted for at least one source", file=sys.stderr)


def cmd_record(args, data):
    cfg = data
    state_path = resolve_state(args, cfg)
    if not cfg["history"].get("enabled", True):
        print("history disabled; nothing recorded")
        return

    state = load_state(state_path)
    expected = state["batch_count"] + 1
    batch = args.batch or expected
    if batch != expected and not args.force:
        raise SystemExit(
            f"batch {batch} does not match expected {expected}; "
            "use --batch with the value returned by select, or --force"
        )

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    added, skipped = 0, 0
    timestamp = now()
    for section in payload.get("sections", []):
        for item in section.get("items", []):
            key = item_key(item)
            if key in state["seen"]:
                skipped += 1
                continue
            state["seen"][key] = {
                "first_seen": timestamp,
                "last_seen": timestamp,
                "title": item.get("name") or "",
                "source": "github" if "github.com" in (item.get("url") or "") else
                          "bilibili" if "bilibili.com" in (item.get("url") or "") else "other",
                "batch": batch,
            }
            added += 1

    state["batch_count"] = max(state["batch_count"], batch)
    state["updated_at"] = timestamp
    save_state(state_path, state)
    print(f"recorded batch {batch}: {added} new, {skipped} already seen -> {state_path}")


def cmd_status(args, data):
    state_path = resolve_state(args, data)
    state = load_state(state_path)
    print(json.dumps({
        "state_file": str(state_path),
        "batch_count": state["batch_count"],
        "seen_count": len(state["seen"]),
        "updated_at": state["updated_at"],
        "enabled": data["history"].get("enabled", True),
    }, ensure_ascii=False, indent=2))


def cmd_reset(args, data):
    if not args.yes:
        raise SystemExit("refusing to reset without --yes")
    state_path = resolve_state(args, data)
    state = {
        "version": 1,
        "batch_count": 0,
        "seen": {},
        "updated_at": now(),
    }
    save_state(state_path, state)
    print(f"reset history -> {state_path}")


def add_common_options(parser):
    parser.add_argument("--config", default=argparse.SUPPRESS)
    parser.add_argument("--state", default=argparse.SUPPRESS, help="override history.state_file")


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Batch continuation state for the digest")
    add_common_options(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    select = sub.add_parser("select", help="select the next ranked batch")
    add_common_options(select)
    select.add_argument("--github", required=True)
    select.add_argument("--bilibili", required=True)
    select.add_argument("--out", required=True)
    select.add_argument("--no-history", action="store_true")

    record = sub.add_parser("record", help="record a generated batch")
    add_common_options(record)
    record.add_argument("--input", required=True)
    record.add_argument("--batch", type=int, default=0)
    record.add_argument("--force", action="store_true")

    status = sub.add_parser("status", help="show state")
    add_common_options(status)
    reset = sub.add_parser("reset", help="clear state")
    add_common_options(reset)
    reset.add_argument("--yes", action="store_true")

    args = parser.parse_args()
    args.config = getattr(args, "config", "")
    args.state = getattr(args, "state", "")
    data = load(args.config or None)
    handlers = {
        "select": cmd_select,
        "record": cmd_record,
        "status": cmd_status,
        "reset": cmd_reset,
    }
    handlers[args.command](args, data)


if __name__ == "__main__":
    main()
