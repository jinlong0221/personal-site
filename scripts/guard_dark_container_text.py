#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_dark_container_text.py — 根因守卫：禁止「硬编码深色容器」里的文字用会随主题变的颜色

背景（2026-09-19 全站 4 页事故，龙兄点名批评的 bug）：
- hero 这类容器若把背景写成**硬编码深色**（渐变/纯色，不随主题变），而里面的标题/正文写
  `color:var(--text)`（随主题，浅色主题下是近黑），就会在**浅色主题下变成黑字压黑底、看不见**。
- 事故页：apple `.ap-hero` / chinajoy `.cj-hero` / marvel `.mv-hero` / typhoon `.tf-hero`
  的 h1 都是 `color:var(--text)`，而各自容器背景是硬编码深色。

判定：
- 「硬编码深色背景」= 某条规则的 background / background-image 里含**深色硬编码色**
  （十六进制按相对亮度 < 0.20 判深；`rgba(r,g,b,a)` 若 rgb 亮度 < 0.20 且 a ≥ 0.30 也算），
  且该规则选择器**不含** `[data-theme=...]`（那是随主题切换的，不算固定），
  也**不含** `::before/::after`（伪元素是叠层，不是容器底），
  且是**简单容器选择器**（只由类名组成，无后代/子代组合符）——避免把后代规则里的类误登记。
- 「随主题变的文字」= 规则里声明 `color:var(--text)` / `--text-secondary` / `--text-muted`
  / `--text-muted-new`。
- 若某条「随主题文字」规则的选择器所含类名 ∩ 硬编码深色容器类集合 ≠ ∅ → 判为泄漏（ERROR）。

正确做法：硬编码深色容器里的文字一律**固定浅色**（本站统一 `#f5f5f7`）。

用法：
    python3 scripts/guard_dark_container_text.py [--root DIR] [-q]
    （--root 用于自检/对临时目录扫描；默认扫仓库根）

退出码：发现泄漏返回 1，否则 0。
"""

import argparse
import os
import re
import sys

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content"]
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy", ".design", "data", "outputs", "scripts"}
SCAN_EXTS = {".css", ".html"}

# 随主题变的文字变量（浅色主题下会变深/变黑）
THEME_TEXT_RE = re.compile(
    r"color\s*:\s*var\(--(?:text|text-secondary|text-muted|text-muted-new)\b"
)

STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
CLASS_RE = re.compile(r"\.([A-Za-z_][\w-]*)")
HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGBA_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([0-9.]+)\s*)?\)"
)
SIMPLE_CONTAINER_RE = re.compile(r"^(?:\.[A-Za-z_][\w-]*)+$")


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum_rgb(r, g, b):
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def is_dark_bg_value(value):
    """background(-image) 的值是否含深色硬编码色。"""
    for h in HEX_RE.findall(value):
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        if lum_rgb(r, g, b) < 0.20:
            return True
    for m in RGBA_RE.finditer(value):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        if a >= 0.30 and lum_rgb(r, g, b) < 0.20:
            return True
    return False


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def collect_css(path):
    """返回该文件里的 CSS 文本（.css 全文；.html 取所有 <style> 块）。"""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        raw = fh.read()
    if path.lower().endswith(".css"):
        return strip_comments(raw)
    return strip_comments("\n".join(STYLE_BLOCK_RE.findall(raw)))


def scan_file(path):
    """返回该文件的泄漏列表 [(selector, detail)]。"""
    css = collect_css(path)
    if not css.strip():
        return []

    rules = RULE_RE.findall(css)

    # 1) 收集「硬编码深色容器」的类名
    dark_classes = {}
    for sel, body in rules:
        if "[data-theme" in sel or "::" in sel:
            continue
        m = re.search(r"background(?:-image)?\s*:\s*([^;]+)", body, re.IGNORECASE)
        if not m:
            continue
        if not is_dark_bg_value(m.group(1)):
            continue
        for part in sel.split(","):
            part = part.strip()
            if SIMPLE_CONTAINER_RE.match(part):
                for cls in CLASS_RE.findall(part):
                    dark_classes.setdefault(cls, part)

    if not dark_classes:
        return []

    # 2) 找出「随主题变的文字」且落在深色容器里的规则
    leaks = []
    for sel, body in rules:
        if "[data-theme" in sel:
            continue
        if not THEME_TEXT_RE.search(body):
            continue
        hit = [c for c in CLASS_RE.findall(sel) if c in dark_classes]
        if hit:
            src = ", ".join(sorted({dark_classes[c] for c in hit}))
            leaks.append((" ".join(sel.split()), src))
    return leaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    total = 0
    for d in SCAN_DIRS:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in SCAN_EXTS:
                    continue
                fpath = os.path.join(dirpath, fn)
                try:
                    leaks = scan_file(fpath)
                except Exception as exc:  # 不让单文件异常吞掉整个守卫
                    print(f"  [warn] 跳过 {fpath}: {exc}")
                    continue
                if leaks:
                    rel = os.path.relpath(fpath, root)
                    for sel, src in leaks:
                        total += 1
                        print(f"❌ {rel}")
                        print(f"     随主题文字规则: {sel}")
                        print(f"     落在硬编码深色容器: {src}")
                        print(f"     → 该容器背景不随主题，文字请改成固定浅色 #f5f5f7")

    if total:
        print(f"\n[guard_dark_container_text] FAIL: 发现 {total} 处「深色容器 + 随主题文字」泄漏")
        print("说明：容器背景是硬编码深色时，color:var(--text) 会在浅色主题下变近黑 → 看不见。")
        return 1

    if not args.quiet:
        print("[guard_dark_container_text] PASS: 无「硬编码深色容器 + 随主题文字」泄漏")
    return 0


if __name__ == "__main__":
    sys.exit(main())
