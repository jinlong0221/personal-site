#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_related.py — 给每个文章页正文末尾静态注入「相关阅读」区块。

背景：全站 185 页之间正文内链近乎为零，板块是孤岛。本脚本把 build_related.py
算出的关联关系写进页面，让文章互相串联。

设计要点：
  1. **相对路径**：站内链接一律用相对路径（../about.html），因此注入的内链必须
     按当前页面在 static/ 下的目录深度换算前缀（根级无前缀、一层 ../ 、两层 ../../）。
  2. **静态注入而非 JS 渲染**：内链写进 HTML 才能被爬虫抓取，对 SEO 与"页面权重
     在站内流动"更有价值。
  3. **幂等**：已注入的页面跳过；关联数据更新后先跑 build_related.py，
     再删标记重跑本脚本即可刷新。

用法：
  python3 scripts/apply_related.py            # 写入
  python3 scripts/apply_related.py --check    # 只统计，不写文件
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
DATA = os.path.join(STATIC, "data", "related.json")

MARK_BEGIN = "<!-- related:begin -->"
MARK_END = "<!-- related:end -->"

# 注入锚点，按语义优先级排列：插在它前面
ANCHORS = [
    re.compile(r"</main>"),
    re.compile(r"<footer"),
    re.compile(r"<!--\s*全站悬浮栏目目录"),
    re.compile(r"</body>"),
]


def rel_prefix(page_rel):
    """按页面在 static/ 下的目录深度，算出回退前缀。

    static/apple.html            -> ''
    static/herbs/dilong.html     -> '../'
    static/pages/zisha/x.html    -> '../../'
    """
    depth = page_rel.count(os.sep)
    return "../" * depth if depth else ""


def build_html(items, prefix):
    lis = []
    for it in items:
        href = prefix + it["url"].lstrip("/")
        name = (it.get("name") or it.get("title") or "").strip()
        board = (it.get("board") or "").strip()
        lis.append(
            '    <li class="lx-related-item">\n'
            f'      <a class="lx-related-link" href="{href}">\n'
            f'        <span class="lx-related-board">{board}</span>\n'
            f'        <span class="lx-related-name">{name}</span>\n'
            "      </a>\n"
            "    </li>"
        )
    return (
        f"{MARK_BEGIN}\n"
        '<section class="lx-related" aria-label="相关阅读">\n'
        '  <div class="lx-related-head">\n'
        '    <span class="lx-related-kicker">继续读</span>\n'
        '    <h2 class="lx-related-title">相关阅读</h2>\n'
        '    <span class="lx-rule1"></span>\n'
        "  </div>\n"
        '  <ul class="lx-related-list">\n'
        + "\n".join(lis)
        + "\n  </ul>\n</section>\n"
        + MARK_END
    )


def process(path, related, check_only, refresh=False):
    page_rel = os.path.relpath(path, STATIC)
    url = "/" + page_rel.replace(os.sep, "/")
    items = related.get(url)
    if not items:
        return False

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    if MARK_BEGIN in html:
        if not refresh:
            return False  # 已注入，保持幂等
        # refresh：先剥掉旧区块，再按新数据重新注入
        html = re.sub(
            re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n?",
            "", html, flags=re.S,
        )

    prefix = rel_prefix(page_rel)
    block = build_html(items, prefix)

    for pat in ANCHORS:
        m = pat.search(html)
        if m:
            html = html[: m.start()] + block + "\n" + html[m.start() :]
            break
    else:
        return False

    if not check_only:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    return True


def main():
    check_only = "--check" in sys.argv
    refresh = "--refresh" in sys.argv
    if not os.path.exists(DATA):
        print(f"[skip] 缺少 {DATA}，请先运行 scripts/build_related.py")
        return
    related = json.load(open(DATA, encoding="utf-8"))

    count = 0
    for dirpath, _, filenames in os.walk(STATIC):
        parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
        if parts & {"admin", "pagefind", "js", "css", "img", "data", "fonts"}:
            continue
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            if process(os.path.join(dirpath, fn), related, check_only, refresh):
                count += 1
    print(("[check] " if check_only else "[done] ")
          + f"注入「相关阅读」的页面: {count}")


if __name__ == "__main__":
    main()
