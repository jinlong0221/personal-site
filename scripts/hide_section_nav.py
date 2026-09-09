#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hide_section_nav.py — 从全站静态页的导航栏里摘除指定板块入口（可逆：内容不删，只摘入口）

背景：站点的导航栏是硬编码复制在每个 static/*.html 里的（不是 Hugo partial），
      下线一个板块需要遍历约 300 个页面删掉对应 <li>。手工改必漏，故写此脚本。

用法：
    python3 scripts/hide_section_nav.py --dry-run          # 只统计，不写
    python3 scripts/hide_section_nav.py                    # 执行摘除

判定（只删导航/菜单里的入口，其他位置的链接不动）：
    1. 桌面导航：被 <li> 包裹的导航项
    2. 移动菜单：<div class="mobile-nav"> 里的裸 <a> 行
    两种都支持 Hugo partial 的 `{{ .Site.BaseURL }}` 前缀与 `../` `../../` 相对前缀。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 目标板块：href 结尾（支持 ../ ../../ 前缀）
TARGETS = ["herbs/chenxiang.html", "herbs.html"]

# href 前缀：Hugo partial 的 {{ .Site.BaseURL }}、或 ../ ../../ 相对路径、或啥都没有
PFX = r"(?:\{\{\s*\.Site\.BaseURL\s*\}\})?(?:\.\./){0,2}"

# 规则 1：桌面导航 —— 被 <li> 包裹
NAV_LI_RE = re.compile(
    r"[ \t]*<li[^>]*>\s*<a[^>]*\bhref=\"%s(?:%s)\"[^>]*>.*?</a>\s*</li>[ \t]*\n?"
    % (PFX, "|".join(re.escape(t) for t in TARGETS)),
    re.S,
)

# 规则 2：移动菜单 —— <div class="mobile-nav"> 里的裸 <a> 单行（内容里不能再含标签，
#          这样首页那种多行卡片 <a class="lx-card"> 就不会被误伤）
NAV_BARE_RE = re.compile(
    r"[ \t]*<a[^>]*\bhref=\"%s(?:%s)\"[^>]*>[^<]*</a>[ \t]*\n?"
    % (PFX, "|".join(re.escape(t) for t in TARGETS))
)

RULES = [NAV_LI_RE, NAV_BARE_RE]

SKIP_DIRS = (".git", "node_modules", "public", "resources", "hidden-sections", ".workbuddy")


def main():
    dry = "--dry-run" in sys.argv
    changed, total = [], 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                s = open(p, encoding="utf-8").read()
            except Exception:
                continue
            s2, n = s, 0
            for rx in RULES:
                s2, k = rx.subn("", s2)
                n += k
            if n:
                total += n
                changed.append((p, n))
                if not dry:
                    open(p, "w", encoding="utf-8").write(s2)
    print(("[预演] " if dry else "") + f"命中文件 {len(changed)} 个，摘除导航项 {total} 处")
    for p, n in changed[:10]:
        print(f"   {n:3d}  {os.path.relpath(p, ROOT)}")
    if len(changed) > 10:
        print(f"   ... 另有 {len(changed)-10} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
