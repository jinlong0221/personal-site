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
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, 'static')
SKIP_DIR_PARTS = {'admin', 'pagefind', 'js', 'css', 'img', 'data', 'fonts'}


def ignored_files():
    """git 忽略的文件绝不能被本脚本改写。

    🔴 教训（2026-09-23）：本脚本曾直接改写 static/travel.html —— 那是被 .gitignore:10
    排除的旅行相册私有文件（明文源），而 `git status` **看不见被忽略文件的改动**，
    差点就这么提交上线。以 git 自身为唯一准绳，不维护第二份名单。
    """
    try:
        out = subprocess.run(
            ['git', 'ls-files', '--others', '--ignored', '--exclude-standard'],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
    except Exception:
        return set()
    if out.returncode != 0:
        return set()
    return {os.path.normpath(l.strip()) for l in out.stdout.splitlines() if l.strip()}

# 悬浮目录脚本的缓存版本号：quick-toc.js 内容变更后需同步 bump（与全站 ?v=YYYYMMDD 约定一致，
# CI 的 bump_v_hash.py 会在 public/ 产物上把它改写成内容哈希；guard_v_param.py 校验一致性）。
#
# [修复 2026-09-22] 原值 '20260918' 落后于仓库现状（quick-toc.js 的 git 最后改动日是 20260920，
# 全站静态页里写的也是 20260920）。后果：本脚本每次运行都把 192 个页面改回 20260918，
# 本地跑一次生成链就凭空产生 190+ 个文件的脏改动；guard_v_param 又会拿 20260918 去比
# quick-toc.js 的 git 日期而报 WARNING。改成与仓库一致后，脚本命中时不再改写任何文件。
# 教训：这个常量是「static 页里 quick-toc 版本号」的唯一真相源，改 quick-toc.js 必须同改这里。
QUICK_TOC_VER = '20260920'

# 手写静态页的「滚动出场 + 站点更新时刻」两个脚本的缓存版本号。
# 与 QUICK_TOC_VER 同理：这里是 static 页里这两个版本号的唯一真相源，改脚本必须同改这里，
# 否则本脚本每次运行都会把页面改回旧值，凭空制造上百个文件的脏改动。
PAGE_REVEAL_VER = '20260923'
SITE_LIVE_VER = '20260925'

# 「有正文骨架」的判定：含 <main>，或含 .page-meta（页尾信息块）。
#
# 🔴 不能只看 <main>（2026-09-23 修）：紫砂 40 个详情页 + 游戏 19 个详情页用的是
#   「nav → .breadcrumb → .detail-hero → 正文块 → .page-meta → footer」骨架，
#   压根没有 <main>。只认 main 会让这 59 个正文页全部漏掉动效 —— 而从
#   games.html（有出场）点进 gta6.html（死板），比两边都没动效更刺眼。
#
# .page-meta 是更准的判据，实测吻合：193 个 static HTML 里 176 个内容页全有它，
# 15 个真跳转壳 / 法务页（console-gc、console-n64、console-wiiu、apple-history、
# bracelet 下 7 个下架品类壳、offline、privacy、shesi-landing、shesi-privacy）
# 全都没有 —— 用「有 page-meta」当判据，恰好把壳挡在门外，不用维护第二份名单。
PAGE_FX_MARK = 'page-reveal.js'
PAGE_FX_GATE = 'class="page-meta"'
PAGE_FX_BLOCK = (
    '\n<!-- 滚动出场 + 站点更新时刻（纯前端，无后端；脚本失效时内容默认全部可见） -->\n'
    '<script src="{jsp}page-reveal.js?v=' + PAGE_REVEAL_VER + '" defer></script>\n'
    '<script src="{jsp}site-live.js?v=' + SITE_LIVE_VER + '" defer></script>\n'
)

WIDGET_BLOCK = (
    '\n<!-- 全站悬浮栏目目录 + 本地收藏（纯前端组件，无后端） -->\n'
    '<div id="quickToc"></div>\n'
    '<script src="{jsp}quick-toc.js?v=' + QUICK_TOC_VER + '" defer></script>\n'
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
        # 已注入：修正脚本相对前缀（按目录深度自修复，幂等）+ 统一缓存版本号
        fixed = re.sub(r'src="(?:\.\./)*js/quick-toc\.js(?:\?v=\w+)?"',
                       'src="%squick-toc.js?v=%s"' % (jsp, QUICK_TOC_VER), html)
        fixed = re.sub(r'src="(?:\.\./)*js/bookmark\.js"',
                       'src="%sbookmark.js"' % jsp, fixed)
        if fixed != html:
            html = fixed
            changed.append('fix-prefix')

    # 1b) 滚动出场 + 站点更新时刻（只给有正文骨架的页；跳转壳/法务页跳过）
    if ('<main' in html or PAGE_FX_GATE in html) and '</body>' in html:
        if PAGE_FX_MARK not in html:
            html = html.replace('</body>', PAGE_FX_BLOCK.format(jsp=jsp) + '</body>', 1)
            changed.append('page-fx')
        else:
            # 已注入：同 1) 的做法，按目录深度自修复相对前缀 + 统一版本号
            fixed = re.sub(r'src="(?:\.\./)*js/page-reveal\.js(?:\?v=\w+)?"',
                           'src="%spage-reveal.js?v=%s"' % (jsp, PAGE_REVEAL_VER), html)
            fixed = re.sub(r'src="(?:\.\./)*js/site-live\.js(?:\?v=\w+)?"',
                           'src="%ssite-live.js?v=%s"' % (jsp, SITE_LIVE_VER), fixed)
            if fixed != html:
                html = fixed
                changed.append('fix-page-fx')

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
    ignored = ignored_files()
    per_page = {}
    n_skipped = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'static')):
        parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
        if parts & SKIP_DIR_PARTS:
            continue
        for fn in filenames:
            if not fn.endswith('.html'):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT)
            if os.path.normpath(rel) in ignored:
                n_skipped += 1
                print(f'  [skip] {rel}（被 .gitignore 排除，本脚本不碰）')
                continue
            res = process_file(full, check_only=check_only)
            if res:
                per_page[rel] = res
    n_widget = sum(1 for v in per_page.values() if 'widget' in v)
    n_bm = sum(1 for v in per_page.values() if 'bm-btn' in v)
    n_fx = sum(1 for v in per_page.values() if 'page-fx' in v or 'fix-page-fx' in v)
    print(('[check] ' if check_only else '[done] ') +
          f'注入小组件页: {n_widget}，文章页收藏按钮: {n_bm}，'
          f'滚动出场/站点更新时间: {n_fx}，跳过(被 gitignore): {n_skipped}')
    if check_only:
        for name, v in list(per_page.items())[:20]:
            print('  +', name, v)
        if len(per_page) > 20:
            print(f'  ... and {len(per_page) - 20} more')


if __name__ == '__main__':
    main()
