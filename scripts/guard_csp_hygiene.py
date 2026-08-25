#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_csp_hygiene.py — 安全基线守卫（退出码 1 = 失败，0 = 通过）
锁定本次红队加固成果，防止回归：
  [FAIL] 源码残留占位死配置 https://umami.example.com（含 umami 孤儿 partial）
  [FAIL] CSP 中 cdn.jsdelivr.net 未收窄到 /npm/gitalk/（整站 CDN 放行过宽）
  [FAIL] HTML 中仍用协议相对外链 //hm.baidu.com / //busuanzi.ibruce.info
  [FAIL] head.html 延迟加载清单仍引用死代码 js/umami-hot.js
  [WARN] CSP 仍含 'unsafe-inline'（已知残留：全站内联事件处理器/页面内联脚本所致；
         彻底移除需将事件处理器改为 addEventListener + 外部化页面脚本，见修复报告路线图）
扫描范围：layouts、static、js（排除 public / pagefind / node_modules / .git / .workbuddy）。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = [
    os.path.join(ROOT, "layouts"),
    os.path.join(ROOT, "static"),
    os.path.join(ROOT, "js"),
]
EXCLUDE = ("/public/", "/pagefind/", "/node_modules/", "/.git/", "/.workbuddy/", "/.design/", "/resources/")

def collect():
    out = []
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for dp, _, fns in os.walk(d):
            if any(seg in dp for seg in EXCLUDE):
                continue
            for fn in fns:
                if fn.endswith((".html", ".js")):
                    out.append(os.path.join(dp, fn))
    return out

def main():
    errors, warns = [], []
    for p in collect():
        rel = os.path.relpath(p, ROOT)
        try:
            text = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue

        # 1) 占位死配置
        if "umami.example.com" in text:
            errors.append(f"[FAIL] {rel}: 残留 umami.example.com")
        # 2) jsdelivr 未收窄
        if "cdn.jsdelivr.net" in text and "cdn.jsdelivr.net/npm/gitalk" not in text:
            errors.append(f"[FAIL] {rel}: cdn.jsdelivr.net 未收窄到 /npm/gitalk/")
        # 3) 协议相对外链
        if re.search(r'(src|href)="//(hm\.baidu\.com|busuanzi\.ibruce\.info)', text):
            errors.append(f"[FAIL] {rel}: 协议相对外链 //hm.baidu.com / //busuanzi.ibruce.info")
        # 4) head.html 延迟清单死代码
        if rel.endswith("layouts/partials/head.html") and "umami-hot.js" in text:
            errors.append(f"[FAIL] {rel}: 延迟加载清单仍引用 js/umami-hot.js")
        # 5) unsafe-inline 残留（已知，仅告警）
        if "'unsafe-inline'" in text:
            warns.append(f"[WARN] {rel}: 仍含 'unsafe-inline'（已知残留，见路线图）")

    print("=" * 60)
    print("安全基线守卫 guard_csp_hygiene")
    print("=" * 60)
    for w in warns:
        print(w)
    for e in errors:
        print(e)
    if not errors and not warns:
        print("全部通过，无告警。")
    elif not errors:
        print(f"\n通过（{len(warns)} 条已知残留告警）。")
    print("=" * 60)
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
