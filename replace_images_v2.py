#!/usr/bin/env python3
"""
批量替换游戏主机详情页的占位图为SVG矢量图 - V2
"""
import re
import os
from pathlib import Path

WEBSITE_DIR = Path("/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站")

# 完整的主机ID到SVG文件名的映射
CONSOLE_MAP = {
    # 任天堂
    "fc": "fc",
    "family-computer": "fc",
    "nes": "fc",
    "sfc": "sfc",
    "super-famicom": "sfc",
    "snes": "sfc",
    "n64": "n64",
    "nintendo-64": "n64",
    "gc": "gc",
    "gamecube": "gc",
    "wii": "wii",
    "wiiu": "wiiu",
    "wii-u": "wiiu",
    "switch": "switch",
    "switch-oled": "switch-oled",
    "switch-lite": "switch-lite",
    "switch-2": "switch-2",
    "gameboy": "gameboy",
    "gb": "gameboy",
    "gameboy-color": "gameboy-color",
    "gbc": "gameboy-color",
    "gameboy-pocket": "gameboy-pocket",
    "gameboy-advance": "gba",
    "gba": "gba",
    "nds": "nds",
    "nintendo-ds": "nds",
    "3ds": "3ds",
    "nintendo-3ds": "3ds",
    "game-watch": "game-watch",
    
    # 索尼
    "ps1": "ps1",
    "playstation": "ps1",
    "ps2": "ps2",
    "ps3": "ps3",
    "playstation-3": "ps3",
    "ps4": "ps4",
    "playstation-4": "ps4",
    "ps5": "ps5",
    "playstation-5": "ps5",
    "playstation-5-pro": "playstation-5-pro",
    "psp": "psp",
    "playstation-portable": "psp",
    "vita": "vita",
    "psvita": "vita",
    "ps-vita": "vita",
    "playstation-portal": "playstation-portal",
    
    # 微软
    "xbox": "xbox",
    "xbox360": "xbox360",
    "xbox-one": "xbox-one",
    "xbox-series-x": "xbox-series-x",
    "xbox-series-s": "xbox-series-s",
    
    # 世嘉
    "sg1000": "sg1000",
    "sg-1000": "sg1000",
    "master-system": "master-system",
    "mega-drive": "mega-drive",
    "game-gear": "game-gear",
    "saturn": "saturn",
    "dreamcast": "dreamcast",
    
    # 雅达利
    "atari-2600": "atari-2600",
    "atari-5200": "atari-5200",
    "atari-7800": "atari-7800",
    "atari-lynx": "atari-lynx",
    
    # 其他
    "neo-geo": "neo-geo",
    "3do": "3do",
    "pc-engine": "pc-engine",
    "steam-deck": "steam-deck",
    "rog-ally": "rog-ally",
    "legion-go": "legion-go",
    "xiaobawang": "xiaobawang",
    "other": "other",
}

