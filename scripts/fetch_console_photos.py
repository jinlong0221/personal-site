#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_console_photos.py — 从 Wikimedia Commons 批量抓取「主机图鉴」各机型的真实产品照。

为什么要在你本机（Mac）跑，而不是在代码助手沙箱里跑：
  代码助手的工作沙箱被防火墙挡住了 upload.wikimedia.org（Wikimedia 图床），
  只有你自己的 Mac 能正常访问。所以这台脚本放在本地执行，抓回真实图写进仓库。

用法（在仓库根目录 longxiong.vip/hugo-site 下执行）：
  pip3 install --user Pillow        # 只需第一次
  python3 scripts/fetch_console_photos.py

做了什么：
  1. 先把 static/img/consoles/* 备份到 static/img/consoles/_backup/
  2. 对每张卡片，用 Wikimedia Commons API 搜「机型名 console」
  3. 过滤掉 logo / 图标 / 矢量图，取第一张真实照片
  4. 下载并转成 webp（质量 82），写回 static/img/consoles/<file>.webp
  5. 同步更新 static/console.html 里对应 <img> 的 width / height
  6. 打印抓取报告（成功 / 失败）
  7. 别名文件（ds / nds / nintendo-ds 等字节相同的副本）只抓一次再复制

跑完后在仓库里：
  git add static/img/consoles static/console.html
  git commit -m "🎮 主机图鉴配图替换为 Wikimedia Commons 真实产品照"
  git push origin main
（或直接把结果发我，我来提交）

注意：脚本无法替你“看”图，抓回的是 Commons 搜索第一名（已排除 logo/图标）。
      跑完后请你扫一眼确认都是真机照；不对的机型可单独重跑或手动换。
"""
import os, re, sys, json, shutil, time, urllib.parse, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLES_DIR = os.path.join(REPO, "static", "img", "consoles")
HTML = os.path.join(REPO, "static", "console.html")

# 规范文件名(无扩展) -> Commons 搜索词
CANON = {
    "switch-2": "Nintendo Switch 2 console",
    "msi-claw": "MSI Claw handheld",
    "playstation-5-pro": "PlayStation 5 Pro console",
    "playstation-portal": "PlayStation Portal",
    "legion-go": "Lenovo Legion Go",
    "rog-ally": "Asus ROG Ally",
    "steam-deck": "Steam Deck",
    "ayaneo": "AYANEO",
    "playstation-5": "PlayStation 5 console",
    "xbox-series-s": "Xbox Series S",
    "xbox-series-x": "Xbox Series X",
    "switch-lite": "Nintendo Switch Lite",
    "new-2ds-xl": "New Nintendo 2DS XL",
    "switch": "Nintendo Switch console",
    "gpd-win": "GPD Win",
    "new-3ds": "New Nintendo 3DS",
    "2ds": "Nintendo 2DS",
    "playstation-4": "PlayStation 4 console",
    "xbox-one": "Xbox One console",
    "3ds-xl": "Nintendo 3DS XL",
    "wii-u": "Wii U console",
    "nintendo-3ds": "Nintendo 3DS",
    "ps-vita": "PlayStation Vita",
    "psp-go": "PSP Go",
    "dsi": "Nintendo DSi",
    "ds-lite": "Nintendo DS Lite",
    "playstation-3": "PlayStation 3 console",
    "wii": "Nintendo Wii console",
    "gb-micro": "Game Boy micro",
    "xbox360": "Xbox 360 console",
    "nintendo-ds": "Nintendo DS console",
    "psp": "PlayStation Portable",
    "gba-sp": "Game Boy Advance SP",
    "ngage": "Nokia N-Gage",
    "gameboy-advance": "Game Boy Advance",
    "gamecube": "Nintendo GameCube",
    "xbox": "Original Xbox console",
    "playstation-2": "PlayStation 2 console",
    "wonderswan": "Bandai WonderSwan",
    "ngpc": "Neo Geo Pocket Color",
    "gameboy-color": "Game Boy Color",
    "gb-light": "Game Boy Light",
    "dreamcast": "Sega Dreamcast",
    "gameboy-pocket": "Game Boy Pocket",
    "nintendo-64": "Nintendo 64 console",
    "sega-nomad": "Sega Nomad",
    "playstation": "Sony PlayStation console",
    "saturn": "Sega Saturn console",
    "3do": "3DO Interactive Multiplayer",
    "neo-geo": "Neo Geo AES console",
    "sfc": "Super Famicom",
    "game-gear": "Sega Game Gear",
    "turboexpress": "TurboExpress",
    "atari-lynx": "Atari Lynx",
    "gameboy": "Game Boy",
    "atari-7800": "Atari 7800",
    "mega-drive": "Sega Mega Drive",
    "xiaobawang": "Subor game console",
    "master-system": "Sega Master System",
    "fc": "Family Computer Nintendo",
    "sg1000": "Sega SG-1000",
    "atari-5200": "Atari 5200",
    "game-watch": "Game and Watch",
    "atari-2600": "Atari 2600",
}

# 别名文件 -> 规范文件（字节相同的副本，只需抓一次再复制）
ALIAS = {
    "nds": "nintendo-ds", "ds": "nintendo-ds",
    "gba": "gameboy-advance",
    "ps1": "playstation", "ps": "playstation",
    "gc": "gamecube",
    "wiiu": "wii-u",
    "super-famicom": "sfc",
    "ps2": "playstation-2",
    "ps3": "playstation-3",
    "ps4": "playstation-4",
    "ps5": "playstation-5",
    "3ds": "nintendo-3ds",
    "n64": "nintendo-64",
    "vita": "ps-vita",
}

UA = {"User-Agent": "longxiong-console-photo-fetch/1.0 (contact: longxiong.vip)"}


def api_search(query):
    params = {
        "action": "query", "generator": "search", "gsrsearch": query,
        "gsrnamespace": 6, "gsrlimit": 20, "prop": "imageinfo",
        "iiprop": "url|mime|size", "iiurlwidth": 800, "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    pages = (data.get("query") or {}).get("pages", {})
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        title = p.get("title", "")
        mime = ii.get("mime", "")
        if not mime.startswith("image") or mime.endswith("svg"):
            continue
        low = title.lower()
        if any(k in low for k in ["logo", "icon", "vector", ".svg"]):
            continue
        out.append((title, ii.get("thumburl") or ii.get("url")))
    return out


def convert_to_webp(src_path, dst_path, width=800):
    from PIL import Image
    im = Image.open(src_path).convert("RGB")
    w, h = im.size
    tw, th = width, int(h * width / w)
    im.resize((tw, th), Image.LANCZOS).save(dst_path, "WEBP", quality=82, method=4)
    return tw, th


def main():
    try:
        from PIL import Image  # noqa
    except ImportError:
        sys.exit("需要先安装 Pillow：\n  pip3 install --user Pillow")

    backup = os.path.join(CONSOLES_DIR, "_backup")
    os.makedirs(backup, exist_ok=True)
    for f in os.listdir(CONSOLES_DIR):
        if f.endswith(".webp"):
            shutil.copy2(os.path.join(CONSOLES_DIR, f), os.path.join(backup, f))

    html = open(HTML, encoding="utf-8").read()
    report = {"ok": [], "fail": []}
    fetched = {}

    for canon, query in CANON.items():
        dest = os.path.join(CONSOLES_DIR, canon + ".webp")
        try:
            results = api_search(query)
        except Exception as e:
            report["fail"].append((canon, query, "search error: %s" % e))
            continue
        if not results:
            report["fail"].append((canon, query, "no image result"))
            continue
        title, url = results[0]
        try:
            tmp = os.path.join(backup, canon + "_dl.jpg")
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                open(tmp, "wb").write(r.read())
            w, h = convert_to_webp(tmp, dest)
            fetched[canon] = (w, h)
            report["ok"].append((canon, title))
        except Exception as e:
            report["fail"].append((canon, query, "download error: %s" % e))
        time.sleep(0.4)

    for alias, canon in ALIAS.items():
        if canon in fetched:
            shutil.copy2(os.path.join(CONSOLES_DIR, canon + ".webp"),
                         os.path.join(CONSOLES_DIR, alias + ".webp"))
            fetched[alias] = fetched[canon]

    for name, (w, h) in fetched.items():
        pat = re.compile(
            r'(<img\s+width=")\d+("\s+height=")\d+('
            r'\s+src="img/consoles/%s.webp")' % re.escape(name))
        html, n = pat.subn(r'\g<1>%d\g<2>%d\g<3>' % (w, h), html)
        if n == 0:
            print("  [warn] 未在 console.html 找到 %s 的 <img>，跳过尺寸更新" % name)

    open(HTML, "w", encoding="utf-8").write(html)

    print("\n===== 抓取成功 (%d) =====" % len(report["ok"]))
    for c, t in report["ok"]:
        print("  %-22s <- %s" % (c, t))
    print("\n===== 未抓到 (%d) =====" % len(report["fail"]))
    for c, q, e in report["fail"]:
        print("  %-22s [%s] %s" % (c, q, e))
    print("\n备份在 static/img/consoles/_backup/ 。确认无误后提交：")
    print("  git add static/img/consoles static/console.html")
    print('  git commit -m "🎮 主机图鉴配图替换为 Wikimedia Commons 真实产品照"')
    print("  git push origin main")


if __name__ == "__main__":
    main()
