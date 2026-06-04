#!/usr/bin/env bash
# 建置 macOS 本機版（需先：pip install "sitespider[desktop]" 或 pip install pyinstaller）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "請先建立虛擬環境：python3 -m venv .venv && .venv/bin/pip install -e '.[desktop]'" >&2
  exit 1
fi

.venv/bin/pip install -q -e ".[desktop]"
.venv/bin/pyinstaller --noconfirm --clean packaging/sitespider-desktop.spec

OUT="$ROOT/dist/SiteSpider"
if [[ -x "$OUT" ]]; then
  echo ""
  echo "建置完成：$OUT"
  echo "執行：\"$OUT\"  或雙擊（終端機會保持開啟）"
  echo "報告預設：~/Library/Application Support/SiteSpider/reports/"
else
  echo "找不到輸出，請檢查 dist/ 目錄。" >&2
  exit 1
fi
