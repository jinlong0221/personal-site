#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_games_table_mobile.py — 修复所有游戏详情页的窄屏表格排版。

问题：.info-table 没有 table-layout:fixed，移动端浏览器把每个汉字拆成单字符换行。
修复（仅改内联 <style> 块，不动 HTML）：

  1) .info-table           加 table-layout:fixed
  2) .info-table th/td     加 word-break:break-word（中文按词组断）
  3) @media(max-width:600px) 两个断点都加：
        .info-table th{width:60px !important; padding:8px 10px; font-size:.9rem}
        .info-table td{padding:8px 10px; font-size:.9rem}

幂等：所有替换都用 assert count==1 防静默跳过。
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "static", "games")

PATCHES = [
    # 1) 主规则：加 table-layout:fixed
    (
        ".info-table{width:100%;border-collapse:collapse;background:var(--gcard);"
        "border:1px solid var(--gb);border-radius:10px;overflow:hidden;margin-bottom:20px}",
        ".info-table{table-layout:fixed;width:100%;border-collapse:collapse;background:var(--gcard);"
        "border:1px solid var(--gb);border-radius:10px;overflow:hidden;margin-bottom:20px}",
    ),
    # 2) th/td：加 word-break:break-word
    (
        ".info-table th,.info-table td{padding:11px 16px;text-align:left;"
        "border-bottom:1px solid var(--gb);font-size:0.98rem}",
        ".info-table th,.info-table td{padding:11px 16px;text-align:left;"
        "border-bottom:1px solid var(--gb);font-size:0.98rem;word-break:break-word}",
    ),
    # 3) 第一个 600px 断点：追加表格规则
    (
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".detail-hero h1{font-size:1.7rem}.screenshot-grid{grid-template-columns:1fr}}",
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".detail-hero h1{font-size:1.7rem}.screenshot-grid{grid-template-columns:1fr}"
        ".info-table th{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
    ),
    # 4) 第二个 600px 断点：同样追加
    (
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".game-title-wrap h1{font-size:1.7rem}}",
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".game-title-wrap h1{font-size:1.7rem}"
        ".info-table th{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
    ),
]


def fix_one(path):
    s = open(path, encoding="utf-8").read()
    if ".info-table{" not in s:
        return False
    for old, new in PATCHES:
        n = s.count(old)
        if n == 0:
            continue
        assert n == 1, f"{path}: {old[:40]!r} 命中 {n} 次"
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)
    return True


def main():
    files = sorted(glob.glob(os.path.join(GAMES, "*.html")))
    n_fix = 0
    for f in files:
        if fix_one(f):
            n_fix += 1
            print(f"  ✅ {os.path.basename(f)}")
    print(f"\n共修复 {n_fix}/{len(files)} 个游戏页")


if __name__ == "__main__":
    sys.exit(main())
