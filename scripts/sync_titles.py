#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_titles.py — 页面标题的唯一真相源：四个字段必须完全一致

## 为什么需要它（2026-09-17 全站体检发现）

同一页面的标题在四个地方各写一份，结果 185 个静态页里 **176 个（95%）互相打架**：

    <title>         文玩手串百科详细科普｜龙兄知识库
    og:title        文玩手串百科详细科普｜龙兄知识库   ← 与 title 一致
    twitter:title   文玩手串百科 - 龙兄知识库          ← 少「详细科普」、连接符是「 - 」
    JSON-LD headline 文玩手串百科 - 龙兄知识库         ← 同上

溯源：早期全站用「 - 龙兄知识库」做后缀，后来统一改成「｜龙兄知识库」时
只改了 `<title>` 与 `og:title`，漏了 `twitter:title` 与 JSON-LD 的 headline。
Hugo 侧没这个问题——`layouts/partials/head.html` 里四处共用同一个 `$title`。
**搜索引擎与社交平台读的正是这几处，四个值不一致＝自己给自己发混乱信号。**

## 本脚本做三件事

1. **规范 `<title>`**：
   - 去掉 SEO 堆词「详细科普」（89 个页在用，另一半没有，本身就不统一；
     且「关于本站详细科普」这类组合根本不通）
   - 站名连接符统一为全角「｜」（把残留的「 - 龙兄知识库」「 · 龙兄知识库」改过来）
   - 清掉去掉堆词后悬挂的「 ·」等分隔符（如 `新坍镇农田气象 ·详细科普`）
2. **把 og:title / twitter:title / JSON-LD headline 全部对齐到规范后的 `<title>`**
3. **补齐缺失的社交分享字段**（ev-sales.html 一个都没有、offline 与 3 个别名跳转页也没有）——
   按站内既有格式补 canonical / og:type / og:url / og:image / og:locale /
   twitter:card / twitter:image，描述取本页已有的 `<meta name="description">`

## 豁免

`privacy.html` / `shesi-landing.html` / `shesi-privacy.html` ——
「脚趾抠地」App 的独立法律与落地页，属另一套品牌资产（与网站的「两套独立资产」
边界约定一致），标题不该套「｜龙兄知识库」。**整文件跳过**。

## 用法

    python3 scripts/sync_titles.py            # 写入
    python3 scripts/sync_titles.py --check    # 只报告差异，不写文件
    python3 scripts/sync_titles.py --ci       # CI 用：写入 + 永远退 0
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

SITE = "龙兄知识库"
SITE_URL = "https://longxiong.vip"
OG_IMAGE = SITE_URL + "/img/og-image.png"

# App 独立资产：整文件跳过（标题属另一套品牌，且待迁移）
EXEMPT_FILES = {"privacy.html", "shesi-landing.html", "shesi-privacy.html"}

# 规范化的堆词清单（用 "实体词 + 这个词" 拼长尾，读起来生硬）
FILLER = ("详细科普",)

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
# 属性写法兼容带引号 / 不带引号（Hugo --minify 会去掉属性引号）
OG_TITLE_PAT = r'<meta\s+property=["\']?og:title["\']?\s+content=["\'](.*?)["\']\s*/?>'
TW_TITLE_PAT = r'<meta\s+name=["\']?twitter:title["\']?\s+content=["\'](.*?)["\']\s*/?>'
DESC_PAT = r'<meta\s+name=["\']?description["\']?\s+content=["\'](.*?)["\']\s*/?>'
HEADLINE_PAT = r'("headline"\s*:\s*")(.*?)(")'


