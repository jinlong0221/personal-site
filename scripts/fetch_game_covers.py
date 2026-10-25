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
  python3 scripts/fetch_game_covers.py --steam-only   # 仅按内置 appid 表抓 Steam 真图（沙箱/离线用，跳过其余）
  # 说明：内置 STEAM_APPID 表覆盖已确认上 Steam 的游戏，沙箱里商店搜索接口被墙、
  #       但图床可直连，故 --steam-only 即可拉到这批真图；其余未发售/主机独占游戏
  #       需在本机（有网络+IGDB 密钥）不加 --steam-only 跑，用 IGDB 兜底。

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

# —— 已知 Steam appid 对照（沙箱里 Steam 商店搜索接口被墙，但图片 CDN 可直连，
#    故内置这份表让脚本在任意环境都能按 appid 直接拉真封面）。优先放 appid 稳定、
#    知名度高的老游戏；拿不准的一律不写，回退到 storesearch/IGDB（需本机网络/密钥）。 ——
STEAM_APPID = {
    # 史低价（22 个全在 Steam，appid 稳定）
    "witcher-3": 292030, "stardew-valley": 413150, "gta5": 271590,
    "cyberpunk-2077": 1091500, "elden-ring": 1245620, "rdr2": 1174180,
    "hades": 1145360, "hollow-knight": 367520, "celeste": 504230,
    "dead-cells": 588650, "portal-2": 620, "dark-souls-3": 374320,
    "sekiro": 814380, "doom-eternal": 782330, "horizon-zero-dawn": 1151640,
    "god-of-war-pc": 1593500, "mh-world": 582010, "mh-rise": 1446780,
    "no-mans-sky": 275850, "disco-elysium": 632470, "re-village": 1196590,
    "baldurs-gate-3": 1086940,
    # 发售日历里已确认上 Steam 的知名作
    "senua-hellblade-sequel": 1558590,
    # —— 以下为「会上 Steam 的未发售/已公布」游戏，appid 经 SteamDB 逐一核对（2026-10-25）——
    "marvel-tokon-fighting-souls": 3787240,
    "mgs-master-collection-2": 3859630,
    "star-wars-zero-company": 2075800,
    "resonance-plague-tale-legacy": 2713000,
    "lego-batman-dark-knight": 2215200,
    "control-resonant": 3669870,
    "ace-combat-8": 2288340,
    "gears-of-war-eday": 3010850,
    "castlevania-belmonts-curse": 4231820,
    "dq-monsters-withered": 3681610,
    "stranger-than-heaven": 4260840,
    "metro-2039": 2590240,
    "tomb-raider-atlantis": 3558670,
    "persona-4-revival": 2963950,
    "fable": 2769570,          # Steam 2027 重启版即名为 Fable（存疑，取不到则留占位）
    "ff7-revelation": 4354570,
    "spyro-realm-beyond": 4245560,
    "re-veronica": 4824610,
    "state-of-decay-3": 1340720,
    # 已查但放弃：cod-modern-warfare-4（基础 appid 实为 2019 MW 父程序，不对版）、
    #   exodus（SteamDB 无明确基础程序）、5 个任天堂独占（绝不上 Steam）。
}
# 这些 slug 已是真实封面（PS5 独占/未上 Steam），无需再抓，直接跳过
ALREADY_REAL = {
    "blood-of-dawnwalker", "marvels-wolverine", "silent-hill-townfall",
    "phantom-blade-zero", "god-of-war-laufey", "gta6",
}

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
    """优先竖版 library 图，回退 header。返回 (bytes, is_portrait)。
    注意：Steam CDN 对缺失资源会返回 200 + 1x1 透明桩图，必须按尺寸剔除，
    否则会存下垃圾图；竖版图要求短边>=400，header 横版图只要求>=100。"""
    for url, portrait, minside in [
        ("https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/%d/library_600x900_2x.jpg" % appid, True, 400),
        ("https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/%d/library_600x900.jpg" % appid, True, 400),
        ("https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/%d/header.jpg" % appid, False, 100),
    ]:
        try:
            data = fetch_bytes(url)
            im = Image.open(__import__("io").BytesIO(data))
            if min(im.size) < minside:
                continue  # CDN 桩图，跳过
            return data, portrait
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
        return None, False
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
    """raw=图片字节；转 webp + 生成 480w/768w 缩略图。
    横版 header（portrait=False）垫成 2:3 竖版海报（深底居中），避免卡片硬裁糊图。"""
    if Image is None:
        return False
    try:
        im = Image.open(__import__("io").BytesIO(raw)).convert("RGB")
    except Exception:
        return False
    if not portrait:
        TW, TH = 600, 900
        canvas = Image.new("RGB", (TW, TH), (18, 18, 20))
        scale = min(TW / im.width, TH / im.height)
        nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
        im = im.resize((nw, nh), Image.LANCZOS)
        canvas.paste(im, ((TW - nw) // 2, (TH - nh) // 2))
        im = canvas
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
    steam_only = "--steam-only" in sys.argv
    os.makedirs(IMG_DIR, exist_ok=True)
    done = load_done()
    token = igdb_token()

    ok = skip = fail = 0
    fails = []
    for name, slug, zh, en, meta in GAMES:
        search = (en.strip() if en and en.strip() and en.strip() != zh.strip() else zh.strip())
        if slug in ALREADY_REAL:
            skip += 1
            print("· %s 已有真实封面（跳过）" % slug)
            continue
        if steam_only and slug not in STEAM_APPID:
            skip += 1
            print("· %s 无内置 appid（--steam-only 跳过，待本机 IGDB 补）" % slug)
            continue
        if (not force) and slug in done:
            skip += 1
            continue
        if dry:
            via = "STEAM_APPID" if slug in STEAM_APPID else "搜索/IGDB"
            print("[dry] 将抓取 %s (%s，来源=%s)" % (slug, search, via))
            continue
        # 优先：内置 appid 直连 Steam 图床（沙箱里商店搜索被墙，但图床可直连）
        appid = STEAM_APPID.get(slug)
        src = "steam(appid表)" if appid else None
        print("· %s <- %s" % (slug, ("appid=%d" % appid) if appid else "搜索「%s」" % search))
        raw, portrait = None, False
        if appid:
            raw, portrait = steam_cover(appid)
            if raw is None and steam_only:
                # 仅 Steam appid 模式：取不到就保留占位，不再撞被墙的搜索/IGDB
                fail += 1
                fails.append(slug)
                print("    ✗ 该 appid 在图床无竖版/横版图（保留占位）")
                continue
        if raw is None:
            a2 = search_steam(search)  # 沙箱多半失败，回退 IGDB
            if a2:
                appid = a2
                raw, portrait = steam_cover(appid)
                src = "steam"
        if raw is None:
            raw, portrait = search_igdb(token, search)
            if raw:
                src = "igdb"
        if raw and save_cover(slug, raw, portrait):
            done[slug] = {"src": src or "?", "portrait": portrait}
            ok += 1
            print("    ✓ 已存真实封面（%s）" % (src or "?"))
        else:
            fail += 1
            fails.append(slug)
            print("    ✗ 未获取到（保留占位图）")
        time.sleep(0.3)  # 礼貌限速

    json.dump(done, open(DONE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n真实封面抓取：成功 %d / 跳过(已存在) %d / 失败(保留占位) %d" % (ok, skip, fail))
    if fails:
        print("未能获取（多为未发售或商店无图，可稍后重跑或手动补）：")
        print("  " + "  ".join(fails))


if __name__ == "__main__":
    main()
