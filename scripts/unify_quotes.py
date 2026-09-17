#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站引号统一 —— 把正文可见文本里的引号一律归一为「」。

站内既有主风格是「」（116 个页面在用，共 421 对），但另有：
  · 直双引号 "   —— 72 页 / 770 处
  · 中文弯引号 “ ” —— 4 页 / 46 对
另有 2 个页面两种风格混用（tesla.html、tesla/roadster.html），观感不统一。

本脚本只改「正文可见文本」里的引号，规则：
  1. 直双引号 " 按出现顺序成对替换 ——「 / 」；
  2. 中文弯引号 “ ” 直接一一映射为 「 」；
  3. 绝不触碰：HTML 属性、HTML 注释、<script>/<style>/<textarea>/<title>
     内容、<code>/<pre>/<kbd>/<samp> 内容、Markdown 的 YAML 头信息、
     围栏代码块（```）与行内代码（`...`）、JSON 的键名与结构。
  4. 单引号 ' 一概不动 —— 站内 18 处全是英文撇号（Nintendon't、
     Marvel's Wolverine）或 CSP 指令语法（frame-src 'none'），不是中文引号。

用法：
  python3 scripts/unify_quotes.py            # 应用
  python3 scripts/unify_quotes.py --check    # 只检查（幂等：无待改返回 0）
  python3 scripts/unify_quotes.py --dry-run  # 打印将要做的替换，不落盘
"""

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# raw-text：内容按原样处理，不当作 HTML 文本（浏览器也不会解析其中的标签）
RAWTEXT = {"script", "style", "textarea", "title"}
# 代码块：其中的引号是代码的一部分，必须原样保留
SKIPTEXT = {"code", "pre", "kbd", "samp"}

OPEN, CLOSE = "「", "」"

TAG_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9:-]*")


def text_spans(src):
    """返回 src 中「正文可见文本」的 [start, end) 区间列表。

    逐字符状态机，正确跳过：HTML 注释 / CDATA / 带引号的属性值 /
    raw-text 元素整体（script/style/textarea/title）/ 代码块内部。
    """
    spans = []
    n = len(src)
    i = 0
    skip_depth = 0            # >0 表示处在 code/pre/kbd/samp 之内
    while i < n:
        if src.startswith("<!--", i):
            j = src.find("-->", i + 4)
            i = n if j < 0 else j + 3
            continue
        if src.startswith("<![CDATA[", i):
            j = src.find("]]>", i + 9)
            i = n if j < 0 else j + 3
            continue
        if src[i] == "<":
            # 扫到正确的 '>' —— 属性值里的 '>' 不算
            k = i + 1
            closing = False
            if k < n and src[k] == "/":
                closing = True
                k += 1
            m = TAG_NAME_RE.match(src, k)
            name = m.group(0).lower() if m else ""
            q = None
            j = i + 1
            while j < n:
                c = src[j]
                if q:
                    if c == q:
                        q = None
                elif c in "\"'":
                    q = c
                elif c == ">":
                    break
                j += 1
            tagtxt = src[i:j + 1] if j < n else src[i:]
            selfclose = tagtxt.rstrip().rstrip(">").rstrip().endswith("/")

            if name in SKIPTEXT:
                if closing:
                    if skip_depth:
                        skip_depth -= 1
                elif not selfclose:
                    skip_depth += 1

            i = j + 1
            # raw-text 元素：内容整段跳过，直到闭合标签
            if name in RAWTEXT and not closing and not selfclose:
                cm = re.compile(r"</\s*%s\s*>" % name, re.I).search(src, i)
                i = n if cm is None else cm.end()
            continue

        j = src.find("<", i)
        if j < 0:
            j = n
        if j > i and not skip_depth:
            spans.append((i, j))
        i = j if j > i else i + 1
    return spans


def convert_text(text, state):
    """把一段可见文本的引号归一为「」。state 是跨片段复用的单元素列表 [is_open]。"""
    if '"' not in text and "“" not in text and "”" not in text:
        return text
    out = []
    for ch in text:
        if ch == "“":
            out.append(OPEN)
        elif ch == "”":
            out.append(CLOSE)
        elif ch == '"':
            if state[0]:
                out.append(CLOSE)
                state[0] = False
            else:
                out.append(OPEN)
                state[0] = True
        else:
            out.append(ch)
    return "".join(out)


def convert_html(src, changes=None):
    """按区间切片重建 HTML，只改可见文本里的引号。"""
    spans = text_spans(src)
    if not spans:
        return src, 0, 0
    state = [False]
    out = []
    prev = 0
    n_changed = 0
    for a, b in spans:
        out.append(src[prev:a])
        raw = src[a:b]
        new = convert_text(raw, state)
        if new != raw:
            n_changed += new.count(OPEN) - raw.count(OPEN) + new.count(CLOSE) - raw.count(CLOSE)
            if changes is not None:
                changes.append((raw, new))
        out.append(new)
        prev = b
    out.append(src[prev:])
    return "".join(out), n_changed, (1 if state[0] else 0)


def md_spans(src):
    """Markdown：返回可编辑区间，跳过 YAML 头、围栏代码块、行内代码。"""
    spans = []
    n = len(src)
    # YAML front matter
    start = 0
    if src.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*(\n|$)", src, re.S)
        if m:
            start = m.end()
    # 围栏代码块 + 行内代码 一起处理：先把整篇切成「可编辑 / 不可编辑」交替段
    segs = []
    i = start
    fence = re.compile(r"^([ \t]*)(`{3,}|~{3,})")
    while i < n:
        line_end = src.find("\n", i)
        if line_end < 0:
            line_end = n
        line = src[i:line_end]
        m = fence.match(line)
        if m:
            close = re.compile(r"^[ \t]*%s" % re.escape(m.group(2)), re.M)
            cm = close.search(src, line_end + 1)
            end = n if cm is None else cm.end()
            segs.append(("skip", i, end))
            i = end
        else:
            segs.append(("text", i, min(line_end + 1, n)))
            i = min(line_end + 1, n)
    # 行内代码：在 text 段内再切
    for kind, a, b in segs:
        if kind == "skip":
            continue
        piece = src[a:b]
        pos = a
        for m in re.finditer(r"`+", piece):
            # 简化处理：按出现顺序成对
            pass
        # 用状态机切分反引号
        j = 0
        while j < len(piece):
            k = piece.find("`", j)
            if k < 0:
                spans.append((pos + j, pos + len(piece)))
                break
            # 找配对的反引号串
            m = re.match(r"`+", piece[k:])
            tick = m.group(0)
            k2 = piece.find(tick, k + len(tick))
            if k2 < 0:
                spans.append((pos + j, pos + len(piece)))
                break
            if k > j:
                spans.append((pos + j, pos + k))
            j = k2 + len(tick)
    spans.sort()
    return spans


