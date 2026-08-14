#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向各板块 static 页注入「本板块原创」容器 + 加载器脚本。

- 仅注入一次（已含 id="boardOriginals" 则跳过，幂等）。
- 在 </body> 前插入 <section id="boardOriginals" data-board="板块名"> 与
  <script defer src="js/board_originals.js">。
- 板块页已含全站严格 CSP，js/board_originals.js 属 'self' 放行，无需改 CSP。
- 板块名（data-board）必须与后台发布时选择的 board 值完全一致，否则匹配不到。

用法：python3 scripts/inject_board_originals.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# 板块页文件名 -> 板块名（须与后台 board 选项一致）
MAP = {
    "herbs.html": "中药材",
    "health-tea.html": "养生茶",
    "bracelet.html": "文玩手串",
    "tesla.html": "特斯拉",
    "marvel.html": "漫威宇宙",
    "zisha.html": "紫砂艺术",
    "console.html": "游戏主机",
    "chinajoy.html": "ChinaJoy",
    "guanghui.html": "光辉电力",
    "pitfalls.html": "踩坑记",
    "gaokao.html": "高考查分",
    "xintan-weather.html": "农田气象",
    "games.html": "游戏库",
    "typhoon.html": "台风监测",
}

MARKER = 'id="boardOriginals"'
BLOCK = (
    '<section class="board-originals" id="boardOriginals" '
    'data-board="{board}" aria-label="本板块原创"></section>\n'
    '<script defer src="js/board_originals.js"></script>\n'
)


def main():
    for fn, board in MAP.items():
        p = os.path.join(STATIC, fn)
        if not os.path.exists(p):
            print("skip (not found):", fn)
            continue
        html = open(p, encoding="utf-8").read()
        if MARKER in html:
            print("exists:", fn)
            continue
        idx = html.rfind("</body>")
        if idx < 0:
            print("no </body>:", fn)
            continue
        html = html[:idx] + BLOCK.format(board=board) + html[idx:]
        open(p, "w", encoding="utf-8").write(html)
        print("injected:", fn, "->", board)


if __name__ == "__main__":
    main()
