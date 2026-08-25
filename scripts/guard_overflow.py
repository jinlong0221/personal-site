#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_overflow.py — 根因守卫：禁止源码出现 overflow-x:hidden

背景：
- `body{overflow-x:hidden}` 会让 body 变成名义滚动容器，导致 position:sticky 永远不吸附
  （搜索框/导航穿透 fixed 导航栏的根因）。正确做法是 overflow-x:clip（永不创建滚动容器）。
- html 级 overflow-x:hidden 虽不破坏 sticky，但为统一与可被本守卫校验，全站应统一为 clip。

扫描范围：css/ static/ layouts/ travel-dist/ content/ js/ scripts/ 下的 .css / .html 文件。
排除：public/ node_modules/ .git/ resources/ .workbuddy/ .design/ data/ outputs/ 及 .md/.json 文档。

退出码：发现违规返回 1（可用于 CI 卡点），否则 0。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content", "js", "scripts"]
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy", ".design", "data", "outputs"}
SCAN_EXTS = {".css", ".html"}

pattern = re.compile(r"overflow-x:\s*hidden")

def main():
    hits = []
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in SCAN_EXTS:
                    continue
                fpath = os.path.join(dirpath, fn)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        lines = fh.readlines()
                except (UnicodeDecodeError, OSError):
                    continue
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        hits.append((os.path.relpath(fpath, ROOT), i, line.strip()[:120]))
    if hits:
        print(f"[guard_overflow] FAIL: 发现 {len(hits)} 处 overflow-x:hidden（应改为 overflow-x:clip）")
        for rel, ln, snippet in hits:
            print(f"  - {rel}:{ln}  {snippet}")
        sys.exit(1)
    print("[guard_overflow] PASS: 源码无 overflow-x:hidden（已统一为 overflow-x:clip）")

if __name__ == "__main__":
    main()
