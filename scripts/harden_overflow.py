#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harden_overflow.py — 一次性全站根因加固（可重复运行，幂等）

将源码中所有 `overflow-x:hidden` / `overflow-x: hidden` 统一替换为 `overflow-x:clip`。

为什么：
- `body{overflow-x:hidden}` 会让 body 变成名义滚动容器，导致 `position:sticky` 永远不吸附
  （搜索框/导航穿透 fixed 导航栏的根因）。
- `overflow-x:clip` 同样裁剪横向溢出，但**永不创建滚动容器**，sticky 始终以视口为滚动祖先。
- `html{overflow-x:hidden}` 虽不破坏 sticky，但为统一与现代化，全站统一为 clip 更彻底、可被 guard 校验。

仅处理 .css / .html（不碰 .js，避免误伤运行时字符串；不碰 public/ 由 Hugo 重建）。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 需要扫的源码根目录
SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content", "scripts"]
# 跳过的目录
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy", ".design"}
SCAN_EXTS = {".css", ".html"}

pattern = re.compile(r"overflow-x:\s*hidden")

def walk_replace(root, changed_files, total_subs):
    for dirpath, dirnames, filenames in os.walk(root):
        # 修剪跳过目录
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SCAN_EXTS:
                continue
            fpath = os.path.join(dirpath, fn)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            if "overflow-x:" not in text:
                continue
            new_text, n = pattern.subn("overflow-x:clip", text)
            if n:
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
                changed_files.append(fpath)
                total_subs.append(n)

def main():
    changed = []
    subs = []
    for d in SCAN_DIRS:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            walk_replace(p, changed, subs)
    print(f"[harden_overflow] 替换 {sum(subs)} 处 overflow-x:hidden -> clip，涉及 {len(changed)} 个文件：")
    for f in changed:
        rel = os.path.relpath(f, ROOT)
        print(f"  - {rel}")
    if not changed:
        print("  (无变更，已为幂等状态)")

if __name__ == "__main__":
    main()
