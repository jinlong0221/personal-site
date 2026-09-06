#!/bin/sh
# 安装仓库版本化的 git hooks。
#
# 背景（2026-09-06）：pre-commit 护栏此前只存在于 .git/hooks/ 里，而 .git/ 是不进
# 版本库的——换台机器克隆、或重装环境，护栏就悄无声息地没了，而且是「提交照样成功」
# 那种没。所以把钩子放进 .githooks/ 纳入版本管理，用 core.hooksPath 指过去。
#
# 用法（仓库根目录执行）：
#     sh scripts/install_hooks.sh
#
# 说明：core.hooksPath 是仓库本地配置（写入 .git/config），不进版本库，
#       所以每台机器克隆后都需跑一次本脚本。
set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if [ ! -f .githooks/pre-commit ]; then
  echo "❌ 找不到 .githooks/pre-commit，钩子未安装"
  exit 1
fi

chmod +x .githooks/pre-commit 2>/dev/null || true

git config core.hooksPath .githooks

echo "✅ git hooks 已指向 .githooks（受版本管理）"
echo "   当前 core.hooksPath = $(git config core.hooksPath)"
echo "   已安装: $(ls .githooks)"
