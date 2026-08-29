#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_zisha_insight.py — 把「深度解读」静态注入 40 个紫砂作品详情页。

紫砂详情页原本只有「图片 + 规格表 + 模板文案」，属参数罗列型。本脚本把
build_zisha_insight.py 由真实规格推导出的解读（适什么茶 / 养壶要点 /
什么场合用 / 器型说 / 工艺与鉴别 / 所属系列）写进页面，让"参数"变成"判断依据"。

设计要点：
  - 插在「相关阅读」之前：先讲透这把壶，再推荐别的，阅读顺序才顺
  - 用 <dl>/<dt>/<dd> 语义化标签，正好对应"条目 → 说明"的结构
  - 幂等：--refresh 先剥旧块再重注（知识库更新后用）
  - 纯 HTML + 站点 style.css，不加任何脚本，CSP 严格态保持

用法：
  python3 scripts/apply_zisha_insight.py            # 写入
  python3 scripts/apply_zisha_insight.py --check    # 只统计，不写文件
  python3 scripts/apply_zisha_insight.py --refresh  # 先删旧块再重写
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
DATA = os.path.join(STATIC, "data", "zisha-insight.json")

MARK_BEGIN = "<!-- insight:begin -->"
MARK_END = "<!-- insight:end -->"
RELATED_BEGIN = "<!-- related:begin -->"

# 注入锚点（按优先级）：优先插在「相关阅读」前，否则退回通用锚点
FALLBACK_ANCHORS = [
    re.compile(r"</main>"),
    re.compile(r"<footer"),
    re.compile(r"</body>"),
]


def build_html(rows):
    items = []
    for r in rows:
        items.append(
            '    <div class="lx-insight-row">\n'
            f'      <dt class="lx-insight-k">{r["k"]}</dt>\n'
            f'      <dd class="lx-insight-v">{r["v"]}</dd>\n'
            "    </div>"
        )
    return (
        f"{MARK_BEGIN}\n"
        '<section class="lx-insight" aria-label="深度解读">\n'
        '  <div class="lx-insight-head">\n'
        '    <span class="lx-insight-kicker">怎么用这把壶</span>\n'
        '    <h2 class="lx-insight-title">深度解读</h2>\n'
        "  </div>\n"
        '  <dl class="lx-insight-list">\n'
        + "\n".join(items)
        + "\n  </dl>\n</section>\n"
        + MARK_END
    )


def process(path, data, check_only, refresh):
    url = "/" + os.path.relpath(path, STATIC).replace(os.sep, "/")
    info = data.get(url)
    if not info or not info.get("rows"):
        return False

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    if MARK_BEGIN in html:
        if not refresh:
            return False
        html = re.sub(
            re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n?",
            "", html, flags=re.S,
        )

    block = build_html(info["rows"]) + "\n"

    # 优先插在「相关阅读」之前；没有则退回通用锚点
    pos = html.find(RELATED_BEGIN)
    if pos != -1:
        html = html[:pos] + block + html[pos:]
    else:
        for pat in FALLBACK_ANCHORS:
            m = pat.search(html)
            if m:
                html = html[: m.start()] + block + html[m.start() :]
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
        print(f"[skip] 缺少 {DATA}，请先运行 scripts/build_zisha_insight.py")
        return
    data = json.load(open(DATA, encoding="utf-8"))

    count = 0
    for fn in sorted(os.listdir(os.path.join(STATIC, "pages", "zisha"))):
        if not fn.startswith("detail-") or not fn.endswith(".html"):
            continue
        if process(os.path.join(STATIC, "pages", "zisha", fn), data,
                   check_only, refresh):
            count += 1
    print(("[check] " if check_only else "[done] ")
          + f"注入「深度解读」的紫砂页: {count}")


if __name__ == "__main__":
    main()
