#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_markdown_marks.py — 「行内 Markdown 记号不成对」守卫。

背景（2026-09-22）：新闻/聚合数据里的 **加粗** 与 `行内代码` 由客户端渲染器解析
（static/js/{auto_news_loader,home-feed,auto_typhoon_loader,changelog}.js 里的 md()）。
md() 只认得「成对」的记号：

    **粗**  ->  <strong>粗</strong>
    `码`    ->  <code>码</code>

一旦某个字段里 `**` 的个数是奇数（漏写了收尾的 `**`），那一个孤立的 `**`
就会**原样显示在页面上**——这正是 2026-09-22 之前全站星号乱冒的观感问题，
而且比「全都不解析」更难发现：其它成对的都正常，只有一处露着星号。

本脚本对「会经过 md() 渲染的 JSON 数据」逐字段做奇偶校验，发现即失败、禁止上线。

用法：
  python3 scripts/guard_markdown_marks.py
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# 数据源 → 说明（写进报错里，方便定位该改哪儿）
TARGETS = [
    ("*-news.json", "板块新闻正文"),
    (os.path.join("tesla", "fsd-news.json"), "特斯拉 FSD 新闻正文"),
    ("home-feed.json", "首页「今日更新」聚合"),
    ("typhoon.json", "台风页（影响说明/整体研判/防范措施/实时动态等）"),
    ("changelog.json", "更新日志（canonical）"),
    (os.path.join("data", "changelog.json"), "更新日志（站内副本）"),
    (os.path.join("data", "changelog-feed.json"), "更新日志 feed（页面实际读取）"),
]


def _collect_files():
    """展开目标清单，返回 [(绝对路径, 说明)]。"""
    out = []
    seen = set()
    for pattern, label in TARGETS:
        if "*" in pattern:
            for p in sorted(glob.glob(os.path.join(STATIC, pattern))):
                if p not in seen:
                    seen.add(p)
                    out.append((p, label))
        else:
            p = os.path.join(STATIC, pattern)
            if os.path.exists(p) and p not in seen:
                seen.add(p)
                out.append((p, label))
    return out


def _walk(node, path, hits):
    """递归遍历，收集「**」或反引号个数为奇数的字符串字段。"""
    if isinstance(node, dict):
        for k, v in node.items():
            _walk(v, "%s.%s" % (path, k), hits)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, "%s[%d]" % (path, i), hits)
    elif isinstance(node, str):
        odd_bold = node.count("**") % 2 == 1
        odd_code = node.count("`") % 2 == 1
        if odd_bold or odd_code:
            hits.append((path, node, odd_bold, odd_code))


def _snippet(text, needle):
    """截取命中位置附近的片段，便于人眼确认。"""
    idx = text.find(needle) if needle else -1
    if idx < 0:
        return text[:80]
    lo = max(0, idx - 40)
    return ("…" if lo else "") + text[lo:idx + 60] + "…"


def main():
    fails = []
    scanned_files = 0
    scanned_strings = 0

    for path, label in _collect_files():
        rel = os.path.relpath(path, ROOT)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # noqa: BLE001
            fails.append("  [%s] JSON 解析失败: %s" % (rel, e))
            continue
        scanned_files += 1

        hits = []
        _walk(data, "$", hits)
        scanned_strings += 1  # 只用于汇总展示，实际统计见下

        # 统计一下这个文件里有多少字段含成对记号（仅作信息展示）
        for p, s, odd_bold, odd_code in hits:
            kinds = []
            if odd_bold:
                kinds.append("** 不成对")
            if odd_code:
                kinds.append("` 不成对")
            needle = "**" if odd_bold else "`"
            fails.append(
                "  [%s · %s]\n      %s  →  %s\n      %s" % (rel, label, p, " / ".join(kinds), _snippet(s, needle))
            )

    print("=" * 60)
    print("行内 Markdown 记号守卫 guard_markdown_marks")
    print("=" * 60)

    if fails:
        print("[FAIL] 发现 %d 处记号不成对：" % len(fails))
        print("        md() 只解析「成对」的记号，落单的那个会原样显示在页面上。\n")
        for line in fails:
            print(line)
        print("\n修法：补上配对（写成 **这样**）或删掉多余的记号。")
        print("注意：若确实要在正文里提到「星号本身」，请写成「加粗记号」等文字，别留裸 **。")
        return 1

    print("[PASS] %d 个数据文件、全部字符串字段的 ** 与 ` 均为成对出现" % scanned_files)
    print("       （覆盖：板块新闻 / FSD / 首页聚合 / 台风 / 更新日志三副本与 feed）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
