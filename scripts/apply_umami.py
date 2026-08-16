#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向所有静态页(<head>)注入 Umami 统计片段，并放宽 meta CSP 放行 Umami / Gitalk 所需域名。
幂等：已含片段或已放宽则跳过。

用法：
  python3 scripts/apply_umami.py            # 写入
  python3 scripts/apply_umami.py --check    # 仅检查，不写入
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIR_PARTS = {'admin', 'pagefind', 'js', 'css', 'img', 'data', 'fonts'}

# 与 layouts/partials/head.html 中的 CSP 保持一致（含 Umami / Gitalk 放行）
NEW_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://hm.baidu.com "
           "https://busuanzi.ibruce.info https://cdn.jsdelivr.net https://umami.example.com; "
           "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
           "img-src 'self' data: https://api.qrserver.com https://avatars.githubusercontent.com "
           "https://*.githubusercontent.com https://umami.example.com; "
           "font-src 'self' data:; connect-src 'self' https://api.open-meteo.com "
           "https://api.github.com https://umami.example.com; "
           "frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests")

# 注入的 Umami 片段（占位，待用户替换域名与 website-id）
UMAMI_SNIPPET = (
    '\n<!-- Umami 轻量访问统计（第三方组件；替换 umami.example.com 与 UMAMI_WEBSITE_ID 后生效） -->\n'
    '<script async src="https://umami.example.com/script.js" data-website-id="UMAMI_WEBSITE_ID"></script>\n'
)


def process_file(path, check_only=False):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    changed = False
    # 1) 放宽 CSP（仅当仍含旧 host 且未含 jsdelivr 时）
    if 'cdn.jsdelivr.net' not in html and 'http-equiv="Content-Security-Policy"' in html:
        import re
        html, n = re.subn(
            r'content="default-src \'self\'; script-src \'self\' \'unsafe-inline\' '
            r'https://hm\.baidu\.com https://busuanzi\.ibruce\.info; style-src \'self\' \'unsafe-inline\'; '
            r'img-src \'self\' data: https://api\.qrserver\.com; font-src \'self\' data:; '
            r'connect-src \'self\' https://api\.open-meteo\.com; frame-src \'none\'; '
            r'object-src \'none\'; base-uri \'self\'; form-action \'self\'; upgrade-insecure-requests"',
            'content="' + NEW_CSP + '"',
            html,
        )
        if n:
            changed = True

    # 2) 注入 Umami 片段（幂等）
    if 'umami.example.com/script.js' not in html and '</head>' in html:
        html = html.replace('</head>', UMAMI_SNIPPET + '</head>', 1)
        changed = True

    if changed and not check_only:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    return changed


def main():
    check_only = '--check' in sys.argv
    count = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, 'static')):
        parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
        if parts & SKIP_DIR_PARTS:
            continue
        for fn in filenames:
            if not fn.endswith('.html'):
                continue
            if process_file(os.path.join(dirpath, fn), check_only=check_only):
                count += 1
                if check_only:
                    print('  would change:', os.path.relpath(os.path.join(dirpath, fn), ROOT))
    print(('[check] ' if check_only else '[done] ') + f'Umami 片段/CSP 处理文件数: {count}')


if __name__ == '__main__':
    main()
