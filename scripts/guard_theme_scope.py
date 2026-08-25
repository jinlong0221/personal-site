#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_theme_scope.py — 根因守卫：禁止非关键 <style> 块用全局选择器重定义全局主题变量

背景：
- 详情页/子页若在第二块 <style>（非 id="critical-css" 的关键样式）里用
  [data-theme="light"] / [data-theme="dark"] / body / :root / html 重定义
  --bg / --card / --text / --border / --nav-bg / --text-secondary 等**全局**主题变量，
  会污染全站 chrome（导航栏被重涂、撑爆等历史事故）。
- 正确做法：页面局部变量统一用命名空间（如 --zb-*），且只通过 body{var(--zb-*)} 作用本页。

判定：
- 跳过 id="critical-css" 的关键样式块（那里定义全局主题是允许的）。
- 其余 <style> 块内若出现非命名空间的全局主题变量赋值（--bg: / --card: / --text: /
  --border: / --nav-bg: / --text-secondary: / --text-muted: / --gold: 等，且不是 --zb-xxx 之类），
  即判定为泄漏。

扫描范围：css/ static/ layouts/ travel-dist/ content/ 下的 .css / .html。
排除：public/ node_modules/ .git/ resources/ .workbuddy/ .design/ data/ outputs/。

退出码：发现泄漏返回 1，否则 0。
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content"]
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy", ".design", "data", "outputs"}
SCAN_EXTS = {".css", ".html"}

# 全局主题变量名（非命名空间）。这些出现在非关键 style 块里即视为泄漏。
GLOBAL_THEME_VARS = [
    "--bg", "--bg-secondary", "--card", "--card-hover", "--border", "--border-light",
    "--text", "--text-secondary", "--text-muted", "--nav-bg", "--nav-height",
    "--gold", "--gold-light", "--blue-light", "--max-width",
]
# 构建匹配：--var: 或 --var （在声明中）。用负向前瞻排除命名空间前缀（如 --zb-）。
var_alt = "|".join(re.escape(v) for v in GLOBAL_THEME_VARS)
# 匹配形如 --bg: 或 --bg （位于声明），但不匹配 --zb-bg 等命名空间变量
theme_var_re = re.compile(r"(?<![-a-zA-Z])(" + var_alt + r")\s*:")

# 切分 <style ...>...</style> 块，并记录是否为 critical-css
style_block_re = re.compile(r"<style\b([^>]*)>(.*?)</style>", re.DOTALL | re.IGNORECASE)

def main():
    hits = []
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in SCAN_EXTS:
                    continue
                fpath = os.path.join(dirpath, fn)
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        text = fh.read()
                except (UnicodeDecodeError, OSError):
                    continue
                for m in style_block_re.finditer(text):
                    attrs, body = m.group(1), m.group(2)
                    if re.search(r'id\s*=\s*["\']critical-css["\']', attrs, re.IGNORECASE):
                        continue  # 关键样式块豁免
                    for vm in theme_var_re.finditer(body):
                        varname = vm.group(1)
                        # 二次排除：确保不是命名空间（如 --zb-bg 不会到这里，因前瞻已挡；
                        # 但 --max-width 可能误伤普通布局变量，这里只对在 :root/[data-theme]/body 选择器内的才算）
                        # 通过检查其前面的选择器是否全局来收紧
                        start = max(0, vm.start() - 200)
                        ctx = body[max(0, vm.start() - 200):vm.start()]
                        if re.search(r"(\[data-theme=|:root|^\s*body\b|html\b)", ctx[-120:]):
                            hits.append((os.path.relpath(fpath, ROOT), varname))
                            break  # 每块只报一次
    if hits:
        print(f"[guard_theme_scope] FAIL: 发现 {len(hits)} 个非关键样式块重定义全局主题变量")
        seen = set()
        for rel, var in hits:
            key = f"{rel} ({var})"
            if key in seen:
                continue
            seen.add(key)
            print(f"  - {rel}  重定义 {var}")
        print("  建议：页面局部变量改用命名空间（如 --zb-*），并通过 body{var(--zb-*)} 仅作用本页。")
        sys.exit(1)
    print("[guard_theme_scope] PASS: 无非关键样式块重定义全局主题变量（命名空间约定未被破坏）")

if __name__ == "__main__":
    main()
