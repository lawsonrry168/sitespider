"""一頁交付摘要（可列印 HTML + 可選 PDF）。"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import TYPE_CHECKING

from sitespider.branding import Branding
from sitespider.report_theme import REPORT_MAIN_OPEN, load_ui_css, report_styles_bundle, report_topbar

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def export_delivery_summary_html(
    report: CrawlReport,
    path: Path,
    *,
    site_label: str | None = None,
    branding: Branding | None = None,
) -> None:
    from sitespider.report_analytics import compute_analytics
    from sitespider.issues import ISSUE_LABELS

    brand = branding or Branding()
    data = compute_analytics(report, site_label=site_label)
    css = report_styles_bundle() + load_ui_css("comfort-display.css")
    issues = report.summary_issues()
    top = sorted(issues.items(), key=lambda x: -len(x[1]))[:8]
    issue_lines = "".join(
        f"<li>{escape(ISSUE_LABELS.get(k, k))} — <strong>{len(v)}</strong> 頁</li>"
        for k, v in top
    )
    actions = data.get("actions") or []
    action_html = "".join(
        f"<li><strong>{escape(a.get('title', ''))}</strong> — {escape((a.get('body') or '')[:100])}</li>"
        for a in actions[:5]
    )
    label = escape(str(data.get("site_label", report.start_url)))

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEO 摘要 — {label}</title>
  <style>
{css}
  </style>
</head>
<body>
  {report_topbar(path.parent, "一頁摘要", active="delivery-summary.html", site_url=report.start_url)}
  {REPORT_MAIN_OPEN}
    {brand.html_header()}
    <h1>{label}</h1>
    <p class="meta">產生：{escape(str(data.get('generated_at', '')))} · {data.get('url_count', 0)} 頁 · {data.get('duration_sec', 0)} 秒</p>
    <p class="score-hero">{data.get('health_score', 0)}<span style="font-size:1rem;color:var(--muted)"> / 100</span></p>
    <p class="lead">{escape(str(data.get('health_grade_label', '')))}</p>
    <div class="card">
      <h2>主要問題</h2>
      <ul>{issue_lines or '<li>未偵測到常見問題</li>'}</ul>
    </div>
    <div class="card" style="margin-top:1rem">
      <h2>建議動作</h2>
      <ul>{action_html or '<li>見 priority_summary.md</li>'}</ul>
    </div>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def export_delivery_pdf(
    report: CrawlReport,
    path: Path,
    *,
    site_label: str | None = None,
    branding: Branding | None = None,
) -> bool:
    """需 pip install fpdf2；失敗時回傳 False。"""
    try:
        from fpdf import FPDF
    except ImportError:
        return False

    from sitespider.report_analytics import compute_analytics
    from sitespider.issues import ISSUE_LABELS

    brand = branding or Branding()
    data = compute_analytics(report, site_label=site_label)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    title = str(data.get("site_label", report.start_url))[:80]
    pdf.cell(0, 10, title, ln=True)
    if brand.consultant_name:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Prepared by: {brand.consultant_name[:60]}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Pages: {data.get('url_count', 0)}  |  Health: {data.get('health_score', 0)}/100", ln=True)
    pdf.cell(0, 7, str(data.get("health_grade_label", ""))[:80], ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top issues", ln=True)
    pdf.set_font("Helvetica", "", 10)
    issues = report.summary_issues()
    for key, urls in sorted(issues.items(), key=lambda x: -len(x[1]))[:10]:
        label = ISSUE_LABELS.get(key, key)[:50]
        pdf.cell(0, 6, f"- {label}: {len(urls)} URLs", ln=True)
    try:
        pdf.output(str(path))
        return True
    except OSError:
        return False
