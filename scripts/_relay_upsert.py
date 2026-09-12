#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新闻补漏接力：把验证后的新条目前置到板块 JSON，裁剪至 8 条，并置 updated=今天。

用法：
  python3 scripts/_relay_upsert.py <json路径> <新条目json文件路径>
新条目 json 文件是一个数组，每项形如：
  {"date":"09-13","tags":[{"text":"...","class":"hot"}],"content":"...","url":"...","sources":["..."]}
"""
import json, os, sys, datetime

def main():
    path = sys.argv[1]
    newfile = sys.argv[2]
    today = datetime.date.today().isoformat()
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    with open(newfile, encoding='utf-8') as f:
        newitems = json.load(f)
    key = 'news' if 'news' in data else ('items' if 'items' in data else None)
    if key is None:
        print('NO_NEWS_ARRAY', path)
        return 1
    arr = data[key]
    # 去重：同 date + content 前 40 字 视为重复
    exist = {(x.get('date'), (x.get('content') or '')[:40]) for x in arr}
    added = 0
    for it in newitems:
        sig = (it.get('date'), (it.get('content') or '')[:40])
        if sig in exist:
            continue
        arr.insert(0, it)
        exist.add(sig)
        added += 1
    data[key] = arr[:8]
    data['updated'] = today
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'OK {path} added={added} total={len(data[key])} updated={today}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
