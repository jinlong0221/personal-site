#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_csp_hygiene.py — 安全基线守卫（退出码 1 = 失败，0 = 通过）
锁定红队加固成果，防止回归：
  [FAIL] 源码残留占位死配置 https://umami.example.com（含 umami 孤儿 partial）
  [FAIL] CSP 中 cdn.jsdelivr.net 未收窄到 /npm/ 子路径（整站 CDN 裸放行过宽）
  [FAIL] HTML 中仍用协议相对外链 //hm.baidu.com / //busuanzi.ibruce.info
  [FAIL] head.html 延迟加载清单仍引用死代码 js/umami-hot.js
  [FAIL] 任一 CSP 的 script-src 仍含 'unsafe-inline'（内联事件处理器/页面脚本须改为
         事件委托 + sha256 哈希白名单；style-src 保留 'unsafe-inline' 属既定技术取舍，不报错）
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

CSP_META_RE = re.compile(r'Content-Security-Policy"\s*content="([^"]*)"', re.IGNORECASE)

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

def csp_directive_has(csp, directive_prefix, token):
    """Return True if a directive (e.g. script-src) within csp contains token."""
    for part in csp.split(";"):
        seg = part.strip()
        if not seg:
            continue
        words = seg.split()
        if words and words[0].lower() == directive_prefix:
            if token in words:
                return True
    return False

def main():
    errors, warns = [], []
    style_kept = 0
    for p in collect():
        rel = os.path.relpath(p, ROOT)
        try:
            text = open(p, "r", encoding="utf-8").read()
        except Exception:
            continue

        # 1) 占位死配置
        if "umami.example.com" in text:
            errors.append(f"[FAIL] {rel}: 残留 umami.example.com")
        # 2) jsdelivr 未收窄（裸 CDN 放行过宽，必须锁定到 /npm/ 具体包路径）
        if "cdn.jsdelivr.net" in text and "cdn.jsdelivr.net/npm/" not in text:
            errors.append(f"[FAIL] {rel}: cdn.jsdelivr.net 未收窄到 /npm/ 子路径")
        # 3) 协议相对外链
        if re.search(r'(src|href)="//(hm\.baidu\.com|busuanzi\.ibruce\.info)', text):
            errors.append(f"[FAIL] {rel}: 协议相对外链 //hm.baidu.com / //busuanzi.ibruce.info")
        # 4) head.html 延迟清单死代码
        if rel.endswith("layouts/partials/head.html") and "umami-hot.js" in text:
            errors.append(f"[FAIL] {rel}: 延迟加载清单仍引用 js/umami-hot.js")
        # 5) script-src 仍含 'unsafe-inline'（硬性失败，阻断回归）
        for m in CSP_META_RE.finditer(text):
            csp = m.group(1)
            if csp_directive_has(csp, "script-src", "'unsafe-inline'"):
                errors.append(f"[FAIL] {rel}: CSP script-src 仍含 'unsafe-inline'（须用 sha256 哈希白名单）")
            elif csp_directive_has(csp, "default-src", "'unsafe-inline'"):
                errors.append(f"[FAIL] {rel}: CSP default-src 仍含 'unsafe-inline'")
        # 6) style-src 保留 unsafe-inline 属既定取舍，仅计数（最后汇总一行）
        for m in CSP_META_RE.finditer(text):
            if csp_directive_has(m.group(1), "style-src", "'unsafe-inline'"):
                style_kept += 1

    print("=" * 60)
    print("安全基线守卫 guard_csp_hygiene")
    print("=" * 60)
    for w in warns:
        print(w)
    for e in errors:
        print(e)
    if style_kept:
        print(f"[NOTE] {style_kept} 个页面 style-src 保留 'unsafe-inline'（既定技术取舍：全站大量内联 style= 与 critical-css，外化成本过高）")
    if not errors and not warns:
        print("全部通过，无告警。")
    elif not errors:
        print(f"\n通过（{len(warns)} 条既定取舍提示）。")
    else:
        print(f"\n失败：{len(errors)} 项必须修复。")
    print("=" * 60)
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
