#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harden_csp_hygiene.py — longxiong.vip 安全加固（幂等）
1) 从 CSP 移除死配置占位域名 https://umami.example.com（script-src / img-src / connect-src）
2) 将 script-src / style-src 中的 https://cdn.jsdelivr.net 收窄为 https://cdn.jsdelivr.net/npm/gitalk/
3) 协议相对地址 //hm.baidu.com、//busuanzi.ibruce.info 改为显式 https://（纵深防御，不依赖 upgrade-insecure-requests）
4) 删除所有 umami.example.com/script.js 的 <script> 标签（head.html 的 {{ partial "umami.html" . }} 及 static 页的内联标签）
5) head.html 的延迟加载清单移除死代码 js/umami-hot.js

只做文本替换，不触碰页面逻辑；先 --check 预览，再默认应用。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    "layouts/partials/head.html",
]
# static 下递归所有 html
def collect_static_html():
    out = []
    base = os.path.join(ROOT, "static")
    for dp, _, fns in os.walk(base):
        # 跳过产物/资源目录
        if any(seg in dp for seg in ("/public", "/node_modules", "/.git", "/resources", "/.workbuddy", "/.design", "/pagefind")):
            continue
        for fn in fns:
            if fn.endswith(".html"):
                out.append(os.path.relpath(os.path.join(dp, fn), ROOT))
    return out

def transform_csp(content):
    """对单一文件内容做全部 CSP / 死配置 替换，返回 (new_content, changed_bool, notes)。"""
    orig = content
    notes = []

    # 1) 定位 CSP meta 并改写其 content
    def csp_repl(m):
        c = m.group(1)
        before = c
        # 移除死配置域名（带前导空白）
        c = re.sub(r"\s+https://umami\.example\.com", "", c)
        # 收窄 jsdelivr（script-src / style-src 中均指向 gitalk 包）
        c = c.replace("https://cdn.jsdelivr.net", "https://cdn.jsdelivr.net/npm/gitalk/")
        if c != before:
            notes.append("CSP 改写：移除 umami.example.com + 收窄 cdn.jsdelivr.net→gitalk")
        return f'<meta http-equiv="Content-Security-Policy" content="{c}">'
    new, n = re.subn(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)">', csp_repl, content)
    content = new

    # 2) 协议相对 → 显式 https（仅针对已知外部域名；不误伤站内 // 注释）
    repls = [
        ('href="//hm.baidu.com"', 'href="https://hm.baidu.com"'),
        ('href="//busuanzi.ibruce.info"', 'href="https://busuanzi.ibruce.info"'),
        ('src="//busuanzi.ibruce.info', 'src="https://busuanzi.ibruce.info'),
    ]
    for a, b in repls:
        if a in content:
            content = content.replace(a, b)
            notes.append(f"协议相对改 https: {a}")

    # 3) 删除 umami 内联 script 标签（占位死配置）
    pat = re.compile(r'<script[^>]*umami\.example\.com/script\.js[^>]*></script>\n?')
    if pat.search(content):
        content = pat.sub("", content)
        notes.append("删除 umami.example.com/script.js 内联标签")

    # 4) head.html 专属：移除 umami partial 及其注释行
    if "partials/head.html" in "" or True:
        # umami partial 行
        if "{{ partial \"umami.html\" . }}" in content:
            content = re.sub(r"\n?<!\-\- Umami 轻量访问统计[^\n]*\-\->\n?", "", content)
            content = content.replace('{{ partial "umami.html" . }}\n', '')
            content = content.replace('{{ partial "umami.html" . }}', '')
            notes.append("移除 {{ partial \"umami.html\" . }}")
        # 延迟加载清单移除 umami-hot.js
        if "js/umami-hot.js" in content:
            content = content.replace("'js/umami-hot.js'", "").replace('"js/umami-hot.js"', "")
            # 清理可能的空逗号 / 多余空格
            content = re.sub(r"\[\s*,", "[", content)
            content = re.sub(r",\s*\]", "]", content)
            content = re.sub(r",\s*,", ",", content)
            notes.append("延迟加载清单移除 js/umami-hot.js")

    changed = content != orig
    return content, changed, notes

def main():
    check = "--check" in sys.argv
    files = TARGETS + collect_static_html()
    total_changed = 0
    for rel in files:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        new, changed, notes = transform_csp(text)
        if changed:
            total_changed += 1
            print(f"[{'CHECK' if check else 'APPLY'}] {rel}")
            for n in notes:
                print(f"    - {n}")
            if not check:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new)
    print(f"\n共 {'将' if check else '已'}处理 {total_changed} 个文件。")

if __name__ == "__main__":
    main()
