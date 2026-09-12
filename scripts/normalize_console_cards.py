#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 static/img/consoles/ 里的机型图统一成「同一尺寸的相纸」，
让 console.html 的卡片图在网格里大小一致、底色一致 —— 对齐苹果板块（.ap-prod-img）的观感。

做法（不改内容，只做版式归一化，不生成任何画面）：
  1. 读原图（真实照片，原封不动保留在 static/img/consoles/ 作底稿）。
  2. 判断底色：
     - 近白底   → 裁去白边，把机身按比例缩放居中贴到白色画布上；
     - 单色底   → 用「从四边泛洪」把底色抠掉（只吃与边缘相连、颜色接近的那一片，
                  不会误伤机身内部像素），再把抠出来的机身贴到白色画布上；
     - 复杂实景 → 直接等比缩放居中，四周留白（当作一张「装裱好的照片」）。
  3. 输出统一 960x480 的画布到 static/img/consoles/plate/。

输出目录与原图分离，原图永远是权威底稿，可随时重跑。
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "static", "img", "consoles")
OUT_DIR = os.path.join(SRC_DIR, "plate")

CW, CH = 960, 480          # 画布尺寸（2:1）
FIT_W, FIT_H = 864, 432    # 机身最大占位（90%），四周留白
PAPER = (255, 255, 255)    # 相纸底色
NEAR_WHITE = 244           # 近白阈值
UNIFORM_TOL = 18           # 边缘色标准差 ≤ 该值 → 视为单色底
FLOOD_TOL = 34             # 泛洪时与边缘色的最大 RGB 距离
MAX_UPSCALE = 1.55         # 最多放大倍数，避免把低清原图糊掉

# 自动抠底的两道闸门：底色必须占住大部分边缘，且抠出来的区域颜色要够单一
BORDER_MIN = 0.60          # 候选底色在四边像素里的占比下限
FRAC_MIN, FRAC_MAX = 0.30, 0.92
CSTD_MAX = 20

# 人工白名单/黑名单（看图定，比纯自动稳）
# 黑名单：手持实拍或背景杂乱，抠底会留下漂在白纸上的孤块 → 一律按照片处理
NO_CUTOUT = {
    "ps-vita.webp", "switch.webp", "psp.webp", "sega-nomad.webp", "steam-deck.webp",
    "rog-ally.webp", "xbox-series-s.webp", "xbox-series-x.webp", "xiaobawang.webp",
    "game-watch.webp", "playstation-5-pro.webp",
    # 底色是带纹理的粉色台面 / 木桌，泛洪抠不干净会留一圈残影 → 按原照片处理
    "gba-sp.webp", "legion-go.webp",
}
# 白名单：底色是深色影棚背板、自动判据卡在色差阈值上，实际抠出来很干净
FORCE_CUTOUT = {"gamecube.webp", "gc.webp"}


def ring_stats(im):
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w, _ = a.shape
    ring = np.concatenate([
        a[1, :, :], a[h - 2, :, :], a[:, 1, :], a[:, w - 2, :], a[2, :, :], a[:, 2, :],
    ])
    med = np.median(ring, axis=0)
    spread = int(max(ring[:, i].max() - ring[:, i].min() for i in range(3)))
    return med.astype(int), spread


def trim_white(im, thr=NEAR_WHITE):
    """裁掉四周近白留白，返回 (图, 内容框)。整张都近白时返回原图。"""
    a = np.asarray(im.convert("RGB"))
    mask = (a.min(axis=2) < thr)
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return im, (0, 0, im.width, im.height)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    # 留一点边距，避免贴得太紧
    pad = 2
    y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
    y1, x1 = min(im.height, y1 + pad), min(im.width, x1 + pad)
    return im.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)


