#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harvest_kiddle_images.py — 从 Kiddle（kids.kiddle.co，维基图文镜像）批量采集条目配图

背景：longxiong.vip 主机图鉴板块曾用 Pexels 关键词搜索补图，因无法看图导致
「文不对图」（如 Game Boy Advance 卡片配了 New 3DS 的图）。现改用 Kiddle 采集
维基百科的官方产品图（CC 授权、型号准确），下载后视觉复核再定稿。

要点：
  * 图片走 /images/thumb/<h1>/<h2>/<Name>/<W>px-<Name> 缩略路径，宽度只接受
    MediaWiki 的标准档位（800/1024/1280…），其它宽度会 404；原图路径为
    /images/<h1>/<h2>/<Name>，体积可达数 MB，故默认优先缩略图。
  * 并发下载，避免单线程被大文件拖住。

用法：
  python3 scripts/harvest_kiddle_images.py --out /tmp/harvest
  python3 scripts/harvest_kiddle_images.py --articles Sega_Saturn Nintendo_3DS --out /tmp/harvest
"""
import argparse
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BASE = "https://kids.kiddle.co"

DEFAULT_ARTICLES = [
    "Atari_7800", "Game_Boy_Advance", "Game_Boy_line", "Nintendo_2DS",
    "Sega_Genesis", "PlayStation_2", "Atari_2600", "Xbox_One",
    "PlayStation_5", "Sega_Saturn", "Nintendo_3DS", "Nintendo_DSi",
    "Nintendo_DS", "Nintendo_Switch", "Nintendo_Switch_2",
    "Xbox_Series_X_and_Series_S", "Neo_Geo", "3DO",
    "PlayStation_Portable", "Sega",
]

SKIP_PAT = re.compile(
    r"(kids-robot|kids_search|icon-kiddle|favicon|Commons-logo|"
    r"Question_book|Ambox|Edit-clear|Padlock|Symbol_|Flag_of|Logo|"
    r"Wikiquote|Wikisource|Wiktionary|Wikipedia-logo)",
    re.I,
)

# MediaWiki 标准缩略档位，从大到小试
THUMB_WIDTHS = (1600, 1280, 1024, 800, 640, 500, 400, 320, 240, 200, 120)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read()


def article_images(article):
    """返回 [(filename, thumb_path)]。"""
    html = fetch(f"{BASE}/{article}").decode("utf-8", "ignore")
    out, seen = [], set()
    for m in re.finditer(r'src="(/images/thumb/[^"]+?/\d+px-([^"/]+))"', html):
        thumb_path, fname = m.group(1), m.group(2)
        if SKIP_PAT.search(fname) or fname in seen:
            continue
        seen.add(fname)
        out.append((fname, thumb_path))
    return out


def original_url(thumb_path):
    """从缩略路径还原原图：/images/thumb/9/95/Name.jpg/120px-Name.jpg -> /images/9/95/Name.jpg"""
    m = re.match(r"^(/images)/thumb(/[0-9a-f]/[0-9a-f]{2}/[^/]+)/\d+px-[^/]+$", thumb_path)
    return (BASE + m.group(1) + m.group(2)) if m else None


def thumb_url(thumb_path, w):
    return BASE + re.sub(r"/\d+px-", f"/{w}px-", thumb_path)


def fetch_first(urls, min_bytes=4000):
    for u in urls:
        try:
            data = fetch(u)
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
        if len(data) >= min_bytes:
            return data, u
    return None, None


def safe_name(fname):
    base, ext = os.path.splitext(fname)
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:60] + (ext.lower() or ".jpg")


def download_one(item, outdir, allow_original=False):
    idx, fname, thumb_path = item
    urls = [thumb_url(thumb_path, w) for w in THUMB_WIDTHS]
    if allow_original:
        o = original_url(thumb_path)
        if o:
            urls.append(o)
    data, used = fetch_first(urls)
    if not data:
        return None
    path = os.path.join(outdir, f"{idx:02d}_{safe_name(fname)}")
    with open(path, "wb") as f:
        f.write(data)
    return path, len(data), used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--articles", nargs="*", default=DEFAULT_ARTICLES)
    ap.add_argument("--out", default="/tmp/harvest")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--allow-original", action="store_true",
                    help="缩略图全失败时回退下载原图（体积大、慢）")
    args = ap.parse_args()

    total = 0
    for art in args.articles:
        try:
            imgs = article_images(art)
        except Exception as e:
            print(f"  ! {art}: 页面抓取失败 {e}", flush=True)
            continue
        if not imgs:
            print(f"  ! {art}: 无配图", flush=True)
            continue
        outdir = os.path.join(args.out, art)
        os.makedirs(outdir, exist_ok=True)
        print(f"[{art}] {len(imgs)} 张候选", flush=True)
        items = [(i, fn, tp) for i, (fn, tp) in enumerate(imgs, 1)]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(download_one, it, outdir, args.allow_original): it for it in items}
            for fu in as_completed(futs):
                try:
                    r = fu.result()
                except Exception:
                    continue
                if r:
                    p, size, used = r
                    w = re.search(r"/(\d+)px-", used)
                    tag = f"{w.group(1)}px" if w else "orig"
                    print(f"    {os.path.basename(p):<60} {tag:<6} {size // 1024}KB", flush=True)
                    total += 1
    print(f"\n共下载 {total} 张 -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
