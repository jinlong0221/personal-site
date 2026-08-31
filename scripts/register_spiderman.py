#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
register_spiderman.py — 把两款蜘蛛侠登记进站点地图与游戏库列表页。

1) data/sitemap_extra.json：在末尾（新游戏区块之后）追加 2 条，
   否则 build_content_index.py 扫不到 → 不进搜索索引、不进 sitemap、拿不到相关阅读。
2) static/games.html：在「已通关」区末尾插入 2 张 game-card，
   并把该区 count 从 4 改成 6。

幂等：已登记则跳过，重跑不会重复插入。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(ROOT, "data", "sitemap_extra.json")
LIST = os.path.join(ROOT, "static", "games.html")

NEW_URLS = [
    ("/games/marvels-spider-man-remastered.html", "0.6"),
    ("/games/marvels-spider-man-2.html", "0.6"),
]

CARDS = [
    {
        "slug": "marvels-spider-man-remastered",
        "zh": "漫威蜘蛛侠 重制版",
        "wh": (1600, 669),
        "tags": ["开放世界", "动作冒险", "超级英雄"],
    },
    {
        "slug": "marvels-spider-man-2",
        "zh": "漫威蜘蛛侠 2",
        "wh": (1600, 900),
        "tags": ["开放世界", "动作冒险", "双主角"],
    },
]


def card_html(c):
    w, h = c["wh"]
    tags = "".join(f'<span class="game-tag">{t}</span>' for t in c["tags"])
    return (
        f'<a href="games/{c["slug"]}.html" class="game-card">\n'
        f'<img width="{w}" height="{h}" loading="lazy" class="game-cover" '
        f'src="img/games/{c["slug"]}-cover.webp" alt="{c["zh"]}">\n'
        '<div class="game-info">\n'
        f'<div class="game-title">{c["zh"]}</div>\n'
        '<div class="game-meta">\n'
        '<span class="platform-badge">PS5</span>\n'
        '<span class="status-badge status-completed">✅ 已通关</span>\n'
        "</div>\n"
        '<div class="game-tags">\n'
        f"{tags}\n"
        "</div>\n"
        "</div>\n"
        "</a>"
    )


def do_sitemap():
    data = json.load(open(SITEMAP, encoding="utf-8"))
    have = {d["url"] for d in data}
    added = 0
    for url, prio in NEW_URLS:
        if url in have:
            print(f"  · sitemap 已存在，跳过：{url}")
            continue
        data.append({"url": url, "priority": prio})
        added += 1
    if added:
        json.dump(data, open(SITEMAP, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        open(SITEMAP, "a", encoding="utf-8").write("\n")
    print(f"✅ sitemap_extra.json：{len(data)} 条（新增 {added}）")


def do_list():
    s = open(LIST, encoding="utf-8").read()
    todo = [c for c in CARDS if f'games/{c["slug"]}.html' not in s]
    for c in CARDS:
        if c not in todo:
            print(f"  · 列表页已存在，跳过：{c['slug']}")
    if todo:
        # 一次性拼好再插入：逐张插会让后一张跑到前一张前面，顺序颠倒
        blob = "\n" + "\n".join(card_html(c) for c in todo)
        # 锚点：「已通关」区的最后一张卡（onimusha-3）之后的 </a>
        i = s.find('href="games/onimusha-3.html"')
        assert i != -1, "找不到 onimusha-3 锚点"
        j = s.find("</a>", i)
        assert j != -1, "找不到 onimusha-3 卡片结尾"
        ins = j + len("</a>")
        s = s[:ins] + blob + s[ins:]
        print(f"  + 已插入 {len(todo)} 张卡片")

    # 已通关区 count：按该区实际卡片数重算，幂等
    m = re.search(
        r'(<span class="icon">✅</span><span>已通关</span><span class="count">)'
        r"(\d+)(</span>)",
        s,
    )
    assert m, "已通关区 count 定位失败"
    # 该区卡片 = 已通关标题之后、下一个 section 之前的 game-card（不含 follow-card）
    head, tail = m.end(), s.find("<!--", m.end())
    seg = s[head:tail] if tail != -1 else s[head:]
    real = len(re.findall(r'class="game-card"(?!\s)', seg))
    assert real >= 4, f"已通关区卡片数异常：{real}"
    s = s[: m.start(2)] + str(real) + s[m.end(2):]

    open(LIST, "w", encoding="utf-8").write(s)
    print(f"✅ games.html：卡片共 {len(re.findall(r'class=\"game-card', s))} 张，"
          f"已通关区 count={real}")


def main():
    print("— 站点地图 —")
    do_sitemap()
    print("— 游戏库列表页 —")
    do_list()


if __name__ == "__main__":
    sys.exit(main())
