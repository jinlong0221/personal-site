#!/usr/bin/env bash
# make_web_video.sh —— 把手机/录屏视频压成适合网站内嵌播放的规格。
#
# 为什么需要它：站内视频必须同时满足「能在网页里播」和「不把仓库和首屏拖垮」，
# 手机原片（1080p、十几 MB 起步）两条都不满足。本脚本一次搞定：
#   ① H.264 + yuv420p + faststart（所有浏览器都能播，且支持边下边播）
#   ② 720p 上限 + 目标码率上限，体积可控
#   ③ 抽一帧做封面（poster），避免视频区域出现黑屏
#
# 用法：
#   bash scripts/make_web_video.sh <输入视频> [输出名] [目标体积MB]
# 例：
#   bash scripts/make_web_video.sh ~/Movies/aaa123.mp4 aaa123 8
#
# 产物：
#   static/media/<输出名>.mp4     视频（建议 ≤ 8MB）
#   static/img/media/<输出名>-poster.jpg   封面（宽 1280）

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-}"
NAME="${2:-}"
TARGET_MB="${3:-8}"

if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then
  echo "用法：bash scripts/make_web_video.sh <输入视频> [输出名] [目标体积MB]" >&2
  exit 1
fi

# ffmpeg 可能在 Homebrew / miniconda / 系统路径
FFMPEG="$(command -v ffmpeg || true)"
if [ -z "$FFMPEG" ]; then
  for c in /Users/chenjinlong/miniconda3/bin/ffmpeg /opt/homebrew/bin/ffmpeg /usr/local/bin/ffmpeg; do
    [ -x "$c" ] && FFMPEG="$c" && break
  done
fi
if [ -z "$FFMPEG" ]; then
  echo "找不到 ffmpeg，请先装：brew install ffmpeg" >&2
  exit 1
fi

[ -n "$NAME" ] || NAME="$(basename "${SRC%.*}")"
OUT_DIR="$ROOT/static/media"
POSTER_DIR="$ROOT/static/img/media"
mkdir -p "$OUT_DIR" "$POSTER_DIR"
OUT="$OUT_DIR/$NAME.mp4"
POSTER="$POSTER_DIR/$NAME-poster.jpg"

# ---- 源信息（ffmpeg 纯探测时退出码非 0，必须 || true 兜住）----
SRC_SIZE=$(du -m "$SRC" 2>/dev/null | cut -f1 || true)
PROBE=$("$FFMPEG" -i "$SRC" 2>&1 || true)
DUR=$(printf '%s' "$PROBE" | grep -o 'Duration: [0-9:.]*' | head -1 | sed 's/Duration: //' || true)
[ -n "$DUR" ] || DUR="未知"
echo "源文件：$SRC"
echo "  体积：${SRC_SIZE} MB    时长：${DUR}"

# ---- 目标码率（留 8% 余量给音频与容器）----
SECS=$(printf '%s' "$DUR" | awk -F: '{if (NF>=2) printf "%.0f", $NF+0; else print 0}' 2>/dev/null || echo 0)
case "$SECS" in ''|*[!0-9]*) SECS=0 ;; esac
if [ "$SECS" -gt 0 ] 2>/dev/null; then
  V_KBPS=$(( TARGET_MB * 920 / SECS ))
  [ "$V_KBPS" -lt 120 ] && V_KBPS=120
  MAXRATE="${V_KBPS}k"
  BUFSIZE=$(( V_KBPS * 2 ))k
  echo "  目标：${TARGET_MB}MB / ${SECS}s → 视频码率上限 ${V_KBPS} kbps"
else
  V_KBPS=1200; MAXRATE="1400k"; BUFSIZE="2800k"
  echo "  读不到时长，回退到 1400 kbps"
fi

# ---- 压视频 ----
"$FFMPEG" -y -i "$SRC" \
  -vf "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,fps=30" \
  -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p \
  -b:v "$MAXRATE" -maxrate "$MAXRATE" -bufsize "$BUFSIZE" \
  -preset veryslow -crf 27 -g 60 \
  -c:a aac -b:a 96k -ac 2 -ar 44100 \
  -movflags +faststart -shortest \
  "$OUT" 2>&1 | tail -3 || true

# ---- 抽封面（取第 3 秒，失败则取第 1 秒）----
if ! "$FFMPEG" -y -ss 3 -i "$OUT" -frames:v 1 -vf "scale=1280:-2" -q:v 4 "$POSTER" 2>/dev/null; then
  "$FFMPEG" -y -ss 1 -i "$OUT" -frames:v 1 -vf "scale=1280:-2" -q:v 4 "$POSTER" 2>/dev/null || true
fi

NEW_SIZE=$(du -m "$OUT" | cut -f1)
NEW_KB=$(du -k "$OUT" | cut -f1)
echo "完成："
echo "  视频 → $OUT （${NEW_SIZE} MB / ${NEW_KB} KB）"
[ -f "$POSTER" ] && echo "  封面 → $POSTER"
if [ "${NEW_SIZE}" -gt "$TARGET_MB" ]; then
  echo "⚠️ 仍超 ${TARGET_MB}MB，建议再压：把目标调小，或用更短的文件"
fi
echo
echo "页面里这样用："
cat <<HTML
<div class="lx-video">
  <video controls preload="none" poster="/img/media/${NAME}-poster.jpg" playsinline>
    <source src="/media/${NAME}.mp4" type="video/mp4">
    你的浏览器不支持内嵌视频，可<a href="/media/${NAME}.mp4">点此下载观看</a>。
  </video>
</div>
HTML
