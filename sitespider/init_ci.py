"""產生 GitHub Actions 工作流程範本。"""

from __future__ import annotations

from pathlib import Path

WORKFLOW = """name: SiteSpider SEO

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  seo-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install SiteSpider
        run: pip install -e ".[excel,yaml]"

      - name: Run crawl
        run: |
          sitespider --mode file --root {site_root} \\
            -o reports/current \\
            --fail-on-issues

      - name: Compare with baseline (optional)
        continue-on-error: true
        run: |
          if [ -f reports/baseline/crawl-report.json ]; then
            sitespider compare reports/baseline/crawl-report.json reports/current/crawl-report.json \\
              --fail-on-new -o reports/compare.md || true
          fi

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: seo-reports
          path: reports/
"""


def write_github_workflow(path: Path, *, site_root: str = ".") -> Path:
    """寫入 workflows/sitespider.yml；site_root 為爬取根目錄（相對於 repo）。"""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = WORKFLOW.format(site_root=site_root)
    path.write_text(content, encoding="utf-8")
    return path
