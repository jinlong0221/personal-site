#!/usr/bin/env python3
"""
替换品牌列表页的emoji图标为SVG小图标
"""
import re
from pathlib import Path

WEBSITE_DIR = Path("/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站")

# 品牌页的大emoji图标映射
BRAND_EMOJI_MAP = {
    "console-nintendo.html": ("🔴", "fc"),
    "console-sony.html": ("🔵", "ps1"),
    "console-microsoft.html": ("🟢", "xbox"),
    "console-sega.html": ("🔵", "dreamcast"),
    "console-atari.html": ("🟤", "atari-2600"),
}

# 卡片中使用的主机名称到SVG的映射
CARD_TITLE_TO_SVG = {
    # 任天堂
    "Family Computer (FC)": "fc",
    "Super Famicom (SFC)": "sfc",
    "Nintendo 64 (N64)": "n64",
    "GameCube (NGC)": "gc",
    "Wii": "wii",
    "Wii U": "wiiu",
    "Switch": "switch",
    "Switch OLED": "switch-oled",
    "Switch Lite": "switch-lite",
    "Switch 2": "switch-2",
    "Game Boy": "gameboy",
    "Game Boy Color": "gameboy-color",
    "Game Boy Advance": "gba",
    "Nintendo DS": "nds",
    "Nintendo 3DS": "3ds",
    
    # 索尼
    "PlayStation (PS1)": "ps1",
    "PlayStation 2 (PS2)": "ps2",
    "PlayStation 3 (PS3)": "ps3",
    "PlayStation 4 (PS4)": "ps4",
    "PlayStation 5 (PS5)": "ps5",
    "PlayStation Portable (PSP)": "psp",
    "PlayStation Vita": "vita",
    
    # 微软
    "Xbox": "xbox",
    "Xbox 360": "xbox360",
    "Xbox One": "xbox-one",
    "Xbox Series X": "xbox-series-x",
    "Xbox Series S": "xbox-series-s",
    
    # 世嘉
    "SG-1000": "sg1000",
    "Master System": "master-system",
    "Mega Drive": "mega-drive",
    "Game Gear": "game-gear",
    "Saturn": "saturn",
    "Dreamcast": "dreamcast",
    
    # 雅达利
    "Atari 2600": "atari-2600",
    "Atari 5200": "atari-5200",
    "Atari 7800": "atari-7800",
    "Atari Lynx": "atari-lynx",
    
    # 其他
    "Neo-Geo AES": "neo-geo",
    "3DO": "3do",
    "PC Engine": "pc-engine",
    "Steam Deck": "steam-deck",
    "ROG Ally": "rog-ally",
    "Legion Go": "legion-go",
    "小霸王学习机": "xiaobawang",
}

def get_svg_img_tag(svg_name, size=72, alt=""):
    """生成SVG img标签"""
    return f'<img src="img/consoles/{svg_name}.svg" alt="{alt}" style="width:{size}px;height:{size}px;border-radius:12px;object-fit:contain;" loading="lazy">'

def main():
    for brand_page, (emoji, default_svg) in BRAND_EMOJI_MAP.items():
        html_file = WEBSITE_DIR / brand_page
        if not html_file.exists():
            print(f"⚠️  文件不存在: {brand_page}")
            continue
        
        content = html_file.read_text(encoding="utf-8")
        
        # 替换顶部的大emoji图标
        content = re.sub(
            r'<div class="emoji-big">' + re.escape(emoji) + '</div>',
            f'<div class="emoji-big">{get_svg_img_tag(default_svg, size=56, alt="品牌图标")}</div>',
            content
        )
        
        # 遍历所有卡片标题，替换emoji
        for title, svg_name in CARD_TITLE_TO_SVG.items():
            svg_path = WEBSITE_DIR / f"img/consoles/{svg_name}.svg"
            if svg_path.exists():
                # 尝试在card-title后面添加小图标
                pattern = rf'(<div class="card-title">' + re.escape(title) + r'</div>)'
                replacement = f'<img src="img/consoles/{svg_name}.svg" alt="{title}" style="width:48px;height:48px;border-radius:8px;object-fit:contain;float:right;margin-left:10px;margin-bottom:5px;" loading="lazy">\n      \\1'
                content = re.sub(pattern, replacement, content)
        
        html_file.write_text(content, encoding="utf-8")
        print(f"✅ 已处理品牌页: {brand_page}")
    
    print("\n🎉 品牌列表页处理完成！")

if __name__ == "__main__":
    main()
