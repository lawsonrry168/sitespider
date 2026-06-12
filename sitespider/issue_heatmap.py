"""依 URL 路徑前綴的問題熱力圖（靜態 HTML）。"""

from __future__ import annotations

from collections import defaultdict
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from sitespider.branding import Branding
from sitespider.issues import ISSUE_LABELS
from sitespider.report_theme import REPORT_MAIN_OPEN, report_styles_bundle, report_topbar

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def _path_prefix(url: str, depth: int = 2) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    if not parts:
        return "/"
    return "/" + "/".join(parts[:depth]) + "/"


def build_prefix_issue_matrix(report: CrawlReport, *, prefix_depth: int = 2) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    page_counts: dict[str, int] = defaultdict(int)
    for url, page in report.pages.items():
        if page.status != 200:
            continue
        prefix = _path_prefix(url, prefix_depth)
        page_counts[prefix] += 1
        for issue in page.issues or []:
            matrix[prefix][issue] += 1
    return {p: dict(matrix[p]) for p in sorted(matrix.keys(), key=lambda x: (-page_counts[x], x))}


def _cell_class(count: int, max_c: int) -> str:
    """CSS class heat levels — colors from analytics-theme-overrides.css."""
    if count <= 0:
        return "heat-cell heat-empty"
    t = min(1.0, count / max(max_c, 1))
    if t < 0.35:
        return "heat-cell heat-low"
    if t < 0.7:
        return "heat-cell heat-mid"
    return "heat-cell heat-high"


def export_issue_heatmap_html(
    report: CrawlReport,
    path: Path,
    *,
    branding: Branding | None = None,
    prefix_depth: int = 2,
) -> None:
    brand = branding or Branding()
    from sitespider.report_theme import load_ui_css

    css = (
        report_styles_bundle()
        + "\n"
        + load_ui_css("analytics-theme-overrides.css")
    )
    matrix = build_prefix_issue_matrix(report, prefix_depth=prefix_depth)
    all_issues: set[str] = set()
    for issues in matrix.values():
        all_issues |= set(issues.keys())
    issue_cols = sorted(all_issues, key=lambda k: -sum(matrix[p].get(k, 0) for p in matrix))

    max_cell = max((v for row in matrix.values() for v in row.values()), default=1)
    header = "".join(
        f"<th title='{escape(k)}'>{escape(ISSUE_LABELS.get(k, k)[:18])}</th>"
        for k in issue_cols[:20]
    )
    body_rows = ""
    for prefix, issues in list(matrix.items())[:40]:
        cells = ""
        for k in issue_cols[:20]:
            n = issues.get(k, 0)
            cls = _cell_class(n, max_cell)
            cells += (
                f'<td class="{cls}" '
                f'style="text-align:center;font-family:var(--font-mono);font-size:11px">'
                f"{n or ''}</td>"
            )
        body_rows += f"<tr><td><code>{escape(prefix)}</code></td>{cells}</tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>問題熱力圖 — {escape(report.start_url)}</title>
  <style>
{css}
  </style>
</head>
<body>
  {report_topbar(path.parent, "熱力圖", active="issue_heatmap.html", site_url=report.start_url)}
  {REPORT_MAIN_OPEN}
    {brand.html_header()}
    <h1>路徑前綴問題熱力圖</h1>
    <p class="lead">依 URL 前 {prefix_depth} 段路徑統計各類問題。顏色越亮（若竹綠）問題越多。</p>
    <div class="card" style="overflow-x:auto">
      <table class="data">
        <tr><th>路徑前綴</th>{header}</tr>
        {body_rows}
      </table>
    </div>
    <div class="heatmap-legend">
      <span><i class="heatmap-swatch"></i> 無問題</span>
      <span><i class="heatmap-swatch"></i> 中等</span>
      <span><i class="heatmap-swatch"></i> 較多</span>
    </div>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
