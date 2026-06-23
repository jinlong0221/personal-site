# 游戏主机图片下载指南

## 概述
本目录包含自动下载游戏主机真实产品图片的脚本和工具。

## 快速开始

### 方法1：使用Python脚本（推荐）

```bash
cd "/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站/"
python3 download_console_images.py
```

### 方法2：手动下载

如果需要手动下载，请参考下方的图片来源列表。

## 图片规格要求

- **格式**: WebP
- **宽度**: 600px（高度自动）
- **质量**: 75（ffmpeg -q:v参数）
- **背景**: 优先白色/浅色背景的产品照
- **存放位置**: `img/consoles/` 目录
- **命名规则**: 与现有SVG文件同名，但扩展名为 `.webp`

## 主机图片来源列表

### 第一批：热门主机（优先处理）

| 主机名 | 文件名 | 推荐图片来源 | 搜索关键词 |
|--------|--------|--------------|------------|
| Nintendo Switch | switch.webp | Wikimedia Commons | "Nintendo Switch console product image" |
| Nintendo Switch Lite | switch-lite.webp | Wikimedia Commons | "Nintendo Switch Lite turquoise" |
| Nintendo Switch 2 | switch-2.webp | 官方/新闻图 | "Nintendo Switch 2 reveal" |
| PlayStation 5 | ps5.webp | PlayStation官网 | "PlayStation 5 console white" |
| PlayStation 4 | ps4.webp | Wikimedia Commons | "PS4 console black" |
| PlayStation 2 | ps2.webp | Wikimedia Commons | "PlayStation 2 console" |
| Xbox Series X | xbox-series-x.webp | Xbox官网 | "Xbox Series X carbon black" |
| Xbox Series S | xbox-series-s.webp | Xbox官网 | "Xbox Series S robot white" |
| Steam Deck | steam-deck.webp | Valve官网 | "Steam Deck console" |
| Sega Dreamcast | dreamcast.webp | Wikimedia Commons | "Sega Dreamcast console" |
| Nintendo 64 | n64.webp | Wikimedia Commons | "Nintendo 64 console" |
| Nintendo GameCube | gamecube.webp | Wikimedia Commons | "Nintendo GameCube purple" |
| Nintendo Wii | wii.webp | Wikimedia Commons | "Nintendo Wii white console" |
| Super Nintendo | snes.webp | Wikimedia Commons | "Super Nintendo console" |
| Nintendo NES | nes.webp | Wikimedia Commons | "Nintendo NES console" |
| Nintendo 3DS | 3ds.webp | Wikimedia Commons | "Nintendo 3DS aqua blue" |

### 第二批

| 主机名 | 文件名 |
|--------|--------|
| PlayStation | ps1.webp |
| PlayStation 3 | ps3.webp |
| PlayStation Vita | ps-vita.webp |
| PlayStation Portable | psp.webp |
| Xbox | xbox.webp |
| Xbox 360 | xbox360.webp |
| Xbox One | xbox-one.webp |
| Atari 2600 | atari-2600.webp |
| Sega Saturn | saturn.webp |
| Sega Mega Drive | mega-drive.webp |
| Neo Geo | neo-geo.webp |
| Sega Game Gear | game-gear.webp |
| Game Boy | gameboy.webp |
| Game Boy Color | gameboy-color.webp |
| Game Boy Advance | gba.webp |
| Nintendo DS | nds.webp |
| PC Engine | pc-engine.webp |

### 第三批（剩余所有）

包括：3do, atari-5200, atari-7800, atari-lynx, family-computer, fc, game-watch, gameboy-pocket, gb, gbc, gc, legion-go, master-system, nintendo-3ds, nintendo-64, nintendo-ds, other, playstation-3, playstation-5-pro, playstation-portable, playstation-portal, psvita, rog-ally, sfc, sg1000, super-famicom, switch-oled, vita, wii-u, wiiu, xiaobawang 等

## 图片下载来源推荐

### 1. Wikimedia Commons（推荐，免费合法）
- 网址：https://commons.wikimedia.org/
- 搜索：`[主机名] console`
- 优点：高清、免费、合法使用
- 示例：https://commons.wikimedia.org/wiki/File:Nintendo-Switch-Console.png

### 2. 官方网站产品页
- Nintendo：https://www.nintendo.com/
- PlayStation：https://www.playstation.com/
- Xbox：https://www.xbox.com/
- Steam：https://store.steampowered.com/

### 3. 使用Wikipedia API获取图片

```bash
# 获取某主机的图片URL
curl -s "https://en.wikipedia.org/api/rest_v1/page/summary/Nintendo_Switch" | \
  python3 -c "import sys,json;print(json.load(sys.stdin).get('thumbnail',{}).get('source',''))"
```

## 图片转换命令

下载JPG/PNG图片后，使用ffmpeg转换为WebP：

```bash
# 基本转换（宽度600px）
ffmpeg -i input.jpg -vf "scale=600:-1" -q:v 75 output.webp

# 批量转换
for img in img/consoles/webp-temp/*.jpg; do
  basename=$(basename "$img" .jpg)
  ffmpeg -i "$img" -vf "scale=600:-1" -q:v 75 "img/consoles/${basename}.webp"
done
```

## 更新HTML引用

图片下载完成后，需要更新HTML文件中的图片引用：

```bash
# 备份HTML文件
cp console-switch.html console-switch.html.bak

# 批量替换SVG引用为WebP
for html in console-*.html; do
  sed -i '' 's/img\/consoles\/\([a-zA-Z0-9_-]*\)\.svg/img\/consoles\/\1.webp/g' "$html"
done
```

## Python脚本说明

`download_console_images.py` 脚本功能：
1. 从Wikipedia API获取主机图片URL
2. 自动下载图片
3. 使用ffmpeg转换为WebP格式
4. 更新HTML文件中的图片引用
5. 提交到Git

### 运行前准备

```bash
# 确保已安装ffmpeg
brew install ffmpeg

# 确保有网络访问
ping wikipedia.org
```

### 自定义脚本

如果需要添加更多主机或调整参数，编辑脚本中的 `CONSOLE_IMAGES` 字典。

## 故障排除

### 问题1：网络访问失败
- 检查网络连接
- 尝试使用VPN
- 手动下载图片后放到 `img/consoles/webp-temp/` 目录

### 问题2：ffmpeg转换失败
- 检查ffmpeg是否正确安装：`ffmpeg -version`
- 检查输入图片是否损坏

### 问题3：HTML引用未更新
- 手动运行sed命令
- 检查HTML文件中的图片引用格式

## 完成后的检查清单

- [ ] 所有第一批主机都有对应的.webp图片
- [ ] 图片宽度为600px
- [ ] HTML文件中的图片引用已更新（.svg -> .webp）
- [ ] 本地测试网站，确认图片正常显示
- [ ] 提交到Git仓库

## 贡献

如果您找到了更好的图片来源或改进了脚本，请更新本文档。

---
创建时间：2026-06-23
作者：AI Assistant
