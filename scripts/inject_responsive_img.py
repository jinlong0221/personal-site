#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_responsive_img.py — 把全站 <img> 包成 <picture>，注入 480w/768w 响应式源（移动端提速）。

与 gen_responsive_images.py 配套：缩略图已预生成，本脚本给 HTML 的 <img> 套 <picture>，
让浏览器按视口宽度自动选图：≤600px(手机) 用 480w，≤1000px(平板) 用 768w，其余用原图。
无损且幂等（已加 data-rsp="1" 标记的跳过）。

只对「缩略图确实存在」的图注入；窄图（无缩略图）保持原 <img> 不变。
即使某图缺缩略图，<picture> 的 <source> 404 也会回退到 <img> 原图，不会破图。

用法：
  python3 scripts/inject_responsive_img.py --check <file>   # 单文件预览（不写回）
  python3 scripts/inject_responsive_img.py                  # 全站 static/ + travel-dist/ 写回
"""
import os
import re
import sys
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_ROOTS = [os.path.join(ROOT, "static"), os.path.join(ROOT, "travel-dist")]
IMG_RE = re.compile(r'<img\b([^>]*)>', re.I)
ATTR_RE = re.compile(r'(\w[\w-]*)="([^"]*)"')


def resolve_thumb(html_path, src, w):
    if src.lower().startswith("http"):
        return None
    if src.startswith("/"):
        disk = os.path.join(ROOT, src.lstrip("/"))
    else:
        disk = os.path.normpath(os.path.join(os.path.dirname(html_path), src))
    base, _ = os.path.splitext(disk)
    return base + f"@{w}w.webp"


def process(html, html_path):
    def repl(m):
        attrs = m.group(1)
        if "data-rsp=" in attrs:
            return m.group(0)  # 已处理，跳过
        sm = re.search(r'src="([^"]+)"', attrs, re.I)
        if not sm:
            return m.group(0)
        src = sm.group(1)
        # 仅当 480w 缩略图存在才注入
        thumb480 = resolve_thumb(html_path, src, 480)
        if not thumb480 or not os.path.exists(thumb480):
            return m.group(0)
        # 保留原标签全部属性（含无引号/畸形/单引号属性，如 games 页的 data-hide-src），
        # 仅剔除可能已有的 srcset（本站当前无），附加 data-rsp 幂等标记。
        attrs_no_ss = re.sub(r'\s+srcset="[^"]*"', ' ', attrs, flags=re.I)
        base, _ = os.path.splitext(src)
        s480 = base + "@480w.webp"
        s768 = base + "@768w.webp"
        new_img = f'<img{attrs_no_ss.rstrip()} data-rsp="1">'
        return (
            f'<picture>\n'
            f'<source media="(max-width:600px)" srcset="{s480}">\n'
            f'<source media="(max-width:1000px)" srcset="{s768}">\n'
            f'{new_img}\n'
            f'</picture>'
        )
    return IMG_RE.sub(repl, html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", help="单文件预览（不写回）")
    ap.add_argument("--dir", action="append", help="额外处理的目录")
    args = ap.parse_args()

    if args.check:
        p = args.check
        html = open(p, encoding="utf-8").read()
        out = process(html, p)
        if args.check.endswith(".html"):
            # 打印变更区域预览
            import difflib
            for line in difflib.unified_diff(
                html.splitlines(), out.splitlines(), lineterm="", n=0
            ):
                print(line)
        else:
            print(out)
        return 0

    roots = list(TARGET_ROOTS)
    if args.dir:
        roots += [os.path.join(ROOT, d) for d in args.dir]
    changed = 0
    count = 0
    for root in roots:
        if not os.path.isdir(root):
            continue  # 目录不存在（如 CI 无 travel-dist）直接跳过，不报错
        for dp, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith(".html"):
                    continue
                p = os.path.join(dp, fn)
                try:
                    html = open(p, encoding="utf-8").read()
                except Exception:
                    continue
                out = process(html, p)
                if out != html:
                    open(p, "w", encoding="utf-8").write(out)
                    changed += 1
                    count += out.count("<picture>")
    print(f"[done] 处理 {changed} 个文件，注入 {count} 个 <picture>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
