#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guard_v_param.py — 根因守卫：?v=YYYYMMDD 缓存版本必须一致且资源存在

背景：
- 站点用 ?v=YYYYMMDD 做 CSS/JS 缓存破坏。若改了文件却忘了 bump ?v，旧缓存不会刷新；
  若不同页面引用同一资源却写了不同 ?v，会出现"有的页新有的页旧"的诡异不一致。
- 本守卫聚焦两类确定性错误（CI 安全，不依赖文件 mtime）：
  1. 同一资源在不同引用里 ?v 不一致 → ERROR（致命，必卡）。
  2. 引用的资源文件不存在 → ERROR（断链）。
- 另做"软校验"：?v 与 git 中该资源最后改动日期不符时给 WARNING（提示该 bump 了）。

扫描范围：css/ static/ layouts/ travel-dist/ content/ js/ scripts/ 下的 .html / .css / .js。
排除：public/ node_modules/ .git/ resources/ .workbuddy/ .design/ data/ outputs/。
外部 URL（http/https///）跳过。

退出码：存在 ERROR 返回 1，否则 0（WARNING 不阻断）。
"""

import os
import re
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content", "js", "scripts"]
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy", ".design", "data", "outputs"}
SCAN_EXTS = {".html", ".css", ".js"}

# 匹配 src/href/url( 后的路径 + ?v=YYYYMMDD
ref_re = re.compile(
    r"""(?:src|href)\s*=\s*["']([^"']+?)\?v=(\d{8})["']"""
    r"""|url\(\s*["']?([^"')]+?)\?v=(\d{8})["']?\s*\)""",
    re.IGNORECASE,
)

def resolve(asset_path, from_file):
    """把引用路径解析为仓库内真实文件路径；解析失败返回 None。"""
    # Hugo 模板变量（如 {{ .Site.BaseURL }}css/style.css）无法静态解析，按外部资源跳过
    if "{{" in asset_path or "}}" in asset_path:
        return None
    if asset_path.startswith(("http://", "https://", "//")):
        return None
    if asset_path.startswith("/"):
        cand = os.path.join(ROOT, "static", asset_path.lstrip("/"))
        if os.path.exists(cand):
            return cand
        cand2 = os.path.join(ROOT, asset_path.lstrip("/"))
        return cand2 if os.path.exists(cand2) else cand
    # 相对路径：先相对当前文件目录，再退化到 static/ 根（travel-dist 等部署期产物
    # 的相对引用在 public/ 下实际解析到 static/ 根，静态扫描需与之对齐，否则误报）。
    base = os.path.dirname(from_file)
    cand = os.path.normpath(os.path.join(base, asset_path))
    if os.path.exists(cand):
        return cand
    cand2 = os.path.normpath(os.path.join(ROOT, "static", asset_path))
    if os.path.exists(cand2):
        return cand2
    cand3 = os.path.normpath(os.path.join(ROOT, asset_path))
    return cand3 if os.path.exists(cand3) else cand

def git_last_date(relpath):
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y%m%d", "--", relpath],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None

def main():
    errors = []
    warnings = []
    # asset_relpath -> set(versions)
    versions = {}

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
                for m in ref_re.finditer(text):
                    asset = m.group(1) or m.group(3)
                    ver = m.group(2) or m.group(4)
                    real = resolve(asset, fpath)
                    if real is None:
                        continue  # 外部资源，跳过
                    if not os.path.exists(real):
                        errors.append(f"{os.path.relpath(fpath, ROOT)} -> 资源不存在: {asset}")
                        continue
                    rel = os.path.relpath(real, ROOT)
                    versions.setdefault(rel, set()).add(ver)

    # 一致性检查
    for rel, vers in sorted(versions.items()):
        if len(vers) > 1:
            errors.append(f"{rel} 的 ?v 不一致: {', '.join(sorted(vers))}（应统一为一个日期）")
        # 软校验：?v 与 git 最后改动日
        gd = git_last_date(rel)
        if gd and len(vers) == 1 and gd != next(iter(vers)):
            warnings.append(f"{rel}: ?v={next(iter(vers))} 但 git 最后改动日={gd}（建议 bump 到 {gd}）")

    if errors:
        print(f"[guard_v_param] FAIL: 发现 {len(errors)} 处 ?v 错误")
        for e in errors:
            print(f"  - {e}")
        if warnings:
            print(f"[guard_v_param] WARNING({len(warnings)}):")
            for w in warnings:
                print(f"  ~ {w}")
        sys.exit(1)
    print(f"[guard_v_param] PASS: {sum(len(v) for v in versions.values())} 处 ?v 引用一致且资源存在"
          + (f"；{len(warnings)} 条建议性 WARNING" if warnings else ""))
    for w in warnings:
        print(f"  ~ {w}")

if __name__ == "__main__":
    main()
