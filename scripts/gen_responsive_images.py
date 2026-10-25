#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_responsive_images.py — 为 static/img 下的大图预生成响应式缩略图（移动端提速核心）。

背景：全站图片都是原始大图（普遍 1280px 宽），但手机屏只有 ~390px 宽，却照样下载整张大图，
移动端首屏常拉 800KB+ 图。本脚本为「宽度 > 阈值」的图生成 480w / 768w 两档 WebP 缩略图，
配合各页 <picture>/srcset，让手机/平板自动选小图，移动端首屏图片流量省 60-80%。

命名约定（与注入逻辑一致）：
  xxx.webp          -> xxx@480w.webp  / xxx@768w.webp
  xxx.png 原图     -> xxx@480w.webp  / xxx@768w.webp  （缩略图统一 WebP，透明保留）

用法：
  python3 scripts/gen_responsive_images.py --dry-run   # 仅统计会生成多少、多大
  python3 scripts/gen_responsive_images.py             # 实际生成（幂等：已存在跳过）
"""
import os
import sys
import argparse
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIRS = [
    os.path.join(ROOT, "static", "img"),
]
WIDTHS = [480, 768]
THRESH_W = 600          # 仅对宽度大于此值的图生成缩略图（窄图本身体积小，不动）
QUALITY = 82            # WebP 有损质量（缩略图够用，透明边沿可接受）


def gen_one(src_path, stem, out_dir, dry, made, skipped, bytes_added):
    w, h = 0, 0
    try:
        with Image.open(src_path) as im:
            w, h = im.size
    except Exception as e:
        print(f"  ! 读取失败 {src_path}: {e}", file=sys.stderr)
        return made, skipped, bytes_added
    if w <= THRESH_W:
        return made, skipped, bytes_added  # 窄图不处理
    for tw in WIDTHS:
        if tw >= w:
            continue
        out = os.path.join(out_dir, f"{stem}@{tw}w.webp")
        if os.path.exists(out):
            skipped += 1
            continue
        th = max(1, int(h * tw / w))
        if dry:
            made += 1
            continue
        try:
            with Image.open(src_path) as im:
                # 重开一次以确保在独立上下文里 resize
                t = im.resize((tw, th), Image.LANCZOS)
                if t.mode in ("RGBA", "LA") or (t.mode == "P" and "transparency" in t.info):
                    t = t.convert("RGBA")
                else:
                    t = t.convert("RGB")
                t.save(out, "WEBP", quality=QUALITY)
            bytes_added += os.path.getsize(out)
            made += 1
        except Exception as e:
            print(f"  ! 生成失败 {out}: {e}", file=sys.stderr)
    return made, skipped, bytes_added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只统计，不写文件")
    ap.add_argument("--dir", action="append", help="额外处理的图片目录（默认 static/img）")
    args = ap.parse_args()

    dirs = list(IMG_DIRS)
    if args.dir:
        dirs += [os.path.join(ROOT, d) for d in args.dir]

    total_made = 0
    total_skip = 0
    total_bytes = 0
    for d in dirs:
        if not os.path.isdir(d):
            print(f"  跳过不存在目录: {d}")
            continue
        for root, _, files in os.walk(d):
            for f in files:
                ext = f.lower().rsplit(".", 1)[-1]
                if ext not in ("webp", "png", "jpg", "jpeg"):
                    continue
                stem = os.path.splitext(f)[0]
                # 防御：跳过本身就是缩略图的文件（stem 已带 @480w/@768w 后缀），
                # 否则会生成 xxx@768w@480w.webp 这类「缩略图的缩略图」垃圾文件
                # （2026-10-25 实测一次跑出 511 个死文件，页面从不引用）。
                if stem.endswith("@480w") or stem.endswith("@768w"):
                    continue
                m, s, b = gen_one(os.path.join(root, f), stem, root, args.dry_run, 0, 0, 0)
                total_made += m
                total_skip += s
                total_bytes += b

    if args.dry_run:
        print(f"[dry-run] 将生成缩略图 {total_made} 个（已存在跳过 {total_skip}）")
        print(f"           预计新增体积约 {total_bytes/1024/1024:.1f} MB（按实际生成计）")
    else:
        print(f"[done] 新生成缩略图 {total_made} 个（已存在跳过 {total_skip}）")
        print(f"       新增体积 {total_bytes/1024/1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
