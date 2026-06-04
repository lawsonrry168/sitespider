"""
產生 HTML / CSV / JSON 報告（類 Screaming Frog 匯出）。
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

from sitespider.crawler import CrawlReport, discover_html_files, report_to_dict
from sitespider.indexability import compute_indexability
from sitespider.issues import ISSUE_LABELS


def export_csv_llms(report: CrawlReport, path: Path) -> None:
    fields = ["name", "url", "status", "bytes", "error"]
    info = report.llms_info or {}
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for name in ("llms.txt", "llms-full.txt"):
            row = info.get(name) or {}
            w.writerow(
                {
                    "name": name,
                    "url": row.get("url") or "",
                    "status": row.get("status") or "",
                    "bytes": row.get("bytes") or "",
                    "error": row.get("error") or "",
                }
            )


def export_csv_actions(report: CrawlReport, path: Path) -> None:
    from sitespider.report_analytics import compute_analytics

    data = compute_analytics(report)
    actions = data.get("actions") or []
    fields = ["priority", "title", "body"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for a in actions:
            w.writerow(
                {
                    "priority": a.get("level") or "",
                    "title": a.get("title") or "",
                    "body": (a.get("body") or "")[:800],
                }
            )


def _sf_row(url: str, p) -> dict:
    title = p.title or ""
    meta = p.meta_description or ""
    idx = getattr(p, "indexability", None) or compute_indexability(p)[0]
    idx_status = getattr(p, "indexability_status", None)
    if idx_status is None:
        idx_status = compute_indexability(p)[1]
    return {
        "Address": url,
        "Content Type": p.content_type or "",
        "Status Code": p.status,
        "Indexability": idx,
        "Indexability Status": idx_status,
        "Title 1": title,
        "Title 1 Length": len(title),
        "Meta Description 1": meta,
        "Meta Description 1 Length": len(meta),
        "H1-1": p.h1[0] if p.h1 else "",
        "H1-1 Length": len(p.h1[0]) if p.h1 else 0,
        "Canonical Link Element 1": p.canonical or "",
        "Crawl Depth": p.crawl_depth,
        "Inlinks": len(p.inlinks),
        "Response Time (ms)": round(p.response_ms, 1),
    }


SF_INTERNAL_FIELDS = [
    "Address",
    "Content Type",
    "Status Code",
    "Indexability",
    "Indexability Status",
    "Title 1",
    "Title 1 Length",
    "Meta Description 1",
    "Meta Description 1 Length",
    "H1-1",
    "H1-1 Length",
    "Canonical Link Element 1",
    "Crawl Depth",
    "Inlinks",
    "Response Time (ms)",
]


def export_csv_internal(report: CrawlReport, path: Path) -> None:
    """Screaming Frog Internal 分頁風格 CSV。"""
    fields = SF_INTERNAL_FIELDS
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(_sf_row(url, p))


def export_csv_response_codes(report: CrawlReport, path: Path) -> None:
    """Screaming Frog Response Codes 分頁風格。"""
    fields = ["Address", "Status Code", "Status", "Indexability", "Content Type", "Inlinks"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            code = p.status
            status = "OK" if code == 200 else ("Error" if code >= 400 else str(code))
            w.writerow(
                {
                    "Address": url,
                    "Status Code": code,
                    "Status": status,
                    "Indexability": p.indexability,
                    "Content Type": (p.content_type or "")[:40],
                    "Inlinks": len(p.inlinks),
                }
            )


def export_csv_page_titles(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Title 1",
        "Title 1 Length",
        "Title 1 Pixel Width",
        "Indexability",
        "Occurrences",
    ]
    title_urls: dict[str, list[str]] = {}
    for url, p in report.pages.items():
        if p.title:
            title_urls.setdefault(p.title.strip(), []).append(url)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            title = p.title or ""
            occ = len(title_urls.get(title.strip(), [])) if title else 0
            w.writerow(
                {
                    "Address": url,
                    "Title 1": title,
                    "Title 1 Length": len(title),
                    "Title 1 Pixel Width": p.serp_title_pixels,
                    "Indexability": p.indexability,
                    "Occurrences": occ if title else "",
                }
            )


def export_csv_h1(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "H1-1", "H1-1 Length", "H1-2", "Indexability"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "H1-1": p.h1[0] if p.h1 else "",
                    "H1-1 Length": len(p.h1[0]) if p.h1 else 0,
                    "H1-2": p.h1[1] if len(p.h1) > 1 else "",
                    "Indexability": p.indexability,
                }
            )


def export_csv_canonicals(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Canonical Link Element 1", "Indexability", "Indexability Status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "Canonical Link Element 1": p.canonical or "",
                    "Indexability": p.indexability,
                    "Indexability Status": p.indexability_status,
                }
            )


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
        "canonical",
        "html_lang",
        "has_viewport",
        "redirect_hops",
        "redirect_chain",
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
                    "canonical": p.canonical or "",
                    "html_lang": p.html_lang or "",
                    "has_viewport": p.has_viewport,
                    "redirect_hops": max(0, len(p.redirect_chain) - 1),
                    "redirect_chain": " → ".join(p.redirect_chain)[:500],
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


def export_csv_issues(report: CrawlReport, path: Path) -> None:
    fields = ["issue", "issue_label", "url", "status", "depth"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            for issue in sorted(set(p.issues)):
                w.writerow(
                    {
                        "issue": issue,
                        "issue_label": ISSUE_LABELS.get(issue, issue),
                        "url": url,
                        "status": p.status,
                        "depth": p.crawl_depth,
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
    fields = [
        "source_url",
        "href",
        "resolved",
        "anchor_text",
        "type",
        "status",
        "follow",
        "link_position",
        "issue",
    ]
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
                        "follow": "Nofollow" if link.nofollow else "Follow",
                        "link_position": link.link_position,
                        "issue": link.issue or "",
                    }
                )


def export_csv_images(report: CrawlReport, path: Path) -> None:
    fields = [
        "source_url",
        "src",
        "resolved",
        "alt",
        "width",
        "height",
        "loading",
        "status",
        "content_type",
        "byte_size",
        "local_file",
        "issue",
    ]
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
                        "width": img.width if img.width is not None else "",
                        "height": img.height if img.height is not None else "",
                        "loading": img.loading or "",
                        "status": img.status or "",
                        "content_type": img.content_type or "",
                        "byte_size": img.byte_size if img.byte_size is not None else "",
                        "local_file": img.local_file or "",
                        "issue": img.issue or "",
                    }
                )


def export_csv_redirects(report: CrawlReport, path: Path) -> None:
    fields = ["final_url", "request_url", "hops", "chain", "status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            if len(p.redirect_chain) <= 1:
                continue
            w.writerow(
                {
                    "final_url": url,
                    "request_url": p.request_url or "",
                    "hops": len(p.redirect_chain) - 1,
                    "chain": " → ".join(p.redirect_chain),
                    "status": p.status,
                }
            )


def export_csv_blocked(report: CrawlReport, path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in report.blocked_urls:
            w.writerow([u])


def compute_chart_data(report: CrawlReport) -> dict:
    depth_counts: Counter[int] = Counter()
    status_counts: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()

    for p in report.pages.values():
        depth_counts[p.crawl_depth] += 1
        key = str(p.status) if p.status else "0"
        status_counts[key] += 1
        for issue in set(p.issues):
            issue_counts[issue] += 1

    return {
        "depth": {str(k): v for k, v in sorted(depth_counts.items())},
        "status": dict(status_counts.most_common()),
        "issues": {
            k: issue_counts[k]
            for k, _ in sorted(issue_counts.items(), key=lambda x: -x[1])
        },
    }


def _bar_chart(title: str, data: dict[str, int], *, max_bars: int = 12) -> str:
    if not data:
        return f"<p class='muted'>無 {escape(title)} 資料</p>"
    items = list(data.items())[:max_bars]
    peak = max(items, key=lambda x: x[1])[1] or 1
    bars = []
    for label, count in items:
        pct = round(100 * count / peak)
        bars.append(
            f"""<div class="bar-row">
              <span class="bar-label">{escape(str(label))}</span>
              <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
              <span class="bar-val">{count}</span>
            </div>"""
        )
    return f"<h3>{escape(title)}</h3><div class='bar-chart'>{''.join(bars)}</div>"


def export_html(report: CrawlReport, path: Path, site_root: Path | None = None) -> None:
    issues = report.summary_issues()
    pages = sorted(report.pages.items(), key=lambda x: x[0])
    duration = (report.finished_at or 0) - report.started_at
    cfg = report.config
    all_html = discover_html_files(site_root) if site_root else []
    charts = compute_chart_data(report)

    idx_counts: Counter[str] = Counter()
    idx_status_counts: Counter[str] = Counter()
    for p in report.pages.values():
        idx_counts[p.indexability] += 1
        if p.indexability_status:
            idx_status_counts[p.indexability_status] += 1

    crawled_names = {Path(urlparse_path(url)).name for url in report.pages}
    uncrawled = [f for f in all_html if f not in crawled_names]

    from sitespider.link_metrics import compute_page_link_stats
    from sitespider.report_theme import load_ui_css, report_topbar

    link_stats = compute_page_link_stats(report)
    out_dir = path.parent
    from sitespider.report_theme import report_styles_bundle

    index_css = load_ui_css("index-report.css") + "\n" + report_styles_bundle()
    topbar = report_topbar(
        out_dir,
        "站內技術報告",
        active="index.html",
        site_url=report.start_url,
        meta_line=f"已完成 {len(report.pages)} 個 URL · {duration:.1f}s",
    )
    internal_rows = []
    canonical_rows = []
    title_rows = []
    for url, p in pages:
        idx_cls = "idx-no" if p.indexability == "Non-Indexable" else "idx-yes"
        st = link_stats.get(url)
        score = st.link_score if st else 0
        internal_rows.append(
            f"""<tr data-idx="{escape(p.indexability)}">
              <td class="addr"><a href="{escape(url)}" target="_blank" rel="noopener">{escape(short_url(url))}</a></td>
              <td>{escape((p.content_type or '')[:30])}</td>
              <td>{p.status}</td>
              <td class="{idx_cls}">{escape(p.indexability)}</td>
              <td>{escape(p.indexability_status or '—')}</td>
              <td>{escape((p.title or '—')[:50])}</td>
              <td>{len(p.title or '')}</td>
              <td>{len(p.inlinks)}</td>
              <td>{score}</td>
            </tr>"""
        )
        if p.canonical or p.indexability_status == "Canonicalised":
            canonical_rows.append(
                f"""<tr>
                  <td class="addr">{escape(short_url(url))}</td>
                  <td>{escape(p.canonical or '—')}</td>
                  <td class="{idx_cls}">{escape(p.indexability_status or p.indexability)}</td>
                </tr>"""
            )
        if p.title:
            title_rows.append(
                f"""<tr>
                  <td class="addr">{escape(short_url(url))}</td>
                  <td>{escape(p.title[:80])}</td>
                  <td>{len(p.title)}</td>
                  <td>{escape(p.indexability)}</td>
                </tr>"""
            )

    response_rows = []
    for url, p in pages:
        code = p.status
        status = "OK" if code == 200 else ("Error" if code >= 400 else str(code))
        response_rows.append(
            f"""<tr>
              <td class="addr">{escape(short_url(url))}</td>
              <td>{code}</td>
              <td>{escape(status)}</td>
              <td>{escape(p.indexability)}</td>
            </tr>"""
        )

    external_rows = []
    for page_url, p in pages:
        for link in p.links:
            if link.link_type != "external":
                continue
            external_rows.append(
                f"""<tr>
                  <td class="addr">{escape(short_url(page_url))}</td>
                  <td class="addr"><a href="{escape(link.resolved)}" target="_blank" rel="noopener">{escape(short_url(link.resolved))}</a></td>
                  <td>{escape(link.text[:60])}</td>
                  <td>{link.status or '—'}</td>
                </tr>"""
            )
            if len(external_rows) >= 800:
                break
        if len(external_rows) >= 800:
            break

    security_rows = []
    for url, p in pages:
        sec = [i for i in p.issues if i in ("insecure_page", "mixed_content")]
        if not sec and p.is_https and not p.mixed_content_count:
            continue
        security_rows.append(
            f"""<tr>
              <td class="addr">{escape(short_url(url))}</td>
              <td>{'HTTPS' if p.is_https else 'HTTP'}</td>
              <td>{p.mixed_content_count}</td>
              <td>{escape('; '.join(sec) or '—')}</td>
            </tr>"""
        )

    h2_rows = []
    for url, p in pages:
        if not p.h2:
            continue
        h2_rows.append(
            f"""<tr>
              <td class="addr">{escape(short_url(url))}</td>
              <td>{escape(p.h2[0][:80])}</td>
              <td>{len(p.h2[0])}</td>
              <td>{escape(p.indexability)}</td>
            </tr>"""
        )

    sitemap_rows = []
    for u in report.sitemap_not_crawled[:100]:
        sitemap_rows.append(
            f'<tr><td class="addr">{escape(short_url(u))}</td><td>在 sitemap</td><td>未爬到</td></tr>'
        )
    for u in report.sitemap_not_in_sitemap[:100]:
        sitemap_rows.append(
            f'<tr><td class="addr">{escape(short_url(u))}</td><td>已爬到</td><td>不在 sitemap</td></tr>'
        )

    issue_rows = []
    for key, urls in sorted(issues.items(), key=lambda x: -len(x[1])):
        label = ISSUE_LABELS.get(key, key)
        for u in sorted(set(urls))[:50]:
            issue_rows.append(
                f"<tr><td>{escape(label)}</td><td class='addr'>{escape(short_url(u))}</td></tr>"
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

    charts_section = f"""
    <div class="charts-grid">
      <div>{_bar_chart("Indexability", dict(idx_counts))}</div>
      <div>{_bar_chart("Indexability Status", dict(idx_status_counts.most_common(8)))}</div>
      <div>{_bar_chart("HTTP 狀態碼", charts["status"])}</div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SiteSpider 報告 — {escape(report.start_url)}</title>
  <style>
{index_css}
  </style>
