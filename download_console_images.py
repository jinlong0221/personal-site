#!/usr/bin/env python3
"""
下载游戏主机真实产品图片并转换为WebP格式
替换现有的SVG占位图
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

# 网站根目录
WEBSITE_ROOT = Path(__file__).parent
IMAGES_DIR = WEBSITE_ROOT / "img/consoles"
TEMP_DIR = IMAGES_DIR / "webp-temp"

# 确保目录存在
TEMP_DIR.mkdir(exist_ok=True)

# 主机图片映射 (文件名 -> Wikipedia标题或图片URL)
CONSOLE_IMAGES = {
    # 第一批：热门主机
    "switch": {
        "wiki": "Nintendo_Switch",
        "search_terms": ["Nintendo Switch console", "Nintendo Switch white"],
        "output": "switch.webp"
    },
    "switch-lite": {
        "wiki": "Nintendo_Switch_Lite",
        "search_terms": ["Nintendo Switch Lite", "Switch Lite turquoise"],
        "output": "switch-lite.webp"
    },
    "switch-2": {
        "wiki": "Nintendo_Switch_2",
        "search_terms": ["Nintendo Switch 2", "Switch 2 console"],
        "output": "switch-2.webp"
    },
    "ps5": {
        "wiki": "PlayStation_5",
        "search_terms": ["PlayStation 5 console", "PS5 white"],
        "output": "ps5.webp"
    },
    "ps4": {
        "wiki": "PlayStation_4",
        "search_terms": ["PlayStation 4 console", "PS4 black"],
        "output": "ps4.webp"
    },
    "ps2": {
        "wiki": "PlayStation_2",
        "search_terms": ["PlayStation 2 console", "PS2 black"],
        "output": "ps2.webp"
    },
    "xbox-series-x": {
        "wiki": "Xbox_Series_X",
        "search_terms": ["Xbox Series X", "Xbox Series X black"],
        "output": "xbox-series-x.webp"
    },
    "xbox-series-s": {
        "wiki": "Xbox_Series_S",
        "search_terms": ["Xbox Series S", "Xbox Series S white"],
        "output": "xbox-series-s.webp"
    },
    "steam-deck": {
        "wiki": "Steam_Deck",
        "search_terms": ["Steam Deck", "Steam Deck black"],
        "output": "steam-deck.webp"
    },
    "dreamcast": {
        "wiki": "Dreamcast",
        "search_terms": ["Sega Dreamcast", "Dreamcast white"],
        "output": "dreamcast.webp"
    },
    "n64": {
        "wiki": "Nintendo_64",
        "search_terms": ["Nintendo 64", "N64 console"],
        "output": "n64.webp"
    },
    "gamecube": {
        "wiki": "GameCube",
        "search_terms": ["Nintendo GameCube", "GameCube purple"],
        "output": "gamecube.webp"
    },
    "wii": {
        "wiki": "Wii",
        "search_terms": ["Nintendo Wii", "Wii white"],
        "output": "wii.webp"
    },
    "snes": {
        "wiki": "Super_Nintendo_Entertainment_System",
        "search_terms": ["Super Nintendo", "SNES console"],
        "output": "snes.webp"
    },
    "nes": {
        "wiki": "Nintendo_Entertainment_System",
        "search_terms": ["Nintendo Entertainment System", "NES console"],
        "output": "nes.webp"
    },
    "3ds": {
        "wiki": "Nintendo_3DS",
        "search_terms": ["Nintendo 3DS", "3DS aqua blue"],
        "output": "3ds.webp"
    },
}

def download_image(url, output_path):
    """下载图片到指定路径"""
    try:
        print(f"  下载: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False

def convert_to_webp(input_path, output_path, width=600):
    """使用ffmpeg将图片转换为WebP格式"""
    try:
        cmd = [
            'ffmpeg', '-i', str(input_path),
            '-vf', f'scale={width}:-1',
            '-q:v', '75',
            '-y',  # 覆盖已存在的文件
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"  转换成功: {output_path}")
            return True
        else:
            print(f"  转换失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"  转换异常: {e}")
        return False

def get_wikipedia_image_url(wiki_title):
    """从Wikipedia API获取图片URL"""
    try:
        # 使用Wikipedia API获取页面图片
        api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_title}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        request = urllib.request.Request(api_url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read())
            if 'thumbnail' in data:
                # 获取缩略图URL，但尝试获取更大的版本
                thumb_url = data['thumbnail']['source']
                # 替换缩略图尺寸以获取更大图片
                # 例如: https://upload.wikimedia.org/wikipedia/commons/thumb/a/b0/Nintendo-Switch-Console.png/300px-Nintendo-Switch-Console.png
                # 改为: https://upload.wikimedia.org/wikipedia/commons/a/b0/Nintendo-Switch-Console.png
                if '/thumb/' in thumb_url:
                    # 提取完整尺寸图片URL
                    parts = thumb_url.split('/thumb/')[1].split('/')
                    # 移除尺寸前缀 (如 "300px-")
                    if len(parts) > 1 and 'px-' in parts[-1]:
                        parts[-1] = parts[-1].split('px-')[1]
                    full_url = 'https://upload.wikimedia.org/wikipedia/commons/' + '/'.join(parts)
                    return full_url
                return thumb_url
    except Exception as e:
        print(f"  Wikipedia API错误 ({wiki_title}): {e}")
    return None

def process_console(console_name, info):
    """处理单个主机的图片下载和转换"""
    print(f"\n处理: {console_name}")
    
    output_webp = IMAGES_DIR / info["output"]
    
    # 如果WebP已存在，跳过
    if output_webp.exists():
        print(f"  已存在: {output_webp}")
        return True
    
    # 尝试从Wikipedia获取图片
    img_url = None
    if "wiki" in info:
        img_url = get_wikipedia_image_url(info["wiki"])
    
    if not img_url:
        print(f"  未找到图片URL")
        return False
    
    # 下载图片
    temp_file = TEMP_DIR / f"{console_name}_temp.jpg"
    if not download_image(img_url, temp_file):
        return False
    
    # 转换为WebP
    success = convert_to_webp(temp_file, output_webp)
    
    # 清理临时文件
    if temp_file.exists():
        temp_file.unlink()
    
    return success

def update_html_references():
    """更新HTML文件中的图片引用：.svg -> .webp"""
    print("\n更新HTML文件中的图片引用...")
    
    # 查找所有console相关的HTML文件
    html_files = list(WEBSITE_ROOT.glob("console-*.html"))
    
    updated_count = 0
    for html_file in html_files:
        print(f"  检查: {html_file.name}")
        content = html_file.read_text(encoding='utf-8')
        
        # 替换图片引用
        new_content = content.replace('img/consoles/', 'img/consoles/')
        # 更精确的替换：只替换存在的.webp文件引用
        
        # 查找所有引用的SVG文件
        import re
        svg_refs = re.findall(r'img/consoles/([a-zA-Z0-9_-]+)\.svg', content)
        
        file_modified = False
        for svg_name in svg_refs:
            webp_file = IMAGES_DIR / f"{svg_name}.webp"
            if webp_file.exists():
                old_ref = f"img/consoles/{svg_name}.svg"
                new_ref = f"img/consoles/{svg_name}.webp"
                new_content = new_content.replace(old_ref, new_ref)
                file_modified = True
                print(f"    替换: {svg_name}.svg -> {svg_name}.webp")
        
        if file_modified:
            html_file.write_text(new_content, encoding='utf-8')
            updated_count += 1
    
    print(f"\n更新了 {updated_count} 个HTML文件")

def main():
    """主函数"""
    print("=" * 60)
    print("游戏主机图片下载工具")
    print("=" * 60)
    
    # 处理所有主机
    success_count = 0
    fail_list = []
    
    for console_name, info in CONSOLE_IMAGES.items():
        if process_console(console_name, info):
            success_count += 1
        else:
            fail_list.append(console_name)
    
    print("\n" + "=" * 60)
    print(f"完成！成功: {success_count}/{len(CONSOLE_IMAGES)}")
    if fail_list:
        print(f"失败列表: {', '.join(fail_list)}")
    print("=" * 60)
    
    # 更新HTML引用
    update_html_references()
    
    # Git提交
    print("\n提交到Git...")
    try:
        subprocess.run(['git', 'add', 'img/consoles/*.webp'], cwd=WEBSITE_ROOT)
        subprocess.run(['git', 'add', 'console-*.html'], cwd=WEBSITE_ROOT)
        subprocess.run(['git', 'commit', '-m', '添加游戏主机真实产品图片(WebP格式)'], cwd=WEBSITE_ROOT)
        print("Git提交成功")
    except Exception as e:
        print(f"Git提交失败: {e}")

if __name__ == "__main__":
    main()