def flood_cutout(im, tol=FLOOD_TOL, seed=None):
    """从四边泛洪抠底色，返回 (RGBA 图, 抠掉占比, 抠掉区域的颜色标准差最大值)。

    只吃「与四边相连 + 颜色接近边缘色」的那一片，机身内部像素碰不到，
    因此不会像整图色键那样把白色机身一起抠掉。
    """
    rgb = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w, _ = rgb.shape
    if seed is None:
        seeds = np.concatenate([rgb[0, :], rgb[h - 1, :], rgb[:, 0], rgb[:, w - 1]])
        seed = np.median(seeds, axis=0)
        del seeds
    seed = np.asarray(seed).astype(np.int16)
    close = (np.abs(rgb - seed).sum(axis=2) <= tol * 3)

    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if close[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if close[y, x] and not visited[y, x]:
                visited[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and close[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    alpha = np.where(visited, 0, 255).astype(np.uint8)
    frac = float(visited.mean())
    if visited.any():
        rem = rgb[visited]
        cstd = int(max(int(rem[:, i].std()) for i in range(3)))
    else:
        cstd = 999
    am = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.7))
    out = im.convert("RGBA")
    out.putalpha(am)
    return out, frac, cstd


def corner_seeds(im):
    """取四角的小色块作候选底色。机身压到边缘时，取整圈中位数会算错底色，四角更稳。"""
    a = np.asarray(im.convert("RGB"))
    h, w, _ = a.shape
    k = max(3, min(h, w) // 12)
    out = []
    for y0, x0 in ((0, 0), (0, w - k), (h - k, 0), (h - k, w - k)):
        out.append(np.median(a[y0:y0 + k, x0:x0 + k].reshape(-1, 3), axis=0))
    return out


def auto_cutout(im, relaxed=False):
    """尝试自动抠底：抠掉的必须是一片「占住边缘 + 面积够大 + 颜色够单一」的底。

    先按「底色是否占住大部分四边」筛种子，再按容差从小到大试，取第一组过关的 ——
    容差越小越不会啃到机身。
    """
    rgb = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0, :], rgb[h - 1, :], rgb[:, 0], rgb[:, w - 1]]).astype(np.int16)
    seeds = list(corner_seeds(im))
    seeds.append(np.median(border, axis=0))
    frac_lo, cstd_max = (0.20, 24) if relaxed else (FRAC_MIN, CSTD_MAX)
    for seed in seeds:
        near = np.abs(border - np.asarray(seed, dtype=np.int16)).sum(axis=1) <= 34 * 3
        if near.mean() < BORDER_MIN:
            continue
        for tol in (22, 26, 34, 44):
            cut, frac, cstd = flood_cutout(im, tol, seed)
            if frac_lo <= frac <= FRAC_MAX and cstd <= cstd_max:
                return cut, frac, cstd, tol
    return None


def alpha_bbox(im):
    a = np.asarray(im.split()[-1])
    ys, xs = np.where(a > 8)
    if len(ys) == 0:
        return (0, 0, im.width, im.height)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def fit_size(w, h):
    s = min(FIT_W / w, FIT_H / h)
    if s > MAX_UPSCALE:
        s = MAX_UPSCALE
    return max(1, int(round(w * s))), max(1, int(round(h * s)))


def main():
    refs = sys.argv[1:]
    if not refs:
        print("usage: normalize_console_cards.py <slug.webp> ...", file=sys.stderr)
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)
    stats = {"white": 0, "keyed": 0, "photo": 0}
    for name in refs:
        src = os.path.join(SRC_DIR, name)
        if not os.path.exists(src):
            print("  ! missing", name)
            continue
        im = Image.open(src)
        med, spread = ring_stats(im)
        is_white = bool(np.all(med >= NEAR_WHITE))
        canvas = Image.new("RGB", (CW, CH), PAPER)

        if is_white:
            content, _ = trim_white(im)
            mode = "white"
            stats["white"] += 1
        else:
            auto = None
            if name not in NO_CUTOUT:
                auto = auto_cutout(im, relaxed=(name in FORCE_CUTOUT))
            if auto is not None:
                cut, frac, cstd, tol = auto
                content = cut.crop(alpha_bbox(cut))
                mode = f"keyed(t{tol},f{frac:.2f},s{cstd})"
                stats["keyed"] += 1
            else:
                content = im.convert("RGBA")
                mode = "photo"
                stats["photo"] += 1

        tw, th = fit_size(content.width, content.height)
        resized = content.resize((tw, th), Image.LANCZOS)
        canvas.paste(resized, ((CW - tw) // 2, (CH - th) // 2), resized if resized.mode == "RGBA" else None)
        out = os.path.join(OUT_DIR, name)
        canvas.save(out, "WEBP", quality=80, method=6)
        print(f"  {name:28} {mode:5} {im.size} -> {tw}x{th}  {os.path.getsize(out)//1024}KB")
    print("stats:", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
