#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_rss.py — 生成全站 RSS 2.0 订阅源（纯静态，无后端）。

输出：static/rss.xml  （Hugo 构建时原样拷贝到 public/rss.xml）
数据来源：
  - static/data/content-index.json  （全站静态/栏目/文章页，build_content_index.py 产出）
  - static/data/feed.json            （原创中心文章，build_feed.py 产出，可选）
  - 站点首页
部署：在 deploy.yml 的 `hugo --gc` 之前运行。head.html 的 RSS discovery 已指向 /rss.xml。

用法：python3 scripts/build_rss.py
"""
import os
import json
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://longxiong.vip'
OUT = os.path.join(ROOT, 'static', 'rss.xml')


def xml_escape(s):
    if s is None:
        return ''
    s = str(s)
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&apos;'))


def rfc822(value):
    dt = None
    if isinstance(value, str) and value:
        try:
            dt = datetime.datetime.strptime(value[:10], '%Y-%m-%d')
        except Exception:
            dt = None
    if not dt:
        dt = datetime.datetime.now(datetime.timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def main():
    items = []
    seen = set()

    # 站点首页
    items.append({
        'title': '龙兄知识库',
        'link': BASE + '/',
        'desc': 'AI 驱动的个人知识库，涵盖沉香鉴别、中药材、文玩紫砂、特斯拉、射阳本地民生等实用内容。',
        'cat': '首页',
        'date': '',
    })
    seen.add(BASE + '/')

    # 全站内容索引（静态页 + 栏目 + 文章）
    idx = load_json(os.path.join(ROOT, 'static', 'data', 'content-index.json'))
    if idx:
        for e in idx:
            url = e.get('url', '')
            if not url:
                continue
            full = BASE + url
            if full in seen:
                continue
            seen.add(full)
            items.append({
                'title': e.get('title', ''),
                'link': full,
                'desc': e.get('desc', ''),
                'cat': e.get('category', ''),
                'date': e.get('updated', ''),
            })

    # 原创中心文章
    feed = load_json(os.path.join(ROOT, 'static', 'data', 'feed.json'))
    if feed:
        arr = feed if isinstance(feed, list) else (feed.get('items') or feed.get('entries') or [])
        for e in arr:
            url = e.get('url') or e.get('link') or ''
            if not url:
                continue
            full = url if url.startswith('http') else BASE + ('/' + url.lstrip('/'))
            if full in seen:
                continue
            seen.add(full)
            items.append({
                'title': e.get('title', ''),
                'link': full,
                'desc': e.get('summary') or e.get('desc') or e.get('description') or '',
                'cat': e.get('board') or e.get('category') or '原创',
                'date': e.get('date') or e.get('updated') or '',
            })

    # 排序：有日期的在前（新 → 旧）
    def sort_key(it):
        d = it['date']
        if d:
            try:
                return (0, -datetime.datetime.strptime(d[:10], '%Y-%m-%d').timestamp())
            except Exception:
                return (1, 0)
        return (1, 0)

    items.sort(key=sort_key)

    now = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<?xml-stylesheet type="text/xsl" href="/rss.xsl"?>')
    lines.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append('  <channel>')
    lines.append('    <title>龙兄知识库</title>')
    lines.append('    <link>' + BASE + '/</link>')
    lines.append('    <description>龙兄知识库 RSS 订阅源：沉香鉴别、中药材、文玩紫砂、特斯拉、射阳本地民生等实用图文。</description>')
    lines.append('    <language>zh-CN</language>')
    lines.append('    <lastBuildDate>' + now + '</lastBuildDate>')
    lines.append('    <pubDate>' + now + '</pubDate>')
    lines.append('    <generator>longxiong-static-rss</generator>')
    lines.append('    <atom:link href="' + BASE + '/rss.xml" rel="self" type="application/rss+xml"/>')
    for it in items:
        lines.append('    <item>')
        lines.append('      <title>' + xml_escape(it['title']) + '</title>')
        lines.append('      <link>' + xml_escape(it['link']) + '</link>')
        lines.append('      <guid isPermaLink="true">' + xml_escape(it['link']) + '</guid>')
        if it['cat']:
            lines.append('      <category>' + xml_escape(it['cat']) + '</category>')
        if it['date']:
            lines.append('      <pubDate>' + rfc822(it['date']) + '</pubDate>')
        lines.append('      <description>' + xml_escape(it['desc']) + '</description>')
        lines.append('    </item>')
    lines.append('  </channel>')
    lines.append('</rss>')

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print('[build_rss] 生成 %s，共 %d 条' % (os.path.relpath(OUT, ROOT), len(items)))


if __name__ == '__main__':
    main()
