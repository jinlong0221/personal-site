#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_review_sheets.py — 把候选图片目录做成带文件名标签的拼图板，供视觉复核

用法：
  python3 scripts/make_review_sheets.py <目录> [--out /tmp/review] [--cols 3] [--rows 3]
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
]
EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def load_font(size=20):
    for c in FONT_CANDIDATES:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def build(src, outdir, cols=3, rows=3, cell=(400, 320), label_h=34):
    files = sorted(
        f for f in os.listdir(src)
        if os.path.splitext(f)[1].lower() in EXTS
    )
    if not files:
        print(f"  (空) {src}")
        return []
    os.makedirs(outdir, exist_ok=True)
    font = load_font(20)
    cw, ch = cell
    per = cols * rows
    tag = os.path.basename(os.path.normpath(src))
    sheets = []
    for si in range(0, len(files), per):
        chunk = files[si:si + per]
        nr = math.ceil(len(chunk) / cols)
        sheet = Image.new("RGB", (cw * cols, ch * nr), (248, 248, 248))
        dr = ImageDraw.Draw(sheet)
        for i, f in enumerate(chunk):
            rr, cc = divmod(i, cols)
            x, y = cc * cw, rr * ch
            dr.rectangle([x, y, x + cw - 1, y + ch - 1], outline=(205, 205, 205))
            try:
                im = Image.open(os.path.join(src, f)).convert("RGB")
            except Exception:
                dr.text((x + 8, y + label_h), f"{f} (读取失败)", fill=(200, 0, 0), font=font)
                continue
            im.thumbnail((cw - 16, ch - label_h - 12))
            sheet.paste(im, (x + 8, y + label_h))
            dr.text((x + 8, y + 6), f[:48], fill=(0, 0, 0), font=font)
        p = os.path.join(outdir, f"sheet_{tag}_{si // per + 1:02d}.png")
        sheet.save(p)
        sheets.append(p)
        print(f"  {len(chunk)} 张 -> {p}")
    return sheets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="/tmp/review")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--rows", type=int, default=3)
    args = ap.parse_args()
    build(args.src, args.out, cols=args.cols, rows=args.rows)


if __name__ == "__main__":
    main()
