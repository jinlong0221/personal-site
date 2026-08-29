#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_related.py — 生成全站「相关阅读」数据 static/data/related.json

背景：全站 185 页之间正文内链近乎为零，板块是孤岛，185 页的价值没有被放大。
本脚本建立文章之间的关联，供 apply_related.py 静态注入「相关阅读」区块。

关联依据（无需第三方分词库）：
  1. 板块归属（权重最高）—— content-index.json 的 category 字段可用时优先，
     否则按 URL 规则推断（console-* / pages/zisha/* / tesla/* / games/* /
     herbs/* / bracelet/*）。
  2. 标题中文 bigram 的 Jaccard 相似度（捕捉"地龙/水蛭"这类同题材词面重合）。
  3. 标签重合（content-index 里有标签的文章才参与）。
  4. 同板块兜底补足，保证每篇都有 N 条相关阅读。

用法：
  python3 scripts/build_related.py            # 写入 static/data/related.json
  python3 scripts/build_related.py --check    # 只打印统计，不写文件
"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "static", "data", "content-index.json")
OUT = os.path.join(ROOT, "static", "data", "related.json")

TOP_N = 4  # 每篇给出的相关阅读条数

# 功能性/私有页不参与关联
EXCLUDE = {
    "/404.html", "/offline.html", "/search.html", "/bookmarks.html",
    "/privacy.html", "/changelog.html", "/about.html", "/status-history.html",
}

# URL 前缀 → 板块
URL_BOARD_RULES = [
    ("/pages/zisha/", "紫砂"),
    ("/console-", "游戏主机"),
    ("/tesla/", "特斯拉"),
    ("/games/", "游戏"),
    ("/herbs/", "中药材香料"),
    ("/bracelet/", "文玩手串"),
]

# 根级单页（无目录可依）按文件名 → 板块
FILE_BOARD = {
    "/apple.html": "苹果",
    "/marvel.html": "漫威",
    "/chinajoy.html": "ChinaJoy",
    "/sheyang.html": "射阳本地",
    "/xintan-weather.html": "射阳气象",
    "/typhoon.html": "射阳气象",
    "/guanghui.html": "光辉电力",
    "/health-tea.html": "养生茶",
    "/gaokao.html": "高考志愿",
    "/pitfalls.html": "踩坑记",
    "/calendar.html": "站点工具",
    "/travel.html": "旅行",
    "/console.html": "游戏主机",
    "/herbs.html": "中药材香料",
    "/zisha.html": "紫砂",
    "/games.html": "游戏",
    "/tesla.html": "特斯拉",
    "/bracelet.html": "文玩手串",
}

# 主题组：板块之上的一层粗分类。
# 站内 26 个根级单页各成一个板块（苹果、漫威、ChinaJoy、台风…各只有 1 篇），
# 若只按板块关联，这些页面只能跨板块乱配（苹果→台风）。因此再套一层主题组，
# 让孤立页优先关联同主题的文章（苹果→特斯拉系、台风→射阳天气系）。
TOPIC_GROUPS = {
    "数码产品": ["苹果", "特斯拉"],
    "气象农事": ["射阳气象", "射阳本地", "射阳本地民生"],
    "游戏娱乐": ["ChinaJoy", "漫威", "游戏", "游戏主机"],
    "香道养生": ["中药材香料", "文玩手串", "养生茶", "沉香"],
    "器与藏": ["紫砂"],
    "乡土民生": ["光辉电力", "高考志愿", "射阳本地", "射阳本地民生"],
    "经验与工具": ["踩坑记", "站点工具", "旅行"],
}

# category 字段里无信息量的占位值
WEAK_CATEGORY = {"未分类", "pages", "", None}


def guess_board(url, category):
    """URL 规则优先于 category 字段。

    content-index 的 category 是粗放的（例如把 /games/* 也标成"游戏主机"），
    而 URL 路径能准确反映子板块，因此先按 URL 判定，category 仅作兜底。
    """
    for prefix, board in URL_BOARD_RULES:
        if url.startswith(prefix):
            return board
    if url in FILE_BOARD:
        return FILE_BOARD[url]
    if category not in WEAK_CATEGORY:
        return category
    return "其他"


# 标题形如「Atari 2600 - 游戏主机图鉴…」「Game Boy Advance SP - …」
# 「Nintendo 3DS XL - …」→ 取首个英文词即品牌/系列，同系列应当优先互相关联
BRAND_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9&]*)")


BOARD_TOPIC = {}
for _topic, _boards in TOPIC_GROUPS.items():
    for _b in _boards:
        BOARD_TOPIC.setdefault(_b, _topic)


def topic_of(board):
    return BOARD_TOPIC.get(board, "")


def core_title(title):
    """取标题主体，去掉模板化后缀。

    站内标题多为「四方穿炉 | 紫砂艺术2026实测避坑」「地龙 | 中药材香料2026实测避坑」
    「Nintendo Switch - 游戏主机图鉴详细科普」。后缀与 desc 全是同一套模板文案，
    若参与相似度计算会把所有同板块文章的得分拉平，退化成随机关联。
    """
    t = title or ""
    for sep in ("|", " - ", "－", "—"):
        if sep in t:
            t = t.split(sep)[0]
            break
    return t.strip()


def brand_of(title):
    m = BRAND_RE.search(title or "")
    return m.group(1).lower() if m else ""


CJK = re.compile(r"[\u4e00-\u9fa5]+")


def bigrams(text):
    """取中文 bigram 集合，作为轻量相似度特征。"""
    segs = CJK.findall(text or "")
    s = "".join(segs)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else set()


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    check_only = "--check" in sys.argv
    items = json.load(open(IDX, encoding="utf-8"))

    docs = []
    for it in items:
        url = it.get("url", "")
        if not url or url in EXCLUDE:
            continue
        board = guess_board(url, it.get("category"))
        core = core_title(it.get("title"))
        docs.append({
            "url": url,
            "title": it.get("title", ""),
            "core": core,
            "desc": (it.get("desc") or "")[:80],
                "board": board,
                "topic": topic_of(board),
                "brand": brand_of(core),
            "tags": set(it.get("tags") or []),
            # 只用标题主体算相似度：desc 是模板文案，会稀释区分度
            "bg": bigrams(core),
        })

    by_board = defaultdict(list)
    for d in docs:
        by_board[d["board"]].append(d)

    related = {}
    for d in docs:
        scored = []
        for o in docs:
            if o["url"] == d["url"]:
                continue
            score = 0.0
            if o["board"] == d["board"]:
                score += 1.0
            # 同主题组：让苹果/台风这类"板块内只有自己"的孤立页，
            # 能关联到同主题的文章（苹果→特斯拉系），而不是跨板块乱配
            elif d["topic"] and o["topic"] == d["topic"]:
                score += 0.6
            # 同品牌/系列（如 Game Boy 全系、Atari 全系、Nintendo 全系）权重最高，
            # 避免 88 篇主机页互相随机关联
            if d["brand"] and o["brand"] == d["brand"]:
                score += 2.0
            score += jaccard(d["bg"], o["bg"]) * 3.0
            if d["tags"] & o["tags"]:
                score += 0.8 * len(d["tags"] & o["tags"])
            if score > 0.05:
                scored.append((score, o))
        scored.sort(key=lambda x: (-x[0], x[1]["title"]))

        picks = [o for _, o in scored[:TOP_N]]
        # 同板块兜底：不足 TOP_N 时用同板块其它文章补齐
        if len(picks) < TOP_N:
            have = {p["url"] for p in picks}
            for o in by_board.get(d["board"], []):
                if o["url"] != d["url"] and o["url"] not in have:
                    picks.append(o)
                    have.add(o["url"])
                if len(picks) >= TOP_N:
                    break

        related[d["url"]] = [
            {
                "url": p["url"],
                "title": p["title"],
                # 展示用的短标题（去掉「| 中药材香料2026实测避坑」这类模板后缀）
                "name": p["core"] or p["title"],
                "desc": p["desc"],
                "board": p["board"],
            }
            for p in picks[:TOP_N]
        ]

    board_stat = defaultdict(int)
    for d in docs:
        board_stat[d["board"]] += 1

    print(f"文章数: {len(docs)}")
    print("板块分布:", dict(sorted(board_stat.items(), key=lambda x: -x[1])))
    empty = [u for u, v in related.items() if not v]
    print(f"无相关阅读的页面: {len(empty)}")

    if not check_only:
        json.dump(related, open(OUT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"已写入 {OUT}")

    # 抽查
    print("\n=== 抽查 ===")
    for u in ["/herbs/dilong.html", "/pages/zisha/detail-sifangchuanlu.html",
              "/console-switch.html", "/games/wukong.html"]:
        if u in related:
            print(f"\n{u}")
        for r in related[u]:
            print(f"  → [{r['board']}] {r['name']}  {r['url']}")


if __name__ == "__main__":
    main()
