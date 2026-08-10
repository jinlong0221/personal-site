#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动重建 data/sitemap_extra.json

背景：static/ 下的静态 HTML 页面不受 Hugo .Pages 管理，需要通过 data/sitemap_extra.json
      手工登记才能进 sitemap.xml。手工维护必然过期（历史上漏收 20+ 页面）。
      本脚本扫描 static/ 真实文件自动生成，杜绝遗漏。

用法：python3 scripts/rebuild_sitemap_extra.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(BASE, 'static')
OUT = os.path.join(BASE, 'data', 'sitemap_extra.json')

# 不应被搜索引擎收录的页面
EXCLUDE = {
    '404.html',        # 错误页
    'search.html',     # 站内搜索结果页（无独立内容价值）
    'console.html.bak',
}
EXCLUDE_DIRS = {'pagefind', 'js', 'css', 'img', 'data', 'fonts'}

# 优先级规则：命中即用，从上往下匹配
PRIORITY_RULES = [
    ('index.html',        '1.0'),   # 首页
    ('tesla.html',        '0.9'),
    ('marvel.html',       '0.9'),
    ('zisha.html',        '0.9'),
    ('herbs.html',        '0.9'),
    ('bracelet.html',     '0.9'),
    ('console.html',      '0.9'),
    ('games.html',        '0.9'),
    ('guanghui.html',     '0.9'),
    ('health-tea.html',   '0.8'),
    ('sheyang.html',      '0.8'),
]


def priority_for(rel: str) -> str:
    for name, p in PRIORITY_RULES:
        if rel == name:
            return p
    # 二级详情页
    if rel.startswith(('pages/zisha/', 'games/')):
        return '0.6'
    if '/' in rel:
        return '0.7'
    return '0.7'


def main() -> int:
    entries = []
    for dp, dn, fn in os.walk(STATIC):
        dn[:] = [d for d in dn if d not in EXCLUDE_DIRS]
        for f in sorted(fn):
            if not f.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(dp, f), STATIC).replace(os.sep, '/')
            if rel in EXCLUDE or f in EXCLUDE:
                continue
            url = '/' if rel == 'index.html' else '/' + rel
            entries.append({'url': url, 'priority': priority_for(rel)})

    entries.sort(key=lambda e: (e['url'] != '/', e['url']))

    old = []
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT, encoding='utf-8'))
        except Exception:
            old = []
    old_urls = {e.get('url') for e in old}
    new_urls = {e['url'] for e in entries}

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(entries, fh, ensure_ascii=False, indent=1)
        fh.write('\n')

    added = sorted(new_urls - old_urls)
    removed = sorted(old_urls - new_urls)
    print(f'sitemap_extra.json 已重建：{len(entries)} 条')
    if added:
        print(f'  新增 {len(added)}: ' + ', '.join(added[:12]) + (' ...' if len(added) > 12 else ''))
    if removed:
        print(f'  移除 {len(removed)}: ' + ', '.join(removed[:12]) + (' ...' if len(removed) > 12 else ''))
    if not added and not removed:
        print('  无变化')
    return 0


if __name__ == '__main__':
    sys.exit(main())
