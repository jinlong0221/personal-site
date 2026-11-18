#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_theme_flash.py — 统一「主题防闪白」内联脚本：按系统偏好优先判断明暗。

背景（2026-11-18）：
  防闪白脚本原按「小时」判断（6-18 点浅色，其余深色），而 app.js / site-bundle.js
  的 getAutoTheme() 按「系统 prefers-color-scheme」判断。两套逻辑不一致 →
  首次打开会先按小时上一个色、JS 加载后再按系统改一次，出现「闪一下」且明暗不符预期。

修法：
  把内联防闪白脚本统一为「系统偏好优先，无偏好再回退按小时」，与 app.js 完全一致：
    var t=localStorage.getItem('theme');
    if(t==='light'||t==='dark') -> 用 t
    else if(window.matchMedia && matchMedia('(prefers-color-scheme: light)').matches) -> light
    else if(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) -> dark
    else -> 回退按小时

用法：
  python3 scripts/sync_theme_flash.py            # 执行替换（幂等）
  python3 scripts/sync_theme_flash.py --check    # 守卫模式：发现未统一则退出码 1
  python3 scripts/sync_theme_flash.py --selftest # 自证：正反用例
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 旧的按小时判断片段（可能存在的两种写法）
OLD_FRAGMENTS = [
    "else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}",
    "else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark');}",
    # games 页变体：三元表达式无外括号
    "else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',h>=6&&h<18?'light':'dark')}",
    "else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',h>=6&&h<18?'light':'dark');}",
]

# 新的系统优先片段（与 app.js getAutoTheme 一致，末尾回退按小时）
NEW_FRAGMENT = (
    "else{var m=window.matchMedia;"
    "if(m&&m('(prefers-color-scheme: light)').matches){document.documentElement.setAttribute('data-theme','light')}"
    "else if(m&&m('(prefers-color-scheme: dark)').matches){document.documentElement.setAttribute('data-theme','dark')}"
    "else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}"
    "}"
)

# 目标文件：含 localStorage.getItem('theme') 的 .html/.js（排除产物与依赖目录）
SKIP_DIRS = {".git", "public", "node_modules", "__pycache__", "img", ".design"}


def iter_targets():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith((".html", ".js")):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    t = f.read()
            except Exception:
                continue
            if "localStorage.getItem('theme')" in t:
                yield p, t


def is_new(t):
    """新脚本特征：防闪白脚本里含 prefers-color-scheme 判断。"""
    return "prefers-color-scheme: light" in t and "window.matchMedia" in t and "getItem('theme')" in t


def is_old(t):
    """旧脚本：含 getItem('theme') 的防闪白脚本，但没有系统偏好判断。"""
    return "getItem('theme')" in t and not is_new(t)


def replace(t):
    # 已是新脚本则不重复处理（避免把回退分支里的 getHours 再次误替换）
    if is_new(t):
        return t
    out = t
    for frag in OLD_FRAGMENTS:
        out = out.replace(frag, NEW_FRAGMENT)
    return out


def rel(p):
    return os.path.relpath(p, ROOT)


def cmd_apply():
    changed, skipped = [], []
    for p, t in iter_targets():
        if is_old(t):
            nt = replace(t)
            with open(p, "w", encoding="utf-8") as f:
                f.write(nt)
            changed.append(rel(p))
        else:
            skipped.append(rel(p))
    print(f"[apply] 已统一 {len(changed)} 个文件为「系统优先」防闪白脚本")
    for f in changed[:20]:
        print("   ✓", f)
    if len(changed) > 20:
        print(f"   ... 另有 {len(changed)-20} 个")
    print(f"[apply] 已符合/无旧脚本 {len(skipped)} 个（未改动）")
    return 0


def cmd_check():
    bad = []
    for p, t in iter_targets():
        # 只要还含旧的「按小时判断明暗」片段就算未统一
        if is_old(t):
            bad.append(rel(p))
    if bad:
        print(f"[check] ❌ 发现 {len(bad)} 个文件仍是「按小时」防闪白（未系统优先）：")
        for f in bad[:30]:
            print("   ✗", f)
        return 1
    print("[check] ✅ 全部内联防闪白脚本均为「系统优先」")
    return 0


def cmd_selftest():
    old_line = "<script>(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}else{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}}catch(e){}})();</script>"
    new_line = replace(old_line)
    ok = True
    checks = [
        ("旧样本被识别为旧", is_old(old_line) and not is_new(old_line)),
        ("转换后不再被识别为旧", not is_old(new_line)),
        ("新样本含 matchMedia", "window.matchMedia" in new_line),
        ("新样本含 light 偏好", "prefers-color-scheme: light" in new_line),
        ("新样本仍保留 localStorage 读取", "getItem('theme')" in new_line),
        ("新样本保留 getHours 作回退", "new Date().getHours()" in new_line),
        ("新样本被 is_new 认可", is_new(new_line)),
    ]
    for name, cond in checks:
        print(("   ✅ " if cond else "   ❌ ") + name)
        ok = ok and cond
    print("[selftest] " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--check":
        sys.exit(cmd_check())
    elif arg == "--selftest":
        sys.exit(cmd_selftest())
    else:
        sys.exit(cmd_apply())
