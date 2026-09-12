#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_console_photos.py — 按「机型 ↔ 权威图源」映射替换主机图鉴配图

背景：主机图鉴早年用 Pexels 关键词搜图补位，因当时无法看图，产生大量
「文不对图」（Game Boy Advance 配了 New 3DS、Atari 7800 配了 Xbox 手柄、
SG-1000 配了 PC 主机……）。本脚本改用权威图源逐张替换：

  1. article  —— Kiddle（kids.kiddle.co，维基图文镜像）条目里的候选图，
                 图片本体是 Wikimedia Commons 的 CC 授权官方产品图
  2. direct   —— 同上，但直接按 Wikimedia 文件名的 md5 哈希路径取
  3. url      —— 直接指定图片地址（维基无自由图时用厂商官网产品图）
  4. local    —— 本地已备好的图片

两种模式：
  --stage   只下载候选，转 PNG 放到 --review-dir，供视觉复核
  --apply   落盘：写 static/img/consoles/<目标>.webp，并同步 console.html 的
            width/height（记录真实像素尺寸）

用法：
  python3 scripts/apply_console_photos.py --stage
  python3 scripts/apply_console_photos.py --apply
"""
import argparse
import hashlib
import io
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_IMG = os.path.join(ROOT, "static", "img", "consoles")
CONSOLE_HTML = os.path.join(ROOT, "static", "console.html")
PAGE_BUILD = os.path.join(ROOT, "public", "console.html")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
KIDDLE = "https://kids.kiddle.co"
THUMB_WIDTHS = (1600, 1280, 1024, 800, 640, 500, 400, 320, 240, 200, 120)
MIN_GOOD_WIDTH = 700
MAX_WIDTH = 1400
WEBP_QUALITY = 82

# ---------------------------------------------------------------------------
# 映射表：输出文件名 <- (来源类型, 来源标识, 文件名 或 URL/本地路径)
# ---------------------------------------------------------------------------
MAP = [
    # ================= 任天堂 3DS 家族 =================
    ("3ds",               "article", "Nintendo_3DS", "Nintendo-3DS-AquaOpen.jpg"),
    ("nintendo-3ds",      "article", "Nintendo_3DS", "Nintendo-3DS-AquaOpen.jpg"),
    ("3ds-xl",            "article", "Nintendo_3DS", "Nintendo-3DS-XL-angled.png"),
    ("new-3ds",           "direct",  "-",            "New_Nintendo_3DS.png"),
    ("new-2ds-xl",        "local",   "-",            "/tmp/cand/new-2ds-xl.png"),
    ("2ds",               "article", "Nintendo_2DS", "Nintendo-2DS-angle.jpg"),
    # ================= 任天堂 DS 家族 =================
    ("ds",                "article", "Nintendo_DS",  "Nintendo-DS-Fat-Blue.jpg"),
    ("nds",               "article", "Nintendo_DS",  "Nintendo-DS-Fat-Blue.jpg"),
    ("nintendo-ds",       "article", "Nintendo_DS",  "Nintendo-DS-Fat-Blue.jpg"),
    ("ds-lite",           "direct",  "-",            "Nintendo-DS-Lite-Black-Open.jpg"),
    ("dsi",               "article", "Nintendo_DSi", "NIntendo_DSi.png"),
    # ================= 任天堂 掌机 =================
    ("gameboy",           "article", "Game_Boy_line", "Game-Boy-FL.jpg"),
    ("gameboy-color",     "article", "Game_Boy_line", "Nintendo-Game-Boy-Color-FL.jpg"),
    ("gameboy-pocket",    "direct",  "-",            "Game-Boy-Pocket-FL.jpg"),
    ("gb-light",          "article", "Game_Boy_line", "Game-Boy-Light-FL.jpg"),
    ("gameboy-advance",   "article", "Game_Boy_Advance",
                          "Nintendo-Game-Boy-Advance-Purple-FL.png"),
    ("gba",               "article", "Game_Boy_Advance",
                          "Nintendo-Game-Boy-Advance-Purple-FL.png"),
    ("switch-lite",       "article", "Nintendo_Switch",
                          "Nintendo_Switch_Lite_Pokemon_Zacian_and_Zamazenta_edition_White_BG.jpg"),
    ("switch-2",          "article", "Nintendo_Switch_2", "Nintendo_Switch_2_in_Handheld_Mode.jpg"),
    # ================= 索尼 =================
    ("playstation-5",     "article", "PlayStation_5",
                          "Black_and_white_Playstation_5_base_edition_with_controller.png"),
    ("ps5",               "article", "PlayStation_5",
                          "Black_and_white_Playstation_5_base_edition_with_controller.png"),
    # PS5 Pro / Portal：维基无自由图，改用索尼官方产品图
    ("playstation-5-pro", "local",   "-",            "/tmp/official/ps5pro_crop.jpg"),
    ("playstation-portal", "local",  "-",            "/tmp/cand/ps-portal.jpg"),
    ("playstation-2",     "article", "PlayStation_2", "Sony-PlayStation-2-70001-Console-BR.jpg"),
    ("ps2",               "article", "PlayStation_2", "Sony-PlayStation-2-70001-Console-BR.jpg"),
    ("psp-go",            "article", "PlayStation_Portable", "PSP-Go-FL.jpg"),
    # ================= 微软 =================
    ("xbox-one",          "article", "Xbox_One", "Microsoft-Xbox-One-Console-Set-wKinect.jpg"),
    ("xbox-series-x",     "article", "Xbox_Series_X_and_Series_S", "Xbox_series_X_(50648118708).jpg"),
    # ================= 世嘉 =================
    ("sg1000",            "article", "Sega",          "Sega-SG-1000-Console-Set.jpg"),
    ("master-system",     "article", "Sega",          "Sega-Master-System-Set.jpg"),
    ("mega-drive",        "article", "Sega_Genesis",  "Sega-Mega-Drive-JP-Mk1-Console-Set.jpg"),
    ("saturn",            "article", "Sega_Saturn",   "Sega-Saturn-JP-Mk1-Console-Set.jpg"),
    ("game-gear",         "article", "Sega",          "Game-Gear-Handheld_(cropped).jpg"),
    ("dreamcast",         "article", "Sega",          "Dreamcast-Console-Set.png"),
    # ================= 雅达利 =================
    ("atari-2600",        "article", "Atari_2600",    "Atari-2600-Woody-FL.jpg"),
    ("atari-7800",        "article", "Atari_7800",    "Atari-7800-Console-Set.jpg"),
    # ================= 其他 =================
    ("neo-geo",           "article", "Neo_Geo",       "Neo-Geo-AES-Console-Set.jpg"),
    ("ngpc",              "direct",  "-",             "NeoGeo-Pocket-Color.jpg"),
    ("3do",               "article", "3DO",           "3DO-FZ1-Console-Set.png"),
    # ================= 厂商官网 / 设备库产品图（维基无自由图） =================
    ("ayaneo",            "local",   "-",            "/tmp/cand/ayaneo-2021.png"),
    ("gpd-win",           "local",   "-",            "/tmp/cand/gpdwin2016.png"),
    ("msi-claw",          "local",   "-",            "/tmp/cand/msi-claw-a1m.jpg"),
]

_ARTICLE_CACHE = {}


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


def article_images(article):
    if article in _ARTICLE_CACHE:
        return _ARTICLE_CACHE[article]
    html = fetch(f"{KIDDLE}/{article}").decode("utf-8", "ignore")
    out = []
    for m in re.finditer(r'src="(/images/thumb/[^"]+?/\d+px-([^"/]+))"', html):
        out.append((urllib.parse.unquote(m.group(2)), m.group(1)))
    _ARTICLE_CACHE[article] = out
    return out


def direct_thumb_path(fname):
    h = hashlib.md5(fname.encode()).hexdigest()
    q = urllib.parse.quote(fname)
    return f"/images/thumb/{h[0]}/{h[0:2]}/{q}/800px-{q}"


def candidate_urls(src_type, src_id, fname):
    """按优先级返回候选 URL：先大后小的缩略图，最后原图兜底。"""
    if src_type in ("url", "local"):
        return [fname]
    tp = None
    if src_type == "article":
        for fn, path in article_images(src_id):
            if fn == fname:
                tp = path
                break
        if tp is None:
            print(f"    ! 条目 {src_id} 中找不到 {fname}", file=sys.stderr)
            return []
    else:
        tp = direct_thumb_path(fname)

    urls = [KIDDLE + re.sub(r"/\d+px-", f"/{w}px-", tp) for w in THUMB_WIDTHS]
    m = re.match(r"^(/images)/thumb(/[0-9a-f]/[0-9a-f]{2}/[^/]+)/\d+px-[^/]+$", tp)
    if m:
        urls.append(KIDDLE + m.group(1) + m.group(2))
    return urls


def fetch_image(src_type, src_id, fname):
    """取图；优先返回宽度达标的版本，都不够时返回最大的那张。"""
    best = None
    if src_type == "local":
        try:
            im = Image.open(fname)
            im.load()
            return im.convert("RGB")
        except Exception as e:
            print(f"    ! 本地文件读取失败 {fname}: {e}", file=sys.stderr)
            return None

    for u in candidate_urls(src_type, src_id, fname):
        try:
            data = fetch(u)
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
        if len(data) < 3000:
            continue
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
        except Exception:
            continue
        im = im.convert("RGB")
        if im.width >= MIN_GOOD_WIDTH:
            return im
        if best is None or im.width > best.width:
            best = im
    return best


def stage(args):
    outdir = args.review_dir
    os.makedirs(outdir, exist_ok=True)
    print(f"下载 {len(MAP)} 张候选 -> {outdir}", flush=True)

    def work(item):
        target, st, sid, fname = item
        im = fetch_image(st, sid, fname)
        if im is None:
            return target, None, None
        im.thumbnail((900, 900))
        p = os.path.join(outdir, f"{target}.png")
        im.save(p)
        return target, p, im.size

    with ThreadPoolExecutor(max_workers=6) as ex:
        for target, p, size in ex.map(work, MAP):
            print(f"  {'OK ' if p else 'FAIL'} {target:<20} {size if size else ''}", flush=True)
    return 0


def sync_dimensions(updated):
    """把新图的真实像素尺寸同步到所有引用它的页面（图鉴页 + 各详情页）。

    卡片图和详情页头图共用同一个 webp，各自的 width/height 属性必须与文件一致，
    否则浏览器按错误的宽高比预留位置，首屏会跳动。
    """
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


def apply(args):
    updated = {}
    for target, st, sid, fname in MAP:
        im = fetch_image(st, sid, fname)
        if im is None:
            print(f"  ! {target}: 取图失败，跳过", file=sys.stderr)
            continue
        if im.width > MAX_WIDTH:
            im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
        out = os.path.join(STATIC_IMG, f"{target}.webp")
        im.save(out, "WEBP", quality=WEBP_QUALITY, method=6)
        updated[target] = im.size
        print(f"  {target:<20} {im.size[0]}x{im.size[1]}  {os.path.getsize(out) // 1024}KB")

    if not updated:
        print("没有任何图片被更新，中止", file=sys.stderr)
        return 1

    sync_dimensions(updated)
    print(f"\n完成：更新 {len(updated)} 张图")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="store_true", help="只下载候选供复核")
    ap.add_argument("--apply", action="store_true", help="落盘替换")
    ap.add_argument("--review-dir", default="/tmp/final")
    args = ap.parse_args()
    if args.apply:
        return apply(args)
    return stage(args)


if __name__ == "__main__":
    sys.exit(main())
