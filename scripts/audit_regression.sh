#!/bin/sh
# audit_regression.sh — 一键跑完所有【自动化】审计回归项，并打印必须【人工复核】的清单。
#
# 背景（2026-09-19，龙兄定规）：
#   历次审计「这轮漏这个、下轮漏那个」，根因是没有把历史问题带着一起查。
#   本脚本 + scripts/AUDIT_REGRESSION.md 就是那个「带着一起查」的机制。
#
# 用法：
#   bash scripts/audit_regression.sh                  # 默认：只读源码级（无副作用、无误报）
#   bash scripts/audit_regression.sh --with-artifact  # 追加产物级（会先跑 unify_quotes --ci 自愈 + 构建到临时目录）
#
# 为什么默认不跑产物级：
#   ① 本地 public/ 常是陈旧产物 → 会得出过期结论（假警报）；
#   ② 产物审计要求先跑 unify_quotes（CI 就是这么排的），否则新闻 JSON 的引号残留会误报。
#   要本地也准，用 --with-artifact（它按 CI 顺序补上这两步）。
#
# 注意：全部通过 ≠ 审计完成。务必再看输出末尾的 C1–C6 人工清单（AUDIT_REGRESSION.md 第三节）。
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 1

WITH_ARTIFACT=0
for a in "$@"; do
  [ "$a" = "--with-artifact" ] && WITH_ARTIFACT=1
done

PY3=""
for c in python3 /usr/bin/python3 /Users/chenjinlong/.workbuddy/binaries/python/versions/3.13.12/bin/python3; do
  if command -v "$c" >/dev/null 2>&1; then PY3="$c"; break; fi
done
[ -z "$PY3" ] && PY3=python3

pass=0
fail=0
FAILED=""

run() {
  name="$1"; shift
  printf "  %-44s" "$name"
  if out="$("$@" 2>&1)"; then
    printf "PASS\n"
    pass=$((pass + 1))
  else
    printf "FAIL\n"
    fail=$((fail + 1))
    FAILED="$FAILED
     ✗ $name"
    printf '%s\n' "$out" | tail -14 | sed 's/^/        /'
  fi
}

note() {
  printf "  %-44sINFO\n" "$1"
  [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/        /'
}

echo "══════════════════════════════════════════════════════════════"
echo " 审计回归 · 自动化项"
echo "══════════════════════════════════════════════════════════════"
echo "[A] 源码守卫（与 CI 同一批，全只读）"
run "A2  overflow-x 安全 (sticky)"   "$PY3" scripts/guard_overflow.py
run "A3  主题变量作用域"             "$PY3" scripts/guard_theme_scope.py
run "A4  CSP 卫生"                   "$PY3" scripts/guard_csp_hygiene.py
run "A5  ?v 缓存版本一致"            "$PY3" scripts/guard_v_param.py
run "A6  编辑器注入元数据"           "$PY3" scripts/guard_editor_noise.py
run "A8  深色容器文字对比度"         "$PY3" scripts/guard_dark_container_text.py
run "A11 标题四字段一致"             "$PY3" scripts/sync_titles.py --check

# A12 只做「提示」不计入成败：新闻 JSON 的引号残留由 CI 的 unify_quotes --ci 自动清洗，
# 本地为「未收敛」状态属正常，不应算审计失败。
echo ""
echo "[A'] 提示项（CI 会自动清洗，不计成败）"
if uq="$("$PY3" scripts/unify_quotes.py --check 2>&1)"; then
  note "A12 引号统一（已收敛）"
else
  note "A12 引号待统一（CI 构建时会 unify_quotes --ci 清洗）" "$(printf '%s\n' "$uq" | tail -5)"
fi

echo ""
echo "[B] 源码审计"
[ -f scripts/audit_strict.py ] && run "B1  死链/缺图/薄弱页/断锚点" "$PY3" scripts/audit_strict.py

if [ "$WITH_ARTIFACT" = "1" ]; then
  echo ""
  echo "[C] 产物级（按 CI 顺序：unify_quotes 自愈 → 构建到临时目录 → 冒烟 + 骨架）"
  run "C0  引号自愈 (unify_quotes --ci)" "$PY3" scripts/unify_quotes.py --ci
  rm -rf /tmp/lx_audit_pub
  run "C0  构建 (hugo --gc --minify)"    hugo --gc --minify --baseURL "http://127.0.0.1:8932/" -d /tmp/lx_audit_pub
  run "A9  冒烟解析"                     "$PY3" scripts/smoke_test.py /tmp/lx_audit_pub
  run "B2  产物骨架/H1/页尾"             "$PY3" scripts/audit_live_artifact.py --root /tmp/lx_audit_pub
else
  echo ""
  echo "  (产物级未跑：加 --with-artifact 走完整 CI 镜像链；默认只跑只读源码项，避免陈旧 public/ 误报)"
fi

echo ""
echo "══════════════════════════════════════════════════════════════"
echo " 结果：PASS $pass / FAIL $fail"
[ -n "$FAILED" ] && echo " 未通过：$FAILED"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "⚠️  自动化只兜住「已机械化」的问题。以下必须人工过（详见 scripts/AUDIT_REGRESSION.md 第三节）:"
echo "     C1 双主题（浅色 + 深色）渲染复核 —— 深色容器里的标题/角标/徽章逐个看"
echo "     C2 浅色主题下金/浅强调色小字对比度（小字 ≥ 4.5:1，大字 ≥ 3:1）"
echo "     C3 脚本挂掉后内容是否全平铺（判可见性 getClientRects()，别数类名）"
echo "     C4 运行时注入组件的样式在 app.js，不在 style.css"
echo "     C5 移动端横向滚动（长/宽表格）"
echo "     C6 配图红线（禁 AI 图 / 保清晰度）"
echo ""
echo " 本轮若有新修的问题 → 必须补进 scripts/AUDIT_REGRESSION.md。"
echo ""

[ "$fail" -eq 0 ]
