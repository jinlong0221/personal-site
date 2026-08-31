#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_v_param.py — 全站 ?v=YYYYMMDD 缓存版本一键同步

为什么需要它：
  站点用 ?v=YYYYMMDD 做 CSS/JS 缓存破坏。改了 css/js 之后，全站上百个页面里
  引用它的 ?v 必须一起 bump，否则会出现「同一资源两种版本号」——guard_v_param.py
  会判 ERROR，CI 直接红。手工一处一处改必漏（历史上 travel-dist/travel.html 就
  漏过一次，导致连挂两次 CI）。

它做什么：
  扫描全站引用，把「每个仓库内资源」的所有 ?v 引用统一成该资源的 git 最后改动日
  （与 guard_v_param.py 的软校验口径完全一致，所以跑完必然 PASS + 零 WARNING）。

用法：
  python3 scripts/sync_v_param.py            # 预览（默认不动文件）
  python3 scripts/sync_v_param.py --write    # 真正落盘
  python3 scripts/sync_v_param.py --date 20260901            # 强制统一成指定日期
  python3 scripts/sync_v_param.py --only css/style.css       # 只处理指定资源

退出码：0=无异常（无论有无改动）；1=参数或执行出错。

扫描范围与 guard_v_param.py 保持一致：
  css/ static/ layouts/ travel-dist/ content/ js/ scripts/ 下的 .html/.css/.js
  排除 public/ node_modules/ .git/ resources/ .workbuddy/ .design/ data/ outputs/
"""

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCAN_DIRS = ["css", "static", "layouts", "travel-dist", "content", "js", "scripts"]
SKIP_DIRS = {"public", "node_modules", ".git", "resources", ".workbuddy", ".design", "data", "outputs"}
SCAN_EXTS = {".html", ".css", ".js"}

# 与 guard_v_param.py 完全一致的引用正则
ref_re = re.compile(
    r"""(?:src|href)\s*=\s*["']([^"']+?)\?v=(\d{8})["']"""
    r"""|url\(\s*["']?([^"')]+?)\?v=(\d{8})["']?\s*\)""",
    re.IGNORECASE,
)


def resolve(asset_path, from_file):
    """把引用路径解析为仓库内真实文件路径；解析失败返回 None（外部资源）。"""
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
    """资源在 git 里的最后改动日，格式 YYYYMMDD。"""
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


def iter_files():
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in SCAN_EXTS:
                    yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser(description="全站 ?v=YYYYMMDD 缓存版本一键同步")
    ap.add_argument("--write", action="store_true", help="真正写回文件（默认只预览）")
    ap.add_argument("--date", help="强制统一成指定日期 YYYYMMDD（默认取资源 git 最后改动日）")
    ap.add_argument("--only", action="append", default=[],
                    help="只处理指定资源（可重复传入，如 --only css/style.css）")
    args = ap.parse_args()

    forced = args.date.strip() if args.date else None
    if forced and not re.fullmatch(r"\d{8}", forced):
        print("[sync_v_param] ERROR: --date 必须是 8 位数字，如 20260901")
        sys.exit(1)
    only = {o.strip().lstrip("./") for o in args.only if o.strip()}

    # 第一遍：收集 资源相对路径 -> 目标版本号
    targets = {}
    for fpath in iter_files():
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        for m in ref_re.finditer(text):
            asset = m.group(1) or m.group(3)
            real = resolve(asset, fpath)
            if real is None or not os.path.exists(real):
                continue
            rel = os.path.relpath(real, ROOT)
            if only and rel.lstrip("./") not in only:
                continue
            if rel in targets:
                continue
            if forced:
                targets[rel] = forced
            else:
                gd = git_last_date(rel)
                if gd:
                    targets[rel] = gd

    if not targets:
        print("[sync_v_param] 没有找到需要同步的仓库内资源引用。")
        sys.exit(0)

    # 第二遍：按目标版本号改写引用
    changed_files = 0
    total_repl = 0
    detail = []

    for fpath in iter_files():
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue

        hits = 0
        out = text

        def _sub(m):
            nonlocal hits
            asset = m.group(1) or m.group(3)
            ver = m.group(2) or m.group(4)
            real = resolve(asset, fpath)
            if real is None or not os.path.exists(real):
                return m.group(0)
            rel = os.path.relpath(real, ROOT)
            want = targets.get(rel)
            if not want or want == ver:
                return m.group(0)
            hits += 1
            return m.group(0).replace("?v=" + ver, "?v=" + want)

        out = ref_re.sub(_sub, out)
        if hits and out != text:
            changed_files += 1
            total_repl += hits
            detail.append((os.path.relpath(fpath, ROOT), hits))
            if args.write:
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(out)

    mode = "已写入" if args.write else "预览（未改动任何文件，加 --write 生效）"
    print(f"[sync_v_param] 目标版本：")
    for rel, want in sorted(targets.items()):
        print(f"  - {rel} -> ?v={want}")
    print(f"[sync_v_param] {mode}：{changed_files} 个文件、{total_repl} 处 ?v 引用")
    for rel, hits in sorted(detail)[:40]:
        print(f"  · {rel}  ({hits} 处)")
    if len(detail) > 40:
        print(f"  … 其余 {len(detail) - 40} 个文件已省略")
    if not args.write and changed_files:
        print("\n提示：确认无误后运行  python3 scripts/sync_v_param.py --write")


if __name__ == "__main__":
    main()
