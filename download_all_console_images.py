#!/usr/bin/env python3
"""
游戏主机图片下载工具 - 完整版
支持多个图片源、自动转换、HTML更新、Git提交
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

# ==================== 配置区 ====================

WEBSITE_ROOT = Path(__file__).parent
IMAGES_DIR = WEBSITE_ROOT / "img/consoles"
TEMP_DIR = IMAGES_DIR / "temp"
REPORT_FILE = WEBSITE_ROOT / "console_images_report.txt"

# 确保目录存在
TEMP_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# ==================== 主机图片映射 ====================

# 格式说明：
# - wiki: Wikipedia页面标题（用于API获取图片）
# - alt_names: 可能的替代名称
# - search_keywords: 搜索关键词（用于备选方案）

CONSOLES_BATCH1 = {
    "switch": {
        "wiki": "Nintendo_Switch",
        "output": "switch.webp",
        "priority": 1
    },
    "switch-lite": {
        "wiki": "Nintendo_Switch_Lite",
        "output": "switch-lite.webp",
        "priority": 1
    },
    "ps5": {
        "wiki": "PlayStation_5",
        "output": "ps5.webp",
        "priority": 1
    },
    "ps4": {
        "wiki": "PlayStation_4",
        "output": "ps4.webp",
        "priority": 1
    },
    "ps2": {
        "wiki": "PlayStation_2",
        "output": "ps2.webp",
        "priority": 1
    },
    "xbox-series-x": {
        "wiki": "Xbox_Series_X",
        "output": "xbox-series-x.webp",
        "priority": 1
    },
    "xbox-series-s": {
        "wiki": "Xbox_Series_S",
        "output": "xbox-series-s.webp",
        "priority": 1
    },
    "steam-deck": {
        "wiki": "Steam_Deck",
        "output": "steam-deck.webp",
        "priority": 1
    },
    "dreamcast": {
        "wiki": "Dreamcast",
        "output": "dreamcast.webp",
        "priority": 1
    },
    "n64": {
        "wiki": "Nintendo_64",
        "output": "n64.webp",
        "priority": 1
    },
    "gamecube": {
        "wiki": "GameCube",
        "output": "gamecube.webp",
        "priority": 1
    },
    "wii": {
        "wiki": "Wii",
        "output": "wii.webp",
        "priority": 1
    },
    "snes": {
        "wiki": "Super_Nintendo_Entertainment_System",
        "output": "snes.webp",
        "priority": 1
    },
    "nes": {
        "wiki": "Nintendo_Entertainment_System",
        "output": "nes.webp",
        "priority": 1
    },
    "3ds": {
        "wiki": "Nintendo_3DS",
        "output": "3ds.webp",
        "priority": 1
    },
}

CONSOLES_BATCH2 = {
    "ps1": {"wiki": "PlayStation_(console)", "output": "ps1.webp"},
    "ps3": {"wiki": "PlayStation_3", "output": "ps3.webp"},
    "ps-vita": {"wiki": "PlayStation_Vita", "output": "ps-vita.webp"},
    "psp": {"wiki": "PlayStation_Portable", "output": "psp.webp"},
    "xbox": {"wiki": "Xbox_(console)", "output": "xbox.webp"},
    "xbox360": {"wiki": "Xbox_360", "output": "xbox360.webp"},
    "xbox-one": {"wiki": "Xbox_One", "output": "xbox-one.webp"},
    "atari-2600": {"wiki": "Atari_2600", "output": "atari-2600.webp"},
    "saturn": {"wiki": "Sega_Saturn", "output": "saturn.webp"},
    "mega-drive": {"wiki": "Genesis_(console)", "output": "mega-drive.webp"},
    "neo-geo": {"wiki": "Neo_Geo_(system)", "output": "neo-geo.webp"},
    "game-gear": {"wiki": "Game_Gear", "output": "game-gear.webp"},
    "gameboy": {"wiki": "Game_Boy", "output": "gameboy.webp"},
    "gameboy-color": {"wiki": "Game_Boy_Color", "output": "gameboy-color.webp"},
    "gba": {"wiki": "Game_Boy_Advance", "output": "gba.webp"},
    "nds": {"wiki": "Nintendo_DS", "output": "nds.webp"},
    "pc-engine": {"wiki": "PC_Engine", "output": "pc-engine.webp"},
}

# ==================== 工具函数 ====================

def log(message, level="INFO"):
    """打印带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "DEBUG": "🔍"
    }.get(level, "📌")
    print(f"[{timestamp}] {prefix} {message}")

