#!/usr/bin/env bash
# 重新生成旅行板块密文产物（travel-dist/），用于更新旅行内容后重新上线。
# 前置：
#   - 明文源已就位：static/travel.html、static/img/travel/*.webp、static/data/travel.json
#     （这些文件已被 .gitignore 忽略，仅本地/私有仓库持有，绝不入公开仓库）
#   - 环境变量 TRAVEL_KEY 已设置（与家人共享的解锁密码）
# 产物：travel-dist/travel.html + travel-dist/img/travel/*.enc（密文，可安全提交公开仓库）
set -e
cd "$(dirname "$0")/.."
require() { command -v "$1" >/dev/null 2>&1 || { echo "缺少命令：$1"; exit 1; }; }
require hugo; require node
if [ -z "$TRAVEL_KEY" ]; then echo "请先设置环境变量 TRAVEL_KEY（旅行页解锁密码），例如：export TRAVEL_KEY='...'"; exit 1; fi
echo "[travel] 清理旧密文残留 ..."; rm -rf public/img/travel
echo "[travel] 构建 public/ ..."; hugo --gc >/dev/null
echo "[travel] AES 加密 ..."; TRAVEL_KEY="$TRAVEL_KEY" node scripts/encrypt_travel.mjs
echo "[travel] 拷贝密文到 travel-dist/ ..."; mkdir -p travel-dist/img
cp -f public/travel.html travel-dist/travel.html
rm -rf travel-dist/img/travel; cp -R public/img/travel travel-dist/img/travel
echo "[travel] 完成。请执行：git add travel-dist && git commit -m 'chore(travel): 重新生成密文' && git push"