</head>
<body class="report-body report-index">
  {topbar}
  <p class="index-extra-meta">
    <a href="priority_summary.md">優先順序</a> ·
    匯出 <code>internal.csv</code> · <code>sitemap_generated.xml</code>
  </p>
  <div class="stats">
    <span><strong>{len(report.pages)}</strong> URLs</span>
    <span><strong>{idx_counts.get('Indexable', 0)}</strong> Indexable</span>
    <span><strong>{idx_counts.get('Non-Indexable', 0)}</strong> Non-Indexable</span>
    <span><strong>{idx_status_counts.get('Canonicalised', 0)}</strong> Canonicalised</span>
    <span><strong>{len(issues)}</strong> 問題類型</span>
  </div>
  <div class="tabs" role="tablist">
    <button type="button" class="active" data-tab="internal">Internal</button>
    <button type="button" data-tab="external">External</button>
    <button type="button" data-tab="security">Security</button>
    <button type="button" data-tab="canonicals">Canonicals</button>
    <button type="button" data-tab="titles">Titles</button>
    <button type="button" data-tab="h2">H2</button>
    <button type="button" data-tab="issues">Issues</button>
    <button type="button" data-tab="response">Response</button>
    <button type="button" data-tab="sitemap">Sitemap</button>
    <button type="button" data-tab="summary">Summary</button>
  </div>
  <input type="search" id="filter" placeholder="篩選 URL / Title…" aria-label="篩選">

  <div id="internal" class="panel active">
    <table id="tbl-internal">
      <thead><tr>
        <th>Address</th><th>Content Type</th><th>Status</th>
        <th>Indexability</th><th>Indexability Status</th>
        <th>Title 1</th><th>Len</th><th>Inlinks</th><th>Link Score</th>
      </tr></thead>
      <tbody>{"".join(internal_rows)}</tbody>
    </table>
  </div>
  <div id="external" class="panel">
    <p style="padding:0.5rem 1rem;color:var(--muted)">完整清單見 <code>external.csv</code></p>
    <table><thead><tr><th>Source</th><th>Destination</th><th>Anchor</th><th>Status</th></tr></thead>
    <tbody>{"".join(external_rows) or '<tr><td colspan="4">無外部連結</td></tr>'}</tbody></table>
  </div>
  <div id="security" class="panel">
    <p style="padding:0.5rem 1rem;color:var(--muted)">見 <code>security.csv</code></p>
    <table><thead><tr><th>Address</th><th>Scheme</th><th>Mixed</th><th>Issues</th></tr></thead>
    <tbody>{"".join(security_rows) or '<tr><td colspan="4">無安全問題</td></tr>'}</tbody></table>
  </div>
  <div id="canonicals" class="panel">
    <table><thead><tr><th>Address</th><th>Canonical</th><th>Status</th></tr></thead>
    <tbody>{"".join(canonical_rows) or '<tr><td colspan="3">無</td></tr>'}</tbody></table>
  </div>
  <div id="titles" class="panel">
    <table><thead><tr><th>Address</th><th>Title 1</th><th>Length</th><th>Indexability</th></tr></thead>
    <tbody>{"".join(title_rows)}</tbody></table>
  </div>
  <div id="h2" class="panel">
    <table><thead><tr><th>Address</th><th>H2-1</th><th>Len</th><th>Indexability</th></tr></thead>
    <tbody>{"".join(h2_rows) or '<tr><td colspan="4">無 H2</td></tr>'}</tbody></table>
  </div>
  <div id="sitemap" class="panel">
    <p style="padding:0.5rem 1rem">Sitemap URL 數：<strong>{len(report.sitemap_urls)}</strong> ·
    未爬到 <strong>{len(report.sitemap_not_crawled)}</strong> ·
    未在 sitemap <strong>{len(report.sitemap_not_in_sitemap)}</strong> · 見 <code>sitemap_diff.csv</code></p>
    <table><thead><tr><th>URL</th><th>狀態</th><th>說明</th></tr></thead>
    <tbody>{"".join(sitemap_rows) or '<tr><td colspan="3">無差異</td></tr>'}</tbody></table>
  </div>
  <div id="issues" class="panel">
    <table><thead><tr><th>Issue</th><th>URL</th></tr></thead>
    <tbody>{"".join(issue_rows) or '<tr><td colspan="2">無</td></tr>'}</tbody></table>
  </div>
  <div id="response" class="panel">
    <table><thead><tr><th>Address</th><th>Status Code</th><th>Status</th><th>Indexability</th></tr></thead>
    <tbody>{"".join(response_rows)}</tbody></table>
  </div>
  <div id="summary" class="panel">
    <div class="charts">{charts_section}
    <h3 style="padding:0 1rem">robots.txt</h3>{robots_section}
    <h3 style="padding:0 1rem">問題清單</h3>{issue_section or '<p style="padding:0 1rem">無</p>'}
    </div>
  </div>
  <script>
    document.querySelectorAll('.tabs button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
      }});
    }});
    document.getElementById('filter').addEventListener('input', e => {{
      const q = e.target.value.toLowerCase();
      document.querySelectorAll('#tbl-internal tbody tr').forEach(tr => {{
        tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
      }});
    }});
  </script>
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


def write_all_reports(
    report: CrawlReport,
    out_dir: Path,
    site_root: Path | None = None,
    *,
    export_xlsx: bool = False,
    client_report: bool = False,
    client_report_label: str | None = None,
    branding: object | None = None,
    plan_id: str | None = None,
    tenant_id: str = "default",
) -> list[str]:
    """寫入所有報告（Fast + Standard + Pro 三層）。"""
    from sitespider.report_tiers import ExportOptions, export_all_tiers

    opts = ExportOptions(
        site_root=site_root,
        export_xlsx=export_xlsx,
        client_report=client_report,
        client_report_label=client_report_label,
        branding=branding,
        plan_id=plan_id,
        tenant_id=tenant_id,
    )
    return export_all_tiers(report, out_dir, opts)
