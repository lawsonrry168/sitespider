"""
產生 HTML / CSV / JSON 報告（類 Screaming Frog 匯出）。
"""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

from sitespider.crawler import CrawlReport, discover_html_files, report_to_dict

ISSUE_LABELS = {
    "missing_title": "缺少 title",
    "title_too_long": "title 超過 60 字元",
    "title_too_short": "title 少於 10 字元",
    "missing_meta_description": "缺少 meta description",
    "meta_description_too_long": "meta description 超過 160 字元",
    "missing_h1": "缺少 H1",
    "multiple_h1": "多個 H1",
    "broken_image": "圖片連結失效",
    "missing_alt": "圖片缺少 alt",
    "http_error": "HTTP 錯誤",
    "orphan_page": "孤立頁（無內部連入）",
    "duplicate_title": "重複 title",
    "blocked_by_robots": "robots.txt 封鎖",
    "meta_noindex": "meta noindex",
    "lighthouse_seo_low": "Lighthouse SEO < 90",
    "lighthouse_perf_low": "Lighthouse 效能 < 50",
    "missing_og_tags": "缺少 Open Graph",
    "missing_json_ld": "缺少 JSON-LD",
}


def export_json(report: CrawlReport, path: Path) -> None:
    path.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_csv_pages(report: CrawlReport, path: Path) -> None:
    fields = [
        "url",
        "status",
        "title",
        "meta_description",
        "h1_count",
        "h1_text",
        "h2_count",
        "h3_count",
        "word_count",
        "images",
        "internal_links_out",
        "inlinks_count",
        "depth",
        "seed_source",
        "blocked_by_robots",
        "og_title",
        "json_ld_types",
        "lh_performance",
        "lh_accessibility",
        "lh_seo",
        "lh_best_practices",
        "issues",
        "response_ms",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            lh = p.lighthouse
            w.writerow(
                {
                    "url": url,
                    "status": p.status,
                    "title": p.title or "",
                    "meta_description": (p.meta_description or "")[:200],
                    "h1_count": len(p.h1),
                    "h1_text": " | ".join(p.h1)[:300],
                    "h2_count": len(p.h2),
                    "h3_count": len(p.h3),
                    "word_count": p.word_count,
                    "images": len(p.images),
                    "internal_links_out": sum(
                        1 for l in p.links if l.link_type == "internal"
                    ),
                    "inlinks_count": len(p.inlinks),
                    "depth": p.crawl_depth,
                    "seed_source": p.seed_source,
                    "blocked_by_robots": p.blocked_by_robots,
                    "og_title": (p.og_title or "")[:80],
                    "json_ld_types": "; ".join(p.json_ld_types),
                    "lh_performance": lh.performance if lh else "",
                    "lh_accessibility": lh.accessibility if lh else "",
                    "lh_seo": lh.seo if lh else "",
                    "lh_best_practices": lh.best_practices if lh else "",
                    "issues": "; ".join(p.issues),
                    "response_ms": round(p.response_ms, 1),
                }
            )


def export_csv_lighthouse(report: CrawlReport, path: Path) -> None:
    fields = ["url", "performance", "accessibility", "best_practices", "seo", "error"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, data in sorted(report.lighthouse.items()):
            w.writerow(
                {
                    "url": url,
                    "performance": data.get("performance", ""),
                    "accessibility": data.get("accessibility", ""),
                    "best_practices": data.get("best_practices", ""),
                    "seo": data.get("seo", ""),
                    "error": data.get("error", ""),
                }
            )
        for url, p in sorted(report.pages.items()):
            if url in report.lighthouse or not p.lighthouse:
                continue
            lh = p.lighthouse
            w.writerow(
                {
                    "url": url,
                    "performance": lh.performance or "",
                    "accessibility": lh.accessibility or "",
                    "best_practices": lh.best_practices or "",
                    "seo": lh.seo or "",
                    "error": lh.error or "",
                }
            )


def export_csv_links(report: CrawlReport, path: Path) -> None:
    fields = ["source_url", "href", "resolved", "anchor_text", "type", "status", "issue"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for page_url, p in sorted(report.pages.items()):
            for link in p.links:
                w.writerow(
                    {
                        "source_url": page_url,
                        "href": link.href,
                        "resolved": link.resolved,
                        "anchor_text": link.text,
                        "type": link.link_type,
                        "status": link.status or "",
                        "issue": link.issue or "",
                    }
                )


def export_csv_images(report: CrawlReport, path: Path) -> None:
    fields = ["source_url", "src", "resolved", "alt", "status", "issue"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for page_url, p in sorted(report.pages.items()):
            for img in p.images:
                w.writerow(
                    {
                        "source_url": page_url,
                        "src": img.src,
                        "resolved": img.resolved,
                        "alt": img.alt or "",
                        "status": img.status or "",
                        "issue": img.issue or "",
                    }
                )


def export_csv_blocked(report: CrawlReport, path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in report.blocked_urls:
            w.writerow([u])


def export_html(report: CrawlReport, path: Path, site_root: Path | None = None) -> None:
    issues = report.summary_issues()
    pages = sorted(report.pages.items(), key=lambda x: x[0])
    duration = (report.finished_at or 0) - report.started_at
    cfg = report.config
    all_html = discover_html_files(site_root) if site_root else []

    crawled_names = {Path(urlparse_path(url)).name for url in report.pages}
    uncrawled = [f for f in all_html if f not in crawled_names]

    rows = []
    for url, p in pages:
        issue_badges = "".join(
            f'<span class="badge badge-warn">{escape(ISSUE_LABELS.get(i, i))}</span>'
            for i in p.issues
        )
        lh = p.lighthouse
        lh_cell = "—"
        if lh and lh.seo is not None:
            lh_cell = f"P{lh.performance or '—'} A{lh.accessibility or '—'} SEO{lh.seo}"
        rows.append(
            f"""<tr>
              <td><code>{escape(short_url(url))}</code></td>
              <td>{p.status}</td>
              <td>{p.crawl_depth}</td>
              <td>{escape(p.seed_source)}</td>
              <td>{escape((p.title or '—')[:40])}</td>
              <td>{escape(p.h1[0][:50]) if p.h1 else '—'}</td>
              <td>{len(p.inlinks)}</td>
              <td>{lh_cell}</td>
              <td>{issue_badges or '<span class="badge badge-ok">OK</span>'}</td>
            </tr>"""
        )

    issue_section = ""
    for key, urls in sorted(issues.items(), key=lambda x: -len(x[1])):
        label = ISSUE_LABELS.get(key, key)
        issue_section += f"<h3>{escape(label)} ({len(set(urls))})</h3><ul>"
        for u in sorted(set(urls))[:30]:
            issue_section += f"<li><code>{escape(short_url(u))}</code></li>"
        issue_section += "</ul>"

    robots_section = f"""
    <p><strong>來源：</strong><code>{escape(str(report.robots_info.get('source', '')))}</code></p>
    <p><strong>Crawl-delay：</strong>{report.robots_info.get('crawl_delay') or '無'}</p>
    <p><strong>Disallow：</strong>{', '.join(report.robots_info.get('disallowed', [])) or '無'}</p>
    <p><strong>封鎖 URL 數：</strong>{len(report.blocked_urls)}</p>
    """

    sitemap_section = "<ul>" + "".join(
        f"<li><code>{escape(short_url(u))}</code></li>" for u in report.sitemap_urls[:20]
    ) + "</ul>" if report.sitemap_urls else "<p>未使用或未找到 sitemap</p>"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEO Crawl 報告</title>
  <style>
    :root {{ font-family: "Noto Sans TC", system-ui, sans-serif; --bg: #0f1419; --card: #1a2332; --text: #e7ecf3; --muted: #8b9cb3; --accent: #3dd6a0; --warn: #f0b429; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); padding: 1.5rem; line-height: 1.5; }}
    h1 {{ font-size: 1.4rem; }}
    .meta {{ color: var(--muted); font-size: 0.9rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.75rem; margin: 1rem 0; }}
    .stat {{ background: var(--card); padding: 0.75rem; border-radius: 8px; }}
    .stat strong {{ display: block; font-size: 1.4rem; color: var(--accent); }}
    section {{ background: var(--card); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid #2a3548; }}
    .badge {{ display: inline-block; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.7rem; margin: 0.05rem; }}
    .badge-ok {{ background: #1e3d32; color: var(--accent); }}
    .badge-warn {{ background: #3d3419; color: var(--warn); }}
    code {{ font-size: 0.78rem; }}
  </style>
</head>
<body>
  <h1>SEO 爬取報告</h1>
  <p class="meta">
    模式 {report.mode} · 深度 ≤{cfg.max_depth} · 並行 {cfg.workers} ·
    robots {'✓' if cfg.respect_robots else '✗'} · sitemap {'✓' if cfg.use_sitemap else '✗'} ·
    {duration:.2f}s · {len(report.pages)} 頁
  </p>
  <div class="grid">
    <div class="stat"><strong>{len(report.pages)}</strong><span>已爬取</span></div>
    <div class="stat"><strong>{len(report.blocked_urls)}</strong><span>robots 封鎖</span></div>
    <div class="stat"><strong>{len(report.sitemap_urls)}</strong><span>sitemap 種子</span></div>
    <div class="stat"><strong>{len(report.lighthouse)}</strong><span>Lighthouse</span></div>
  </div>
  <section><h2>robots.txt</h2>{robots_section}</section>
  <section><h2>sitemap.xml 種子</h2>{sitemap_section}</section>
  <section><h2>問題摘要</h2>{issue_section or '<p>無</p>'}</section>
  {"<section><h2>未爬取到的 HTML</h2><ul>" + "".join(f"<li><code>{escape(f)}</code></li>" for f in uncrawled) + "</ul></section>" if uncrawled else ""}
  <section>
    <h2>所有頁面</h2>
    <table>
      <thead><tr>
        <th>URL</th><th>狀態</th><th>深度</th><th>來源</th><th>Title</th><th>H1</th><th>連入</th><th>Lighthouse</th><th>問題</th>
      </tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </section>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")


def urlparse_path(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).path or url


def short_url(url: str) -> str:
    if len(url) > 55:
        return "…" + url[-50:]
    return url


def write_all_reports(report: CrawlReport, out_dir: Path, site_root: Path | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    export_json(report, out_dir / "crawl-report.json")
    export_csv_pages(report, out_dir / "pages.csv")
    export_csv_links(report, out_dir / "links.csv")
    export_csv_images(report, out_dir / "images.csv")
    export_csv_blocked(report, out_dir / "blocked.csv")
    export_csv_lighthouse(report, out_dir / "lighthouse.csv")
    export_html(report, out_dir / "index.html", site_root=site_root)
