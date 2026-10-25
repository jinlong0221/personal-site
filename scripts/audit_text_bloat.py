#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_text_bloat.py — 全站文案臃肿度体检（技术交流站「取其精华」改造的诊断工具）

回答三个问题：
  ① 哪些页文字最多（臃肿重灾区排序）
  ② 每个板块的「说明性文字」占多少（导读/写在前面/写在最后这类注水区）
  ③ 哪些段落被多个页面重复使用（跨页套话，最典型的浮肿）

用法：
  python3 scripts/audit_text_bloat.py --root public            # 体检 + 排序
  python3 scripts/audit_text_bloat.py --root public --top 30   # 只看前 30
  python3 scripts/audit_text_bloat.py --root public --dupes    # 只看跨页重复段
  python3 scripts/audit_text_bloat.py --root public --json     # 机器可读
"""
import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict

CJK = re.compile(r"[\u4e00-\u9fff]")
TAG = re.compile(r"<[^>]+>")
SCRIPT_STYLE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.I | re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
P_BLOCK = re.compile(r"<p\b[^>]*>(.*?)</p>", re.I | re.S)
# 导读/说明性容器：这些块里几乎全是「写给读者的话」，是注水高发区
BOILER_LABEL = re.compile(
    r"(写在前面|写在最后|导读|引言|前言|说明|须知|小贴士|温馨提示|编者按|"
    r"为什么|背景|关于本站|本站说明|使用说明|阅读指南|导航说明)", re.I
)


def strip_html(s: str) -> str:
    s = SCRIPT_STYLE.sub(" ", s)
    s = COMMENT.sub(" ", s)
    s = TAG.sub(" ", s)
    return html.unescape(s)


def cjk_count(s: str) -> int:
    return len(CJK.findall(s))


def text_blocks(raw: str):
    """取出正文段落（<p>）的纯文本，作为重复检测单元。"""
    out = []
    for m in P_BLOCK.finditer(raw):
        t = strip_html(m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        if len(CJK.findall(t)) >= 12:
            out.append(t)
    return out


def page_files(root: str):
    for dp, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(".html"):
                yield os.path.join(dp, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="public")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--dupes", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(f"! 目录不存在: {args.root}", file=sys.stderr)
        return 1

    rows = []
    block_index = defaultdict(set)   # 段落文本 -> 出现该段的页面集合
    for p in page_files(args.root):
        rel = os.path.relpath(p, args.root)
        try:
            raw = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = re.search(r"<main\b.*?</main>", raw, re.I | re.S)
        body = m.group(0) if m else raw
        txt = strip_html(body)
        n_cjk = cjk_count(txt)
        blocks = text_blocks(body)
        if blocks:
            # 指南针：段落前 40 字做 key，避免标点差异导致漏判
            for b in blocks:
                block_index[re.sub(r"\s+", "", b)[:40]].add(rel)
        rows.append({
            "page": rel,
            "cjk": n_cjk,
            "paras": len(blocks),
            "avg": (n_cjk // max(1, len(blocks))),
        })

    rows.sort(key=lambda r: -r["cjk"])
    dupes = {k: sorted(v) for k, v in block_index.items() if len(v) >= 3}

    if args.json:
        print(json.dumps({
            "pages": len(rows),
            "total_cjk": sum(r["cjk"] for r in rows),
            "top": rows[: args.top],
            "dupes": dupes,
        }, ensure_ascii=False, indent=2))
        return 0

    total = sum(r["cjk"] for r in rows)
    print(f"=== 文案臃肿体检：{len(rows)} 页，正文合计 {total} 中文字 ===\n")

    if args.dupes:
        print("--- 跨页重复段落（同一段文字出现在 ≥3 页，典型套话）---")
        for k, pages in sorted(dupes.items(), key=lambda kv: -len(kv[1])):
            print(f"  [{len(pages)} 页] {k}…")
            for pg in pages[:6]:
                print(f"        - {pg}")
            if len(pages) > 6:
                print(f"        … 另 {len(pages) - 6} 页")
        print()
        return 0

    print(f"--- 文字量前 {min(args.top, len(rows))} 页 ---")
    print(f"{'中文字':>8}  {'段数':>5}  {'均段':>5}  页面")
    for r in rows[: args.top]:
        print(f"{r['cjk']:>8}  {r['paras']:>5}  {r['avg']:>5}  {r['page']}")

    if dupes:
        print(f"\n--- 跨页重复段落：{len(dupes)} 组（出现在 ≥3 页）---")
        for k, pages in sorted(dupes.items(), key=lambda kv: -len(kv[1]))[:15]:
            print(f"  [{len(pages):>3} 页] {k[:60]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
