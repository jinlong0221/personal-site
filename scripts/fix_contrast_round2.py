# -*- coding: utf-8 -*-
"""
第二轮对比度修复（承接 fix_muted_contrast.py / fix_dark_contrast.py）。

第一轮漏网原因：
  1. drop_opacity 的正则 `opacity:\\s*\\.?\\d+` 只认 `.7` 这种省略前导零的写法，
     外部样式表里是 `opacity:0.7`，整条规则漏掉。
  2. 大文件用编辑工具改动出现过「返回成功但没落盘」，故本轮一律用脚本 + 回读校验。

本轮处理：
  A. 去掉 .footer-legal / .nav-clock 等「颜色已达标却又叠透明度」的 opacity
  B. .nav-more-btn 使用浏览器默认按钮外观（浅灰底 + 黑边），深色模式下是块亮斑，重置掉
  C. 邮箱紫色 #42b883 在米色底上只有 1.69，改随主题反转的变量
  D. 热点标签红在浅色底上 3.59，压深到 #B91C1C
"""
import glob
import re
import sys

ROOT = 'static/css/style.css'

OPACITY_SELECTORS = [
    r'\.footer-legal',
    r'\.breadcrumb\s+\.sep',
    r'\.footer-info-row\s+\.sep',
    r'\.nav-clock',
    r'\.update-time',
    r'\.page-meta\s+\.update-time',
]


def drop_opacity(css, selector):
    # 兼容 0.7 / .7 / 0.75 三种写法
    pat = re.compile(r'(' + selector + r'\s*\{[^}]*?)opacity:\s*[\d.]+\s*;', re.I)
    n = len(pat.findall(css))
    return pat.sub(lambda m: m.group(1), css), n


def main():
    apply = '--dry' not in sys.argv
    stats = {'opacity': 0, 'obf': 0, 'taghot': 0, 'navbtn': 0, 'emailvar': 0}
    touched = set()

    # ---------- A. 去掉叠在弱化文字上的 opacity ----------
    targets = sorted(glob.glob('static/*.html')) + [ROOT, 'layouts/partials/head.html']
    for p in targets:
        src = open(p, encoding='utf-8', errors='ignore').read()
        out = src
        for sel in OPACITY_SELECTORS:
            out, n = drop_opacity(out, sel)
            stats['opacity'] += n
        if out != src:
            touched.add(p)
            if apply:
                open(p, 'w', encoding='utf-8').write(out)

    # ---------- C. 邮箱绿色改成随主题反转的变量 ----------
    obf_pat = re.compile(r'(<a[^>]*class="[^"]*obf-email[^"]*"[^>]*?style="color:)#42b883(")', re.I)
    for p in sorted(glob.glob('static/*.html')) + sorted(glob.glob('layouts/**/*.html', recursive=True)):
        src = open(p, encoding='utf-8', errors='ignore').read()
        out, n = obf_pat.subn(r'\1var(--email-green)\2', src)
        if n:
            stats['obf'] += n
            touched.add(p)
            if apply:
                open(p, 'w', encoding='utf-8').write(out)

    # ---------- B/D. 外部样式表：按钮重置 + 热点红压深 + 邮箱变量定义 ----------
    css = open(ROOT, encoding='utf-8', errors='ignore').read()
    orig = css

    # light 主题块里的热点红压深（vs 浅红底 3.59 -> 4.82）
    css, n = re.subn(r'(--gold-text:\s*#4A3508;\s*\n\s*--tag-hot:\s*)#dc2626',
                     r'\1#B91C1C', css, flags=re.I)
    stats['taghot'] += n

    # 邮箱变量：深色沿用原绿，昼白压深
    if '--email-green' not in css:
        css, n = re.subn(r'(\n\s*--tag-hot:\s*#F87171;)', r'\1\n  --email-green: #42B883;', css, count=1)
        stats['emailvar'] += n
    if '--email-green' in css and not re.search(r'--tag-hot:\s*#B91C1C;?\s*\n\s*--email-green', css):
        css, n = re.subn(r'(\n\s*--tag-hot:\s*#B91C1C;)', r'\1\n  --email-green: #1A6E44;', css, count=1)
        stats['emailvar'] += n

    # 导航「更多」按钮：浏览器默认外观在深色模式下是一块浅灰亮斑
    if 'nav-more-btn' in css and 'nav-more-btn{background:none' not in css.replace(' ', ''):
        css += ('\n/* [BUG-FIX] 导航「更多」按钮沿用浏览器默认按钮外观（浅灰底+黑边），'
                '深色模式下是一块亮斑，且文字对比度仅 2.05 */\n'
                '.nav-more-btn{background:none;border:none;font:inherit;color:var(--text-secondary)}\n')
        stats['navbtn'] = 1

    if css != orig:
        touched.add(ROOT)
        if apply:
            open(ROOT, 'w', encoding='utf-8').write(css)

    print('模式:', '写入' if apply else '演练')
    print('改动文件:', len(touched))
    for k, v in stats.items():
        print(f'  {k:10s}: {v}')


if __name__ == '__main__':
    main()
