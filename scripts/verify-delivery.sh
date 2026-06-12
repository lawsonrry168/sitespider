#!/usr/bin/env bash
# 驗證本機控制台與最新報告的交付功能（需 dev-ui 已啟動）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${SITESPIDER_PORT:-8765}"
BASE="http://127.0.0.1:${PORT}"

if ! curl -sf "${BASE}/api/info" >/dev/null; then
  echo "錯誤：控制台未啟動。請先執行：bash scripts/dev-ui.sh" >&2
  exit 1
fi

JOB="${1:-}"
if [[ -z "$JOB" ]]; then
  JOB="$(find reports/default -name crawl-report.json -print 2>/dev/null | head -1 | xargs dirname | xargs basename)"
fi
if [[ -z "$JOB" || ! -f "reports/default/${JOB}/crawl-report.json" ]]; then
  echo "錯誤：找不到報告任務目錄（用法：$0 [job_id]）" >&2
  exit 1
fi

echo "驗證任務：default/${JOB}"
fail=0
check() {
  local path="$1"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "${BASE}${path}")"
  if [[ "$code" == "200" ]]; then
    echo "  OK  ${code}  ${path}"
  else
    echo "  FAIL ${code}  ${path}" >&2
    fail=1
  fi
}

check "/reports/default/${JOB}/REPORT-zh.html"
check "/reports/default/${JOB}/seo-briefs.html"
check "/reports/default/${JOB}/delivery-summary.html"
check "/reports/default/${JOB}/dashboard.html"
check "/api/job/${JOB}/package.zip"

if [[ -f "reports/default/${JOB}/ai-hub.html" ]]; then
  check "/reports/default/${JOB}/ai-hub.html"
fi

echo ""
if [[ "$fail" -eq 0 ]]; then
  echo "全部通過。瀏覽器開啟：${BASE}/?desktop=1&job=${JOB}&step=3"
else
  echo "部分檢查失敗。"
  exit 1
fi
