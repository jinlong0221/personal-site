#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_changelog_entry.py — 往 changelog 三副本同一位置插入同一条更新日志

changelog 有三份（data/changelog.json、static/changelog.json、static/data/changelog.json），
guard_changelog.py 会校验三者 MD5 一致，所以必须插完全相同的 entry。

用法：
  python3 scripts/add_changelog_entry.py --date "2026-09-12 16:50" --text "……"
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIES = [
    os.path.join(ROOT, "data", "changelog.json"),
    os.path.join(ROOT, "static", "changelog.json"),
    os.path.join(ROOT, "static", "data", "changelog.json"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for p in COPIES:
        if not os.path.exists(p):
            print(f"! 缺失 {p}", file=sys.stderr)
            return 1

    entry = {"date": args.date, "content": args.text}
    payloads = []
    for p in COPIES:
        items = json.load(open(p, encoding="utf-8"))
        if any(e.get("content") == args.text for e in items[:5]):
            print(f"! {os.path.relpath(p, ROOT)} 已在头部包含相同条目，跳过", file=sys.stderr)
            return 1
        items.insert(0, entry)
        payloads.append((p, items))

    if args.dry_run:
        print("dry-run：将写入", len(payloads), "份")
        return 0

    for p, items in payloads:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  已写入 {os.path.relpath(p, ROOT)}（{len(items)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
