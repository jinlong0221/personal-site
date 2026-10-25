#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_game_covers.py — 为「游戏发售日历」批量抓取【真实游戏封面】并自托管。

为什么需要本脚本：
  游戏封面都是厂商版权图，不能让 AI 生成、也不能从新闻站盗图。稳妥做法是
  从官方商店（Steam）/ 游戏资料库（IGDB）把封面拉下来，自己托管在
  static/img/games/<slug>-cover.webp（站点 CSP 要求图片必须同源 self-host）。

用法（在本机、有正常网络的终端里跑；沙箱/CI 网络多半连不上 Steam API）：
  python3 scripts/fetch_game_covers.py            # 抓取缺失的真实封面
  python3 scripts/fetch_game_covers.py --force    # 强制重新抓取（覆盖占位图）
  python3 scripts/fetch_game_covers.py --dry-run  # 只报告会抓哪些、跳过哪些

数据源优先级（每个游戏依次尝试，命中即存）：
  1) Steam 商店搜索 -> appid -> library_600x900（竖版官方图，最像封面）
       缺失则回退 header.jpg（横版，会被裁成海报比例）
  2) IGDB（需环境变量 TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET，免费申请）：
       覆盖 Steam 没有的游戏（任天堂/PS 独占、未上 Steam 的）
获取到的图统一转 webp 并存到 static/img/games/，同时生成 480w/768w 两档缩略图
（与全站响应式图管线一致）。脚本幂等：已抓过的（记录在 .game_cover_done.json）
默认跳过。

注意：未发售（2026-2027 待定）的游戏可能还没有官方封面，会保留占位图，属正常。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import ssl

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "static", "img", "games")
DONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".game_cover_done.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# 引入游戏清单（slug -> 中/英/信息），搜索用英文名优先
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_game_calendar_covers import GAMES  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch_bytes(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://store.steampowered.com/"})
    return urllib.request.urlopen(req, timeout=timeout, context=CTX).read()


def search_steam(name):
    """返回 appid 或 None。"""
    u = "https://store.steampowered.com/api/storesearch/?term=%s&cc=us&l=en" % urllib.parse.quote(name)
    try:
        data = json.loads(fetch_bytes(u))
        items = data.get("items") or []
        if items:
            return int(items[0]["id"])
    except Exception as e:
        print("    ! Steam 搜索失败 %s: %s" % (name, str(e)[:80]))
    return None


def steam_cover(appid):
    """优先竖版 library 图，回退 header。返回 (bytes, is_portrait)。"""
    for url, portrait in [
        ("https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/%d/library_600x900_2x.jpg" % appid, True),
        ("https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/%d/library_600x900.jpg" % appid, True),
        ("https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/%d/header.jpg" % appid, False),
    ]:
        try:
            return fetch_bytes(url), portrait
        except Exception:
            continue
    return None, False


def igdb_token():
    cid = os.environ.get("TWITCH_CLIENT_ID")
    secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not (cid and secret):
        return None
    try:
        import base64
        basic = base64.b64encode(("%s:%s" % (cid, secret)).encode()).decode()
        req = urllib.request.Request(
            "https://id.twitch.tv/oauth2/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"},
        )
        return json.loads(urllib.request.urlopen(req, timeout=20, context=CTX).read())["access_token"]
    except Exception as e:
        print("    ! IGDB 取 token 失败: %s" % str(e)[:80])
        return None


def search_igdb(token, name):
    if not token:
        return None
    cid = os.environ["TWITCH_CLIENT_ID"]
    body = 'search "%s"; fields cover.image_id; limit 1;' % name.replace('"', '\\"')
    try:
        req = urllib.request.Request(
            "https://api.igdb.com/v4/games",
            data=body.encode(),
            headers={"Client-ID": cid, "Authorization": "Bearer " + token, "Content-Type": "text/plain"},
        )
        data = json.loads(urllib.request.urlopen(req, timeout=20, context=CTX).read())
        cov = (data[0].get("cover") or {}).get("image_id") if data else None
        if cov:
            # 竖版 box art（cover_big 约 264x374，够用；再上采样到 480/768）
            return fetch_bytes("https://images.igdb.com/igdb/image/upload/t_cover_big/%s.jpg" % cov), True
    except Exception as e:
        print("    ! IGDB 搜索失败 %s: %s" % (name, str(e)[:80]))
    return None, False


def save_cover(slug, raw, portrait):
    """raw=图片字节；转 webp + 生成 480w/768w 缩略图。"""
    if Image is None:
        return False
    try:
        im = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
    except Exception:
        return False
    base = os.path.join(IMG_DIR, "%s-cover" % slug)
    im.save(base + ".webp", "WEBP", quality=88)
    for tw in (480, 768):
        if im.width >= tw:
            th = max(1, int(im.height * tw / im.width))
        else:
            th = im.height
        t = im.resize((tw, th), Image.LANCZOS)
        t.save(base + "@%dw.webp" % tw, "WEBP", quality=85)
    return True


def load_done():
    if os.path.exists(DONE):
        try:
            return json.load(open(DONE, encoding="utf-8"))
        except Exception:
            pass
    return {}


def main():
    force = "--force" in sys.argv
    dry = "--dry-run" in sys.argv
    os.makedirs(IMG_DIR, exist_ok=True)
    done = load_done()
    token = igdb_token()

    ok = skip = fail = 0
    fails = []
    for name, slug, zh, en, meta in GAMES:
        search = (en.strip() if en and en.strip() and en.strip() != zh.strip() else zh.strip())
        if (not force) and slug in done:
            skip += 1
            continue
        if dry:
            print("[dry] 将抓取 %s (%s)" % (slug, search))
            continue
        print("· %s <- 搜索「%s」" % (slug, search))
        raw, portrait = None, False
        appid = search_steam(search)
        if appid:
            raw, portrait = steam_cover(appid)
        if raw is None:
            raw, portrait = search_igdb(token, search)
        if raw and save_cover(slug, raw, portrait):
            done[slug] = {"src": "steam" if appid else "igdb", "portrait": portrait}
            ok += 1
            print("    ✓ 已存真实封面")
        else:
            fail += 1
            fails.append(slug)
            print("    ✗ 未获取到（保留占位图）")
        time.sleep(0.4)  # 礼貌限速

    json.dump(done, open(DONE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n真实封面抓取：成功 %d / 跳过(已存在) %d / 失败(保留占位) %d" % (ok, skip, fail))
    if fails:
        print("未能获取（多为未发售或商店无图，可稍后重跑或手动补）：")
        print("  " + "  ".join(fails))


if __name__ == "__main__":
    main()
