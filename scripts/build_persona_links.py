#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_persona_links.py — 给各板块页注入「龙兄视角」aside（互通层 + 感情色彩的安全扩展）

背景：
  - 全站相关阅读（build_related / apply_related）已能算法配对文章，但只是"同主题推荐"，
    没有龙兄本人的味道；紫砂页的「深度解读」也只是领域知识推导，不是龙兄口气。
  - 本脚本消费 data/persona.json（龙兄人格库），为每个有"真实态度"的板块页挂接：
      1) 龙兄本人的真实原话（pull_quote，带出处）——只引用，不代写；
      2) 龙兄写过的、与该板块相关的一手随笔页（persona_links，真实链接）。
  → 让板块之间不仅"算法串联"，还带上龙兄这个人的气息，且 100% 可复核、零编造。

护栏（来自 persona.json 的 review_policy / red_lines）：
  - 绝不把 persona 里的第三人称 stance 当成龙兄口吻去自由造句；
  - 只有"引用原话"和"挂真实链接"两种安全动作；
  - 不在龙兄自己的随笔页（persona_pages）上再注入，避免自指。

实现要点：
  - 板块判定复用 build_related.guess_board（与全站 related 系统一致，不漂移）；
  - 复用现有 .lx-related* 样式类，不新增全局 CSS，不碰受管控的 ?v= 与 CSP；
  - 相对路径、幂等标记、刷新机制，与 apply_related 同一套范式。

用法：
  python3 scripts/build_persona_links.py            # 写入
  python3 scripts/build_persona_links.py --check    # 只统计，不写文件
  python3 scripts/build_persona_links.py --refresh  # 先剥旧块再重写
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
STATIC = os.path.join(ROOT, "static")
PERSONA = os.path.join(ROOT, "data", "persona.json")

# 复用全站 related 系统的板块判定，保证口径一致
sys.path.insert(0, SCRIPTS)
import build_related as br  # noqa: E402

# 天气页在 build_related 的 FILE_BOARD 里没有，这里补上，让"留一块给射阳"能挂出来
# 养生茶同理（persona 新加的态度，build_related 尚未收录）
EXTRA_BOARD = {
    "/weather.html": "天气",
    "/sheyang-weather.html": "天气",
    "/health-tea.html": "养生茶",
    "/ev-sales.html": "新能源销量榜",
}

# 龙兄自己的随笔页不注入（避免自指 + 这些页本身就是人格出口）
PERSONA_OWN = {
    "/notes.html", "/about.html", "/methodology.html",
    "/pitfalls.html", "/reading.html", "/privacy.html",
}

EXCLUDE = {
    "/404.html", "/offline.html", "/search.html", "/bookmarks.html",
    "/changelog.html", "/status-history.html", "/game-calendar.html",
}

# 只注入"板块入口页"（聚合 hub），不在几十个详情子页（如 console-switch.html）上重复挂，
# 避免稀释龙兄个人气息。文章级互通已由「相关阅读」承担，这里只负责在板块门口亮出"龙兄本人视角"。
# 要扩展：把页面 url 加进下面这个白名单即可。
HUB_PAGES = {
    "/zisha.html", "/bracelet.html", "/tesla.html", "/apple.html",
    "/ev-sales.html", "/marvel.html", "/console.html", "/games.html",
    "/herbs.html", "/health-tea.html", "/weather.html",
    "/sheyang-weather.html", "/tools.html", "/calendar.html",
}

MARK_BEGIN = "<!-- persona:begin -->"
MARK_END = "<!-- persona:end -->"

# 注入锚点：优先插在「相关阅读」之前，使阅读顺序为 正文 → 龙兄视角 → 相关阅读
ANCHORS = [
    re.compile(r"<!--\s*related:begin\s*-->"),
    re.compile(r"</main>"),
    re.compile(r"<footer"),
    re.compile(r"</body>"),
]


