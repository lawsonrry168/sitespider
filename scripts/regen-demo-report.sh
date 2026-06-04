#!/usr/bin/env bash
# 重新產生範例報告 reports/123deal-smoke（供 /demo 與 /reports/demo/ 預覽）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="reports/123deal-smoke"
mkdir -p "$OUT"
echo "爬取 123deal（最多 12 頁）→ $OUT"
.venv/bin/sitespider -c examples/123deal-sitespider.json --max-pages 12 -o "$OUT"
echo "完成。請開啟 http://127.0.0.1:8765/demo"
