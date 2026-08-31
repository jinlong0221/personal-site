#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_games_table_mobile_v2.py — 窄屏表格排版修复 v2。

上一版把 table-layout:fixed 加到了 .info-table 主规则，桌面端也会被影响。
修正：主规则只保留 word-break:break-word（桌面无副作用），
     table-layout:fixed 仅在 @media(max-width:600px) 断点内启用。
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "static", "games")

PATCHES = [
    # 1) 主规则：去掉上一版误加的 table-layout:fixed
    (
        ".info-table{table-layout:fixed;width:100%;border-collapse:collapse;"
        "background:var(--gcard);border:1px solid var(--gb);border-radius:10px;"
        "overflow:hidden;margin-bottom:20px}",
        ".info-table{width:100%;border-collapse:collapse;"
        "background:var(--gcard);border:1px solid var(--gb);border-radius:10px;"
        "overflow:hidden;margin-bottom:20px}",
    ),
    # 2) 第一个 600px 断点：table-layout:fixed 放在这里
    (
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".detail-hero h1{font-size:1.7rem}.screenshot-grid{grid-template-columns:1fr}"
        ".info-table th{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
        "@media(max-width:600px){.info-table{table-layout:fixed}"
        ".pro-cons{grid-template-columns:1fr}.detail-hero h1{font-size:1.7rem}"
        ".screenshot-grid{grid-template-columns:1fr}"
        ".info-table th{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
    ),
    # 3) 第二个 600px 断点：同样
    (
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".game-title-wrap h1{font-size:1.7rem}"
        ".info-table th{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
        "@media(max-width:600px){.info-table{table-layout:fixed}"
        ".pro-cons{grid-template-columns:1fr}.game-title-wrap h1{font-size:1.7rem}"
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
        assert n == 1, f"{path}: {old[:50]!r} 命中 {n} 次"
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
    print(f"\n共修正 {n_fix}/{len(files)} 个游戏页")


if __name__ == "__main__":
    sys.exit(main())
