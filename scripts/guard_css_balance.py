#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_css_balance.py —— 页内 <style> 块花括号平衡守卫。

背景（2026-10-03 真实事故）：给游戏详情页扩写板块时，批量替换把一条规则写成了
「嵌在另一条规则里」的畸形 CSS：

    .lx-aa-step-no{ ...;border-radius:50%;.lx-aa-step-no{background:var(--gold);...}

整个 style 块多出一个未闭合的 `{`。**浏览器从那一行起会静默丢弃该块内之后的
所有规则** —— 源码里规则一条不少、grep 也查不出来，页面表现却是「后半段像没写样式」
（当时是 Playwright 量到 `border-left: 0px`、`display:inline-block` 没生效才发现）。

判据（只判这一条，刻意保守、零误报）：
    剥离注释与字符串后，每个 <style> 块的花括号必须严格平衡，
    既不能中途出现多余的 `}`，结束时深度也必须回到 0。
不判「规则嵌套是否合法」—— 那条启发式在 @media 正常嵌套下会大量误报，不值得。

用法：
  python3 scripts/guard_css_balance.py            # 扫 static/ 全部 html
  python3 scripts/guard_css_balance.py --file X   # 只扫一个文件
  python3 scripts/guard_css_balance.py -q         # 安静模式（只靠退出码）
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")
SKIP_DIRS = {"pagefind", "admin"}

STYLE_RE = re.compile(r"<style([^>]*)>(.*?)</style>", re.S)
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
STRING_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def strip_noise(css):
    """去掉注释与字符串字面量，避免其中的花括号干扰计数。"""
    css = COMMENT_RE.sub(lambda m: " " * len(m.group(0)), css)
    css = STRING_RE.sub(lambda m: " " * len(m.group(0)), css)
    return css


def scan_css(css):
    """返回 (错误列表, 每行深度信息)。"""
    clean = strip_noise(css)
    depth = 0
    line = 1
    opened_at = None
    errs = []
    for ch in clean:
        if ch == "\n":
            line += 1
        elif ch == "{":
            if depth == 0:
                opened_at = line
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                errs.append(f"第 {line} 行：出现多余的 `}}`（花括号提前闭合）")
                depth = 0
    if depth != 0:
        errs.append(
            f"块结束时花括号仍多 {depth} 个未闭合（首个多余的开括号约在第 {opened_at} 行）"
            f" —— 浏览器会把该行之后的**所有规则**静默丢弃")
    return errs


def scan_html(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()
    out = []
    for idx, (attr, css) in enumerate(STYLE_RE.findall(html)):
        errs = scan_css(css)
        if errs:
            name = "critical-css" if "critical-css" in attr else f"style#{idx}"
            for e in errs:
                out.append(f"  {name}: {e}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None)
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    if args.file:
        files = [args.file]
    else:
        files = []
        for dirpath, dirnames, filenames in os.walk(STATIC):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(".html"):
                    files.append(os.path.join(dirpath, fn))

    bad = 0
    for p in sorted(files):
        try:
            errs = scan_html(p)
        except Exception as e:
            errs = [f"  读取失败：{e}"]
        if errs:
            bad += 1
            print(f"[FAIL] {os.path.relpath(p, ROOT)}")
            for e in errs:
                print(e)
    total = len(files)
    if not args.quiet:
        if bad:
            print(f"\n[guard_css_balance] FAIL：{bad}/{total} 个页面的页内样式块花括号不平衡")
            print("  典型症状：该行之后的规则全部被浏览器忽略，页面「像没写样式」但源码看着没问题。")
            print("  修法：把多出来的 } 补回去；批量替换 CSS 后务必让本守卫过一遍。")
        else:
            print(f"[guard_css_balance] PASS：{total} 个页面的页内样式块花括号全部平衡")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