def download_file(url, output_path, timeout=30):
    """
    下载文件到指定路径
    返回: (success: bool, error_message: str)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        request = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}"
            
            with open(output_path, 'wb') as f:
                f.write(response.read())
            
            file_size = os.path.getsize(output_path)
            if file_size < 1024:  # 小于1KB可能是错误页面
                os.remove(output_path)
                return False, "File too small (可能下载了错误页面)"
            
            return True, ""
    
    except urllib.error.URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def get_wikipedia_image_url(wiki_title, retry=3):
    """
    从Wikipedia API获取图片URL
    返回: (image_url: str or None, error: str)
    """
    for attempt in range(retry):
        try:
            api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_title)}"
            
            headers = {'User-Agent': 'ConsoleImageDownloader/1.0'}
            request = urllib.request.Request(api_url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if 'thumbnail' in data and 'source' in data['thumbnail']:
                    thumb_url = data['thumbnail']['source']
                    
                    # 尝试获取原始尺寸图片
                    # 缩略图URL格式: https://upload.wikimedia.org/wikipedia/commons/thumb/X/XX/File.png/300px-File.png
                    # 原始图片URL: https://upload.wikimedia.org/wikipedia/commons/X/XX/File.png
                    
                    if '/thumb/' in thumb_url:
                        # 提取路径
                        path_part = thumb_url.split('/thumb/')[1]
                        # 移除尺寸前缀 (如 "300px-")
                        filename = path_part.split('/')[-1]
                        if 'px-' in filename:
                            filename = filename.split('px-')[1]
                        
                        # 重建原始图片URL
                        base_path = '/'.join(path_part.split('/')[:-1])
                        original_url = f"https://upload.wikimedia.org/wikipedia/commons/{base_path}/{filename}"
                        return original_url, ""
                    
                    return thumb_url, ""
                
                return None, "No thumbnail in API response"
        
        except Exception as e:
            error = str(e)
            if attempt < retry - 1:
                log(f"重试 ({attempt+1}/{retry}): {wiki_title}", "WARNING")
                time.sleep(2)
            else:
                return None, error
    
    return None, "Max retries exceeded"

def convert_to_webp(input_path, output_path, width=600, quality=75):
    """
    使用Pillow将图片转换为WebP格式
    返回: (success: bool, error_message: str)
    """
    try:
        # 检查输入文件是否存在
        if not input_path.exists():
            return False, "Input file not found"
        
        from PIL import Image
        
        # 打开图片
        img = Image.open(input_path)
        
        # 转换为RGB（如果是RGBA或其他模式）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 调整大小
        original_width, original_height = img.size
        if original_width > width:
            height = int(original_height * (width / original_width))
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # 保存为WebP
        img.save(output_path, 'WebP', quality=quality, method=6)
        
        return True, ""
    
    except Exception as e:
        return False, str(e)

def update_html_references():
    """
    更新所有console HTML文件中的图片引用
    将 .svg 替换为 .webp (仅当.webp文件存在时)
    """
    log("开始更新HTML文件中的图片引用...", "INFO")
    
    html_files = list(WEBSITE_ROOT.glob("console-*.html"))
    updated_count = 0
    error_count = 0
    
    import re
    
    for html_file in html_files:
        try:
            content = html_file.read_text(encoding='utf-8')
            new_content = content
            file_updated = False
            
            # 查找所有引用的SVG文件
            svg_refs = re.findall(r'img/consoles/([a-zA-Z0-9_-]+)\.svg', content)
            
            for svg_name in set(svg_refs):  # 使用set去重
                webp_file = IMAGES_DIR / f"{svg_name}.webp"
                
                if webp_file.exists():
                    old_ref = f"img/consoles/{svg_name}.svg"
                    new_ref = f"img/consoles/{svg_name}.webp"
                    new_content = new_content.replace(old_ref, new_ref)
                    file_updated = True
                    log(f"  {html_file.name}: {svg_name}.svg -> {svg_name}.webp", "DEBUG")
            
            if file_updated:
                html_file.write_text(new_content, encoding='utf-8')
                updated_count += 1
                log(f"  已更新: {html_file.name}", "SUCCESS")
            
        except Exception as e:
            error_count += 1
            log(f"  更新失败 {html_file.name}: {e}", "ERROR")
    
    log(f"HTML更新完成: 成功={updated_count}, 失败={error_count}", "INFO")
    return updated_count, error_count

def git_commit():
    """
    提交更改到Git
    """
    try:
        log("提交到Git...", "INFO")
        
        # git add
        result = subprocess.run(
            ['git', 'add', 'img/consoles/*.webp'],
            cwd=WEBSITE_ROOT,
            capture_output=True,
            text=True
        )
        
        result = subprocess.run(
            ['git', 'add', 'console-*.html'],
            cwd=WEBSITE_ROOT,
            capture_output=True,
            text=True
        )
        
        # git commit
        commit_msg = f"添加游戏主机真实产品图片 {datetime.now().strftime('%Y-%m-%d')}"
        result = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=WEBSITE_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log("Git提交成功", "SUCCESS")
            return True
        else:
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                log("没有需要提交的更改", "WARNING")
                return True
            else:
                log(f"Git提交失败: {result.stderr}", "ERROR")
                return False
    
    except Exception as e:
        log(f"Git操作异常: {e}", "ERROR")
        return False

# ==================== 主处理逻辑 ====================

def process_console(console_name, info):
    """
    处理单个主机的图片下载和转换
    返回: (success: bool, message: str)
    """
    log(f"处理主机: {console_name}", "INFO")
    
    output_webp = IMAGES_DIR / info["output"]
    
    # 如果WebP已存在，跳过
    if output_webp.exists():
        log(f"  已存在，跳过: {info['output']}", "WARNING")
        return True, "已存在"
    
    # 步骤1：获取图片URL
    image_url = None
    error_msg = ""
    
    if "wiki" in info:
        log(f"  从Wikipedia获取图片: {info['wiki']}", "DEBUG")
        image_url, error_msg = get_wikipedia_image_url(info["wiki"])
    
    if not image_url:
        return False, f"无法获取图片URL: {error_msg}"
    
    log(f"  图片URL: {image_url}", "DEBUG")
    
    # 步骤2：下载图片
    temp_file = TEMP_DIR / f"{console_name}_temp"
    
    # 根据URL判断文件扩展名
    url_path = urllib.parse.urlparse(image_url).path
    ext = os.path.splitext(url_path)[1] or '.jpg'
    temp_file = temp_file.with_suffix(ext)
    
    log(f"  下载图片...", "DEBUG")
    success, error = download_file(image_url, temp_file)
    
    if not success:
        return False, f"下载失败: {error}"
    
    log(f"  下载成功: {temp_file.name}", "SUCCESS")
    
    # 步骤3：转换为WebP
    log(f"  转换为WebP...", "DEBUG")
    success, error = convert_to_webp(temp_file, output_webp)
    
    # 清理临时文件
    if temp_file.exists():
        temp_file.unlink()
    
    if not success:
        return False, f"转换失败: {error}"
    
    log(f"  转换成功: {output_webp.name}", "SUCCESS")
    
    return True, "成功"

def main():
    """
    主函数
    """
    print("=" * 70)
    print(" " * 15 + "游戏主机图片下载工具")
    print("=" * 70)
    print()
    
    # 检查依赖
    log("检查依赖工具...", "INFO")
    try:
        from PIL import Image
        log("Pillow已安装 ✓", "SUCCESS")
    except ImportError:
        log("Pillow未安装！请运行: pip3 install Pillow", "ERROR")
        return
    
    # 处理第一批主机
    log("开始处理第一批主机（热门主机）...", "INFO")
    
    success_list = []
    fail_list = []
    
    for console_name, info in CONSOLES_BATCH1.items():
        success, message = process_console(console_name, info)
        
        if success:
            success_list.append((console_name, message))
        else:
            fail_list.append((console_name, message))
        
        # 避免请求过快
        time.sleep(1)
    
    # 打印报告
    print()
    print("=" * 70)
    print("下载报告")
    print("=" * 70)
    print()
    print(f"第一批主机处理完成:")
    print(f"  成功: {len(success_list)}/{len(CONSOLES_BATCH1)}")
    print(f"  失败: {len(fail_list)}/{len(CONSOLES_BATCH1)}")
    print()
    
    if success_list:
        print("成功列表:")
        for name, msg in success_list:
            print(f"  ✓ {name}: {msg}")
        print()
    
    if fail_list:
        print("失败列表:")
        for name, msg in fail_list:
            print(f"  ✗ {name}: {msg}")
        print()
    
    # 询问是否继续第二批
    if len(fail_list) < len(CONSOLES_BATCH1):
        print("=" * 70)
        response = input("是否继续处理第二批主机？(y/n): ")
        
        if response.lower() == 'y':
            log("开始处理第二批主机...", "INFO")
            # TODO: 处理第二批
            print("第二批处理功能开发中...")
    
    # 更新HTML引用
    print()
    print("=" * 70)
    response = input("是否更新HTML文件中的图片引用？(y/n): ")
    
    if response.lower() == 'y':
        update_html_references()
    
    # Git提交
    print()
    print("=" * 70)
    response = input("是否提交到Git？(y/n): ")
    
    if response.lower() == 'y':
        git_commit()
    
    print()
    print("=" * 70)
    print("任务完成！")
    print("=" * 70)
    
    # 保存报告
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"游戏主机图片下载报告\n")
        f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n第一批处理:\n")
        f.write(f"  成功: {len(success_list)}/{len(CONSOLES_BATCH1)}\n")
        f.write(f"  失败: {len(fail_list)}/{len(CONSOLES_BATCH1)}\n")
        f.write(f"\n成功列表:\n")
        for name, msg in success_list:
            f.write(f"  ✓ {name}: {msg}\n")
        f.write(f"\n失败列表:\n")
        for name, msg in fail_list:
            f.write(f"  ✗ {name}: {msg}\n")
    
    log(f"报告已保存到: {REPORT_FILE}", "INFO")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，退出...")
        sys.exit(1)
    except Exception as e:
        log(f"未预期的错误: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
