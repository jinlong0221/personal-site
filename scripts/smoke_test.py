#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smoke_test.py — 部署前站点冒烟测试（后端回归闸）

作用：在 hugo 构建出的 public/ 上，静态校验「本地资源引用是否全部可解析」，
拦截会导致线上页面渲染断裂的 404（img/script/css/font/link 等），并提醒内链死链。
不做网络请求、不依赖密钥，CI 可安全运行。

检测项：
  - <img src> / <script src> / <link href>（含预加载字体/样式）的本地引用必须存在文件
  - <a href> 内部链接：仅 WARN（不阻断），因目录路由/锚点易误判
  - public/index.html 必须存在（构建确实产出首页）

跳过：http(s)://、// 协议相对、data:、mailto:、tel:、javascript:、纯 # 锚点

用法：python3 scripts/smoke_test.py [public_dir]
退出码：发现本地资源 404 → 1；否则 0（内链 WARN 不阻断）。
"""
import os
import sys
from html.parser import HTMLParser

PUBLIC = sys.argv[1] if len(sys.argv) > 1 else "public"
SKIP_PREFIXES = ("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:", "#")


def normalize(ref: str) -> str:
    return ref.split("#", 1)[0].split("?", 1)[0]


def is_external(ref: str) -> bool:
    return ref == "" or ref.startswith(SKIP_PREFIXES)


def candidates(public_root: str, html_path: str, ref: str):
    """返回 ref 在 public 下的候选文件路径列表。"""
    ref = normalize(ref)
    if is_external(ref):
        return None
    if ref.startswith("/"):
        base = os.path.normpath(public_root + "/" + ref)
    else:
        base = os.path.normpath(os.path.join(os.path.dirname(html_path), ref))
    cands = [base]
    if os.path.isdir(base):
        cands.append(os.path.join(base, "index.html"))
    if not os.path.splitext(base)[1]:  # 无扩展名：尝试 .html 与目录索引
        cands.append(base + ".html")
        cands.append(os.path.join(base, "index.html"))
    return cands


def exists_any(cands):
    return any(os.path.exists(c) for c in cands)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets = []  # (ref, tag)
        self.links = []   # ref

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in ("img", "script"):
            s = d.get("src")
            if s:
                self.assets.append((s, tag))
        elif tag == "link":
            h = d.get("href")
            if h:
                self.assets.append((h, "link:" + (d.get("rel") or "")))
        elif tag == "a":
            h = d.get("href")
            if h:
                self.links.append(h)


def main():
    if not os.path.isdir(PUBLIC):
        print(f"❌ 构建产物目录不存在：{PUBLIC}")
        sys.exit(1)

    html_files = []
    for root, _, files in os.walk(PUBLIC):
        for f in files:
            if f.endswith(".html"):
                html_files.append(os.path.join(root, f))

    missing_assets = []  # (page, tag, ref)
    warn_links = []      # (page, ref)

    for p in html_files:
        try:
            html = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        c = Collector()
        c.feed(html)
        rel = os.path.relpath(p, PUBLIC)
        for ref, tag in c.assets:
            if is_external(ref):
                continue
            cands = candidates(PUBLIC, p, ref)
            if not exists_any(cands):
                missing_assets.append((rel, tag, ref))
        for ref in c.links:
            if is_external(ref):
                continue
            cands = candidates(PUBLIC, p, ref)
            if not exists_any(cands):
                warn_links.append((rel, ref))

    if not os.path.exists(os.path.join(PUBLIC, "index.html")):
        print("❌ 构建产物缺失 public/index.html（Hugo 未产出首页）")
        sys.exit(1)

    if missing_assets:
        print(f"❌ 发现 {len(missing_assets)} 处本地资源引用 404（会导致页面渲染断裂，阻断部署）：")
        for page, tag, ref in missing_assets[:60]:
            print(f"   - {page}: <{tag}> {ref}")
        sys.exit(1)

    print(f"✅ 站点冒烟测试通过：{len(html_files)} 个 HTML 页面，本地资源引用全部可解析")
    if warn_links:
        print(f"⚠️ {len(warn_links)} 处内链疑似 404（仅供参考，不阻断部署）：")
        for page, ref in warn_links[:30]:
            print(f"   - {page} -> {ref}")
    sys.exit(0)


if __name__ == "__main__":
    main()
