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
- 文案按板块细分（紫砂/手串/游戏机/特斯拉/通用），提升点击转化
- 幂等重注：无论旧块有无标记，先清除旧 vip-fab 块再写新文案
用法：在 hugo-site 根目录运行  python3 scripts/inject_vip_fab.py
"""
import os
import re
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_TAG = '<link rel="stylesheet" href="/css/vip-fab.css">'
START = "<!-- VIP_FAB_START -->"
END = "<!-- VIP_FAB_END -->"

# 默认（通用 / 聚合页）文案
DEF_TXT = '<b>龙兄私房</b> · 烧钱爱好那么多坑，进圈给你趟平'
# 各板块文案
ZISHA_TXT = '<b>龙兄私房</b> · 进圈看懂壶，泥料避坑不交学费'
BRACELET_TXT = '<b>龙兄私房</b> · 进圈辨料性，手串避坑少踩雷'
CONSOLE_TXT = '<b>龙兄私房</b> · 进圈选对机，复古游戏不交智商税'
TESLA_TXT = '<b>龙兄私房</b> · 进圈看实测，用车配件避坑'


def bar_html(txt):
    return (START + "\n"
            '<div class="vip-fab">\n'
            '  <span class="vip-fab-seal">龙</span>\n'
            '  <span class="vip-fab-txt">' + txt + '</span>\n'
            '  <a class="vip-fab-btn" href="/join.html">立即进圈 →</a>\n'
            '</div>\n' + END)


def pick_text(rel, base):
    rel = rel.replace(os.sep, "/")
    # 游戏机 / 复古游戏
    if (base.startswith("console")
            or base in ("games.html", "game-calendar.html")
            or "/games/" in rel):
        return CONSOLE_TXT
    # 手串 / 文玩
    if "bracelet" in rel:
        return BRACELET_TXT
    # 紫砂（详情页在 static/pages/ 下，板页 zisha.html）
    if "/pages/" in rel or base == "zisha.html":
        return ZISHA_TXT
    # 特斯拉
    if "tesla" in rel or base == "tesla.html":
        return TESLA_TXT
    return DEF_TXT


def strip_old(html):
    # 带标记块（本脚本新版本注入）
    html = re.sub(re.escape(START) + r'[\s\S]*?' + re.escape(END) + r'\s*', '', html)
    # 无标记旧块（兼容早期注入，无 START/END 注释）
    html = re.sub(r'<div class="vip-fab">[\s\S]*?</div>\s*', '', html)
    return html


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

    html = strip_old(html)
    changed = True  # 已重注（清旧+写新），内容可能相同也可能更新

    txt = pick_text(path_rel, os.path.basename(path))
    if "</body>" in html:
        html = html.replace("</body>", bar_html(txt) + "\n</body>", 1)
    else:
        html = html + bar_html(txt)
        changed = True

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("INJECTED:", path_rel)


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
