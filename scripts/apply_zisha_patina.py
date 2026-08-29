#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_zisha_patina.py — 把「养壶记录」时间线注入紫砂作品页。

这是让页面"活起来"的那一环：紫砂壶会随着泡养慢慢变润，把这个过程按时间
拍下来、记下来，页面就不再是静态的资料页，而是会随时间生长的记录。

数据放在 static/data/zisha-patina.json，往 works 里对应壶的 records 追加即可：
    {"date": "2026-08-29", "stage": "开壶", "note": "...", "photo": "/img/zisha/xxx.webp"}

设计要点：
  - 有记录才渲染区块；没记录的壶保持页面干净，不留空壳
  - 按日期倒序（最新在上）
  - 插在「深度解读」之后、「相关阅读」之前
  - 幂等：--refresh 先剥旧块再重注（追加新记录后用）
  - 纯 HTML + 站点 style.css；照片走本地路径，CSP img-src 'self' 已放行

用法：
  python3 scripts/apply_zisha_patina.py            # 写入
  python3 scripts/apply_zisha_patina.py --check    # 只统计，不写文件
  python3 scripts/apply_zisha_patina.py --refresh  # 先删旧块再重写
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
DATA = os.path.join(STATIC, "data", "zisha-patina.json")
ZISHA_DIR = os.path.join(STATIC, "pages", "zisha")

MARK_BEGIN = "<!-- patina:begin -->"
MARK_END = "<!-- patina:end -->"
RELATED_BEGIN = "<!-- related:begin -->"

FALLBACK_ANCHORS = [
    re.compile(r"</main>"),
    re.compile(r"<footer"),
    re.compile(r"</body>"),
]


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(records):
    """按日期倒序渲染时间线。"""
    ordered = sorted(records, key=lambda r: r.get("date", ""), reverse=True)
    items = []
    for r in ordered:
        date = esc(r.get("date", ""))
        stage = esc(r.get("stage", ""))
        note = esc(r.get("note", ""))
        photo = r.get("photo", "")
        img = ""
        if photo:
            img = (
                f'\n        <img class="lx-patina-img" src="{esc(photo)}" '
                f'alt="{stage or date} 的养壶状态" loading="lazy" decoding="async">'
            )
        head = f'<span class="lx-patina-stage">{stage}</span>' if stage else ""
        body = f'<p class="lx-patina-note">{note}</p>' if note else ""
        items.append(
            '    <li class="lx-patina-item">\n'
            f'      <div class="lx-patina-date">{date}</div>\n'
            '      <div class="lx-patina-body">\n'
            f'        {head}{body}{img}\n'
            "      </div>\n"
            "    </li>"
        )
    return (
        f"{MARK_BEGIN}\n"
        '<section class="lx-patina" aria-label="养壶记录">\n'
        '  <div class="lx-patina-head">\n'
        '    <span class="lx-patina-kicker">养壶记录</span>\n'
        '    <h2 class="lx-patina-title">这把壶的变化</h2>\n'
        "  </div>\n"
        '  <ol class="lx-patina-list">\n'
        + "\n".join(items)
        + "\n  </ol>\n</section>\n"
        + MARK_END
    )


def process(path, works, check_only, refresh):
    url = "/" + os.path.relpath(path, STATIC).replace(os.sep, "/")
    entry = works.get(url) or {}
    records = entry.get("records") or []

    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    has_old = MARK_BEGIN in html

    # 没记录：若页面残留旧块（记录被删），refresh 时一并剥掉，不留空壳
    if not records:
        if has_old and refresh:
            html = re.sub(
                re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n?",
                "", html, flags=re.S,
            )
            if not check_only:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)
            return True
        return False

    if has_old:
        if not refresh:
            return False  # 已注入，保持幂等
        html = re.sub(
            re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\n?",
            "", html, flags=re.S,
        )

    block = build_html(records) + "\n"
    # 插在「深度解读」之后（若有）、「相关阅读」之前
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
        print(f"[skip] 缺少 {DATA}，跳过养壶记录注入")
        return
    raw = json.load(open(DATA, encoding="utf-8"))
    works = raw.get("works") or {}

    count = 0
    for fn in sorted(os.listdir(ZISHA_DIR)):
        if not fn.startswith("detail-") or not fn.endswith(".html"):
            continue
        if process(os.path.join(ZISHA_DIR, fn), works, check_only, refresh):
            count += 1
    total = sum(1 for v in works.values() if v.get("records"))
    print(("[check] " if check_only else "[done] ")
          + f"注入「养壶记录」的紫砂页: {count}"
          + f"（数据中有记录的壶: {total}）")


if __name__ == "__main__":
    main()
