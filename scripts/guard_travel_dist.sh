#!/usr/bin/env bash
# guard_travel_dist.sh — 旅行板块部署前防御闸（key-free，CI 可跑，无需 TRAVEL_KEY）
#
# 目的：堵死「陈旧/误提交的明文 travel.html 被照常部署上线、导致私照泄露或 hero 裂图」的根因。
#   CI 是 key-free 部署（不持有 TRAVEL_KEY，无法解密校验），故本闸只做「无需密钥即可判断」的
#   明文/完整性检查：
#     1. travel-dist/travel.html 不存在 → 放行（部署步骤会跳过旅行页）；
#     2. 含 data-tl-wrap → 明文源未加密，禁止上线（会泄露私照）；
#     3. 含明文照片引用 src/href="img/travel/...webp" → 禁止上线；
#     4. 缺 noindex 或密码门 tlGate → 不是有效加密外壳，禁止上线；
#     5. travel-dist/img/travel 混入明文照片（webp/jpg/...）→ 禁止上线；
#     6. travel-dist/img/travel 无 album-*.tlpk 分片 → 禁止上线。
#   全部通过才放行；任一不过则非零退出，CI 构建失败、阻断部署。
#
# 用法：bash scripts/guard_travel_dist.sh [travel-dist/travel.html]
set -e
SHELL_FILE="${1:-travel-dist/travel.html}"
IMG_DIR="$(dirname "$SHELL_FILE")/img/travel"

echo "[travel-guard] 校验旅行密文产物（无需密钥）..."

if [ ! -f "$SHELL_FILE" ]; then
  echo "[travel-guard] ✅ 未提供 travel-dist/travel.html，跳过（部署步骤将跳过旅行页）"
  exit 0
fi

# 2. 明文源标记（未加密的私密正文，含 data-tl-wrap）
if grep -q 'data-tl-wrap' "$SHELL_FILE"; then
  echo "❌ [travel-guard] travel-dist/travel.html 仍是明文源（含 data-tl-wrap）——线上将泄露私照！"
  echo "   请本地用 TRAVEL_KEY 跑：bash scripts/rebuild_travel_dist.sh  重生成后再提交。"
  exit 1
fi

# 3. 明文照片引用（未加密的 img/href 指向 img/travel/*.webp）
if grep -Eq 'img/travel/[^"'"'"' ]+\.(webp|jpg|jpeg|png|avif|gif)' "$SHELL_FILE"; then
  echo "❌ [travel-guard] travel-dist/travel.html 仍含明文照片引用（img/travel/*.webp），禁止上线。"
  exit 1
fi

# 4. 有效加密外壳必备标记
if ! grep -q 'name="robots" content="noindex"' "$SHELL_FILE"; then
  echo "❌ [travel-guard] 缺少 <meta name=robots content=noindex>，非完整加密外壳。"
  exit 1
fi
if ! grep -q 'tlGate' "$SHELL_FILE"; then
  echo "❌ [travel-guard] 缺少密码门 tlGate，非加密外壳。"
  exit 1
fi

# 5. 分片目录不得混入明文照片
if [ -d "$IMG_DIR" ]; then
  plains=$(find "$IMG_DIR" -type f \( -iname '*.webp' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.gif' \) 2>/dev/null || true)
  if [ -n "$plains" ]; then
    echo "❌ [travel-guard] travel-dist/img/travel 含明文照片，禁止上线："
    echo "$plains" | sed 's#^#     - #'
    exit 1
  fi
  # 6. 必须存在 album-*.tlpk 分片
  tlps=$(find "$IMG_DIR" -type f -name 'album-*.tlpk' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$tlps" -eq 0 ]; then
    echo "❌ [travel-guard] travel-dist/img/travel 无 album-*.tlpk 分片，禁止上线。"
    exit 1
  fi
  echo "[travel-guard] ✅ 分片目录干净：album-*.tlpk 共 ${tlps} 片，无明文照片残留"
else
  echo "❌ [travel-guard] travel-dist/img/travel 目录缺失，无法部署相册。"
  exit 1
fi

echo "[travel-guard] ✅ 旅行密文产物校验通过（无明文、含密码门/noindex、分片完整），允许部署。"
