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


def _cell_color(count: int, max_c: int) -> str:
    if count <= 0:
        return "#10141c"
    t = min(1.0, count / max(max_c, 1))
    r = int(16 + (110 - 16) * t)
    g = int(20 + (201 - 20) * t)
    b = int(28 + (160 - 28) * t)
    return f"rgb({r},{g},{b})"


def _cell_fg(count: int, max_c: int) -> str:
    if count <= 0:
        return "#8b95a8"
    t = min(1.0, count / max(max_c, 1))
    return "#0a1812" if t > 0.5 else "#f4f2ec"


def export_issue_heatmap_html(
    report: CrawlReport,
    path: Path,
    *,
    branding: Branding | None = None,
    prefix_depth: int = 2,
) -> None:
    brand = branding or Branding()
    css = report_styles_bundle()
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
            bg = _cell_color(n, max_cell)
            fg = _cell_fg(n, max_cell)
            cells += f'<td style="background:{bg};color:{fg};text-align:center;font-family:var(--font-mono);font-size:11px">{n or ""}</td>'
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
      <span><i class="heatmap-swatch" style="background:#10141c"></i> 無問題</span>
      <span><i class="heatmap-swatch" style="background:#2a7d5a"></i> 中等</span>
      <span><i class="heatmap-swatch" style="background:#6ec9a0"></i> 較多</span>
    </div>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
