#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
restore_hidden_boards.py — 隐藏板块「一键恢复」预案脚本（⚠️ 默认不执行，仅 dry-run）

## 背景
2026-10 用户要求把 8 个板块临时隐藏（不进搜索、任何页面不给入口，但 URL 仍可直接打开）：
    guanghui(光辉电力) / herbs(中药材) / health-tea(养生茶) / sheyang(射阳)
    solar-terms(节气) / typhoon(台风) / xintan-weather(新滩天气) / gaokao(高考)
当时通过两道闸实现隐藏（已逐一核实 2026-10-12）：
    ① 18 个页面 <body> 带 data-pagefind-ignore → 搜索/站点索引不收录（pagefind 跳过）。
    ② 全站 JSON 数据源（home-feed.json / hot-picks.json / feed.json 等）里没有这些
       板块的条目 → 首页"今日更新 / 热门精选"不渲染它们。
    （导航栏 / 分类页已确认不链隐藏板块，无泄漏；构建脚本 scripts/ 里也无硬编码跳过清单。）

## 本脚本负责的「机械可逆」部分（机制①）
把 18 个隐藏页 <body data-pagefind-ignore> 改回 <body>，让 pagefind 重新收录它们。
配套动作（机制②，本脚本不替你做，见 HIDDEN_BOARDS_RESTORE.md）：
    - 重新把隐藏板块条目写回 home-feed.json / hot-picks.json / feed.json（或重跑对应构建器），
      否则首页"今日更新/热门精选"仍不会出现它们。

## 安全设计
    - 默认 --dry-run：只打印将要改哪些文件，绝不写盘、绝不碰别的页面。
    - 真实执行需显式 --apply；且只对「整页 <body ...> 里含 data-pagefind-ignore」的页面生效，
      不会误伤正文里偶然出现该字符串的页面（用整标签正则，不是全文替换）。
    - 脚本不改 JSON（机制②属内容决策，留给人确认，避免自动恢复出半吊子状态）。

## 用法
    python3 scripts/restore_hidden_boards.py            # 仅预览，不改任何文件
    python3 scripts/restore_hidden_boards.py --apply    # 真正移除 data-pagefind-ignore
    # 之后由 CI（hugo build → pagefind）自动重建索引；或本地手动：
    #   hugo --gc --minify && npx pagefind --site public
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# 整页 <body ...> 标签里带 data-pagefind-ignore 才匹配（避免误伤正文）
BODY_TAG_RE = re.compile(r'<body\b([^>]*?)\bdata-pagefind-ignore\b([^>]*)>', re.IGNORECASE)


def find_hidden_pages():
    """返回所有 <body> 带 data-pagefind-ignore 的静态页相对路径。"""
    out = []
    for base, _dirs, files in os.walk(STATIC):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(base, fn)
            try:
                html = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if BODY_TAG_RE.search(html):
                out.append(os.path.relpath(p, ROOT))
    return sorted(out)


def restore_one(rel, apply):
    p = os.path.join(ROOT, rel)
    html = open(p, encoding="utf-8").read()
    # 去掉 body 标签里的 data-pagefind-ignore（连同前导空格，保持标签整洁）
    new_html = BODY_TAG_RE.sub(
        lambda m: "<body" + m.group(1).rstrip() + m.group(2).rstrip() + ">",
        html,
    )
    if new_html == html:
        return False
    if apply:
        open(p, "w", encoding="utf-8").write(new_html)
    return True


def main():
    apply = "--apply" in sys.argv
    pages = find_hidden_pages()
    print(f"[restore_hidden_boards] 发现 {len(pages)} 个带 data-pagefind-ignore 的页面")
    print(f"模式: {'APPLY（将写盘）' if apply else 'DRY-RUN（仅预览）'}\n")
    for rel in pages:
        changed = restore_one(rel, apply)
        mark = "✓ 将移除" if (changed and apply) else ("· 待移除" if changed else "· 无变化")
        print(f"  {mark}  {rel}")
    if not apply:
        print("\n（以上为预览。确认无误后加 --apply 真实执行；"
              "执行后还需按 HIDDEN_BOARDS_RESTORE.md 第②步恢复 JSON 数据源条目，"
              "再由 CI 重建 pagefind 索引。）")
    else:
        print(f"\n已移除 {len(pages)} 个页面的 data-pagefind-ignore。"
              "下一步：恢复 JSON 数据源条目（见文档）→ push → CI 重建索引。")


if __name__ == "__main__":
    main()
