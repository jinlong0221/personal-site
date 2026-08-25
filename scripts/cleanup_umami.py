#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_umami.py — 删除源码中残留的 Umami 占位死配置（注释行 + 孤儿 partial）。
Umami 从未配置，已从 CSP 白名单与 <script> 标签移除，此处清掉所有注释痕迹与 partial 文件。
不触碰 public/（构建产物，重建即覆盖）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def collect_html():
    out = []
    base = os.path.join(ROOT, "static")
    for dp, _, fns in os.walk(base):
        if any(seg in dp for seg in ("/public", "/node_modules", "/.git", "/resources", "/.workbuddy", "/.design", "/pagefind")):
            continue
        for fn in fns:
            if fn.endswith(".html"):
                out.append(os.path.join(dp, fn))
    # layouts
    for dp, _, fns in os.walk(os.path.join(ROOT, "layouts")):
        for fn in fns:
            if fn.endswith(".html"):
                out.append(os.path.join(dp, fn))
    return out

def main():
    check = "--check" in sys.argv
    # 1) 删除孤儿 partial
    umami_partial = os.path.join(ROOT, "layouts/partials/umami.html")
    if os.path.exists(umami_partial):
        print(f"[{'CHECK' if check else 'APPLY'}] 删除孤儿 partial: layouts/partials/umami.html")
        if not check:
            os.remove(umami_partial)

    # 2) 删除含 umami.example.com 的整行（注释行 / 说明行）
    pat = re.compile(r".*umami\.example\.com.*\n")
    count = 0
    for p in collect_html():
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        if "umami.example.com" in text:
            new = pat.sub("", text)
            # 清理可能产生的连续空行（最多保留一个）
            new = re.sub(r"\n{3,}", "\n\n", new)
            if new != text:
                count += 1
                print(f"[{'CHECK' if check else 'APPLY'}] 清注释: {os.path.relpath(p, ROOT)}")
                if not check:
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(new)
    print(f"\n共 {'将' if check else '已'}清理 {count} 个文件中的 umami 注释痕迹。")

if __name__ == "__main__":
    main()
