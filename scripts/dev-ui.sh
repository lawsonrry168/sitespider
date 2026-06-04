#!/usr/bin/env bash
# 本機開發用：略過配額、預設 Pro 方案
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${SITESPIDER_PORT:-8765}"
HOST="${SITESPIDER_HOST:-127.0.0.1}"
URL="http://${HOST}:${PORT}/"

if lsof -ti ":$PORT" >/dev/null 2>&1; then
  echo "埠 ${PORT} 已被佔用，正在結束舊程序…" >&2
  lsof -ti ":$PORT" | xargs kill -9 2>/dev/null || true
  sleep 0.4
fi

export SITESPIDER_SKIP_QUOTA=1
export SITESPIDER_ALLOW_USAGE_RESET=1
export SITESPIDER_DEFAULT_PLAN=pro

RUNNER=""
if [[ -x ".venv/bin/sitespider" ]]; then
  RUNNER=".venv/bin/sitespider"
elif command -v sitespider >/dev/null 2>&1; then
  RUNNER="sitespider"
else
  echo "找不到 sitespider 指令。" >&2
  echo "請在專案目錄執行：" >&2
  echo "  python3 -m venv .venv" >&2
  echo "  .venv/bin/pip install -e ." >&2
  echo "  bash scripts/dev-ui.sh" >&2
  exit 1
fi

echo "SiteSpider 控制台啟動中…"
echo "  預覽：${URL}"
echo "  範例：${URL}demo"
echo "  說明：${URL}guide"
echo "  請用瀏覽器或 Cursor 簡易瀏覽器開啟以上網址（勿用 file:// 開 HTML）"
echo "  按 Ctrl+C 結束"
exec "$RUNNER" --ui --host "$HOST" --port "$PORT"
