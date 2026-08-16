#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_site_widgets.py — 向全站静态 HTML 注入纯前端小组件（幂等）。

注入内容：
  1. 全站（任何含 </body> 的页面）：
     - <div id="quickToc"></div> 挂载点（悬浮栏目目录，渲染见 /js/quick-toc.js）
     - <script src=".../js/quick-toc.js" defer>
     - <script src=".../js/bookmark.js" defer>
     脚本相对路径按文件目录深度自动加 ../ 前缀，与 static 页现有引用一致。
  2. 文章页（含 <h1> 标题）：在首个 <h1> 后注入「收藏」按钮 .bm-bar。

用法：
  python3 scripts/apply_site_widgets.py          # 写入
  python3 scripts/apply_site_widgets.py --check  # 仅检查
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, 'static')
SKIP_DIR_PARTS = {'admin', 'pagefind', 'js', 'css', 'img', 'data', 'fonts'}

WIDGET_BLOCK = (
    '\n<!-- 全站悬浮栏目目录 + 本地收藏（纯前端组件，无后端） -->\n'
    '<div id="quickToc"></div>\n'
    '<script src="{jsp}quick-toc.js" defer></script>\n'
    '<script src="{jsp}bookmark.js" defer></script>\n'
)

BM_BTN = (
    '<div class="bm-bar">'
    '<button class="bm-btn" type="button" data-bm-btn aria-pressed="false" title="收藏这篇文章（本地保存，无需登录）">'
    '<svg class="bm-star" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
    '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>'
    '<span class="bm-label">收藏</span></button></div>'
)

def js_prefix(depth):
    return '../' * depth + 'js/'


def process_file(path, check_only=False):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    changed = []
    depth = os.path.relpath(path, STATIC_DIR).count(os.sep)
    jsp = js_prefix(depth)

    # 1) 全站小组件挂载 + 脚本
    if '</body>' in html and 'id="quickToc"' not in html:
        block = WIDGET_BLOCK.format(jsp=jsp)
        html = html.replace('</body>', block + '</body>', 1)
        changed.append('widget')
    elif 'id="quickToc"' in html:
        # 已注入：修正脚本相对前缀（按目录深度自修复，幂等）
        fixed = re.sub(r'src="(?:\.\./)*js/quick-toc\.js"',
                       'src="%squick-toc.js"' % jsp, html)
        fixed = re.sub(r'src="(?:\.\./)*js/bookmark\.js"',
                       'src="%sbookmark.js"' % jsp, fixed)
        if fixed != html:
            html = fixed
            changed.append('fix-prefix')

    # 2) 文章页（depth>=1）「收藏」按钮：改在首个 <h1> 后注入
    if depth >= 1 and 'data-bm-btn' not in html:
        m = re.search(r'(<h1[^>]*>.*?</h1>)', html, re.I | re.S)
        if m:
            html = html.replace(m.group(1), m.group(1) + '\n' + BM_BTN, 1)
            changed.append('bm-btn')

    if not changed:
        return False
    if not check_only:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    return changed


def main():
    check_only = '--check' in sys.argv
    per_page = {}
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'static')):
        parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
        if parts & SKIP_DIR_PARTS:
            continue
        for fn in filenames:
            if not fn.endswith('.html'):
                continue
            res = process_file(os.path.join(dirpath, fn), check_only=check_only)
            if res:
                per_page[os.path.relpath(os.path.join(dirpath, fn), ROOT)] = res
    n_widget = sum(1 for v in per_page.values() if 'widget' in v)
    n_bm = sum(1 for v in per_page.values() if 'bm-btn' in v)
    print(('[check] ' if check_only else '[done] ') +
          f'注入小组件页: {n_widget}，其中文章页收藏按钮: {n_bm}')
    if check_only:
        for name, v in list(per_page.items())[:20]:
            print('  +', name, v)
        if len(per_page) > 20:
            print(f'  ... and {len(per_page) - 20} more')


if __name__ == '__main__':
    main()
