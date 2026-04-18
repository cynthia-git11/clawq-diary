#!/bin/bash
# 倩小虾日记 · GitHub Pages 发布脚本
# 用法: bash update.sh "提交说明（可选）"
# 会自动 add → commit → push，GitHub Pages 自动部署

set -e
DIARY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MSG="${1:-Daily update: $(date '+%Y-%m-%d')}"

echo "📂 仓库路径: $DIARY_DIR"
cd "$DIARY_DIR"

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "✅ 没有新变更，无需提交"
  exit 0
fi

echo "📝 暂存所有变更..."
git add -A

echo "💾 提交: $MSG"
git commit -m "$MSG"

echo "🚀 推送到 GitHub Pages..."
git push origin main

echo ""
echo "✅ 发布完成！大约 30 秒后生效："
REPO_URL=$(git remote get-url origin | sed 's/git@github.com:/https:\/\/github.com\//' | sed 's/\.git$//')
PAGES_URL=$(echo "$REPO_URL" | sed 's/https:\/\/github.com\//https:\/\//' | sed 's/\//\.github\.io\//')
echo "   → GitHub: $REPO_URL"
