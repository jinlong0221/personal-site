#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新闻补漏接力：向板块 JSON 前置新条目并归一 updated 到今天。

用法:
  python3 scripts/news_relay_add.py <json路径> <payload.json> [--max 8]

payload.json 结构:
  { "updated": "2026-09-14",
    "items": [ {"date":"09-14","tags":[{"text":"","class":""}],"content":"","url":"","sources":["",""]} ] }

只前置条目 + 更新 updated，不改动既有条目。
"""
import json
import os
import sys


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    json_path = sys.argv[1]
    payload_path = sys.argv[2]
    maxn = 8
    if '--max' in sys.argv:
        maxn = int(sys.argv[sys.argv.index('--max') + 1])

    data = load(json_path)
    payload = load(payload_path)

    if 'updated' in data:
        data['updated'] = payload.get('updated', data['updated'])

    if 'news' in data and isinstance(data['news'], list):
        news = data['news']
        exist = set()
        for n in news:
            if isinstance(n, dict):
                exist.add((str(n.get('date', '')), str(n.get('content', ''))[:60]))
        added = 0
        for it in reversed(payload.get('items', [])):
            key = (str(it.get('date', '')), str(it.get('content', ''))[:60])
            if key in exist:
                continue
            exist.add(key)
            news.insert(0, it)
            added += 1
        data['news'] = news[:maxn]
        print(f"[OK] {json_path} 新增 {added} 条，现有 {len(data['news'])} 条，updated={data.get('updated')}")
    else:
        # boxoffice 类：movie/status 结构
        for k, v in payload.get('set', {}).items():
            data[k] = v
        print(f"[OK] {json_path} 已写入字段 {list(payload.get('set', {}).keys())}，updated={data.get('updated')}")

    save(json_path, data)


if __name__ == '__main__':
    main()
