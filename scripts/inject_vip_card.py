#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量在网站内容页底部注入「龙兄私房」私域引流卡片。
- 卡片样式走 static/css/vip-card.css（外部文件，规避 CSP 对 inline style 的限制）
- 卡片 HTML 纯 class、零 JS（规避 CSP 对 inline script 的哈希白名单限制）
- 仅注入 static/ 下已发布的公开页；hidden-sections/ 与无内容页不碰
用法：在 hugo-site 根目录运行  python3 scripts/inject_vip_card.py
"""
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_TAG = '<link rel="stylesheet" href="/css/vip-card.css">'

CARD = {
    "zisha": """<aside class="vip-card">
  <div class="vc-seal">龙</div>
  <div class="vc-body">
    <span class="vc-tag">紫砂 · 文玩鉴赏</span>
    <h3 class="vc-title">看完这篇，想系统避坑？</h3>
    <p class="vc-desc">壶型、泥料、真伪与溯源的实拍图解和避坑指南，在「龙兄私房」圈子持续更新。扫码加龙兄进微信，慢慢聊、少交学费。</p>
  </div>
  <div class="vc-cta"><a class="vc-btn" href="/join.html">进入私域 →</a></div>
</aside>""",
    "bracelet": """<aside class="vip-card">
  <div class="vc-seal">龙</div>
  <div class="vc-body">
    <span class="vc-tag">文玩 · 手串盘玩</span>
    <h3 class="vc-title">想看懂料性、不被绕晕？</h3>
    <p class="vc-desc">主流材质盘玩与真假鉴别的图文对照，在「龙兄私房」圈子持续更新。扫码加龙兄进微信，新手也能少踩坑。</p>
  </div>
  <div class="vc-cta"><a class="vc-btn" href="/join.html">进入私域 →</a></div>
</aside>""",
}

# (相对 ROOT 的路径, 品类)
TARGETS = [
    ("static/zisha.html", "zisha"),
    ("static/bracelet.html", "bracelet"),
]
for f in sorted(glob.glob(os.path.join(ROOT, "static", "bracelet", "*.html"))):
    rel = os.path.relpath(f, ROOT)
    TARGETS.append((rel, "bracelet"))


def inject(path_rel, cat):
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
    if 'class="vip-card"' not in html and "</body>" in html:
        html = html.replace("</body>", CARD[cat] + "\n</body>", 1)
        changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("INJECTED:", path_rel)
    else:
        print("NO-CHANGE:", path_rel)


if __name__ == "__main__":
    for p, c in TARGETS:
        inject(p, c)
    print("=== 共处理 %d 个目标 ===" % len(TARGETS))
