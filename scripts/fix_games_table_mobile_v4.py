#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_games_table_mobile_v4.py — 最终方案：窄屏横向滚动。

经过 v2/v3 实验发现：table-layout:fixed 下中文默认按字断行，
把列宽加宽也救不回来（"拉开距离躲电球，用绝缘装置破防，别贪刀"
在 116px 容器里仍会拆成「拉开距离躲 / 电球」2 段）。

最终方案：
- 桌面端：保持原样（wukong 等页现有桌面布局无变化）
- 移动端（≤600px）：表格容器横向滚动（display:block + overflow-x:auto），
  内部保留表格布局（min-width 让它不被压扁），内容按词组自然断
- 单元格 padding/字号适度收紧，给内容更多空间

撤回 v2/v3 的：table-layout:fixed、第一列强制宽度。
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "static", "games")

PATCHES = [
    # 1) 撤回 table-layout:fixed（v2 误加）
    (
        ".info-table{table-layout:fixed;width:100%;border-collapse:collapse;",
        ".info-table{width:100%;border-collapse:collapse;",
    ),
    # 2) 第一个 600px 断点：去掉 fixed + 强制首列宽，换成横向滚动
    (
        "@media(max-width:600px){.info-table{table-layout:fixed}"
        ".pro-cons{grid-template-columns:1fr}.detail-hero h1{font-size:1.7rem}"
        ".screenshot-grid{grid-template-columns:1fr}"
        ".info-table th:first-child,.info-table td:first-child{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".detail-hero h1{font-size:1.7rem}.screenshot-grid{grid-template-columns:1fr}"
        ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}"
        ".info-table{min-width:480px;font-size:.92rem}"
        ".info-table th,.info-table td{padding:8px 12px}}",
    ),
    # 3) 第二个 600px 断点：同样
    (
        "@media(max-width:600px){.info-table{table-layout:fixed}"
        ".pro-cons{grid-template-columns:1fr}.game-title-wrap h1{font-size:1.7rem}"
        ".info-table th:first-child,.info-table td:first-child{width:60px !important}"
        ".info-table th,.info-table td{padding:8px 10px;font-size:.9rem}}",
        "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
        ".game-title-wrap h1{font-size:1.7rem}"
        ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}"
        ".info-table{min-width:480px;font-size:.92rem}"
        ".info-table th,.info-table td{padding:8px 12px}}",
    ),
]


def fix_one(path):
    s = open(path, encoding="utf-8").read()
    if ".info-table" not in s:
        return False
    for old, new in PATCHES:
        n = s.count(old)
        if n == 0:
            continue
        assert n in (1, 2), f"{path}: {old[:60]!r} 命中 {n} 次"
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
