#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
restore_local_nav.py — 在全部 static 静态页的导航里补回「本地生活」分组入口
（hide_local_nav.py 的逆操作；2026-10-25 站长明确恢复 8 个板块后启用）

插两处，均按目录深度自动加 ../ 前缀，幂等：
  1. 桌面「更多 ▾」下拉：插在「家庭旅行」锚点前（无 travel 锚点的页面退化为插在下拉收尾 </div> 前）
  2. 移动端菜单：插在「家庭旅行」锚点前（退化：插在 mobileNav 收尾 </div> 前）
"""
import os, re, glob, sys

STATIC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

BOARDS = [
    ("guanghui.html", "光辉电力"),
    ("herbs.html", "中药材"),
    ("health-tea.html", "养生茶"),
    ("sheyang.html", "射阳"),
    ("solar-terms.html", "节气"),
    ("typhoon.html", "台风监测"),
    ("xintan-weather.html", "新坍天气"),
    ("gaokao.html", "高考"),
]

def depth_prefix(relpath):
    d = relpath.count("/")
    return "../" * d

def build_desktop(pfx):
    lines = ['          <span class="nav-more-hd">本地生活</span>']
    for f, name in BOARDS:
        lines.append(f'          <a href="{pfx}{f}">{name}</a>')
    return "\n".join(lines) + "\n"

def build_mobile(pfx):
    lines = ['  <span class="nav-hd">本地生活</span>']
    for f, name in BOARDS:
        lines.append(f'  <a href="{pfx}{f}">{name}</a>')
    return "\n".join(lines) + "\n"

TRAVEL_RE = re.compile(r'([ \t]*<a href="(?:\.\./)*travel\.html">家庭旅行</a>)')
DROPDOWN_CLOSE_RE = re.compile(r'(\n        </div>\n      </li>)')      # 桌面下拉收尾
MOBILE_CLOSE_RE = re.compile(r'(\n  </div>\n</nav>)')                   # 移动菜单收尾
# 只认 HTML 元素，不认 CSS 规则（内联 <style> 里也有 .nav-more-dropdown/.mobile-nav）
DROPDOWN_EL_RE = re.compile(r'<div class="nav-more-dropdown">')
MOBILE_EL_RE = re.compile(r'<div class="mobile-nav"[^>]*>')

def insert_block(src, start_idx, block, close_re):
    """在 start_idx 之后找 travel 锚点插入；找不到就用 close_re 兜底。"""
    seg = src[start_idx:]
    m = TRAVEL_RE.search(seg)
    if m:
        abs_pos = start_idx + m.start()
        return src[:abs_pos] + block + src[abs_pos:], True
    m2 = close_re.search(seg)
    if m2:
        abs_pos = start_idx + m2.start() + 1  # 保留换行在 block 之后
        return src[:abs_pos] + block + src[abs_pos:], True
    return src, False

def main():
    dry = "--dry-run" in sys.argv
    changed = 0
    skipped = 0
    for path in glob.glob(os.path.join(STATIC, "**", "*.html"), recursive=True):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        if "本地生活" in src or "navbar" not in src:
            skipped += 1
            continue
        rel = os.path.relpath(path, STATIC)
        pfx = depth_prefix(rel)
        new = src
        ok_d = ok_m = False
        m_d = DROPDOWN_EL_RE.search(new)
        if m_d:
            new, ok_d = insert_block(new, m_d.end(), build_desktop(pfx), DROPDOWN_CLOSE_RE)
        m_m = MOBILE_EL_RE.search(new)
        if m_m:
            new, ok_m = insert_block(new, m_m.end(), build_mobile(pfx), MOBILE_CLOSE_RE)
        if new != src:
            if not dry:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
            changed += 1
        else:
            skipped += 1
            print(f"  ! 未改动: {rel} (desktop={ok_d}, mobile={ok_m})")
    print(("[预演] " if dry else "") + f"已处理 {changed} 页，跳过 {skipped} 页")

if __name__ == "__main__":
    sys.exit(main())
