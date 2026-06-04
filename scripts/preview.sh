#!/usr/bin/env bash
# 啟動本機控制台並開啟瀏覽器預覽（Cursor Simple Browser 請用此 URL）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${SITESPIDER_PORT:-8765}"
HOST="${SITESPIDER_HOST:-127.0.0.1}"
URL="http://${HOST}:${PORT}/"

health() {
  curl -sf --connect-timeout 2 "${URL}api/info" >/dev/null 2>&1
}

if ! health; then
  echo "啟動 SiteSpider 控制台（${HOST}:${PORT}）…"
  nohup bash "$ROOT/scripts/dev-ui.sh" >>"$ROOT/.sitespider-dev-ui.log" 2>&1 &
  for _ in $(seq 1 40); do
    if health; then
      break
    fi
    sleep 0.25
  done
fi

if ! health; then
  echo "預覽失敗：無法連線 ${URL}" >&2
  echo "" >&2
  echo "請檢查：" >&2
  echo "  1. 在終端機執行：cd \"$ROOT\" && bash scripts/dev-ui.sh" >&2
  echo "  2. 看到「SiteSpider 控制台：http://…」後，用瀏覽器開該網址" >&2
  echo "  3. 勿用 Finder 雙擊 reports/*.html（file:// 無法回爬取中心）" >&2
  echo "  4. 若 .venv 不存在：python3 -m venv .venv && .venv/bin/pip install -e ." >&2
  if [[ -f "$ROOT/.sitespider-dev-ui.log" ]]; then
    echo "" >&2
    echo "最近啟動日誌（末尾）：" >&2
    tail -n 15 "$ROOT/.sitespider-dev-ui.log" >&2 || true
  fi
  exit 1
fi

echo "控制台就緒：${URL}"
echo "範例報告：${URL}demo"
echo "圖片稽核：${URL}reports/123deal-smoke/images-gallery.html"
echo "（Cursor 內建預覽請貼上以上網址，勿用 file://）"
if command -v open >/dev/null 2>&1; then
  open "$URL"
fi
