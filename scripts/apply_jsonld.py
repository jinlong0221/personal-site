#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_jsonld.py — 为「缺失结构化数据」的静态页注入 schema.org JSON-LD（幂等、通用、非字典）。

设计要点：
- 扫描全部 static/**/*.html，仅对「尚未含 application/ld+json」的页注入，已注入的 144 个页一律跳过，
  绝不覆盖既有手工/历史结构化数据（避免破坏 Zisha 等页可能存在的更丰富 schema）。
- 注入模板与线上已部署的 144 个静态页保持一致：@graph = [WebSite(含 SearchAction), Article(author=Person, publisher=Organization)]。
- 元数据来源：<title> / <meta name="description"> / <link rel="canonical">（缺则按文件路径推导）
  / <meta name="article-*">（分类/标签/更新）。
- 旅行加密页 travel.html 跳过（由 encrypt 流水线控制，且已自带 ld+json）。
- 注入点：</head> 之前。application/ld+json 不受 meta CSP 的 script-src 限制（线上既有块已印证）。

用法：
  python3 scripts/apply_jsonld.py            # 注入/补齐缺失页
  python3 scripts/apply_jsonld.py --check    # 仅报告将改动的页，不写回

注意：本脚本在 CI 构建前对 static/ 源文件就地改写（与 apply_gitalk/apply_site_widgets 同范式），
      不回写仓库；幂等，重复运行无副作用。
"""
import os
import re
import sys
import json
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

SITE_NAME = "龙兄知识库"
SITE_BASE = "https://longxiong.vip/"
AUTHOR = "龙兄"
# 与线上已部署 144 个静态页的 WebSite 描述保持一致，避免两套描述
SITE_DESC = "AI驱动的个人知识库，涵盖AI学习、沉香鉴别、中药材、文玩手串、中药养生茶、特斯拉动态新闻、射阳天气等实用内容。"

LD_TYPE = "application/ld+json"


def rel_of(path):
    return os.path.relpath(path, ROOT)


def derive_url(rel):
    """static/foo.html -> https://longxiong.vip/foo.html；static/a/b.html -> .../a/b.html"""
    rel = rel.replace("\\", "/")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]
    return SITE_BASE + rel


def extract(html):
    meta = {}

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    meta["title"] = m.group(1).strip() if m else ""

    m = re.search(r'<meta\b[^>]*name\s*=\s*["\']description["\'][^>]*content\s*=\s*["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<meta\b[^>]*content\s*=\s*["\']([^"\']*)["\'][^>]*name\s*=\s*["\']description["\']', html, re.IGNORECASE)
    meta["description"] = m.group(1).strip() if m else ""

    m = re.search(r'<link\b[^>]*rel\s*=\s*["\']canonical["\'][^>]*href\s*=\s*["\']([^"\']*)["\']', html, re.IGNORECASE)
    if not m:
        m = re.search(r'<link\b[^>]*href\s*=\s*["\']([^"\']*)["\'][^>]*rel\s*=\s*["\']canonical["\']', html, re.IGNORECASE)
    meta["canonical"] = m.group(1).strip() if m else ""

    m = re.search(r'<meta\b[^>]*name\s*=\s*["\']article-category["\'][^>]*content\s*=\s*["\']([^"\']*)["\']', html, re.IGNORECASE)
    meta["category"] = m.group(1).strip() if m else ""

    return meta


def build_graph(meta, url):
    graph = [
        {
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE_BASE,
            "description": SITE_DESC,
            "potentialAction": {
                "@type": "SearchAction",
                "target": SITE_BASE + "search.html?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@type": "Article",
            "headline": meta["title"] or SITE_NAME,
            "description": meta["description"] or SITE_DESC,
            "url": url,
            "author": {"@type": "Person", "name": AUTHOR},
            "publisher": {"@type": "Organization", "name": SITE_NAME},
        },
    ]
    return {"@context": "https://schema.org", "@graph": graph}


def inject(html, block):
    idx = html.rfind("</head>")
    if idx == -1:
        idx = html.lower().rfind("</head>")
    if idx == -1:
        return None
    snippet = '\n<script type="application/ld+json">\n' + block + "\n</script>\n"
    return html[:idx] + snippet + html[idx:]


def process_file(path, check_only=False):
    rel = rel_of(path)
    if os.path.basename(rel) == "travel.html":
        print("  - 跳过(travel 加密页):", rel)
        return False
    if os.path.basename(rel) == "offline.html":
        print("  - 跳过(offline 应用外壳页):", rel)
        return False
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    if LD_TYPE in html:
        return False  # 已含结构化数据，跳过，绝不覆盖
    meta = extract(html)
    url = meta["canonical"] or derive_url(rel)
    graph = build_graph(meta, url)
    block = json.dumps(graph, ensure_ascii=False, indent=2)
    new_html = inject(html, block)
    if new_html is None:
        print("  ! 跳过(无 </head>):", rel)
        return False
    if check_only:
        print("  ~ 将注入:", rel)
        return True
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("  + 已注入:", rel, "(headline=%s)" % (meta["title"][:24] or "—"))
    return True


def main():
    check = "--check" in sys.argv
    print("apply_jsonld.py", "(check-only)" if check else "(写入)")
    changed = skipped = 0
    for dirpath, dirnames, filenames in os.walk(STATIC):
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            if "travel-dist" in dirpath.replace("\\", "/"):
                continue
            p = os.path.join(dirpath, fn)
            if process_file(p, check_only=check):
                changed += 1
            else:
                skipped += 1
    print("完成：%d 个文件已注入 / %d 个跳过（已含或 travel）。" % (changed, skipped))


if __name__ == "__main__":
    main()
