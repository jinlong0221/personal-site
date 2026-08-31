#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_game_covers.py — 为「即将发售」的 PS5 新游戏生成封面占位图。

背景：
- games.html 的关注卡片用 <img class="game-cover" src="img/games/<slug>-cover.webp">，
  缺少文件会 404。官方美术图有版权、不可随意取用，因此生成**程序化文字封面占位图**：
  暗底 + 金色中文标题 + 英文名 + 发售日。后续拿到官方授权素材可直接覆盖同名文件。

性质说明（非 AI 生成）：
- 本脚本用 Pillow 做确定性绘制（纯文字排版 + 纯色/渐变背景），
  不涉及任何生成式模型，也不是照片。仅为 UI 占位图。

用法：
  python3 scripts/build_game_covers.py            # 生成缺失的封面
  python3 scripts/build_game_covers.py --force    # 全部重生成
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "static", "img", "games")

W, H = 1200, 630
BG_TOP = (20, 20, 20)
BG_BOTTOM = (34, 32, 30)
GOLD = (201, 168, 76)
MUTED = (150, 145, 135)
WHITE = (232, 226, 214)

# slug, 中文标题, 英文名, 发售日, 平台短标
GAMES = [
    ("marvels-wolverine", "漫威金刚狼", "Marvel's Wolverine", "2026-09-15", "PS5 独占"),
    ("blood-of-dawnwalker", "破晓行者之血", "The Blood of Dawnwalker", "2026-09-03", "PS5 / Xbox / PC"),
    ("silent-hill-townfall", "寂静岭：Townfall", "Silent Hill: Townfall", "2026-09-24", "PS5 / Xbox / PC"),
    ("onimusha-way-of-the-sword", "鬼武者 Way of the Sword", "Onimusha: Way of the Sword", "2026-09-25", "PS5 / Xbox / PC / Switch 2"),
    ("phantom-blade-zero", "影之刃：零", "Phantom Blade Zero", "2026-10-29", "PS5 / PC"),
    ("god-of-war-laufey", "战神：劳菲", "God of War: Laufey", "2027-02-16", "PS5 独占"),
]


def pick_font(size, bold=False):
    """挑一个可用的中文字体（macOS 优先 STHeiti / PingFang / Hiragino）。"""
    patterns = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for pat in patterns:
        for fp in glob.glob(pat):
            try:
                return ImageFont.truetype(fp, size, index=0)
            except Exception:
                continue
    return ImageFont.load_default()


def fit_font(draw, text, max_width, start_size, min_size, bold=False):
    """从 start_size 逐步缩小，直到文本宽度 <= max_width。"""
    size = start_size
    while size >= min_size:
        f = pick_font(size, bold)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 2
    return pick_font(min_size, bold)


def make_cover(slug, title_zh, title_en, release, platform):
    img = Image.new("RGB", (W, H), BG_TOP)
    d = ImageDraw.Draw(img)

    # 竖向渐变背景
    for y in range(H):
        t = y / (H - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # 顶部/底部金色细边
    d.rectangle([0, 0, W, 6], fill=GOLD)
    d.rectangle([0, H - 6, W, H], fill=GOLD)

    # 中文标题（自动缩放到 90% 宽度内）
    f_title = fit_font(d, title_zh, W * 0.86, start_size=88, min_size=42)
    tw = d.textlength(title_zh, font=f_title)
    d.text(((W - tw) / 2, H * 0.30), title_zh, font=f_title, fill=GOLD)

    # 英文名
    f_en = fit_font(d, title_en, W * 0.80, start_size=40, min_size=22)
    ew = d.textlength(title_en, font=f_en)
    d.text(((W - ew) / 2, H * 0.50), title_en, font=f_en, fill=WHITE)

    # 分隔线
    line_y = int(H * 0.60)
    d.line([(W * 0.38, line_y), (W * 0.62, line_y)], fill=GOLD, width=2)

    # 发售日 + 平台
    meta = f"📅 {release} 发售 · {platform}"
    f_meta = fit_font(d, meta, W * 0.84, start_size=34, min_size=20)
    mw = d.textlength(meta, font=f_meta)
    d.text(((W - mw) / 2, H * 0.68), meta, font=f_meta, fill=MUTED)

    # 占位说明（小字，便于辨认这是占位图）
    note = "封面占位图 · 待补官方素材"
    f_note = pick_font(22)
    nw = d.textlength(note, font=f_note)
    d.text(((W - nw) / 2, H * 0.86), note, font=f_note, fill=(110, 106, 100))

    out = os.path.join(IMG_DIR, f"{slug}-cover.webp")
    img.save(out, "WEBP", quality=86)
    return out


def main():
    force = "--force" in sys.argv
    os.makedirs(IMG_DIR, exist_ok=True)
    n_new = n_skip = 0
    for slug, zh, en, rel, plat in GAMES:
        dst = os.path.join(IMG_DIR, f"{slug}-cover.webp")
        if os.path.exists(dst) and not force:
            n_skip += 1
            continue
        p = make_cover(slug, zh, en, rel, plat)
        n_new += 1
        print(f"  ✓ {os.path.basename(p)}")
    print(f"\n生成 {n_new} 张，跳过已存在 {n_skip} 张 → {IMG_DIR}")


if __name__ == "__main__":
    main()
