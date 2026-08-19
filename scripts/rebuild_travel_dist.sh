#!/usr/bin/env bash
# 重新生成旅行板块密文产物（travel-dist/），用于更新旅行内容后重新上线。
# 前置：
#   - 明文源已就位：static/travel.html、static/img/travel/*.webp、static/data/travel.json
#     （这些文件已被 .gitignore 忽略，仅本地/私有仓库持有，绝不入公开仓库）
#   - 环境变量 TRAVEL_KEY 已设置（与家人共享的解锁密码）
# 产物：travel-dist/travel.html + travel-dist/img/travel/album.tlpk.enc（单包密文，可安全提交公开仓库）
# 单包架构（2026-08-19）：全部照片打包为一个 album.tlpk.enc，浏览器解锁时 1 次请求全量加载，
# 根除“逐张 .enc 偶发连接超时导致个别照片永久缺图”的历史问题。
set -e
cd "$(dirname "$0")/.."
require() { command -v "$1" >/dev/null 2>&1 || { echo "缺少命令：$1"; exit 1; }; }
require hugo; require node
if [ -z "$TRAVEL_KEY" ]; then echo "请先设置环境变量 TRAVEL_KEY（旅行页解锁密码），例如：export TRAVEL_KEY='...'"; exit 1; fi
echo "[travel] 清理旧密文残留 ..."; rm -rf public/img/travel
echo "[travel] 构建 public/ ..."; hugo --gc >/dev/null
echo "[travel] AES 加密（单包 album.tlpk.enc）..."; TRAVEL_KEY="$TRAVEL_KEY" node scripts/encrypt_travel.mjs
echo "[travel] 拷贝密文到 travel-dist/ ..."; mkdir -p travel-dist/img
cp -f public/travel.html travel-dist/travel.html
rm -rf travel-dist/img/travel; cp -R public/img/travel travel-dist/img/travel
echo "[travel] 校验产物（解密外壳 BLOB + 相册包自洽性）..."
node scripts/verify_travel_dist.mjs || { echo "[travel] ❌ 产物校验失败，请排查后再提交！"; exit 1; }
echo "[travel] 完成。请执行：git add travel-dist scripts && git commit -m 'chore(travel): 重新生成密文' && git push"
