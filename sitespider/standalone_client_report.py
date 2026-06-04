"""
單一 HTML 客戶報告 — 可離線開啟、不需本機伺服器。

含健康分、主要問題、優先頁面與 AI 文案摘要；互動圖表仍請用 ZIP 內多檔 HTML。
"""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sitespider.branding import Branding
from sitespider.issues import ISSUE_LABELS
from sitespider.report_theme import load_ui_css, report_styles_bundle

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

STANDALONE_FILENAME = "client-report.html"


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _priority_rows(report_dir: Path, limit: int = 20) -> list[dict[str, str]]:
    csv_path = report_dir / "priority_pages.csv"
    if not csv_path.is_file():
        return []
    rows: list[dict[str, str]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append({k: str(v or "") for k, v in row.items()})
            if len(rows) >= limit:
                break
    return rows


def _issues_section(report: CrawlReport) -> str:
    issues = report.summary_issues()
    top = sorted(issues.items(), key=lambda x: -len(x[1]))[:12]
    if not top:
        return "<p>未偵測到常見問題類型。</p>"
    lis = "".join(
        f"<li>{escape(ISSUE_LABELS.get(k, k))} — <strong>{len(v)}</strong> 頁</li>"
        for k, v in top
    )
    return f"<ul>{lis}</ul>"


def _priority_table(report_dir: Path) -> str:
    rows = _priority_rows(report_dir)
    if not rows:
        return "<p class=\"meta\">見 priority_pages.csv</p>"
    head = rows[0].keys()
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = ""
    for row in rows:
        tds = "".join(f"<td>{escape(row.get(h, ''))}</td>" for h in head)
        body += f"<tr>{tds}</tr>"
    return (
        '<div class="card" style="overflow-x:auto">'
        f'<table class="data"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'
        "</div>"
    )


def _ai_section(report_dir: Path) -> str:
    meta = _load_json(report_dir / "ai-polish-meta.json") or {}
    copies = _load_json(report_dir / "ai-page-copy.json")
    if not meta and not copies:
        return (
            "<p class=\"meta\">本次未含 AI 文案。顧問可在爬取中心執行「產生 AI 文案」後重新匯出。</p>"
        )
    parts: list[str] = []
    if meta:
        prov = escape(str(meta.get("provider_name") or meta.get("provider_id") or ""))
        model = escape(str(meta.get("model") or ""))
        errs = meta.get("errors") or []
        parts.append(
            f"<p class=\"meta\">AI 平台 <code>{prov}</code> · 模型 <code>{model}</code></p>"
        )
        if errs:
            parts.append(
                "<p class=\"meta\" style=\"color:var(--color-danger,#c45c5c)\">"
                + escape("; ".join(str(e) for e in errs[:4]))
                + "</p>"
            )
    if isinstance(copies, list) and copies:
        lis = ""
        for item in copies[:8]:
            if not isinstance(item, dict):
                continue
            url = escape(str(item.get("url") or ""))
            titles = item.get("titles") or []
            t0 = titles[0].get("text", "") if titles and isinstance(titles[0], dict) else ""
            metas = item.get("metas") or []
            m0 = metas[0].get("text", "") if metas and isinstance(metas[0], dict) else ""
            lis += (
                f"<li><strong>{url}</strong><br>"
                f"Title：{escape(str(t0)[:80])}<br>"
                f"Meta：{escape(str(m0)[:120])}</li>"
            )
        parts.append(f"<ul>{lis}</ul>")
        parts.append(
            '<p class="meta">完整 AI 交付（FAQ、llms.txt）請開啟同資料夾內 '
            '<code>ai-hub.html</code>（ZIP 交付包內亦有）。</p>'
        )
    return "\n".join(parts)


def _zip_companion_note(report_dir: Path) -> str:
    extras = []
    for name in (
        "REPORT-zh.html",
        "dashboard.html",
        "index.html",
        "link_graph.html",
        "images-gallery.html",
        "seo-briefs.html",
        "ai-hub.html",
    ):
        if (report_dir / name).is_file():
            extras.append(name)
    if not extras:
        return ""
    lis = "".join(f"<li><code>{escape(n)}</code></li>" for n in extras)
    return f"""<h2 id="full-pack">完整互動報告（同資料夾 / ZIP）</h2>
    <p class="lead">本檔為<strong>單檔精簡版</strong>，方便 email 傳送與離線閱讀摘要。
    圖表、內鏈圖、逐頁檢視請在解壓後的資料夾中雙擊下列 HTML：</p>
    <ul>{lis}</ul>"""


def export_standalone_client_html(
    report_dir: Path,
    path: Path | None = None,
    *,
    report: CrawlReport | None = None,
    site_label: str | None = None,
    branding: Branding | None = None,
) -> Path:
    """產生單一 HTML 客戶報告。"""
    from sitespider.report_load import load_report_json

    report_dir = report_dir.resolve()
    out = path or (report_dir / STANDALONE_FILENAME)
    if report is None:
        crawl = report_dir / "crawl-report.json"
        if not crawl.is_file():
            raise FileNotFoundError(f"找不到 crawl-report.json：{report_dir}")
        report = load_report_json(crawl)

    from sitespider.report_analytics import compute_analytics

    brand = branding or Branding()
    data = compute_analytics(report, site_label=site_label)
    label = escape(str(data.get("site_label", report.start_url)))
    score = int(data.get("health_score") or 0)
    ring_cls = " danger" if score < 40 else (" warn" if score < 70 else "")
    css = report_styles_bundle() + load_ui_css("comfort-display.css")

    actions = data.get("actions") or []
    action_html = "".join(
        f"<li><strong>{escape(a.get('title', ''))}</strong> — "
        f"{escape((a.get('body') or '')[:140])}</li>"
        for a in actions[:6]
    ) or "<li>見 actions.csv</li>"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEO 客戶報告 — {label}</title>
  <style>
{css}
.standalone-toc {{ display:flex; flex-wrap:wrap; gap:0.5rem; margin:1rem 0; }}
.standalone-toc a {{ padding:0.35rem 0.75rem; border-radius:6px; background:var(--surface-2,#f0f4f8);
  text-decoration:none; font-size:0.9rem; }}
  </style>
</head>
<body>
  <a class="skip-link report-skip" href="#main-content">跳至主要內容</a>
  <main class="report-main" id="main-content">
    {brand.html_header()}
    <div class="readme-hero">
      <div class="health-ring-lg{ring_cls}">{score}</div>
      <div>
        <h1>{label}</h1>
        <p class="lead">{escape(str(data.get("health_grade_label", "")))}</p>
        <p class="meta">{escape(str(data.get("generated_at", "")))} · {escape(report.start_url)}</p>
        <div class="stat-row">
          <span class="stat-chip">{data.get("url_count", 0)} 頁</span>
          <span class="stat-chip">{data.get("duration_sec", 0)}s</span>
          <span class="stat-chip">可索引 {data.get("indexable", 0)}</span>
        </div>
      </div>
    </div>
    <nav class="standalone-toc" aria-label="章節">
      <a href="#issues">主要問題</a>
      <a href="#actions">建議動作</a>
      <a href="#priority">優先頁面</a>
      <a href="#ai">AI 文案摘要</a>
      <a href="#full-pack">完整報告檔案</a>
    </nav>
    <h2 id="issues">主要問題</h2>
    <div class="card">{_issues_section(report)}</div>
    <h2 id="actions">建議動作</h2>
    <div class="card"><ul>{action_html}</ul></div>
    <h2 id="priority">優先處理頁面（前 20 筆）</h2>
    {_priority_table(report_dir)}
    <h2 id="ai">AI 文案摘要</h2>
    <div class="card">{_ai_section(report_dir)}</div>
    {_zip_companion_note(report_dir)}
    <p class="meta report-footnote" style="margin-top:2rem">
      由 SiteSpider 產生 · 單檔離線版 <code>{escape(STANDALONE_FILENAME)}</code>
      · 無需 Google 帳號即可閱讀站內稽核摘要
    </p>
  </main>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out
