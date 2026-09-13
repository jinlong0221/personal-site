#!/usr/bin/env python3
"""Download Tesla images from qqpublic CDN and create card thumbnails."""

import os
import sys
import urllib.request
import urllib.error
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

BASE = "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/img/tesla"
os.makedirs(BASE, exist_ok=True)

# All image URLs organized by product
IMAGES = {
    "model3": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-2383914182-9CAD82B66DA8E66A2FA412D06FD8C809/0?fmt=jpg&size=533&h=1050&w=1400&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3420296956-4BDAD1227A39B631F37CD60C965B503C/0?fmt=jpg&size=550&h=1050&w=1400&ppv=1", "side.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-1571410180-585F00B9C9092498A487FCFE174C4D5F/0?fmt=jpg&size=477&h=1050&w=1400&ppv=1", "rear.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-2600717107-E1A342B6E5DA898FF49F54AA0CAD4EE9/0?fmt=jpg&size=190&h=1050&w=1400&ppv=1", "interior.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-2566172228-56284B8D7000DA758F66EBDE1A44312D/0?fmt=jpg&size=296&h=1280&w=1707&ppv=1", "performance.jpg"),
    ],
    "modely": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-1075477979-5ED15E288F1F3D0804D85218B15BE68A/0?fmt=jpg&size=301&h=828&w=1328&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3891451236-B0AAD1CC614A33551F7B0F53FC991EE7/0?fmt=jpg&size=390&h=844&w=1326&ppv=1", "side.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-1768461657-CF31880EFE8053198D97EEDE723C27D6/0?fmt=jpg&size=224&h=832&w=1330&ppv=1", "rear.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3629372296-2DE925B3CB2179E9FB08A3F16589DFA4/0?fmt=jpg&size=149&h=842&w=1332&ppv=1", "interior.jpg"),
    ],
    "modely-l": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-821791116-7BCBBADEC8AEB70758AFD8895F0286B2/0?fmt=jpg&size=124&h=1495&w=690&ppv=1", "exterior.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-2891633841-92811A9ABB657484B15ED54119316751/0?fmt=png&size=224&h=643&w=628&ppv=1", "interior.jpg"),
    ],
    "cybertruck": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-1752240085-EA6427FF4C8893270B62024907787A22/0?fmt=png&size=344&h=448&w=600&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3419433259-C05B24E92F06F098C393D6A02128A86F/0?fmt=png&size=313&h=445&w=600&ppv=1", "side.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3812210428-8A08226E8167BEFE773CFFD9436068DD/0?fmt=png&size=416&h=1066&w=600&ppv=1", "side2.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-950685113-61E40033940271A937EA5152B679E296/0?fmt=png&size=383&h=447&w=600&ppv=1", "rear.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-948560620-1D999409F847DB8D8C2FC6D210CE4C80/0?fmt=png&size=351&h=448&w=600&ppv=1", "rear2.jpg"),
    ],
    "roadster": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-2062226409-C4D49E7FC29397E623AA379BA02F1B9A/0?fmt=jpg&size=380&h=1194&w=1565&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3592635264-C557283786787494860235C231FC5968/0?fmt=jpg&size=361&h=1188&w=1560&ppv=1", "side.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3682055908-017AB243FF028D2F9CACF70F6B5747F1/0?fmt=jpg&size=373&h=1138&w=1554&ppv=1", "side2.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3597039638-D7F28FA8D970BEDE1B1C0D53A1B517AB/0?fmt=jpg&size=484&h=1141&w=1558&ppv=1", "rear.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-300533910-168ED4F2B920BFFD16FF7B55AB9946B4/0?fmt=jpg&size=587&h=1043&w=1573&ppv=1", "interior.jpg"),
    ],
    "semi": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-549863202-575E641BF8D94BE472E62235BAC7959B/0?fmt=jpg&size=37&h=600&w=560&ppv=1", "front.jpg"),
    ],
    "cybercab": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-1295346826-2A66D4263F3E8349F8C610FC5AADE6AB/0?fmt=png&size=794&h=916&w=637&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3346303538-341003E19CFE5BDDCC02B4C0A98F94F4/0?fmt=png&size=1001&h=685&w=946&ppv=1", "side.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-77111552-631F166FDBB1615EAB485E56F103163C/0?fmt=png&size=475&h=518&w=944&ppv=1", "rear.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-2557669540-CB9C57BEECA56B963413D58DA84B3FE6/0?fmt=png&size=605&h=606&w=944&ppv=1", "interior.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3455876167-7ED14A5A328F5ADA127C1CDE4C5756DC/0?fmt=png&size=887&h=692&w=1104&ppv=1", "production.jpg"),
    ],
    "models": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-1599387254-562E4F9549D5BD93B273DF7DE129B231/0?fmt=jpg&size=278&h=1280&w=1707&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-3990871077-AE3F5778CD2D7E1EF612FCAB684FC231/0?fmt=jpg&size=287&h=1280&w=1707&ppv=1", "rear.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-2945921959-E21E8EDEA0AC3804F4DEC7A0FC70D514/0?fmt=jpg&size=288&h=1280&w=1707&ppv=1", "interior.jpg"),
    ],
    "modelx": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-3849671403-E93C74663145F3E617BE290576AE11DF/0?fmt=jpg&size=325&h=1500&w=2250&ppv=1", "front.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-627628095-0546F2F3EFB0EC0D86B7DFE8FB4C30F6/0?fmt=jpg&size=408&h=1500&w=2250&ppv=1", "side.jpg"),
        ("https://qqpublic.qpic.cn/qq_public/0/28-2527816672-4F42C8D2D8BFF2DF956B660515A2436C/0?fmt=jpg&size=279&h=1500&w=2250&ppv=1", "interior.jpg"),
    ],
    "powerwall": [
        ("https://qqpublic.qpic.cn/qq_public/0/28-4174884033-CB94B9A986CB83BAA17B45AF96227846/0?fmt=png&size=95&h=386&w=653&ppv=1", "unit.jpg"),
    ],
}


