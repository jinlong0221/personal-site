#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_home_feed.py — 聚合各板块 *-news.json 的最新一条新闻，生成首页「今日更新」聚合源
static/home-feed.json，供 static/js/home-feed.js 在首页渲染。

- 取每个新闻文件数组首条（自动化约定：当天新闻前置到最前）作为该板块最新动态。
- 跨板块按日期倒序，截最多 8 条。
- CI 部署前自动运行，保证每次部署都基于最新新闻数据；本地提交前亦可运行以保持仓库一致。
"""
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hugo-site/
STATIC = os.path.join(ROOT, "static")

# 板块文件（仓库根 static/ 下） -> 中文显示名
BOARD_FILES = {
    "tesla-news.json": "特斯拉",
    "apple-news.json": "苹果新品",
    "marvel-news.json": "漫威宇宙",
    "herbs-news.json": "中药材",
    "health-tea-news.json": "养生茶",
    "zisha-news.json": "紫砂艺术",
    "bracelet-news.json": "文玩手串",
    "sheyang-news.json": "射阳动态",
    "chinajoy-news.json": "ChinaJoy",
    "console-news.json": "游戏主机",
}
# 子目录新闻文件（页面以相对路径加载，须写入原路径）
SUB_BOARD_FILES = {
    os.path.join("tesla", "fsd-news.json"): "特斯拉 FSD",
}

MAX_ITEMS = 8


def sort_key(item):
    """按 月-日 倒序；跨年（去年底）按去年处理，避免排序错乱。"""
    d = str(item.get("date", ""))
    parts = d.split("-")
    try:
        mm, dd = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return (0, 0, 0)
    now = datetime.now()
    yr = now.year
    if mm > now.month:  # 大概率属于上一年底
        yr -= 1
    return (yr, mm, dd)


def collect():
    items = []
    sources = []

    def grab(path, board):
        if not os.path.exists(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[home-feed] 跳过 {os.path.relpath(path, ROOT)}: {e}")
            return
        if not isinstance(data, dict):
            return
        news = data.get("news") or []
        if not news or not isinstance(news[0], dict):
            return
        top = news[0]
        items.append({
            "board": board,
            "date": top.get("date", ""),
            "content": top.get("content", ""),
            "url": top.get("url", ""),
            "tags": top.get("tags", []),
            "sources": top.get("sources", []),
        })

    for fname, board in BOARD_FILES.items():
        grab(os.path.join(STATIC, fname), board)
    for rel, board in SUB_BOARD_FILES.items():
        grab(os.path.join(STATIC, rel), board)

    items.sort(key=sort_key, reverse=True)
    return items[:MAX_ITEMS]


def main():
    items = collect()
    out = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(items),
        "items": items,
    }
    out_path = os.path.join(STATIC, "home-feed.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[home-feed] 已生成 {os.path.relpath(out_path, ROOT)}（{len(items)} 条）")


if __name__ == "__main__":
    main()
