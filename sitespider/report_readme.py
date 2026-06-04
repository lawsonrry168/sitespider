"""
客戶交付導覽 — REPORT-zh.md + REPORT-zh.html（GUI）。
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

from sitespider.delivery_manifest import DELIVERY_TILES  # noqa: F401 — re-export

FILE_ROWS = [
    ("全頁總覽", "internal.csv、pages.csv"),
    ("標題 / Meta / H1–H3", "page_titles.csv、meta_descriptions.csv、h1.csv …"),
    ("連結", "all_inlinks.csv、outlinks.csv、link_graph.html"),
    ("索引 / Canonical", "canonicals.csv、directives.csv"),
    ("內容重複", "duplicate_content.csv、content.csv"),
    ("圖片", "images.csv"),
    ("優先修復", "priority_pages.csv、actions.csv"),
    ("拼寫 / N-gram", "spelling.csv、ngrams.csv"),
    ("結構化資料", "structured_data.csv、rich_results.csv"),
    ("原始資料", "crawl-report.json"),
]


def _build_readme_context(
    report: CrawlReport,
    *,
    site_label: str | None = None,
    branding: object | None = None,
) -> dict[str, Any]:
    from sitespider.branding import Branding
    from sitespider.report_analytics import compute_analytics

    brand = branding if isinstance(branding, Branding) else Branding.from_dict(
        branding if isinstance(branding, dict) else None
    )
    data = compute_analytics(report, site_label=site_label)
    gsc_n = len(report.gsc_rich_inspections or {})
    gsc_cfg = getattr(report.config, "gsc_inspect_max", 0) or 0
    llms = report.llms_info or {}

    if gsc_n > 0:
        gsc_items = [
            f"已透過 Search Console API 檢查 {gsc_n} 個 URL → 見 rich_results_gsc.csv"
        ]
    elif gsc_cfg > 0:
        gsc_items = ["已設定 GSC 檢查但未取得結果（請確認 Search Console 資源與授權）"]
    else:
        gsc_items = [
            "未使用 Google Search Console（無客戶授權時屬正常）",
            "結構化資料請看 rich_results.csv（本機 JSON-LD 分析）",
            "若客戶日後提供 GSC，可在設定檔加入 gsc.inspect_max",
        ]

    llms_items = [
        f"{name}：HTTP {info.get('status', '?')}" for name, info in llms.items()
    ] or ["（未檢查 llms.txt）"]

    return {
        "brand": brand,
        "data": data,
        "gsc_items": gsc_items,
        "llms_items": llms_items,
        "actions": (data.get("actions") or [])[:5],
    }


def export_report_readme_md(
    report: CrawlReport,
    path: Path,
    *,
    site_label: str | None = None,
    branding: object | None = None,
) -> None:
    ctx = _build_readme_context(report, site_label=site_label, branding=branding)
    brand = ctx["brand"]
    data = ctx["data"]
    brand_line = f"**顧問**：{brand.consultant_name}  \n" if brand.consultant_name else ""
    action_lines = "\n".join(
        f"{i + 1}. **{a.get('title', '')}** — {a.get('body', '')[:120]}"
        for i, a in enumerate(ctx["actions"])
    )
    gsc_block = "\n".join(f"- {x}" for x in ctx["gsc_items"])
    llms_block = "\n".join(f"- `{x.split('：')[0]}`：{x.split('：', 1)[-1]}" if "：" in x else f"- {x}" for x in ctx["llms_items"])

    text = f"""# SiteSpider 報告導覽

{brand_line}**網站**：{data.get("site_label", report.start_url)}  
**起始 URL**：{report.start_url}  
**產生時間**：{data.get("generated_at", "")}  
**爬取**：{data.get("url_count", 0)} 頁 · {data.get("duration_sec", 0)} 秒  
**技術 SEO 健康分**：{data.get("health_score", 0)}/100（{data.get("health_grade_label", "")}）  
**可索引**：{data.get("indexable", 0)} 頁 · **不可索引**：{data.get("non_indexable", 0)} 頁  

---

## 建議閱讀順序（顧問 / 客戶）

1. **[delivery-summary.html](delivery-summary.html)** — 一頁摘要（可列印 / PDF）  
2. **[issue_heatmap.html](issue_heatmap.html)** — 依路徑前綴的問題熱力圖  
3. **[dashboard.html](dashboard.html)** — 圖表總覽、問題分佈、GEO、優先修復 URL  
4. **[seo-briefs.html](seo-briefs.html)** — SEO / GEO 文案 brief（Title / Meta / H1 建議）  
5. **[ai-hub.html](ai-hub.html)** — AI 文案交付（多平台；Title/Meta、FAQ、llms.txt；見 `ai-polish-meta.json`）  
6. **[priority_summary.md](priority_summary.md)** — Top 優先 URL + **7 日執行排程**  
7. **[index.html](index.html)** — SF 風格分頁表格（Internal / Titles / Issues…）  
8. **[link_graph.html](link_graph.html)** — 內鏈互動圖 · [簡易版](link_graph_simple.html)  
9. **[inspector.html](inspector.html)** — 單頁詳情與內鏈來源  

---

## 站級建議（摘要）

{action_lines or "（見 actions.csv）"}

---

## Google Search Console

