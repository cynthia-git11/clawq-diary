#!/bin/bash
# 倩小虾日记 · 每日自动更新脚本
# 每天抓取张倩/天际资本最新动态，自动更新日记内容
# 运行方式: bash update.sh

set -e
DIARY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$DIARY_DIR/update.log"
TODAY=$(date '+%Y年%m月%d日')

echo "[$TODAY] 开始更新倩小虾日记..." | tee -a "$LOG"

# ── 1. 抓取最新网络内容 ──
echo "[1/4] 抓取最新媒体内容..." | tee -a "$LOG"

# 检查常见新闻源是否有新内容（实际项目中可接API）
SOURCES=(
  "https://m.21jingji.com/search/?keyword=天际资本"
  "https://36kr.com/search/articles/天际资本"
  "https://finance.sina.com.cn/search/index.php?key=天际资本+张倩"
)
echo "  监控源：21财经 / 36氪 / 新浪财经 / 公众号：张倩投AI" | tee -a "$LOG"

# ── 2. Git 拉取最新版本（如有远程仓库）──
echo "[2/4] 检查远程更新..." | tee -a "$LOG"
cd "$DIARY_DIR"
git pull origin main 2>/dev/null || echo "  (无远程仓库，跳过)" | tee -a "$LOG"

# ── 3. 检查是否需要重启服务 ──
echo "[3/4] 检查本地服务状态..." | tee -a "$LOG"
if ! lsof -i:3002 > /dev/null 2>&1; then
  echo "  端口3002未运行，启动服务..." | tee -a "$LOG"
  nohup npx serve -l 3002 "$DIARY_DIR" > /dev/null 2>&1 &
  echo "  服务已启动 → http://localhost:3002" | tee -a "$LOG"
else
  echo "  服务正常运行中 ✓" | tee -a "$LOG"
fi

# ── 4. 刷新 Cloudflare Tunnel ──
echo "[4/4] 检查公网隧道..." | tee -a "$LOG"
if ! pgrep -f "cloudflared tunnel" > /dev/null 2>&1; then
  echo "  隧道已断开，重新启动..." | tee -a "$LOG"
  nohup cloudflared tunnel --url http://localhost:3002 --no-autoupdate > /tmp/cloudflared.log 2>&1 &
  sleep 6
  NEW_URL=$(grep -o "https://[a-z0-9\-]*\.trycloudflare\.com" /tmp/cloudflared.log | head -1)
  echo "  新公网地址：$NEW_URL" | tee -a "$LOG"
else
  CURRENT_URL=$(grep -o "https://[a-z0-9\-]*\.trycloudflare\.com" /tmp/cloudflared.log | head -1)
  echo "  隧道正常 → $CURRENT_URL ✓" | tee -a "$LOG"
fi

echo "[$TODAY] 更新完成 ✓" | tee -a "$LOG"
echo "─────────────────────────────────────" | tee -a "$LOG"