def board_of(url):
    if url in EXTRA_BOARD:
        return EXTRA_BOARD[url]
    return br.guess_board(url, None)


def rel_prefix(page_rel):
    depth = page_rel.count(os.sep)
    return "../" * depth if depth else ""


def build_html(att, persona_pages, prefix):
    # 只做两种安全动作：引用龙兄原话 + 挂真实随笔链接
    quote_html = ""
    pq = att.get("pull_quote")
    if pq:
        src = att.get("pull_source", "")
        cite = f' <span class="lx-persona-cite">——{src}</span>' if src else ""
        quote_html = (
            '  <blockquote class="lx-persona-quote">'
            f'{pq}{cite}</blockquote>\n'
        )

    links = []
    for url in att.get("persona_links", []):
        p = persona_pages.get(url)
        if not p:
            continue
        href = prefix + url.lstrip("/")
        title = p.get("title", url)
        role = p.get("role", "")
        links.append(
            '    <li class="lx-related-item">\n'
            '      <a class="lx-related-link" href="' + href + '">\n'
            f'        <span class="lx-related-board">随笔</span>\n'
            f'        <span class="lx-related-name">{title}</span>\n'
            "      </a>\n"
            "    </li>"
        )

    if not links:
        return ""  # 没有可挂的随笔链接就不注入（宁缺毋滥）

    return (
        f"{MARK_BEGIN}\n"
        '<section class="lx-related lx-persona" aria-label="龙兄视角">\n'
        '  <div class="lx-related-head">\n'
        '    <span class="lx-related-kicker">站长视角</span>\n'
        '    <h2 class="lx-related-title">龙兄也聊过这个</h2>\n'
        '    <span class="lx-rule1"></span>\n'
        "  </div>\n"
        + quote_html
        + '  <ul class="lx-related-list">\n'
        + "\n".join(links)
        + "\n  </ul>\n</section>\n"
        + MARK_END
    )


def process(path, persona, check_only, refresh):
    page_rel = os.path.relpath(path, STATIC)
    url = "/" + page_rel.replace(os.sep, "/")
    if url in PERSONA_OWN or url in EXCLUDE:
        return False

    board = board_of(url)
    att = persona.get("board_attitudes", {}).get(board)
    if not att:
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

    block = build_html(att, persona.get("persona_pages_map", {}), rel_prefix(page_rel))
    if not block:
        return False

    for pat in ANCHORS:
        m = pat.search(html)
        if m:
            html = html[: m.start()] + block + "\n" + html[m.start():]
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
    persona = json.load(open(PERSONA, encoding="utf-8"))

    # 把 persona_pages 列表转成 url→info 的字典，方便挂链接
    pm = {}
    for p in persona.get("persona_pages", []):
        pm[p["url"]] = p
    persona["persona_pages_map"] = pm

    boards_with_att = set(persona.get("board_attitudes", {}).keys())
    print(f"人格库板块态度数: {len(boards_with_att)}  → {sorted(boards_with_att)}")

    count = 0
    skipped_no_board = 0
    for dirpath, _, filenames in os.walk(STATIC):
        parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
        if parts & {"admin", "pagefind", "js", "css", "img", "data", "fonts"}:
            continue
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            fp = os.path.join(dirpath, fn)
            page_rel = os.path.relpath(fp, STATIC)
            url = "/" + page_rel.replace(os.sep, "/")
            if url in PERSONA_OWN or url in EXCLUDE:
                continue
            if url not in HUB_PAGES:
                continue
            if board_of(url) not in boards_with_att:
                skipped_no_board += 1
                continue
            if process(fp, persona, check_only, refresh):
                count += 1

    print(("[check] " if check_only else "[done] ")
          + f"注入「龙兄视角」的板块页: {count}（无人格态度的页跳过: {skipped_no_board}）")

    if not check_only:
        print("提示：本脚本只引用龙兄原话 + 挂真实随笔链接，未编造任何第一人称内容。")


if __name__ == "__main__":
    main()
