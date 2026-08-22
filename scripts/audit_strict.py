#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""longxiong.vip 全站审计：基础(死链/缺图/空alt/薄弱页) + 严格(desc/title/heading/lazy/js_link)。
扫 public/**/*.html。排除 http/https/#/mailto/tel/javascript/data:。"""
import os, re, sys, glob, hashlib
from html.parser import HTMLParser
from collections import defaultdict, Counter

PUBLIC = os.path.expanduser("~/陈金龙/代码与脚本/个人知识网站/hugo-site/public")
SITE_ROOT = "https://longxiong.vip"  # 仅用于内部链接相对解析的“站点根”

# ---------- 解析器 ----------
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []          # (href, text_snippet, lineno)
        self.imgs = []           # (src, alt, loading, fetchpriority, lineno)
        self.title = None
        self.desc = None
        self.headings = []       # (level, text, lineno)
        self._in_head = False
        self._in_title = False
        self._title_buf = []
        self._in_meta_desc = False
        self._text_buf = []
        self.visible_text = []
        self._skip = 0           # 计数 script/style 嵌套
        self._cur_tag = None
        self._lineno = 1
        self._last_lineno = 1

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'head':
            self._in_head = True
        if tag == 'script' or tag == 'style':
            self._skip += 1
        if tag == 'a':
            href = d.get('href', '')
            self.links.append((href, '', self.getpos()[0] if self.getpos() else 0))
        if tag == 'img':
            src = d.get('src', '')
            alt = d.get('alt', None)  # None=缺失, ''=空
            loading = d.get('loading', '')
            fetch = d.get('fetchpriority', d.get('fetch-priority', ''))
            self.imgs.append((src, alt, loading, fetch, self.getpos()[0] if self.getpos() else 0))
        if tag in ('h1','h2','h3','h4','h5','h6'):
            self.headings.append((int(tag[1]), None, self.getpos()[0] if self.getpos() else 0))
            self._cur_tag = tag
            self._title_buf = [] if tag=='title' else self._title_buf
            if tag == 'title':
                self._in_title = True

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'img':
            src = d.get('src', '')
            alt = d.get('alt', None)
            loading = d.get('loading', '')
            fetch = d.get('fetchpriority', d.get('fetch-priority', ''))
            self.imgs.append((src, alt, loading, fetch, self.getpos()[0] if self.getpos() else 0))
        if tag == 'a':
            href = d.get('href', '')
            self.links.append((href, '', self.getpos()[0] if self.getpos() else 0))
        if tag == 'link' and d.get('rel','') in ('canonical',):
            pass

    def handle_endtag(self, tag):
        if tag == 'head':
            self._in_head = False
        if tag == 'script' or tag == 'style':
            self._skip = max(0, self._skip-1)
        if tag == 'title' and self._in_title:
            self._in_title = False
            self.title = ''.join(self._title_buf).strip()
        if tag in ('h1','h2','h3','h4','h5','h6') and self._cur_tag == tag:
            text = ''.join(self._title_buf) if False else None
            # headings text captured in handle_data via _cur_tag
            self._cur_tag = None
        if tag == 'meta' and self._in_meta_desc:
            self._in_meta_desc = False

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)
        if self._cur_tag in ('h1','h2','h3','h4','h5','h6'):
            # append to last heading text
            if self.headings and self.headings[-1][1] is None:
                self.headings[-1] = (self.headings[-1][0], data.strip(), self.headings[-1][2])
            else:
                # merge
                lst = list(self.headings[-1])
                lst[1] = (lst[1] or '') + data
                self.headings[-1] = tuple(lst)
        if self._skip == 0 and self._in_head is False:
            stripped = data.strip()
            if stripped:
                self.visible_text.append(stripped)

    def handle_comment(self, data):
        pass

