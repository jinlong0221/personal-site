#!/bin/bash
# 批量替换游戏主机详情页的占位图为SVG矢量图

WEBSITE_DIR="/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站"

# 定义主机ID到SVG文件名的映射
declare -A CONSOLE_MAP=(
    # 任天堂
    ["fc"]="fc"
    ["family-computer"]="fc"
    ["nes"]="fc"
    ["sfc"]="sfc"
    ["super-famicom"]="sfc"
    ["snes"]="sfc"
    ["n64"]="n64"
    ["nintendo-64"]="n64"
    ["gc"]="gc"
    ["gamecube"]="gc"
    ["wii"]="wii"
    ["wiiu"]="wiiu"
    ["switch"]="switch"
    ["switch-oled"]="switch-oled"
    ["switch-lite"]="switch-lite"
    ["switch-2"]="switch-2"
    ["gameboy"]="gameboy"
    ["gb"]="gameboy"
    ["gbc"]="gbc"
    ["gba"]="gba"
    ["nds"]="nds"
    ["nintendo-ds"]="nds"
    ["3ds"]="3ds"
    
    # 索尼
    ["ps1"]="ps1"
    ["playstation"]="ps1"
    ["ps2"]="ps2"
    ["ps3"]="ps3"
    ["ps4"]="ps4"
    ["ps5"]="ps5"
    ["psp"]="psp"
    ["vita"]="vita"
    ["psvita"]="vita"
    
    # 微软
    ["xbox"]="xbox"
    ["xbox360"]="xbox360"
    ["xbox-one"]="xbox-one"
    ["xbox-series-x"]="xbox-series-x"
    ["xbox-series-s"]="xbox-series-s"
    
    # 世嘉
    ["sg1000"]="sg1000"
    ["master-system"]="master-system"
    ["mega-drive"]="mega-drive"
    ["game-gear"]="game-gear"
    ["saturn"]="saturn"
    ["dreamcast"]="dreamcast"
    
    # 雅达利
    ["atari-2600"]="atari-2600"
    ["atari-5200"]="atari-5200"
    ["atari-7800"]="atari-7800"
    ["atari-lynx"]="atari-lynx"
    
    # 其他
    ["neo-geo"]="neo-geo"
    ["3do"]="3do"
    ["pc-engine"]="pc-engine"
    ["steam-deck"]="steam-deck"
    ["rog-ally"]="rog-ally"
    ["legion-go"]="legion-go"
    ["xiaobawang"]="xiaobawang"
)

# 遍历所有console-*.html文件
for html_file in "$WEBSITE_DIR"/console-*.html; do
    filename=$(basename "$html_file")
    
    # 跳过品牌列表页
    if [[ "$filename" == "console-nintendo.html" ]] || \
       [[ "$filename" == "console-sony.html" ]] || \
       [[ "$filename" == "console-microsoft.html" ]] || \
       [[ "$filename" == "console-sega.html" ]] || \
       [[ "$filename" == "console-atari.html" ]] || \
       [[ "$filename" == "console.html" ]]; then
        continue
    fi
    
    # 提取主机ID（去掉console-前缀和.html后缀）
    console_id="${filename#console-}"
    console_id="${console_id%.html}"
    
    # 查找对应的SVG文件名
    svg_name="${CONSOLE_MAP[$console_id]}"
    if [[ -z "$svg_name" ]]; then
        # 如果没有明确映射，尝试使用原始ID
        svg_name="$console_id"
    fi
    
    svg_file="img/consoles/${svg_name}.svg"
    
    # 检查SVG文件是否存在
    if [[ ! -f "$WEBSITE_DIR/$svg_file" ]]; then
        echo "⚠️  SVG不存在: $svg_file (for $filename)"
        continue
    fi
    
    # 构建要匹配的主机名称（从文件名推断）
    # 大多数占位div包含主机名称
    
    # 使用perl进行复杂替换
    perl -i -0777 -pe '
        # 替换占位div为img标签
        s{<div style="width:100%;aspect-ratio:4/3;background:linear-gradient\([^)]+\)[^>]*>([^<]+)<br><span[^>]*>([^<]+)<br>([^<]+)</span></div>}{<img src="'"$svg_file"'" alt="$1" style="width:100%;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.18);" loading="lazy">}g;
    ' "$html_file"
    
    echo "✅ 已处理: $filename -> $svg_file"
done

echo ""
echo "🎉 批量替换完成！"
