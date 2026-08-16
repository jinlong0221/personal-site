#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_article_meta.py — 为静态文章注入「文章标签」三件套 meta 标签（幂等）。

打标签格式（放每篇文章 <head> 内，紧跟 <meta name="description"> 之后）：
  <!-- 文章标签（手动维护：分类 / 标签 / 更新时间） -->
  <meta name="article-category" content="沉香">
  <meta name="article-tags" content="沉香,鉴别,收藏">
  <meta name="article-updated" content="2026-08-16">

用法：
  python3 scripts/apply_article_meta.py            # 按内置 SAMPLES 注入/更新样例
  python3 scripts/apply_article_meta.py --check    # 只报告将改动哪些文件，不写回

说明：
  - 仅改 <head> 内的标签，正文与链接一律不动。
  - 已存在 article-category/article-tags/article-updated 时只更新 content，不重复插入。
  - 想给其它文章打标签：把文件路径与 (分类, [标签…], 更新时间) 加进 SAMPLES 再运行。
  - Hugo 文章(Markdown)不用本脚本，直接在 frontmatter 加 category/tags/updated 字段。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 打样：覆盖用户示例标签 沉香/紫砂/特斯拉/射阳气象/高考志愿/台风
# 键为相对于仓库根的路径；值为 (分类, [标签列表], 更新时间 YYYY-MM-DD)
SAMPLES = {
    "static/typhoon.html":        ("射阳气象",     ["台风", "射阳气象", "预警"],         "2026-08-15"),
    "static/xintan-weather.html": ("射阳气象",     ["射阳气象", "农田", "天气"],         "2026-08-15"),
    "static/sheyang.html":        ("射阳本地民生", ["射阳", "本地民生", "便民"],         "2026-08-10"),
    "static/gaokao.html":         ("高考志愿",     ["高考志愿", "查分", "志愿填报"],     "2026-06-25"),
    "static/zisha.html":          ("紫砂",         ["紫砂", "壶艺", "收藏"],             "2026-08-01"),
    "static/tesla.html":          ("特斯拉",       ["特斯拉", "用车", "充电"],           "2026-08-01"),
    "static/tesla/fsd.html":      ("特斯拉",       ["特斯拉", "FSD", "自动驾驶"],        "2026-08-10"),
    "static/bracelet.html":       ("文玩手串",     ["文玩", "手串", "收藏"],             "2026-07-20"),
    "static/marvel.html":         ("漫威",         ["漫威", "电影", "宇宙"],             "2026-08-01"),
    "static/console.html":        ("游戏主机",     ["游戏主机", "主机", "评测"],         "2026-08-01"),
    "static/games.html":          ("游戏主机",     ["游戏库", "主机", "攻略"],           "2026-08-01"),
    "static/herbs.html":          ("中药材香料",   ["中药材", "香料", "科普"],           "2026-08-01"),
    "static/health-tea.html":     ("养生茶",       ["养生茶", "茶饮", "调理"],           "2026-08-01"),
    "static/apple.html":          ("苹果",         ["苹果", "新品", "iPhone"],           "2026-08-01"),
    "static/chinajoy.html":       ("ChinaJoy",     ["ChinaJoy", "漫展", "游戏"],         "2026-08-01"),
}

COMMENT = "<!-- 文章标签（手动维护：分类 / 标签 / 更新时间） -->"


def tag_block(cat, tags, updated):
    return (
        COMMENT + "\n"
        f'<meta name="article-category" content="{cat}">\n'
        f'<meta name="article-tags" content="{",".join(tags)}">\n'
        f'<meta name="article-updated" content="{updated}">'
    )


def upsert_meta(html, name, content):
    """在 html 中把 <meta name="name" content="..."> 更新为 content；不存在则标记需插入。"""
    pat = re.compile(r'<meta name="%s" content="[^"]*"' % re.escape(name))
    repl = f'<meta name="{name}" content="{content}"'
    if pat.search(html):
        return pat.sub(repl, html, count=1), False  # 已存在->更新
    return html, True  # 需插入


def process_file(rel, check_only=False):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        print("  ! 跳过(不存在):", rel)
        return False
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    cat, tags, updated = SAMPLES[rel]
    block = tag_block(cat, tags, updated)

    # 先更新已存在的三个 meta
    html, need_cat = upsert_meta(html, "article-category", cat)
    html, need_tags = upsert_meta(html, "article-tags", ",".join(tags))
    html, need_upd = upsert_meta(html, "article-updated", updated)

    if not (need_cat or need_tags or need_upd):
        # 已是最新
        if COMMENT in html:
            return False
        # 有 meta 但缺注释，补注释（极少情况）
    # 插入/补齐注释 + 缺失的 meta
    if COMMENT not in html:
        # 锚点：description 之后；否则 title 之后；否则 </head> 之前
        m = re.search(r'<meta name="description" content="[^"]*">', html)
        if m:
            anchor_end = m.end()
        else:
            m2 = re.search(r"<title>[^<]*</title>", html)
            anchor_end = m2.end() if m2 else html.find("</head>")
        html = html[:anchor_end] + "\n" + block + html[anchor_end:]
    else:
        # 注释在，但某 meta 缺失（理论不会，因上面已 upsert 存在的；缺失的说明从未插入）
        # 确保三行齐全：简单重建块（已存在行会被 upsert 覆盖，这里只补缺失行）
        for name, content in (
            ("article-category", cat),
            ("article-tags", ",".join(tags)),
            ("article-updated", updated),
        ):
            if f'name="{name}"' not in html:
                html = html.replace(COMMENT, COMMENT + "\n" + f'<meta name="{name}" content="{content}">', 1)

    if check_only:
        print("  ~ 将改动:", path)
        return True
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("  + 已写入:", path, f"(分类={cat}, 标签={tags}, 更新={updated})")
    return True


def main():
    check = "--check" in sys.argv
    print("apply_article_meta.py", "(check-only)" if check else "(写入)")
    changed = 0
    for rel in SAMPLES:
        if process_file(rel, check_only=check):
            changed += 1
    print(f"完成：{changed} 个文件{'待' if check else '已'}处理。")


if __name__ == "__main__":
    main()
