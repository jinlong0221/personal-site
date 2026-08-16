#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向所有“文章页”静态 HTML（含 seo-art-head 标记的页面）底部注入 Gitalk 评论容器与初始化脚本。
幂等：已含 .gitalk-container 则跳过。

注入位置：</body> 之前（文章正文与“相关专题推荐”之后）。
Gitalk 配置（GitHub OAuth Client ID 等）见 static/js/gitalk-init.js。

用法：
  python3 scripts/apply_gitalk.py            # 写入
  python3 scripts/apply_gitalk.py --check    # 仅检查
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIR_PARTS = {'admin', 'pagefind', 'js', 'css', 'img', 'data', 'fonts'}

GITALK_BLOCK = (
    '\n<!-- Gitalk 评论（底部，第三方，存于 GitHub Issues；配置见 /js/gitalk-init.js） -->\n'
    '<div class="gitalk-container" aria-label="评论区"></div>\n'
    '<script src="/js/gitalk-init.js" defer></script>\n'
)


def process_file(path, check_only=False):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    # 仅文章页（带统一文章头部标记），且未注入过
    if 'seo-art-head' not in html:
        return False
    if 'gitalk-container' in html:
        return False
    if '</body>' not in html:
        return False
    if not check_only:
        html = html.replace('</body>', GITALK_BLOCK + '</body>', 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    return True


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
    print(('[check] ' if check_only else '[done] ') + f'注入 Gitalk 的文章页: {count}')


if __name__ == '__main__':
    main()
