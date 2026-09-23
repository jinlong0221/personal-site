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
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # hugo-site/
STATIC = os.path.join(ROOT, "static")

# 🔴 北京时间固定偏移。CI 跑在 UTC 容器里，裸 datetime.now() 取到的是 UTC——
# 早期生成的 generated 就这么写出去，导致线上「更新于」整整差 8 小时
# （实测 2026-09-23：构建发生在北京 10:20，文件里写的是 02:20）。
# 生成时间一律走这里，不依赖运行环境的时区设置。
CN_TZ = timezone(timedelta(hours=8))


def now_cn():
    return datetime.now(CN_TZ)

# 板块文件（仓库根 static/ 下） -> 中文显示名
BOARD_FILES = {
    "tesla-news.json": "特斯拉",
    "apple-news.json": "苹果新品",
    "marvel-news.json": "漫威宇宙",
    "health-tea-news.json": "养生茶",
    "zisha-news.json": "紫砂艺术",
    "bracelet-news.json": "文玩手串",
    "sheyang-news.json": "射阳动态",
    "chinajoy-news.json": "ChinaJoy",
    "console-news.json": "主机图鉴",
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
    now = now_cn()
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
    gen = now_cn()
    out = {
        # generated 保留原格式（首页既有渲染依赖它），但时区已修正为北京时间
        "generated": gen.strftime("%Y-%m-%d %H:%M"),
        # generated_at 带显式 +08:00 偏移，供前端精确算「多久之前」
        # （static/js/site-live.js）。ISO 8601 带偏移 = 谁解析都不会错。
        "generated_at": gen.isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    out_path = os.path.join(STATIC, "home-feed.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[home-feed] 已生成 {os.path.relpath(out_path, ROOT)}（{len(items)} 条）")


if __name__ == "__main__":
    main()
