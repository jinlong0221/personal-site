#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
longxiong.vip 全站审计脚本
扫描 public/ 构建产物（最客观）：死链 / 缺图 / 空alt / 薄弱页 / 混合内容 / 缺尺寸。
用法:
    hugo --gc
    python3 scripts/audit_site.py public
依赖: 标准库（无需 pip）
"""
import os, sys, re
from html.parser import HTMLParser

PUBLIC = sys.argv[1] if len(sys.argv) > 1 else "public"
SKIP_PREFIXES = ("http://", "https://", "#", "mailto:", "tel:", "javascript:", "data:")


def collect_html(base):
    out = []
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".html"):
                out.append(os.path.join(root, f))
    return out


class AuditParser(HTMLParser):
    def __init__(self, base_dir, page_rel):
        super().__init__(convert_charrefs=True)
        self.base_dir = base_dir
        self.page_rel = page_rel
        self.page_dir = os.path.dirname(os.path.join(base_dir, page_rel))
        self.text = []
        self.dead, self.miss, self.alt, self.nodim, self.http = [], [], [], [], []

    def _norm(self, href):
        href = href.split("?")[0].split("#")[0]
        return href

    def check_link(self, href):
        if not href:
            return
        if href.startswith(SKIP_PREFIXES):
            if href.startswith("http://") and "w3.org" not in href:
                self.http.append(href)
            return
        norm = self._norm(href)
        if norm.startswith("/"):
            tgt = os.path.normpath(os.path.join(self.base_dir, norm.lstrip("/")))
        else:
            tgt = os.path.normpath(os.path.join(self.page_dir, norm))
        if not os.path.exists(tgt):
            self.dead.append(href)

    def check_img(self, d):
        src = d.get("src", "")
        if not src:
            return
        if src.startswith(SKIP_PREFIXES):
            if src.startswith("http://") and "w3.org" not in src:
                self.http.append(src)
            return
        norm = self._norm(src)
        if norm.startswith("/"):
            tgt = os.path.normpath(os.path.join(self.base_dir, norm.lstrip("/")))
        else:
            tgt = os.path.normpath(os.path.join(self.page_dir, norm))
        if not os.path.exists(tgt):
            self.miss.append(src)
        alt = d.get("alt")
        if alt is None or alt.strip() == "":
            self.alt.append(src)          # 装饰性背景图 alt="" 可接受，人工判断
        if not d.get("width") or not d.get("height"):
            self.nodim.append(src)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a":
            self.check_link(d.get("href", ""))
        elif tag == "img":
            self.check_img(d)
        elif tag in ("link", "script"):
            s = d.get("href") or d.get("src") or ""
            if s.startswith("http://") and "w3.org" not in s:
                self.http.append(s)

    def handle_data(self, data):
        self.text.append(data)


def main():
    html_files = collect_html(PUBLIC)
    dead = []; miss = []; alt = []; nodim = []; http = []; thin = []
    for hf in html_files:
        page_rel = os.path.relpath(hf, PUBLIC)
        p = AuditParser(PUBLIC, page_rel)
        try:
            with open(hf, encoding="utf-8", errors="ignore") as fh:
                p.feed(fh.read())
        except Exception as e:
            print("PARSE ERR", page_rel, e)
        dead += [(page_rel, x) for x in p.dead]
        miss += [(page_rel, x) for x in p.miss]
        alt += [(page_rel, x) for x in p.alt]
        nodim += [(page_rel, x) for x in p.nodim]
        http += [(page_rel, x) for x in p.http]
        tlen = len("".join(p.text).strip())
        if tlen < 400:
            thin.append((page_rel, tlen))

    def show(title, items, cap=80):
        print(f"\n=== {title} ({len(items)}) ===")
        for it in items[:cap]:
            print("   " + "  ·  ".join(it))

    show("死链 DEAD LINKS", dead)
    show("缺图 MISSING IMAGES", miss)
    show("空 alt (含装饰图, 人工判断)", alt)
    show("薄弱页 <400字", thin)
    show("混合内容 http:// (排除 w3.org)", http)
    show("图片缺 width/height (CLS风险)", nodim)

    print("\n=== 汇总 ===")
    print(f"  HTML 页数 : {len(html_files)}")
    print(f"  死链      : {len(dead)}")
    print(f"  缺图      : {len(miss)}")
    print(f"  空 alt    : {len(alt)}")
    print(f"  薄弱页    : {len(thin)}")
    print(f"  混合 http : {len(http)}")
    print(f"  缺尺寸    : {len(nodim)}")
    print("\n目标: 死链=0, 缺图=0, 空alt=0(装饰图除外), 混合http=0")


if __name__ == "__main__":
    main()