def convert_md(src, changes=None):
    spans = md_spans(src)
    state = [False]
    out = []
    prev = 0
    n_changed = 0
    for a, b in spans:
        out.append(src[prev:a])
        raw = src[a:b]
        new = convert_text(raw, state)
        if new != raw:
            n_changed += 1
            if changes is not None:
                changes.append((raw, new))
        out.append(new)
        prev = b
    out.append(src[prev:])
    return "".join(out), n_changed, (1 if state[0] else 0)


def convert_json(src, changes=None):
    """JSON 数据文件：`“`/`”` 直接映射为「」；`\\"` 按出现顺序成对替换，跳过反引号内代码。

    为什么 JSON 也要管：站点不少正文其实是数据驱动的——台风名、板块新闻、
    更新日志都由 JSON 喂给页面。只在 HTML 层归一，这些地方会漏网
    （实测：首页「今年第25号台风“杜鹃”」就来自 static/typhoon.json）。

    安全阀：反引号外可替换的 `\\"` 数量为奇数时（配不成对），只做弯引号映射、
    放弃对 `\\"` 的替换，避免把不成对的地方改坏。
    """
    excluded = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]*`", src)]

    def in_excluded(p):
        return any(a <= p < b for a, b in excluded)

    eligible = {m.start() for m in re.finditer(r'\\"', src) if not in_excluded(m.start())}
    if len(eligible) % 2:
        eligible = set()

    out = []
    prev = 0
    n = 0
    state = [False]
    i = 0
    L = len(src)
    while i < L:
        ch = src[i]
        if ch in "“”":
            out.append(src[prev:i])
            out.append(OPEN if ch == "“" else CLOSE)
            prev = i + 1
            n += 1
        elif ch == "\\" and i + 1 < L and src[i + 1] == '"' and i in eligible:
            is_open = not state[0]
            state[0] = is_open
            out.append(src[prev:i])
            out.append(OPEN if is_open else CLOSE)
            prev = i + 2
            i += 2
            n += 1
            continue
        i += 1
    out.append(src[prev:])
    new = "".join(out)
    if changes is not None and new != src:
        changes.append((src, new))
    return new, n, (1 if state[0] else 0)


def _pair_lines(raw, new):
    """给 dry-run 用：截取 raw/new 第一处不同的窗口，便于肉眼核对。"""
    i = 0
    m = min(len(raw), len(new))
    while i < m and raw[i] == new[i]:
        i += 1
    a = max(0, i - 30)
    b = min(len(raw), i + 40)
    c = min(len(new), i + 40)
    return [(raw[a:b].strip(), new[a:c].strip())]


def collect_targets():
    """待处理文件清单。

    刻意**不含** layouts/**：Hugo 模板里混着 Go 模板语法（例如
    `findRE "<h1" .Content`），其中的 `<` 与引号不是 HTML 文本，交给分词器
    会误判；模板侧的可见文案极少（目前仅 layouts/index.html 一句），手工改。
    """
    htmls = sorted(glob.glob(os.path.join(ROOT, "static", "**", "*.html"), recursive=True))
    mds = sorted(glob.glob(os.path.join(ROOT, "content", "**", "*.md"), recursive=True))

    # 数据文件也要管：不少「正文」是数据驱动的（台风名 / 板块新闻 / 更新日志）。
    EXCLUDE_JSON = {"search-index.json", "content-index.json", "sitemap_extra.json"}
    jsons = [
        p for p in sorted(glob.glob(os.path.join(ROOT, "static", "**", "*.json"), recursive=True))
        + sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True))
        if os.path.basename(p) not in EXCLUDE_JSON
    ]
    return htmls, mds, jsons


def rel(p):
    return os.path.relpath(p, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查，不改动")
    ap.add_argument("--dry-run", action="store_true", help="打印替换明细，不落盘")
    ap.add_argument("--ci", action="store_true",
                    help="CI 模式：一律退出 0（引号配不平时只告警不阻断构建），"
                         "用于部署前自愈，避免自动化新写的文案把构建搞挂")
    args = ap.parse_args()

    htmls, mds, jsons = collect_targets()
    pending = []      # (path, new_src, 替换次数, 未闭合标记)
    skipped = []
    for group, conv in ((htmls, convert_html), (mds, convert_md)):
        for p in group:
            src = open(p, encoding="utf-8").read()
            new, n_chg, unclosed = conv(src)
            if new != src:
                pending.append((p, new, n_chg, unclosed))
    for p in jsons:
        src = open(p, encoding="utf-8").read()
        new, n_chg, unclosed = convert_json(src)
        # JSON 必须在替换后仍是合法 JSON，否则放弃这个文件
        try:
            json.loads(new)
        except Exception as e:
            skipped.append((p, f"改完不是合法 JSON：{e}"))
            continue
        if new != src:
            pending.append((p, new, n_chg, unclosed))

    n_quote = sum(n for _, _, n, _ in pending)
    print(f"待处理文件 {len(pending)} 个，替换引号 {n_quote} 处")
    for p, why in skipped:
        print(f"  !! 跳过 {rel(p)}：{why}")

    bad = [p for p, _, _, uncl in pending if uncl]
    if bad:
        msg = "引号未能配平（末尾处于「已开未闭」状态）"
        if args.ci:
            print(f"  ⚠️ {msg}，CI 模式下仍继续：")
            for p in bad:
                print("     ", rel(p))
        else:
            print(f"!! 以下文件{msg}，请人工检查：")
            for p in bad:
                print("   ", rel(p))
            return 2

    if args.dry_run:
        for p, _, _, _ in pending:
            src = open(p, encoding="utf-8").read()
            changes = []
            if p.endswith(".json"):
                convert_json(src, changes)
            elif p.endswith(".md"):
                convert_md(src, changes)
            else:
                convert_html(src, changes)
            print(f"\n=== {rel(p)} ===")
            shown = 0
            for raw, new in changes:
                a, b = _pair_lines(raw, new)[0]
                print(f"   - {a}")
                print(f"   + {b}")
                shown += 1
                if shown >= 3:
                    break
        return 0

    if args.check:
        print(f"需要修改 {len(pending)} 个文件（引号未统一）")
        return 1 if pending else 0

    for p, new, n_chg, _ in pending:
        open(p, "w", encoding="utf-8").write(new)
        print(f"  改 {rel(p)}")
    print(f"完成：{len(pending)} 个文件已统一为「」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