# meta description 单独正则抓（HTMLParser 对 <meta .../> 处理不稳）
def extract_desc(html):
    m = re.search(r'<meta\b[^>]*\bname\s*=\s*["\']?description["\']?[^>]*?content\s*=\s*["\'](.*?)["\']', html, re.S|re.I)
    if m:
        return m.group(1)
    # content 在前 name 在后
    m = re.search(r'<meta\b[^>]*content\s*=\s*["\'](.*?)["\']\s[^>]*\bname\s*=\s*["\']?description["\']?', html, re.S|re.I)
    return m.group(1) if m else None

# ---------- 工具 ----------
def is_internal(url):
    if not url: return False
    if url.startswith(('http://','https://','//','mailto:','tel:','javascript:','data:','#')):
        return False
    return True

def resolve_local(rel, page_dir):
    # 剥离 #fragment 与 ?query 再解析
    rel_clean = rel.split('#')[0].split('?')[0]
    if not rel_clean:
        return None
    # 相对 public 根
    if rel_clean.startswith('/'):
        target = os.path.normpath(os.path.join(PUBLIC, rel_clean.lstrip('/')))
    else:
        target = os.path.normpath(os.path.join(page_dir, rel_clean))
    return target

def visible_len(texts):
    s = ''.join(texts)
    s = re.sub(r'\s+', '', s)
    return len(s)

# ---------- 主流程 ----------
html_files = glob.glob(os.path.join(PUBLIC, '**', '*.html'), recursive=True)
print(f"[scan] {len(html_files)} html files\n")

issues = defaultdict(list)   # file -> list of (sev, code, msg)
desc_counter = Counter()
title_list = []

for f in html_files:
    rel = os.path.relpath(f, PUBLIC)
    with open(f, encoding='utf-8', errors='replace') as fh:
        html = fh.read()
    p = PageParser()
    try:
        p.feed(html)
    except Exception as e:
        issues[rel].append(('P0','parse_error', str(e)))
    page_dir = os.path.dirname(f)
    desc = extract_desc(html)
    if desc is not None:
        desc_counter[(desc or '').strip()] += 1

    # 死链 + 锚点校验
    for href, txt, ln in p.links:
        h = href.strip()
        if not h: continue
        if h.startswith('javascript:'):
            issues[rel].append(('P1','js_link', f'L{ln}: {h[:60]}'))
            continue
        if h == '#' : 
            continue  # 占位
        if is_internal(h):
            frag = h.split('#',1)[1] if '#' in h else ''
            tgt = resolve_local(h, page_dir)
            if tgt is None or not os.path.exists(tgt):
                issues[rel].append(('P0','dead_link', f'L{ln}: {h}'))
            elif frag:
                try:
                    with open(tgt, encoding='utf-8', errors='replace') as tf:
                        tcontent = tf.read()
                    if not re.search(r'(?:id|name)\s*=\s*["\']%s["\']' % re.escape(frag), tcontent):
                        issues[rel].append(('P1','broken_anchor', f'L{ln}: {h} (目标页无 id={frag})'))
                except Exception:
                    pass

    # 缺图 + 空alt + lazy/fetch
    n_imgs = len(p.imgs)
    for i,(src, alt, loading, fetch, ln) in enumerate(p.imgs):
        if src is None:
            issues[rel].append(('P2','img_no_src', f'L{ln}: <img> 无 src 属性(或 JS 轮播占位)'))
            continue
        s = src.strip()
        if not s: continue
        if s.startswith(('http://','https://','//','data:')):
            continue
        tgt = resolve_local(s, page_dir)
        if not os.path.exists(tgt):
            issues[rel].append(('P0','missing_img', f'L{ln}: {s}'))
            continue
        # 空 alt（仅内部图；装饰背景 alt="" 视为遗留，记录 P2 不强制）
        if alt is None:
            issues[rel].append(('P1','empty_alt', f'L{ln}: {s} (alt 缺失)'))
        # lazy（首屏已带 fetchpriority=high 的 hero 属有意 eager，豁免）
        pos_ratio = (i+1)/n_imgs if n_imgs else 1
        if pos_ratio > 0.30 and loading != 'lazy' and fetch != 'high':
            issues[rel].append(('P1','img_no_lazy', f'L{ln}: {s} (non-firstscreen missing lazy)'))
        if pos_ratio <= 0.30 and not fetch:
            issues[rel].append(('P2','img_no_fetch', f'L{ln}: {s} (firstscreen missing fetchpriority)'))

    # 薄弱页（可见正文 < 400 字）——功能页/聚合页/后台豁免
    vl = visible_len(p.visible_text)
    exempt = any(k in rel for k in ['search','calendar','weather','404','sitemap','rss','feed',
                                    'admin/','bookmarks.html','original/','tag','tags','/tags/'])
    if not exempt and vl < 400:
        issues[rel].append(('P1','weak_page', f'visible_text={vl} 字'))

    # desc_len
    if desc is None:
        issues[rel].append(('P1','no_desc', 'missing meta description'))
    else:
        L = len(desc.strip())
        if L < 50 or L > 160:
            issues[rel].append(('P1','desc_len', f'len={L} (应50-160): {desc.strip()[:40]}'))

    # title
    if p.title:
        title_list.append((rel, p.title))

    # heading_skip
    levels = [h[0] for h in p.headings]
    for i in range(1, len(levels)):
        if levels[i] > levels[i-1] + 1:
            issues[rel].append(('P1','heading_skip', f'h{levels[i-1]}->h{levels[i]} at L{p.headings[i][2]}'))

