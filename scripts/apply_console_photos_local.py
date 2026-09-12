#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_console_photos_local.py —— 用本地已核验成品图落盘替换主机图鉴配图

与 apply_console_photos.py 的区别：本脚本不联网。所有候选图早已下载并逐张
肉眼核验过（拼图板复核），存于 /tmp/final2（42 张，统一 ≤900px）与
/tmp/cand、/tmp/official（少数需要更高分辨率或特殊裁剪的）：

  /tmp/cand/new-2ds-xl.png   2898x2800  原图下载被截断 100px 后的裁剪版
  /tmp/official/ps5pro_crop.jpg        索尼官方 PS5 Pro 主视觉裁切
  /tmp/cand/ps-portal.jpg              索尼官方 PS Portal 产品图
  /tmp/cand/ayaneo-2021.png            AYANEO 官网 2021 款
  /tmp/cand/gpdwin2016.png             GPD 官网 Win 2016 款
  /tmp/cand/msi-claw-a1m.jpg           微星 Claw A1M 产品图

落盘后调用 sync_dimensions()，把真实像素尺寸同步到所有引用该图的页面
（图鉴页 static/console.html + 75 个 console-*.html 详情页 + public/ 构建产物）。

用法：
  python3 scripts/apply_console_photos_local.py --dry-run
  python3 scripts/apply_console_photos_local.py --apply
"""
import argparse
import os
import re
import shutil
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_IMG = os.path.join(ROOT, "static", "img", "consoles")

MAX_WIDTH = 1400
WEBP_QUALITY = 82

FINAL2 = "/tmp/final2"
CAND = "/tmp/cand"
OFFICIAL = "/tmp/official"

# 目标名 -> 本地成品图路径（override 在前，其余回落到 /tmp/final2/<name>.png）
OVERRIDE = {
    "new-2ds-xl":       os.path.join(CAND, "new-2ds-xl.png"),
    "playstation-5-pro": os.path.join(OFFICIAL, "ps5pro_crop.jpg"),
    "playstation-portal": os.path.join(CAND, "ps-portal.jpg"),
    "ayaneo":           os.path.join(CAND, "ayaneo-2021.png"),
    "gpd-win":          os.path.join(CAND, "gpdwin2016.png"),
    "msi-claw":         os.path.join(CAND, "msi-claw-a1m.jpg"),
    "ngpc":             os.path.join(CAND, "ngpc_official.jpg"),
}

TARGETS = [
    # 任天堂 3DS / DS 家族
    "3ds", "nintendo-3ds", "3ds-xl", "new-3ds", "new-2ds-xl", "2ds",
    "ds", "nds", "nintendo-ds", "ds-lite", "dsi",
    # 任天堂 掌机 / 主机
    "gameboy", "gameboy-color", "gameboy-pocket", "gb-light",
    "gameboy-advance", "gba", "switch-lite", "switch-2",
    # 索尼
    "playstation-5", "ps5", "playstation-5-pro", "playstation-portal",
    "playstation-2", "ps2", "psp-go",
    # 微软
    "xbox-one", "xbox-series-x",
    # 世嘉
    "sg1000", "master-system", "mega-drive", "saturn", "game-gear", "dreamcast",
    # 雅达利 / 其他
    "atari-2600", "atari-7800", "neo-geo", "ngpc", "3do",
    # Windows 掌机
    "ayaneo", "gpd-win", "msi-claw",
]


def source_path(target):
    return OVERRIDE.get(target) or os.path.join(FINAL2, f"{target}.png")


def load(target):
    p = source_path(target)
    if not os.path.exists(p):
        return None, None
    im = Image.open(p)
    im.load()
    return im.convert("RGB"), p


def sync_dimensions(updated):
    """把新图真实像素尺寸同步到所有引用它的页面（图鉴页 + 各详情页）。"""
    targets = {f"img/consoles/{t}.webp" for t in updated}
    pages = set()
    for base in (os.path.join(ROOT, "static"), os.path.join(ROOT, "public")):
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith(".html"):
                    pages.add(os.path.join(dirpath, fn))

    total_files, total_imgs = 0, 0
    for page in sorted(pages):
        try:
            html = open(page, encoding="utf-8").read()
        except Exception:
            continue
        if not any(t in html for t in targets):
            continue
        n = 0

        def repl(m):
            nonlocal n
            tag = m.group(0)
            hit = next((t for t in targets if f'src="{t}"' in tag), None)
            if not hit:
                return tag
            key = hit.split("/")[-1][:-5]
            w, h = updated[key]
            new_tag = re.sub(r'width="\d+"', f'width="{w}"', tag, count=1)
            new_tag = re.sub(r'height="\d+"', f'height="{h}"', new_tag, count=1)
            if new_tag != tag:
                n += 1
            return new_tag

        html = re.sub(r"<img\b[^>]*>", repl, html)
        if n:
            open(page, "w", encoding="utf-8").write(html)
            total_files += 1
            total_imgs += n
    print(f"  尺寸同步：{total_files} 个页面 / {total_imgs} 处 <img> 已更新")
    return total_files, total_imgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(FINAL2):
        print(f"缺少候选目录 {FINAL2}", file=sys.stderr)
        return 1

    # 备份
    if args.apply:
        bak = "/tmp/consoles_backup_round2"
        if not os.path.isdir(bak):
            shutil.copytree(STATIC_IMG, bak)
            print(f"  已备份原图 -> {bak}")

    updated = {}
    fail = []
    for t in TARGETS:
        im, p = load(t)
        if im is None:
            fail.append(t)
            print(f"  ! {t:<20} 缺少本地图 {source_path(t)}", file=sys.stderr)
            continue
        if im.width > MAX_WIDTH:
            im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
        out = os.path.join(STATIC_IMG, f"{t}.webp")
        if args.apply:
            im.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
        updated[t] = im.size
        kb = os.path.getsize(out) // 1024 if (args.apply and os.path.exists(out)) else 0
        print(f"  {t:<20} {im.size[0]}x{im.size[1]:<5} {kb}KB  <- {os.path.basename(p)}")

    if not updated:
        print("没有任何图片被更新，中止", file=sys.stderr)
        return 1

    if args.apply:
        sync_dimensions(updated)
        print(f"\n完成：更新 {len(updated)} 张图")
    else:
        print(f"\n[dry-run] 可更新 {len(updated)} 张图")
    if fail:
        print(f"失败 {len(fail)}: {fail}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
