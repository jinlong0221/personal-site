#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全站知识星球引导条注入：在每一个 static 公开页底部加固定引导条（.vip-fab），
指向 /join.html。纯 CSS + 纯 HTML、零 JS，规避站点严格 CSP。
- 样式走 static/css/vip-fab.css（外部文件）
- 底栏 HTML 注入到 </body> 前，CSS link 注入到 </head> 前
- 跳过：join.html（落地页本身）、404/offline/privacy/shesi-privacy（法律与错误页）、
        shesi-landing（App 落地页，项目冻结）、travel（家庭加密相册）
- 跳过 hidden-sections/（未发布目录）
- 幂等：已注入则跳过
用法：在 hugo-site 根目录运行  python3 scripts/inject_vip_fab.py
"""
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_TAG = '<link rel="stylesheet" href="/css/vip-fab.css">'
BAR = """<div class="vip-fab">
  <span class="vip-fab-seal">龙</span>
  <span class="vip-fab-txt"><b>龙兄私房</b> · 进圈领紫砂 / 手串 / AI 避坑指南</span>
  <a class="vip-fab-btn" href="/join.html">立即进圈 →</a>
</div>"""

# 以文件名(basename)跳过
DENY_BASENAME = {
    "join.html", "404.html", "offline.html", "privacy.html",
    "shesi-privacy.html", "shesi-landing.html", "travel.html",
}


def inject(path_rel):
    path = os.path.join(ROOT, path_rel)
    if not os.path.exists(path):
        print("SKIP (不存在):", path_rel)
        return
    with open(path, encoding="utf-8") as fh:
        html = fh.read()

    changed = False
    if LINK_TAG not in html and "</head>" in html:
        html = html.replace("</head>", LINK_TAG + "\n</head>", 1)
        changed = True
    if 'class="vip-fab"' not in html and "</body>" in html:
        html = html.replace("</body>", BAR + "\n</body>", 1)
        changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("INJECTED:", path_rel)
    else:
        print("NO-CHANGE:", path_rel)


def main():
    count = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "static", "**", "*.html"), recursive=True)):
        rel = os.path.relpath(f, ROOT)
        if "hidden-sections" in rel.replace(os.sep, "/"):
            continue
        base = os.path.basename(f)
        if base in DENY_BASENAME:
            continue
        inject(rel)
        count += 1
    print("=== 共处理 %d 个 static 页 ===" % count)


if __name__ == "__main__":
    main()