def get_alt_text(console_id, svg_name):
    """生成alt文本"""
    names = {
        "fc": "Nintendo Famicom (FC) 红白机",
        "sfc": "Super Famicom (SFC) 超级任天堂",
        "n64": "Nintendo 64",
        "gc": "Nintendo GameCube",
        "wii": "Nintendo Wii",
        "wiiu": "Nintendo Wii U",
        "switch": "Nintendo Switch",
        "switch-oled": "Nintendo Switch OLED",
        "switch-lite": "Nintendo Switch Lite",
        "switch-2": "Nintendo Switch 2",
        "gameboy": "Nintendo Game Boy",
        "gameboy-color": "Nintendo Game Boy Color",
        "gameboy-pocket": "Nintendo Game Boy Pocket",
        "gba": "Nintendo Game Boy Advance",
        "nds": "Nintendo DS",
        "3ds": "Nintendo 3DS",
        "game-watch": "Nintendo Game & Watch",
        "ps1": "Sony PlayStation 1",
        "ps2": "Sony PlayStation 2",
        "ps3": "Sony PlayStation 3",
        "ps4": "Sony PlayStation 4",
        "ps5": "Sony PlayStation 5",
        "playstation-5-pro": "Sony PlayStation 5 Pro",
        "psp": "Sony PlayStation Portable",
        "vita": "Sony PlayStation Vita",
        "playstation-portal": "Sony PlayStation Portal",
        "xbox": "Microsoft Xbox",
        "xbox360": "Microsoft Xbox 360",
        "xbox-one": "Microsoft Xbox One",
        "xbox-series-x": "Microsoft Xbox Series X",
        "xbox-series-s": "Microsoft Xbox Series S",
        "sg1000": "Sega SG-1000",
        "master-system": "Sega Master System",
        "mega-drive": "Sega Mega Drive",
        "game-gear": "Sega Game Gear",
        "saturn": "Sega Saturn",
        "dreamcast": "Sega Dreamcast",
        "atari-2600": "Atari 2600",
        "atari-5200": "Atari 5200",
        "atari-7800": "Atari 7800",
        "atari-lynx": "Atari Lynx",
        "neo-geo": "SNK Neo-Geo AES",
        "3do": "3DO Interactive Multiplayer",
        "pc-engine": "NEC PC Engine",
        "steam-deck": "Valve Steam Deck",
        "rog-ally": "ASUS ROG Ally",
        "legion-go": "Lenovo Legion Go",
        "xiaobawang": "小霸王学习机",
        "other": "其他游戏主机",
    }
    return names.get(svg_name, f"{console_id} 游戏主机")

def replace_placeholder_div(html_content, svg_file, alt_text):
    """替换占位div为img标签"""
    
    # 模式1: 带linear-gradient的div（更宽松的匹配）
    pattern1 = r'<div style="width:100%;aspect-ratio:4/3;background:linear-gradient\([^)]+\)[^>]*>.*?</div>'
    
    replacement = f'<img src="{svg_file}" alt="{alt_text}" style="width:100%;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.18);" loading="lazy">'
    
    result = re.sub(pattern1, replacement, html_content, flags=re.DOTALL)
    
    return result

def main():
    processed = 0
    skipped = 0
    
    for html_file in WEBSITE_DIR.glob("console-*.html"):
        filename = html_file.name
        
        # 跳过品牌列表页和主列表页
        if filename in ["console-nintendo.html", "console-sony.html", 
                        "console-microsoft.html", "console-sega.html", 
                        "console-atari.html", "console.html"]:
            continue
        
        # 提取主机ID
        console_id = filename.replace("console-", "").replace(".html", "")
        
        # 查找对应的SVG文件名
        svg_name = CONSOLE_MAP.get(console_id, console_id)
        svg_file = f"img/consoles/{svg_name}.svg"
        svg_path = WEBSITE_DIR / svg_file
        
        # 检查SVG文件是否存在
        if not svg_path.exists():
            print(f"⚠️  SVG不存在: {svg_file} (for {filename})")
            skipped += 1
            continue
        
        # 读取HTML内容
        content = html_file.read_text(encoding="utf-8")
        
        # 检查是否已经有img标签（已替换过）
        if f'<img src="{svg_file}"' in content:
            print(f"⏭️  已替换过: {filename}")
            continue
        
        # 检查是否有占位div
        if "待补充真实照片" not in content and "background:linear-gradient" not in content:
            print(f"❓ 无占位div: {filename}")
            skipped += 1
            continue
        
        # 替换占位div
        alt_text = get_alt_text(console_id, svg_name)
        new_content = replace_placeholder_div(content, svg_file, alt_text)
        
        if new_content != content:
            html_file.write_text(new_content, encoding="utf-8")
            print(f"✅ 已处理: {filename} -> {svg_file}")
            processed += 1
        else:
            print(f"❌ 替换失败: {filename}")
            skipped += 1
    
    print(f"\n🎉 完成！处理了 {processed} 个文件，跳过 {skipped} 个")

if __name__ == "__main__":
    main()
