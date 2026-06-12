"""
SEO 分析圖表儀表板 — dashboard.html
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from sitespider.crawler import CrawlReport
from sitespider.geo_audit import compute_geo_summary
from sitespider.issues import ISSUE_LABELS
from sitespider.priority import compute_priority_rows
from sitespider.report_theme import brand_mark_inline, load_ui_css, report_styles_bundle, report_topbar

_UI = Path(__file__).resolve().parent / "ui" / "analytics_dashboard.html"
_ANALYTICS_THEME = _UI.parent / "analytics-theme.css"

# 不計入「內容品質」懲罰的問題（多為 CMS 全站設定）
_CMS_WIDE = frozenset(
    {
        "canonical_mismatch",
        "missing_canonical",
        "missing_html_lang",
        "missing_og_tags",
    }
)

_HIGH = frozenset(
    {
        "canonical_mismatch",
        "missing_canonical",
        "http_error",
        "broken_internal_link",
        "meta_noindex",
        "blocked_by_robots",
    }
)


def _priority(issue: str) -> str:
    if issue in _HIGH:
        return "high"
    if issue in {
        "missing_title",
        "missing_meta_description",
        "missing_h1",
        "duplicate_title",
        "redirect_chain",
        "multiple_h1",
    }:
        return "medium"
    return "low"


def _grade(score: int) -> tuple[str, str]:
    if score >= 85:
        return "A", "優秀"
    if score >= 70:
        return "B", "良好"
    if score >= 55:
        return "C", "尚可"
    if score >= 40:
        return "D", "待改善"
    return "F", "需優先處理"


def compute_analytics(report: CrawlReport, *, site_label: str | None = None) -> dict:
    pages = list(report.pages.values())
    n = len(pages) or 1
    page_count = len(pages)

    idx = Counter(p.indexability for p in pages)
    idx_status = Counter(p.indexability_status for p in pages if p.indexability_status)
    status = Counter(str(p.status) for p in pages)

    issue_counts: Counter[str] = Counter()
    pages_with_any_issue = 0
    for p in pages:
        clean_issues = [i for i in set(p.issues) if not i.startswith("request_failed")]
        if clean_issues:
            pages_with_any_issue += 1
        for i in clean_issues:
            issue_counts[i] += 1

    issue_rows = []
    for key, count in issue_counts.most_common(25):
        issue_rows.append(
            {
                "key": key,
                "label": ISSUE_LABELS.get(key, key),
                "count": count,
                "pct": round(100 * count / n, 1),
                "priority": _priority(key),
            }
        )

    # 各問題範例 URL（供儀表板展開）
    issue_samples: dict[str, list[str]] = {}
    for key in issue_counts:
        sample = []
        for url, p in report.pages.items():
            if key in p.issues:
                sample.append(url)
            if len(sample) >= 5:
                break
        issue_samples[ISSUE_LABELS.get(key, key)] = sample[:5]

    link_pos = Counter()
    for p in pages:
        for link in p.links:
            if link.link_type == "internal":
                link_pos[link.link_position or "Content"] += 1
    link_position_order = ["Navigation", "Footer", "Header", "Aside", "Content"]

    depth = Counter(p.crawl_depth for p in pages)

    def bucket_counter(items, fn, order):
        c = Counter(fn(x) for x in items)
        return {k: c.get(k, 0) for k in order}

    title_order = ["缺少", "1–30", "31–60（理想）", "61–100", "100+"]
    meta_order = ["缺少", "<50", "50–160（理想）", "160+"]
    h1_order = ["0", "1（理想）", "2+"]
    inlink_order = ["0（孤立風險）", "1–3", "4–10", "10+"]
    word_order = ["<100", "100–299", "300–599", "600+"]

    def title_bucket(p):
        L = len(p.title or "")
        if L == 0:
            return "缺少"
        if L <= 30:
            return "1–30"
        if L <= 60:
            return "31–60（理想）"
        if L <= 100:
            return "61–100"
        return "100+"

    def meta_bucket(p):
        L = len(p.meta_description or "")
        if L == 0:
            return "缺少"
        if L < 50:
            return "<50"
        if L <= 160:
            return "50–160（理想）"
        return "160+"

    indexable = idx.get("Indexable", 0)
    non_indexable = idx.get("Non-Indexable", 0)
    ok_200 = sum(1 for p in pages if p.status == 200)
    error_pages = sum(1 for p in pages if p.status >= 400)
    canon = idx_status.get("Canonicalised", 0)
    n404 = status.get("404", 0)
    status_ok_pct = round(100 * ok_200 / n, 1)

    # 技術 SEO 健康分（與 Indexable 分開；canonical 屬 CMS 設定）
    no_high = sum(1 for p in pages if not any(i in _HIGH for i in p.issues))
    has_core_meta = sum(
        1 for p in pages if p.title and p.meta_description and p.h1 and p.status == 200
    )
    content_issues_pages = sum(
        1
        for p in pages
        if not any(i for i in p.issues if i not in _CMS_WIDE and not i.startswith("request_failed"))
    )

    score_http = round(35 * ok_200 / n)
    score_content = round(35 * content_issues_pages / n)
    score_critical = round(30 * no_high / n)
    health = min(100, score_http + score_content + score_critical)

    grade, grade_label = _grade(health)

    lh_pages = [p for p in pages if p.lighthouse and p.lighthouse.seo is not None]
    lh_data = None
    if lh_pages:
        lh_data = {
            "labels": ["效能", "無障礙", "最佳實踐", "SEO"],
            "perf": round(sum(p.lighthouse.performance or 0 for p in lh_pages) / len(lh_pages), 1),
            "a11y": round(sum(p.lighthouse.accessibility or 0 for p in lh_pages) / len(lh_pages), 1),
            "bp": round(sum(p.lighthouse.best_practices or 0 for p in lh_pages) / len(lh_pages), 1),
            "seo": round(sum(p.lighthouse.seo or 0 for p in lh_pages) / len(lh_pages), 1),
            "count": len(lh_pages),
        }

    resp_times = [p.response_ms for p in pages if p.response_ms > 0]
    host = urlparse(report.start_url).netloc or report.start_url

    actions = _build_actions(canon, n404, issue_counts, n)
    geo = compute_geo_summary(report)
    llms = report.llms_info or {}
    priority_pages = [
        {
            "url": r.url,
            "score": r.score,
            "segment": r.segment,
            "money_page": r.money_page,
            "issues": r.top_issues,
            "indexability": r.indexability,
        }
        for r in compute_priority_rows(report)[:10]
    ]

    return {
        "site_url": report.start_url,
        "site_label": site_label or host,
        "host": host,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "duration_sec": round((report.finished_at or 0) - report.started_at, 1),
        "url_count": page_count,
        "health_score": health,
        "health_grade": grade,
        "health_grade_label": grade_label,
        "score_breakdown": {
            "HTTP 回應正常": score_http,
            "內容欄位完整": score_content,
            "無高風險問題": score_critical,
        },
        "indexable": indexable,
        "non_indexable": non_indexable,
        "indexable_pct": round(100 * indexable / n, 1),
        "status_ok_pct": status_ok_pct,
        "pages_with_issues": pages_with_any_issue,
        "pages_clean": n - pages_with_any_issue,
        "error_pages": error_pages,
        "canon_count": canon,
        "n404": n404,
        "issue_type_count": len(issue_counts),
        "avg_response_ms": round(sum(resp_times) / len(resp_times), 0) if resp_times else 0,
        "indexability": dict(idx),
        "indexability_status": dict(idx_status.most_common(12)),
        "status_codes": dict(status.most_common(10)),
        "issues_chart": {
            ISSUE_LABELS.get(k, k): v for k, v in issue_counts.most_common(12)
        },
        "issue_rows": issue_rows,
        "issue_samples": issue_samples,
        "crawl_depth": {str(k): v for k, v in sorted(depth.items())},
        "title_length": bucket_counter(pages, title_bucket, title_order),
        "meta_length": bucket_counter(pages, meta_bucket, meta_order),
        "h1_count": bucket_counter(
            pages,
            lambda p: "0" if not p.h1 else ("1（理想）" if len(p.h1) == 1 else "2+"),
            h1_order,
        ),
        "inlinks": bucket_counter(
            pages,
            lambda p: (
                "0（孤立風險）"
                if not p.inlinks
                else ("1–3" if len(p.inlinks) <= 3 else ("4–10" if len(p.inlinks) <= 10 else "10+"))
            ),
            inlink_order,
        ),
        "link_positions": {
            k: link_pos.get(k, 0) for k in link_position_order if link_pos.get(k, 0)
        },
        "word_count": bucket_counter(
            pages,
            lambda p: (
                "<100"
                if p.word_count < 100
                else ("100–299" if p.word_count < 300 else ("300–599" if p.word_count < 600 else "600+"))
            ),
            word_order,
        ),
        "lighthouse": lh_data,
        "actions": actions,
        "geo": geo,
        "llms": llms,
        "priority_pages": priority_pages,
        "summary_text": _summary_text(canon, n404, issue_counts, n, health, indexable, n),
    }


def _summary_text(
    canon: int, n404: int, issues: Counter, n: int, health: int, indexable: int, total: int
) -> str:
    parts = [
        f"技術 SEO 健康分 {health}/100（不含 Indexable 指標；目前可索引比例 {round(100*indexable/max(total,1),1)}%）。"
    ]
    if canon:
        parts.append(f" {canon} 頁 Canonicalised，請優先修正 CMS canonical。")
    if n404:
        parts.append(f" {n404} 個 404 死鏈需清理。")
    top = issues.most_common(1)
    if top:
        parts.append(f" 最常見：{ISSUE_LABELS.get(top[0][0], top[0][0])}（{top[0][1]} 頁）。")
    return "".join(parts)


def _build_actions(canon: int, n404: int, issues: Counter, n: int) -> list[dict]:
    actions = []
    if canon > n * 0.15:
        actions.append(
            {
                "title": "修正 Canonical URL",
                "body": f"{canon} 頁 Canonicalised。在 Webflow → Page settings → SEO 設為該頁正式網址。",
                "level": "high",
                "icon": "⚙️",
            }
        )
    if n404 > 0:
        actions.append(
            {
                "title": "清理 404 死鏈",
                "body": f"{n404} 個 404。移除內部連結或設 301 至對應新頁。",
                "level": "high",
                "icon": "🔗",
            }
        )
    if issues.get("missing_meta_description", 0) > n * 0.25:
        actions.append(
            {
                "title": "補齊 Meta Description",
                "body": f"約 {issues['missing_meta_description']} 頁缺描述，影響搜尋摘要 CTR。",
                "level": "medium",
                "icon": "📝",
            }
        )
    if issues.get("missing_alt", 0) > n * 0.25:
        actions.append(
            {
                "title": "圖片 Alt 文字",
                "body": "多數圖片缺少 alt，建議在 Webflow 資產庫補上。",
                "level": "medium",
                "icon": "🖼️",
            }
        )
    if issues.get("duplicate_title", 0) > 5:
        actions.append(
            {
                "title": "去重 Title 標籤",
                "body": f"{issues['duplicate_title']} 組重複 title，中英文頁需區隔。",
                "level": "medium",
                "icon": "🏷️",
            }
        )
    return actions[:6]


def _render_score_bars(breakdown: dict[str, int]) -> str:
    rows = []
    for label, val in breakdown.items():
        cls = "good" if val >= 25 else ("mid" if val >= 15 else "low")
        rows.append(
            f'<div class="score-row"><span class="score-lbl">{escape(label)}</span>'
            f'<div class="score-track"><div class="score-fill {cls}" style="width:{val}%"></div></div>'
            f'<span class="score-num">{val}</span></div>'
        )
    return "".join(rows)


def _render_actions(actions: list[dict]) -> str:
    if not actions:
        return '<p class="empty">未產生額外建議，請查看問題清單分頁。</p>'
    return "".join(
        f'<div class="action action-{a["level"]}">'
        f'<span class="action-icon">{a.get("icon","")}</span>'
        f'<div><h3>{escape(a["title"])}</h3><p>{escape(a["body"])}</p></div></div>'
        for a in actions
    )


def _render_issue_table(rows: list[dict]) -> str:
    if not rows:
        return '<p class="empty">未偵測到問題。</p>'
    trs = []
    for r in rows:
        pri = {"high": "高", "medium": "中", "low": "低"}.get(r["priority"], "低")
        trs.append(
            f'<tr data-pri="{r["priority"]}" data-label="{escape(r["label"]).lower()}">'
            f'<td><span class="pri pri-{r["priority"]}">{pri}</span></td>'
            f"<td>{escape(r['label'])}</td>"
            f'<td class="num">{r["count"]}</td>'
            f'<td class="num"><div class="bar-cell"><div class="bar-fill" style="width:{min(r["pct"],100)}%"></div>'
            f'</div> {r["pct"]}%</td></tr>'
        )
    return (
        '<table class="issue-table" id="issue-table"><thead><tr>'
        "<th>優先級</th><th>問題</th><th>頁數</th><th>占比</th>"
        "</tr></thead><tbody>"
        + "".join(trs)
        + "</tbody></table>"
    )


def _render_issue_samples(samples: dict[str, list[str]]) -> str:
    if not samples:
        return ""
    blocks = []
    for label, urls in list(samples.items())[:6]:
        items = "".join(f"<li><a href='{escape(u)}' target='_blank' rel='noopener'>{escape(_short_url(u))}</a></li>" for u in urls)
        blocks.append(f"<div class='sample-block'><h4>{escape(label)}</h4><ul>{items}</ul></div>")
    return '<div class="samples">' + "".join(blocks) + "</div>"


def _llms_status(data: dict, name: str) -> str:
    info = (data.get("llms") or {}).get(name) or {}
    status = info.get("status") or 0
    if status == 200:
        size = info.get("bytes") or 0
        return f"OK {status} · {size} bytes"
    if status:
        return f"HTTP {status}"
    err = info.get("error")
    return f"不可達{(' · ' + err) if err else ''}"


def _render_priority_pages(rows: list[dict]) -> str:
    if not rows:
        return "<p class='empty'>無資料</p>"
    items = []
    for r in rows[:10]:
        url = r.get("url") or ""
        score = r.get("score") or 0
        segment = r.get("segment") or ""
        money = "Yes" if r.get("money_page") else ""
        idx = r.get("indexability") or ""
        issues = r.get("issues") or ""
        items.append(
            f"<tr><td style='font-family: ui-monospace, monospace; font-size: .78rem; word-break: break-all;'>{escape(url)}</td>"
            f"<td class='num'>{score}</td><td>{escape(segment)}</td><td>{money}</td><td>{escape(idx)}</td><td>{escape(issues)}</td></tr>"
        )
    return (
        "<table class='issue-table'><thead><tr><th>URL</th><th class='num'>Score</th><th>Segment</th><th>Money</th><th>Indexability</th><th>Top Issues</th></tr></thead>"
        "<tbody>"
        + "".join(items)
        + "</tbody></table>"
        "<p class='section-label' style='margin-top:.75rem'>完整清單見 <code>priority_pages.csv</code></p>"
    )

def _short_url(url: str) -> str:
    if len(url) > 52:
        return "…" + url[-48:]
    return url


def export_dashboard_html(
    report: CrawlReport, path: Path, *, site_label: str | None = None
) -> None:
    data = compute_analytics(report, site_label=site_label)
    template = _UI.read_text(encoding="utf-8")
    theme_css = (
        report_styles_bundle()
        + "\n"
        + _ANALYTICS_THEME.read_text(encoding="utf-8")
        + "\n"
        + load_ui_css("analytics-theme-overrides.css")
    )

    health_class = "good" if data["health_score"] >= 70 else ("warn" if data["health_score"] >= 40 else "bad")
    idx_class = "bad" if data["indexable_pct"] < 30 else ("warn" if data["indexable_pct"] < 70 else "")

    lh_block = ""
    if data.get("lighthouse"):
        lh = data["lighthouse"]
        lh_block = f"""
    <div class="card wide"><h3>Lighthouse 均分（{lh['count']} 頁）</h3>
      <canvas id="chart-lighthouse"></canvas></div>"""

    replacements = {
        "{{SITE_LABEL}}": escape(data["site_label"]),
        "{{SITE_URL}}": escape(data["site_url"]),
        "{{HOST}}": escape(data["host"]),
        "{{GENERATED_AT}}": escape(data["generated_at"]),
        "{{DURATION}}": str(data["duration_sec"]),
        "{{URL_COUNT}}": str(data["url_count"]),
        "{{HEALTH_SCORE}}": str(data["health_score"]),
        "{{HEALTH_GRADE}}": data["health_grade"],
        "{{HEALTH_GRADE_LABEL}}": escape(data["health_grade_label"]),
        "{{HEALTH_CLASS}}": health_class,
        "{{HEALTH_OFFSET}}": str(round(283 * (1 - data["health_score"] / 100), 1)),
        "{{INDEXABLE_PCT}}": str(data["indexable_pct"]),
        "{{INDEXABLE_CLASS}}": idx_class,
        "{{STATUS_OK_PCT}}": str(data["status_ok_pct"]),
        "{{INDEXABLE}}": str(data["indexable"]),
        "{{NON_INDEXABLE}}": str(data["non_indexable"]),
        "{{PAGES_ISSUES}}": str(data["pages_with_issues"]),
        "{{PAGES_CLEAN}}": str(data["pages_clean"]),
        "{{ERROR_PAGES}}": str(data["error_pages"]),
        "{{CANON_COUNT}}": str(data["canon_count"]),
        "{{N404}}": str(data["n404"]),
        "{{ISSUE_TYPES}}": str(data["issue_type_count"]),
        "{{AVG_MS}}": str(data["avg_response_ms"]),
        "{{SUMMARY}}": escape(data["summary_text"]),
        "{{SCORE_BARS}}": _render_score_bars(data["score_breakdown"]),
        "{{ACTIONS}}": _render_actions(data["actions"]),
        "{{GEO_AVG}}": str((data.get("geo") or {}).get("avg_score", 0)),
        "{{LLMS_TXT}}": _llms_status(data, "llms.txt"),
        "{{LLMS_FULL}}": _llms_status(data, "llms-full.txt"),
        "{{PRIORITY_PAGES}}": _render_priority_pages(data.get("priority_pages") or []),
        "{{ISSUE_TABLE}}": _render_issue_table(data["issue_rows"]),
        "{{ISSUE_SAMPLES}}": _render_issue_samples(data["issue_samples"]),
        "{{LH_BLOCK}}": lh_block,
        "{{DATA_JSON}}": json.dumps(data, ensure_ascii=False),
        "{{ANALYTICS_THEME_CSS}}": theme_css,
        "{{BRAND_MARK_INLINE}}": brand_mark_inline(),
        "{{REPORT_TOPBAR}}": report_topbar(
            path.parent,
            "分析圖表",
            active="dashboard.html",
            site_url=data["site_url"],
            meta_line=f"{data['generated_at']} · {data['url_count']} URLs",
        ),
    }

    html = template
    for k, v in replacements.items():
        html = html.replace(k, v)
    path.write_text(html, encoding="utf-8")
