#!/usr/bin/env bash
# 清除 SiteSpider 本機開發快取（不刪 reports/、.sitespider/ 任務與設定）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

removed=0
prune() {
  while IFS= read -r -d '' p; do
    rm -rf "$p"
    echo "  removed $p"
    removed=$((removed + 1))
  done
}

echo "Cleaning Python / test caches under $ROOT …"
find . -path './.git' -prune -o -type d -name '__pycache__' -print0 | prune
find . -path './.git' -prune -o -type d \( \
  -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' -o \
  -name '.hypothesis' -o -name '.tox' -o -name 'htmlcov' \
\) -print0 | prune
find . -path './.git' -prune -o -type f -name '*.py[co]' -print0 | while IFS= read -r -d '' f; do
  rm -f "$f"
  echo "  removed $f"
  removed=$((removed + 1))
done

for d in build dist sitespider.egg-info .eggs; do
  if [[ -e "$d" ]]; then
    rm -rf "$d"
    echo "  removed $d/"
    removed=$((removed + 1))
  fi
done

echo "Done ($removed item(s))."
echo "Tip: 瀏覽器請 Cmd+Shift+R 硬重新整理；若 dev server 在跑，請重啟 bash scripts/dev-ui.sh"
