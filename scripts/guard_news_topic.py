#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_news_topic.py — 板块新闻「主题一致性」守卫（防错板）。

历史教训（2026-09-21）：自动更新任务把「文玩手串」错认成「黄金/金手镯」，
把金价/现货金/品牌金店等内容写进了 bracelet-news.json。

本脚本对静态新闻 JSON 做关键词红线扫描：若某板命中其「禁止词」，
退出码非零，调用方（CI / 自动提交前）应判失败、禁止上线。

用法：
  python3 scripts/guard_news_topic.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 各新闻板 → 禁止出现的关键词（命中任一即判主题错配 / 错板）。
# 仅列已确证的错配板，后续可按需扩展。
FORBIDDEN = {
    "bracelet-news.json": [
        "金价", "现货金", "黄金", "金饰", "足金", "美联储", "盎司", "XAU",
        "周大福", "老凤祥", "老庙", "回收价", "品牌金", "国际金价", "金店",
    ],
}


def _scan_file(fname):
    path = os.path.join(ROOT, "static", fname)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        return [f"  [{fname}] JSON 解析失败: {e}"]

    bad = []
    news = data.get("news", []) if isinstance(data, dict) else []
    for i, item in enumerate(news):
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        for kw in FORBIDDEN.get(fname, []):
            if kw and kw in content:
                snippet = content[:42]
                bad.append(f"  [{fname}] news[{i}] 命中禁止词「{kw}」: {snippet}…")
    return bad


def main():
    fails = []
    for fname in FORBIDDEN:
        fails.extend(_scan_file(fname))

    if fails:
        print("❌ 新闻主题一致性守卫未通过（发现错板内容）：")
        for line in fails:
            print(line)
        sys.exit(1)

    print("✅ 新闻主题一致性守卫通过：未命中任何错板禁止词。")
    sys.exit(0)


if __name__ == "__main__":
    main()