{gsc_block}

---

## GEO / LLM

{llms_block}

- **SEO 文案 brief** → `seo-briefs.html` / `seo-briefs.md`（規則型）
- **AI 文案**（需 API key，支援 OpenAI / Claude / Gemini / DeepSeek 等 14 平台）→ `ai-hub.html`、`ai-page-copy.html`、`ai-faq.html`、`ai-faq-cms.html`、`llms.txt.draft`、`ai-polish-meta.json`

- 頁級 GEO 分數 → `geo.csv`

---

## 主要檔案對照（Screaming Frog 風格）

| 用途 | 檔案 |
|------|------|
| 全頁總覽 | `internal.csv`、`pages.csv` |
| 標題 / Meta / H1–H3 | `page_titles.csv`、`meta_descriptions.csv`、`h1.csv` … |
| 連結 | `all_inlinks.csv`、`outlinks.csv`、`link_graph.html` |
| 索引 / Canonical | `canonicals.csv`、`directives.csv` |
| 內容重複 | `duplicate_content.csv`、`content.csv` |
| 圖片 | `images.csv` |
| 優先修復 | `priority_pages.csv`、`actions.csv` |
| 拼寫 / N-gram | `spelling.csv`、`ngrams.csv` |
| 結構化資料 | `structured_data.csv`、`rich_results.csv` |
| 原始資料 | `crawl-report.json` |

---

## 修復後比對

```bash
sitespider --config your-config.json -o reports/after-fix
sitespider compare reports/before/crawl-report.json reports/after-fix/crawl-report.json
```

---

*由 SiteSpider 自動產生 · 無需 GSC 即可完成站內 SEO 稽核交付*
"""
    path.write_text(text, encoding="utf-8")


def export_report_readme_html(
    report: CrawlReport,
    path: Path,
    *,
    site_label: str | None = None,
    branding: object | None = None,
    out_dir: Path | None = None,
) -> None:
    """圖形化交付導覽（REPORT-zh.html）。"""
    from sitespider.report_theme import REPORT_MAIN_OPEN, load_ui_css, report_styles_bundle, report_topbar

    ctx = _build_readme_context(report, site_label=site_label, branding=branding)
    brand = ctx["brand"]
    data = ctx["data"]
    base = out_dir or path.parent

    score = int(data.get("health_score") or 0)
    ring_cls = ""
    if score < 40:
        ring_cls = " danger"
    elif score < 70:
        ring_cls = " warn"

    tiles_html = ""
    for fname, title, desc in DELIVERY_TILES:
        if not (base / fname).is_file():
            continue
        tiles_html += (
            f'<a class="delivery-tile" href="{escape(fname)}">'
            f"<strong>{escape(title)}</strong>"
            f"<span>{escape(desc)}</span>"
            f"<em>{escape(fname)}</em></a>"
        )

    actions_html = "".join(
        f"<li><strong>{escape(a.get('title', ''))}</strong> — "
        f"{escape((a.get('body') or '')[:120])}</li>"
        for a in ctx["actions"]
    ) or "<li>見 actions.csv</li>"

    gsc_html = "".join(f"<li>{escape(x)}</li>" for x in ctx["gsc_items"])
    llms_html = "".join(f"<li>{escape(x)}</li>" for x in ctx["llms_items"])

    table_html = "".join(
        f"<tr><td>{escape(use)}</td><td><code>{escape(files)}</code></td></tr>"
        for use, files in FILE_ROWS
    )

    label = escape(str(data.get("site_label", report.start_url)))
    css = report_styles_bundle() + load_ui_css("comfort-display.css")

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>交付導覽 — {label}</title>
  <style>
{css}
  </style>
</head>
<body>
  {report_topbar(out_dir or path.parent, "交付導覽", active="REPORT-zh.html", site_url=report.start_url)}
  {REPORT_MAIN_OPEN}
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
          <span class="stat-chip">不可索引 {data.get("non_indexable", 0)}</span>
        </div>
      </div>
    </div>

    <h2>交付入口</h2>
    <div class="delivery-grid">{tiles_html or '<p class="lead">匯出進行中…</p>'}</div>

    <h2>站級建議</h2>
    <div class="card"><ul>{actions_html}</ul></div>

    <h2>Google Search Console</h2>
    <div class="card"><ul>{gsc_html}</ul></div>

    <h2>GEO / LLM</h2>
    <div class="card">
      <ul>{llms_html}</ul>
      <p class="meta" style="margin-top:0.75rem">
        SEO brief → seo-briefs.html · AI 文案 → ai-hub.html · GEO 分數 → geo.csv
      </p>
    </div>

    <h2>主要檔案對照</h2>
    <div class="card" style="overflow-x:auto">
      <table class="data"><thead><tr><th>用途</th><th>檔案</th></tr></thead>
      <tbody>{table_html}</tbody></table>
    </div>

    <h2>修復後比對</h2>
    <div class="card"><pre class="meta" style="margin:0;white-space:pre-wrap">sitespider --config your-config.json -o reports/after-fix
sitespider compare reports/before/crawl-report.json reports/after-fix/crawl-report.json</pre></div>

    <p class="meta report-footnote">由 SiteSpider 自動產生 · 無需 GSC 即可完成站內 SEO 稽核交付</p>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
