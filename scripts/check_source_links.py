#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验本次新增的所有出处外链是否真实可达（防止编造 URL）。"""
import re, os, glob, concurrent.futures as cf, urllib.request, ssl

ROOT = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/hugo-site/public"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# 只抽检出现在「来源」段落里的外链
SRC_BLOCK = re.compile(
    r'(?:资料来源|信息来源|数据来源|内容来源|参考资料)[^<]{0,200}'
    r'(?:<[^>]+>[^<]*){0,40}', re.S)
HREF = re.compile(r'href="(https?://[^"]+)"')

urls = set()
for path in glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True):
    html = open(path, encoding="utf-8", errors="ignore").read()
    for block in SRC_BLOCK.findall(html):
        for u in HREF.findall(block):
            if "longxiong.vip" in u or "github.com/jinlong0221" in u:
                continue
            urls.add(u)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def check(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            return u, r.status
    except Exception as e:
        code = getattr(e, "code", None)
        return u, code if code else f"ERR:{type(e).__name__}"


print(f"待检外链 {len(urls)} 条\n" + "-" * 70)
bad = []
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for u, st in sorted(ex.map(check, sorted(urls)), key=lambda x: str(x[1])):
        ok = st == 200
        # 403/429 通常是反爬，域名本身有效
        soft = st in (403, 429, 412)
        mark = "OK " if ok else ("~  " if soft else "BAD")
        print(f"  {mark} {st:<22} {u}")
        if not ok and not soft:
            bad.append((u, st))

print("-" * 70)
print(f"不可达({len(bad)}): " + ("无 ✅" if not bad else ""))
for u, s in bad:
    print(f"  {s}  {u}")
