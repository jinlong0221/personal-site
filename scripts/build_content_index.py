#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_content_index.py — 生成全站「内容索引」static/data/content-index.json

供两处使用：
  1) 升级后的站内搜索（layouts/search.html + static/js/filter-search.js）
     —— 支持 关键词 + 分类 + 标签 + 更新时间 筛选
  2) 标签聚合页（layouts/tag.html / tags.html + static/js/tag.js）
     —— 按标签列出全部文章

数据来源（零依赖、纯静态）：
  A. 静态页：读 data/sitemap_extra.json 得到全部 URL，再扫描对应 static/<url>
     提取 <title> / description / article-category / article-tags / article-updated
  B. Hugo 文章：扫描 content/**/*.md 的 frontmatter（title/url/description/
     category/tags/updated）

分类缺省按「目录 / 文件名」映射；标签缺省为空数组（未打标签的文章仍可关键词检索）。

用法：
  python3 scripts/build_content_index.py            # 生成 static/data/content-index.json
  python3 scripts/build_content_index.py --check    # 只打印条数，不写文件

维护：给文章打标签后（见 apply_article_meta.py / frontmatter），重跑本脚本即可。
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
DATA = os.path.join(STATIC, "data")
SITEMAP_EXTRA = os.path.join(ROOT, "data", "sitemap_extra.json")
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(DATA, "content-index.json")

# 不进入搜索/标签索引的功能性或私有页
EXCLUDE_FILES = {
    "about.html", "changelog.html", "status-history.html", "search.html",
    "tags.html", "tag.html", "404.html", "calendar.html", "index.html",
    "microblog.html", "checklist.html",
}
EXCLUDE_PREFIXES = ("admin/", "pagefind/", "js/", "css/", "img/", "data/", "fonts/")

# 顶层栏目文件 → 分类
FILE_CAT = {
    "herbs.html": "中药材香料", "bracelet.html": "文玩手串", "zisha.html": "紫砂",
    "tesla.html": "特斯拉", "health-tea.html": "养生茶", "marvel.html": "漫威",
    "apple.html": "苹果", "chinajoy.html": "ChinaJoy", "console.html": "游戏主机",
    "games.html": "游戏主机", "gaokao.html": "高考志愿", "guanghui.html": "光辉电力",
    "pitfalls.html": "踩坑记", "sheyang.html": "射阳本地民生",
    "typhoon.html": "射阳气象", "xintan-weather.html": "射阳气象",
}
# 一级目录 → 分类
DIR_CAT = {
    "herbs": "中药材香料", "bracelet": "文玩手串", "zisha": "紫砂", "tesla": "特斯拉",
    "health-tea": "养生茶", "marvel": "漫威", "apple": "苹果", "chinajoy": "ChinaJoy",
    "console": "游戏主机", "games": "游戏主机", "gaokao": "高考志愿",
    "guanghui": "光辉电力", "pitfalls": "踩坑记", "sheyang": "射阳本地民生",
    "typhoon": "射阳气象", "xintan-weather": "射阳气象", "original": "原创",
}


def strip_brand(t):
    t = re.sub(r"\s*[｜|]\s*龙兄知识库\s*$", "", t)
    t = re.sub(r"\s*-\s*龙兄知识库\s*$", "", t)
    return t.strip()


def meta_content(html, name):
    m = re.search(r'<meta name="%s" content="([^"]*)"' % re.escape(name), html)
    return m.group(1).strip() if m else ""


def resolve_category(bare, meta_cat):
    if meta_cat:
        return meta_cat
    base = os.path.basename(bare)
    if base in FILE_CAT:
        return FILE_CAT[base]
    seg = bare.split("/", 1)[0] if "/" in bare else ""
    return DIR_CAT.get(seg, seg or "未分类")


def collect_static():
    out = []
    with open(SITEMAP_EXTRA, "r", encoding="utf-8") as f:
        urls = json.load(f)
    for e in urls:
        url = e.get("url", "").lstrip("/")
        if not url or not url.endswith(".html"):
            continue
        if url in EXCLUDE_FILES or url.startswith(EXCLUDE_PREFIXES):
            continue
        src = os.path.join(STATIC, url)
        if not os.path.isfile(src):
            continue
        with open(src, "r", encoding="utf-8", errors="ignore") as fh:
            html = fh.read()
        title = strip_brand(meta_content(html, "title") or re.sub(r"<[^>]+>", "", (re.search(r"<title>([^<]*)</title>", html) or ["", ""])[1]))
        cat = resolve_category(url, meta_content(html, "article-category"))
        tags_raw = meta_content(html, "article-tags")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        out.append({
            "url": "/" + url,
            "title": title,
            "category": cat,
            "tags": tags,
            "updated": meta_content(html, "article-updated"),
            "desc": meta_content(html, "description"),
        })
    return out


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    fm = {}
    for line in block.splitlines():
        m = re.match(r'\s*([A-Za-z_][\w-]*)\s*:\s*(.*)$', line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        v = v.strip('"').strip("'")
        fm[k] = v
    return fm


def fm_tags(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()] if inner else []
    return [t.strip().strip('"').strip("'") for t in v.split(",") if t.strip()] if v else []


def collect_hugo():
    out = []
    for dirpath, _, files in os.walk(CONTENT):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), CONTENT)
            if rel in ("search.md", "tags.md", "tag.md", "tags-index.md", "checklist.md", "microblog.md"):
                continue
            if rel.endswith("_index.md"):
                continue
            with open(os.path.join(dirpath, fn), "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            fm = parse_frontmatter(text)
            if not fm.get("title"):
                continue
            url = fm.get("url", "").strip().strip('"').strip("'")
            if not url:
                if rel.startswith("original/"):
                    url = "/" + rel[:-3] + "/"  # /original/<slug>/
                else:
                    url = "/" + rel[:-3] + ".html"
            if url.startswith("./"):
                url = url[1:]
            cat = fm.get("category", "").strip().strip('"').strip("'")
            if not cat:
                seg = rel.split("/", 1)[0]
                cat = DIR_CAT.get(seg, seg or "未分类")
            tags = fm_tags(fm.get("tags", ""))
            out.append({
                "url": url,
                "title": fm["title"].strip().strip('"').strip("'"),
                "category": cat,
                "tags": tags,
                "updated": fm.get("updated", "").strip().strip('"').strip("'"),
                "desc": fm.get("description", "").strip().strip('"').strip("'"),
            })
    return out


def main():
    static_items = collect_static()
    hugo_items = collect_hugo()
    # 合并：以 url 去重，Hugo 优先（标签更可能齐全）
    by_url = {}
    for it in static_items + hugo_items:
        by_url[it["url"]] = it
    merged = sorted(by_url.values(), key=lambda x: (x["category"], x["title"]))
    if "--check" in sys.argv:
        tagged = sum(1 for x in merged if x["tags"])
        print(f"静态页条目: {len(static_items)} | Hugo 条目: {len(hugo_items)} | 合并去重: {len(merged)} | 已打标签: {tagged}")
        return
    os.makedirs(DATA, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    tagged = sum(1 for x in merged if x["tags"])
    print(f"已生成 {OUT}：共 {len(merged)} 条（其中已打标签 {tagged} 条）。")


if __name__ == "__main__":
    main()
