#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_games_table_mobile_v5.py — 修掉 v4 引入的「网格列被撑爆」副作用。

v4 的做法：窄屏给 .info-table 加 min-width:480px + 容器 overflow-x:auto。
副作用（本次修复）：
  页面头图区 .detail-hero 是 display:grid，窄屏列定义 grid-template-columns:1fr。
  而 1fr 等价于 minmax(auto,1fr)，网格项的 min-content 宽度会把轨道撑开——
  属性表的最小宽度 480px 于是把整列撑到 480px，而视口只有 390px；
  body 又是 overflow-x:clip，结果右侧约 90px 直接被切掉且滑不出来。

v5 三条：
  1. .detail-hero 窄屏列改 minmax(0,1fr) —— 轨道最小可为 0，不再被内容撑开
  2. .detail-hero>*{min-width:0} —— 兜底，防其它子孙元素再撑爆网格
  3. .game-title-wrap .info-table{min-width:0} —— 头部属性表内容很短，
     让它自适应容器宽度即可，不必横向滚动；正文区表格仍保留 480px 滚动

幂等：只替换 v4 生成的断点文本，重复执行无副作用。
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "static", "games")

# v4 生成的两种断点文本 -> v5
V4_A = (
    "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
    ".detail-hero h1{font-size:1.7rem}.screenshot-grid{grid-template-columns:1fr}"
    ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}"
    ".info-table{min-width:480px;font-size:.92rem}"
    ".info-table th,.info-table td{padding:8px 12px}}"
)
V4_B = (
    "@media(max-width:600px){.pro-cons{grid-template-columns:1fr}"
    ".game-title-wrap h1{font-size:1.7rem}"
    ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}"
    ".info-table{min-width:480px;font-size:.92rem}"
    ".info-table th,.info-table td{padding:8px 12px}}"
)

HERO_FIX = (
    ".detail-hero{grid-template-columns:minmax(0,1fr)}"
    ".detail-hero>*{min-width:0}"
    ".game-title-wrap .info-table{min-width:0}"
)

V5_A = V4_A.replace(
    ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
    HERO_FIX + ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
)
V5_B = V4_B.replace(
    ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
    HERO_FIX + ".table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch}",
)

PATCHES = [(V4_A, V5_A), (V4_B, V5_B)]


def fix_one(path):
    s = open(path, encoding="utf-8").read()
    if ".info-table" not in s:
        return False, "跳过（无表格）"
    hit = 0
    for old, new in PATCHES:
        n = s.count(old)
        if n == 0:
            continue
        assert n == 1, f"{os.path.basename(path)}: 命中 {n} 次，预期 1"
        s = s.replace(old, new)
        hit += 1
    if hit == 0:
        return False, "已处理过/无匹配"
    assert "minmax(0,1fr)" in s, f"{os.path.basename(path)}: 注入失败"
    open(path, "w", encoding="utf-8").write(s)
    return True, f"注入 {hit} 处"


def main():
    files = sorted(glob.glob(os.path.join(GAMES, "*.html")))
    n_fix = 0
    for f in files:
        ok, msg = fix_one(f)
        mark = "✅" if ok else "· "
        print(f"  {mark} {os.path.basename(f):48s} {msg}")
        n_fix += 1 if ok else 0
    print(f"\n共修正 {n_fix}/{len(files)} 个游戏页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