# title_dup
title_counter = Counter(t for _,t in title_list)
dup_titles = {t:c for t,c in title_counter.items() if c>1}

# desc 重复
desc_dups = {d:c for d,c in desc_counter.items() if c>1 and d}

# ---------- 汇总 ----------
all_issues = []
for f in sorted(issues):
    for sev, code, msg in issues[f]:
        all_issues.append((sev, code, f, msg))

sev_order = {'P0':0,'P1':1,'P2':2}
all_issues.sort(key=lambda x:(sev_order[x[0]], x[1], x[2]))

print("="*70)
print("审计结果汇总")
print("="*70)
counts = Counter((i[0], i[1]) for i in all_issues)
for sev in ('P0','P1','P2'):
    for code in sorted(set(c for (s,c) in counts if s==sev)):
        print(f"  {sev}  {code:14s} x{counts[(sev,code)]}")
print(f"\n总问题数: {len(all_issues)}")
print(f"P0={sum(1 for i in all_issues if i[0]=='P0')}  P1={sum(1 for i in all_issues if i[0]=='P1')}  P2={sum(1 for i in all_issues if i[0]=='P2')}")

print("\n--- P0 明细 ---")
for sev,code,f,msg in all_issues:
    if sev=='P0':
        print(f"[{code}] {f}\n    {msg}")

print("\n--- P1 明细（按文件）---")
p1_by_file = defaultdict(list)
for sev,code,f,msg in all_issues:
    if sev=='P1':
        p1_by_file[f].append(f"  [{code}] {msg}")
for f in sorted(p1_by_file):
    print(f"\n{f}")
    for m in p1_by_file[f]:
        print(m)

print("\n--- title 重复 ---")
for t,c in dup_titles.items():
    print(f"  x{c}: {t}")
print("\n--- desc 重复 ---")
for d,c in desc_dups.items():
    print(f"  x{c}: {d[:60]}")

# 写出 JSON 以便后续处理
import json
out = {
  'counts': {f"{s}|{c}": counts[(s,c)] for (s,c) in counts},
  'p0': [{'code':c,'file':f,'msg':m} for s,c,f,m in all_issues if s=='P0'],
  'p1': [{'code':c,'file':f,'msg':m} for s,c,f,m in all_issues if s=='P1'],
  'p2': [{'code':c,'file':f,'msg':m} for s,c,f,m in all_issues if s=='P2'],
  'dup_titles': dup_titles,
  'dup_descs': {d:c for d,c in desc_dups.items()},
  'total_files': len(html_files),
}
with open('/tmp/audit_result.json','w') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)
print("\n[done] 结果写入 /tmp/audit_result.json")