def download_and_save(url, path):
    """Download image from URL, resize for card, save as webp."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        
        img = Image.open(BytesIO(data))
        if img.mode in ('RGBA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize for card: max 400px wide, keep aspect ratio
        w, h = img.size
        card_w, card_h = 400, int(400 * h / w)
        img_card = img.resize((card_w, card_h), Image.LANCZOS)
        
        img_card.save(path, 'WEBP', quality=80)
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✅ {os.path.basename(path)}: {img.size[0]}x{img.size[1]} → {card_w}x{card_h}, {size_kb:.0f}KB")
        return True
    except Exception as e:
        print(f"  ❌ {url[-50:]}: {e}")
        return False


def main():
    results = {}
    all_tasks = []
    
    for category, files in IMAGES.items():
        cat_dir = os.path.join(BASE, category)
        os.makedirs(cat_dir, exist_ok=True)
        for url, fname in files:
            fpath = os.path.join(cat_dir, fname)
            all_tasks.append((category, url, fpath))
    
    print(f"Downloading {len(all_tasks)} images...")
    
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(download_and_save, url, path): (cat, fname) for cat, url, path in all_tasks}
        for fut in as_completed(futures):
            cat, fname = futures[fut]
            results[f"{cat}/{fname}"] = fut.result()
    
    success = sum(1 for v in results.values() if v)
    print(f"\nDone: {success}/{len(all_tasks)} images saved.")
    
    # List what's available
    print("\nAvailable images:")
    for cat in sorted(IMAGES.keys()):
        cat_dir = os.path.join(BASE, cat)
        files = sorted(os.listdir(cat_dir)) if os.path.exists(cat_dir) else []
        print(f"  {cat}: {files}")

if __name__ == "__main__":
    main()
