#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_console_guide.py — 把「选购与避坑」静态注入游戏主机图鉴页。

主机图鉴 75 页原本已有完整正文（历史/规格/游戏阵容/型号演变/市场表现），
缺的是读者做决策时真正要的判断：二手值不值得、这台有什么出了名的毛病、
挑的时候看哪里。本脚本把 build_console_guide.py 生成的解读写进页面。

复用紫砂那套已验证的做法：
  - 相对路径（主机页都在 static 根级，无需 ../ 前缀，但仍走同一套计算）
  - 插在「相关阅读」之前：先讲这台机器，再推荐别的
  - <dl>/<dt>/<dd> 语义化
  - 幂等 + --refresh
  - 纯 HTML + 站点 style.css，零脚本，CSP 严格态保持

用法：
  python3 scripts/apply_console_guide.py            # 写入
  python3 scripts/apply_console_guide.py --check    # 只统计
  python3 scripts/apply_console_guide.py --refresh  # 先删旧块再重写
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
DATA = os.path.join(STATIC, "data", "console-guide.json")

MARK_BEGIN = "<!-- guide:begin -->"
MARK_END = "<!-- guide:end -->"
RELATED_BEGIN = "<!-- related:begin -->"

FALLBACK_ANCHORS = [
    re.compile(r"</main>"),
    re.compile(r"<footer"),
    re.compile(r"</body>"),
]


def rel_prefix(page_rel):
    depth = page_rel.count(os.sep)
    return "../" * depth if depth else ""


def build_html(rows, prefix):
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
        '<section class="lx-insight lx-insight-guide" aria-label="选购与避坑">\n'
        '  <div class="lx-insight-head">\n'
        '    <span class="lx-insight-kicker">买之前先看这个</span>\n'
        '    <h2 class="lx-insight-title">选购与避坑</h2>\n'
        "  </div>\n"
        '  <dl class="lx-insight-list">\n'
        + "\n".join(items)
        + "\n  </dl>\n</section>\n"
        + MARK_END
    )


def process(path, data, check_only, refresh):
    page_rel = os.path.relpath(path, STATIC)
    url = "/" + page_rel.replace(os.sep, "/")
    info = data.get(url)
    if not info or not info.get("rows"):
        return False

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    if MARK_BEGIN in html:
        if not refresh:
            return False  # 已注入，保持幂等
        html = re.sub(
            re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n?",
            "", html, flags=re.S,
        )

    block = build_html(info["rows"], rel_prefix(page_rel)) + "\n"
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
        print(f"[skip] 缺少 {DATA}，请先运行 scripts/build_console_guide.py")
        return
    data = json.load(open(DATA, encoding="utf-8"))

    count = 0
    for fn in sorted(os.listdir(STATIC)):
        if not (fn.startswith("console-") and fn.endswith(".html")):
            continue
        if process(os.path.join(STATIC, fn), data, check_only, refresh):
            count += 1
    print(("[check] " if check_only else "[done] ")
          + f"注入「选购与避坑」的主机页: {count}")


if __name__ == "__main__":
    main()
