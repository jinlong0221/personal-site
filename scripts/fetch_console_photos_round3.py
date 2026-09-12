#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_console_photos_round3.py —— 第三轮：把仍属图库缩略图/偏暗的主机配图
换成 Wikimedia Commons 的官方产品图（经 Kiddle 镜像取，沙箱可达）。

背景：第一、二轮修掉了「文不对图」。质量扫描又发现一批图仍是 600x450 的
图库缩略图（偏小、偏暗），虽内容正确但达不到成品标准。

取图规则（Kiddle = kids.kiddle.co，MediaWiki 图文镜像）：
  /images/<h1>/<h2>/<FileName>          原图（全分辨率，大，慢）
  /images/thumb/<h1>/<h2>/<FileName>/<W>px-<FileName>   缩略图
其中 <h1>/<h2> = md5(FileName) 前 1 / 前 2 位；W 必须用 MediaWiki 标准档位。

用法：
  --stage   只下载候选到 /tmp/round3 供复核
"""
import argparse
import hashlib
import io
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

ImageFile_LOAD_TRUNCATED = getattr(Image, "LOAD_TRUNCATED_IMAGES", None)

BASE = "https://kids.kiddle.co"
OUT = "/tmp/round3"
THUMB_WIDTHS = (1280, 1024, 800, 640, 500)
MIN_GOOD_WIDTH = 800
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}

# 目标名 -> 候选 Commons 文件名（按优先级）
CAND = {
    "playstation-4": ["PlayStation-4-Console-FL.jpg", "PS4-Console-wDS4.jpg",
                      "Sony-PlayStation-4-Console-FL.jpg"],
    "ps4": ["PlayStation-4-Console-FL.jpg", "PS4-Console-wDS4.jpg"],
    "gamecube": ["GameCube-Console-Set.png", "Nintendo-GameCube-Console-Set.png",
                 "GameCube-Set.jpg"],
    "gc": ["GameCube-Console-Set.png", "Nintendo-GameCube-Console-Set.png"],
    "xbox": ["Xbox-Console-Set.jpg", "Microsoft-Xbox-Console-Set.jpg",
             "Xbox-console.jpg"],
    "wii-u": ["Wii-U-Console-Set.png", "Nintendo-Wii-U-Console-Set.png",
              "Wii-U-Console-FL.jpg"],
    "wiiu": ["Wii-U-Console-Set.png", "Nintendo-Wii-U-Console-Set.png"],
    "wii": ["Wii-Console-Set.png", "Nintendo-Wii-Console-Set.png", "Wii-Console-FL.jpg"],
    "atari-5200": ["Atari-5200-4-Port-Console-Set.jpg", "Atari-5200-Console-Set.jpg"],
    "atari-lynx": ["Atari-Lynx-I-Handheld.jpg", "Atari-Lynx-II-Handheld.jpg",
                   "Atari-Lynx.jpg"],
    "game-watch": ["Game and watch ball.jpg", "Nintendo-Game-and-Watch-Ball.jpg",
                   "Game-and-Watch-Ball.jpg"],
    "xbox-series-s": ["Xbox Series S (50648118705).jpg", "Xbox-Series-S-Console.jpg"],
    "xbox360": ["Xbox-360-Console-with-Wireless-Controller.png",
                "Xbox-360-S-Console-Set.jpg", "Xbox-360-Console-Set.jpg"],
    "playstation-3": ["PS3-Console-and-Controller.jpg", "Sony-PlayStation-3-Console-FL.jpg",
                      "PlayStation-3-Console-Set.jpg"],
    "ps3": ["PS3-Console-and-Controller.jpg", "Sony-PlayStation-3-Console-FL.jpg"],
    "n64": ["Nintendo-64-wController-L.jpg", "Nintendo-64-Console-Set.jpg"],
    "nintendo-64": ["Nintendo-64-wController-L.jpg", "Nintendo-64-Console-Set.jpg"],
    "ngage": ["Nokia N-Gage.jpg", "Nokia-N-Gage-QD.jpg", "N-Gage.jpg"],
    "legion-go": ["Lenovo Legion Go.jpg", "Lenovo-Legion-Go.jpg"],
    "rog-ally": ["Asus ROG Ally.jpg", "Asus-ROG-Ally.jpg", "ROG-Ally.jpg"],
    "xiaobawang": ["Subor-Console.jpg", "Xiao Ba Wang.jpg"],
}


def hashed(fname):
    h = hashlib.md5(fname.encode("utf-8")).hexdigest()
    return h[0], h[:2]


def thumb_url(fname, w):
    a, b = hashed(fname)
    return f"{BASE}/images/thumb/{a}/{b}/{urllib.parse.quote(fname)}/{w}px-{urllib.parse.quote(fname)}"


def orig_url(fname):
    a, b = hashed(fname)
    return f"{BASE}/images/{a}/{b}/{urllib.parse.quote(fname)}"


def try_get(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if len(data) < 3000:
            return None
        return data
    except Exception:
        return None


def load(data):
    if ImageFile_LOAD_TRUNCATED:
        Image.LOAD_TRUNCATED_IMAGES = True
    im = Image.open(io.BytesIO(data))
    im.load()
    return im.convert("RGB")


def fetch_one(item):
    target, names = item
    best = None
    best_src = None
    for fname in names:
        for w in THUMB_WIDTHS:
            d = try_get(thumb_url(fname, w))
            if not d:
                continue
            try:
                im = load(d)
            except Exception:
                continue
            if im.width >= MIN_GOOD_WIDTH:
                return target, im, f"{fname}@{w}px"
            if best is None or im.width > best.width:
                best, best_src = im, f"{fname}@{w}px"
            break
        if best is None or best.width < 1000:
            d = try_get(orig_url(fname), timeout=90)
            if d:
                try:
                    im = load(d)
                    if best is None or im.width > best.width:
                        best, best_src = im, f"{fname}@orig"
                except Exception:
                    pass
        if best is not None and best.width >= MIN_GOOD_WIDTH:
            break
    return target, best, best_src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    items = [(k, v) for k, v in CAND.items()]
    if args.only:
        keep = set(args.only.split(","))
        items = [i for i in items if i[0] in keep]

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        for target, im, src in ex.map(fetch_one, items):
            if im is None:
                fail += 1
                print(f"  FAIL {target}", flush=True)
                continue
            if im.width > 1400:
                im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
            im.save(os.path.join(OUT, f"{target}.png"))
            ok += 1
            print(f"  OK   {target:<16} {im.size[0]}x{im.size[1]:<5} <- {src}", flush=True)
    print(f"\n成功 {ok} / 失败 {fail}  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
