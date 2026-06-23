#!/bin/bash
# 游戏主机图片下载脚本 V2
# 使用Wikimedia Commons的直接图片链接

set -e
mkdir -p img/consoles/webp-temp

# 定义图片下载列表 (主机名 -> Wikimedia图片文件名)
declare -A CONSOLE_IMAGES

# 第一批：热门主机
CONSOLE_IMAGES["switch"]="Nintendo-Switch-Console.png"
CONSOLE_IMAGES["switch-lite"]="Nintendo-Switch-Lite.jpg"
CONSOLE_IMAGES["ps5"]="PS5-Console-wDS-Controller-Front.png"
CONSOLE_IMAGES["ps4"]="PS4-Console-wDS4.jpg"
CONSOLE_IMAGES["ps2"]="PS2-Console.jpg"
CONSOLE_IMAGES["xbox-series-x"]="Xbox-Series-X-Console.jpg"
CONSOLE_IMAGES["xbox-series-s"]="Xbox-Series-S-PNG.png"
CONSOLE_IMAGES["steam-deck"]="Steam-Deck-console.jpg"
CONSOLE_IMAGES["dreamcast"]="Dreamcast-Console-Set.jpg"
CONSOLE_IMAGES["n64"]="Nintendo-64-Console.png"
CONSOLE_IMAGES["gamecube"]="GameCube-Console-Set.jpg"
CONSOLE_IMAGES["wii"]="Wii-Console-Set.png"
CONSOLE_IMAGES["snes"]="SNES-Model-SNS-101.jpg"
CONSOLE_IMAGES["nes"]="NES-Console-Set.jpg"
CONSOLE_IMAGES["3ds"]="Nintendo-3DS-Aqua-Blue.png"

echo "开始下载主机图片..."

success_count=0
fail_list=()

for console in "${!CONSOLE_IMAGES[@]}"; do
    filename="${CONSOLE_IMAGES[$console]}"
    output_webp="img/consoles/${console}.webp"
    
    # 如果已存在，跳过
    if [ -f "$output_webp" ]; then
        echo "✓ 已存在: $console.webp"
        ((success_count++))
        continue
    fi
    
    echo "下载: $console (${filename})"
    
    # 从Wikimedia Commons下载
    # 注意：这里需要完整的MD5哈希路径，我们先尝试搜索
    temp_file="img/consoles/webp-temp/${console}_temp.jpg"
    
    # 使用Wikipedia API获取图片URL
    api_url="https://en.wikipedia.org/api/rest_v1/page/summary/$(echo $console | sed 's/-/_/g')"
    
    # 这里简化：直接尝试一些已知的图片URL模式
    # 实际使用时需要更复杂的逻辑来获取正确的图片URL
    
    echo "  暂不支持自动下载，需要手动下载"
    fail_list+=("$console")
done

echo ""
echo "========================================"
echo "成功: $success_count/${#CONSOLE_IMAGES[@]}"
if [ ${#fail_list[@]} -gt 0 ]; then
    echo "失败: ${fail_list[*]}"
fi
echo "========================================"

