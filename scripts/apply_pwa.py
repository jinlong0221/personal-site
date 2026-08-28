#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_pwa.py — 为静态页注入 Service Worker 注册脚本（幂等、通用）。

设计要点：
- 扫描全部 static/**/*.html，在 </head> 之前幂等注入：
      <!-- PWA: 注册 Service Worker（离线阅读） -->
      <script src="/js/pwa-register.js?v=20260826" defer></script>
- 用上方注释 MARKER 去重：已含 MARKER 的页跳过，绝不重复注入。
- 旅行加密页 travel.html 跳过（由 encrypt 流水线控制）。
- 注入的是「同源外部脚本」（src=/js/pwa-register.js），受 meta CSP 的 script-src 'self' 允许，
  无需内联、无需 sha256 白名单；?v=YYYYMMDD 会被 bump_v_hash 在构建产物上改写为内容哈希。
- Hugo 渲染页（首页/栏目/标签页）由 layouts/partials/head.html 统一注册，不走本脚本。

用法：
  python3 scripts/apply_pwa.py            # 注入注册脚本
  python3 scripts/apply_pwa.py --check    # 仅报告将改动的页，不写回

说明：本脚本在 CI 构建前对 static/ 源文件就地改写（与 apply_gitalk 同范式），不回写仓库；幂等。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

MARKER = "<!-- PWA: 注册 Service Worker（离线阅读） -->"
SNIPPET = MARKER + '\n<script src="/js/pwa-register.js?v=20260826" defer></script>\n'


def rel_of(path):
    return os.path.relpath(path, ROOT)


def process_file(path, check_only=False):
    rel = rel_of(path)
    if os.path.basename(rel) == "travel.html":
        print("  - 跳过(travel 加密页):", rel)
        return False
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    if MARKER in html:
        return False  # 已注入，跳过
    idx = html.rfind("</head>")
    if idx == -1:
        idx = html.lower().rfind("</head>")
    if idx == -1:
        print("  ! 跳过(无 </head>):", rel)
        return False
    if check_only:
        print("  ~ 将注入:", rel)
        return True
    new_html = html[:idx] + SNIPPET + html[idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("  + 已注入:", rel)
    return True


def main():
    check = "--check" in sys.argv
    print("apply_pwa.py", "(check-only)" if check else "(写入)")
    changed = skipped = 0
    for dirpath, dirnames, filenames in os.walk(STATIC):
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            if "travel-dist" in dirpath.replace("\\", "/"):
                continue
            p = os.path.join(dirpath, fn)
            if process_file(p, check_only=check):
                changed += 1
            else:
                skipped += 1
    print("完成：%d 个文件已注入 / %d 个跳过（已含或 travel）。" % (changed, skipped))


if __name__ == "__main__":
    main()