def normalize_title(raw):
    """规范标题：统一站名连接符 + 去堆词 + 清悬挂分隔符。"""
    t = re.sub(r"\s+", " ", (raw or "").strip())

    # 1) 站名连接符统一为「｜」（仅当还没有「｜」时才动，避免误伤标题主体里的「 - 」）
    if "｜" not in t and t.endswith(SITE):
        t = re.sub(r"\s*[·・\-—－]\s*" + re.escape(SITE) + r"$", "｜" + SITE, t)

    # 2) 去堆词 —— 只动「｜」之前的主体，别碰站名
    head, sep, tail = t.partition("｜")
    for w in FILLER:
        head = head.replace(w, "")
    # 3) 清掉去掉堆词后悬挂在末尾的分隔符与空白（`新坍镇农田气象 ·详细科普` -> `新坍镇农田气象`）
    head = re.sub(r"[\s·・\-—－]+$", "", head).strip()
    head = re.sub(r"\s+", " ", head)
    return head + (sep + tail if sep else "")


def social_block(title, desc, url):
    """缺失时补的标准社交分享字段（与站内既有页格式一致）。"""
    return "\n".join([
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:type" content="article">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{desc}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        f'<meta property="og:locale" content="zh_CN">',
        f'<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:description" content="{desc}">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
    ])


def process(path, rel, check_only):
    html = open(path, encoding="utf-8").read()
    orig = html
    notes = []

    m = TITLE_RE.search(html)
    if not m:
        return None
    old_title = m.group(1).strip()
    new_title = normalize_title(old_title)

    # ---- 1) <title> ----
    if new_title != old_title:
        html = html[:m.start(1)] + new_title + html[m.end(1):]
        notes.append(f"title: {old_title}  ->  {new_title}")

    # ---- 2) og:title / twitter:title ----
    for name, pat in (("og:title", OG_TITLE_PAT), ("twitter:title", TW_TITLE_PAT)):
        mm = re.search(pat, html)
        if mm:
            if mm.group(1) != new_title:
                html = html[:mm.start(1)] + new_title + html[mm.end(1):]
                notes.append(f"{name}: 对齐")
        else:
            notes.append(f"{name}: 缺失")

    # ---- 3) JSON-LD headline ----
    mm = re.search(HEADLINE_PAT, html)
    if mm and mm.group(2) != new_title:
        html = html[:mm.start(2)] + new_title + html[mm.end(2):]
        notes.append("ld headline: 对齐")

    # ---- 4) 缺失的社交分享字段（整段补）----
    desc_m = re.search(DESC_PAT, html, re.S)
    desc = desc_m.group(1).strip() if desc_m else f"{new_title}。"
    ext = rel[:-5] if rel.endswith(".html") else rel
    if os.path.basename(rel) == "index.html":
        ext = os.path.dirname(rel)
    url = f"{SITE_URL}/{ext}.html" if not ext.endswith("index.html") else f"{SITE_URL}/{ext}"
    if ext == "404":
        url = f"{SITE_URL}/404.html"

    need = []
    if 'rel="canonical"' not in html:
        need.append("canonical")
    if "og:type" not in html:
        need.append("og")
    if "twitter:card" not in html:
        need.append("twitter")
    if need:
        block = social_block(new_title, desc, url)
        # 插在 </title> 之后，紧随标题
        t2 = TITLE_RE.search(html)
        html = html[:t2.end()] + "\n<!-- 社交分享与规范链接（sync_titles.py 补） -->\n" + block + html[t2.end():]
        notes.append("补齐: " + "+".join(need))

    if html == orig:
        return None
    if not check_only:
        open(path, "w", encoding="utf-8").write(html)
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(STATIC, "**", "*.html"), recursive=True))
    changed = 0
    detail = []
    for path in files:
        rel = os.path.relpath(path, STATIC)
        if os.path.basename(rel) in EXEMPT_FILES:
            continue
        notes = process(path, rel, args.check)
        if notes:
            changed += 1
            detail.append((rel, notes))

    print(f"[sync_titles] {'check_only' if args.check else '写入'}  "
          f"共 {len(files)} 页，需改动 {changed} 页（豁免 {len(EXEMPT_FILES)} 个 App 页）")
    for rel, notes in detail[:40]:
        print(f"  {rel}")
        for n in notes[:4]:
            print(f"      {n}")
    if len(detail) > 40:
        print(f"  ... 另有 {len(detail) - 40} 页")

    # .update-time 之外的正文引号已由 unify_quotes 管；这里只管标题族
    if args.ci:
        return 0
    return 0 if not args.check or changed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
