"""
頁級優先級（Priority Score）— 將稽核訊號轉成可執行修復清單。

目標：
- 站級 actions.csv 很適合「做什麼」
- priority_pages.csv 用於「先修哪一頁」
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from collections import Counter

from sitespider.crawler import CrawlReport
from sitespider.geo_audit import compute_geo_rows
from sitespider.issues import ISSUE_LABELS
from sitespider.link_metrics import compute_page_link_stats


@dataclass(frozen=True)
class PriorityRow:
    url: str
    score: int
    segment: str
    money_page: bool
    indexability: str
    status: int
    depth: int
    link_score: float
    inlinks: int
    geo_score: int
    issue_count: int
    top_issues: str


_ISSUE_WEIGHT: dict[str, int] = {
    # blockers
    "http_error": 40,
    "broken_internal_link": 25,
    "meta_noindex": 30,
    "blocked_by_robots": 30,
    "canonical_mismatch": 25,
    "missing_canonical": 18,
    "redirect_chain": 10,
    # on-page
    "missing_title": 12,
    "missing_meta_description": 12,
    "missing_h1": 10,
    "multiple_h1": 6,
    "duplicate_title": 6,
    "duplicate_meta_description": 6,
    "thin_content": 12,
    "missing_html_lang": 6,
    "missing_viewport": 5,
    "missing_og_tags": 4,
    # media
    "missing_alt": 6,
    "image_missing_dimensions": 4,
}


_MONEY_KEYWORDS = (
    "/product",
    "/products",
    "/service",
    "/services",
    "/pricing",
    "/price",
    "/quote",
    "/book",
    "/booking",
    "/checkout",
    "/shop",
    "/contact",
)


def _segment_from_url(url: str) -> str:
    path = (urlparse(url).path or "/").lower()
    if any(k in path for k in ("/product", "/products")):
        return "product"
    if any(k in path for k in ("/service", "/services", "/treatment", "/treatments")):
        return "service"
    if any(k in path for k in ("/blog", "/news", "/article", "/post")):
        return "content"
    if path in ("/", "/index.html"):
        return "homepage"
    if any(k in path for k in ("/category", "/tag", "/collection")):
        return "category"
    if any(k in path for k in ("/contact", "/about", "/faq", "/pricing")):
        return "conversion"
    return "other"


def _is_money_page(url: str) -> bool:
    path = (urlparse(url).path or "/").lower()
    return any(k in path for k in _MONEY_KEYWORDS)


def compute_priority_rows(report: CrawlReport) -> list[PriorityRow]:
    link_stats = compute_page_link_stats(report)
    geo_map = {r.url: r.score for r in compute_geo_rows(report)}

    rows: list[PriorityRow] = []
    for url, p in report.pages.items():
        st = link_stats.get(url)
        link_score = st.link_score if st else 0.0
        inlinks = st.unique_inlinks if st else len(p.inlinks)
        geo_score = geo_map.get(url, 0)
        segment = _segment_from_url(url)
        money_page = _is_money_page(url)

        # 基礎分：Indexable + 200 優先修（更可能帶來回報）
        score = 0
        if p.status == 200 and p.indexability == "Indexable":
            score += 30
        elif p.status >= 400:
            score += 12  # 錯誤頁也要修，但通常先救可索引頁
        else:
            score -= 8  # Non-indexable / redirected，通常次優先

        if money_page:
            score += 18
        elif segment in {"homepage", "category", "service"}:
            score += 8

        # Link Score：越重要頁越優先（0–100 轉 0–15）
        score += int(min(15, (link_score / 100.0) * 15))

        # GEO：越低越值得補（以缺口計分）
        score += int(max(0, (60 - geo_score) / 4))  # 0..15

        # 問題加權（只算前幾個主要問題避免爆分）
        issues = list(dict.fromkeys(p.issues or []))
        weighted = sorted(
            ((i, _ISSUE_WEIGHT.get(i, 2)) for i in issues),
            key=lambda x: -x[1],
        )
        score += sum(w for _i, w in weighted[:6])

        # 深度懲罰：越深通常越低優先（0–10）
        score -= min(10, int(p.crawl_depth or 0))

        score = max(0, min(100, int(score)))

        top_issues = "; ".join(
            ISSUE_LABELS.get(i, i) for i, _w in weighted[:5]
        )[:240]

        rows.append(
            PriorityRow(
                url=url,
                score=score,
                segment=segment,
                money_page=money_page,
                indexability=p.indexability,
                status=int(p.status or 0),
                depth=int(p.crawl_depth or 0),
                link_score=round(link_score, 2),
                inlinks=int(inlinks or 0),
                geo_score=int(geo_score or 0),
                issue_count=len(issues),
                top_issues=top_issues,
            )
        )

    rows.sort(
        key=lambda r: (
            -r.score,
            not r.money_page,
            r.indexability != "Indexable",
            r.depth,
            -r.link_score,
            r.url,
        )
    )
    return rows


def export_priority_pages_csv(report: CrawlReport, path: Path, *, limit: int = 200) -> None:
    fields = [
        "Address",
        "Priority Score",
        "Segment",
        "Money Page",
        "Indexability",
        "Status Code",
        "Depth",
        "Link Score",
        "Inlinks",
        "GEO Score",
        "Issue Count",
        "Top Issues",
    ]
    rows = compute_priority_rows(report)[: max(1, int(limit))]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "Address": r.url,
                    "Priority Score": r.score,
                    "Segment": r.segment,
                    "Money Page": "Yes" if r.money_page else "",
                    "Indexability": r.indexability,
                    "Status Code": r.status,
                    "Depth": r.depth,
                    "Link Score": r.link_score,
                    "Inlinks": r.inlinks,
                    "GEO Score": r.geo_score,
                    "Issue Count": r.issue_count,
                    "Top Issues": r.top_issues,
                }
            )


def _build_seven_day_plan(report: CrawlReport, *, top_rows: list[PriorityRow]) -> list[tuple[str, list[str]]]:
    """依問題類型與商業頁面產出 Day 1–7 任務清單。"""
    issues = Counter()
    for p in report.pages.values():
        for code in set(p.issues or []):
            issues[code] += 1
    money_urls = [r.url for r in top_rows if r.money_page][:5]
    money_hint = ""
    if money_urls:
        money_hint = "優先頁：" + "、".join(f"`{u}`" for u in money_urls[:3])
        if len(money_urls) > 3:
            money_hint += f" 等 {len(money_urls)} 頁"

    def task(text: str) -> str:
        return text

    day1: list[str] = []
    if issues.get("http_error") or issues.get("broken_internal_link"):
        day1.append(
            task(
                f"修復失效連結與錯誤頁（約 {issues.get('broken_internal_link', 0)} 內鏈 / "
                f"{issues.get('http_error', 0)} HTTP 錯誤）"
            )
        )
    if issues.get("canonical_mismatch") or issues.get("missing_canonical"):
        day1.append(
            task(
                f"修正 canonical（不一致 {issues.get('canonical_mismatch', 0)} · "
                f"缺少 {issues.get('missing_canonical', 0)}）"
            )
        )
    if not day1:
        day1.append(task("複查 Response Codes / Canonicals 分頁，確認無阻斷性問題"))

    day2 = [
        task("確認 Indexable 頁 robots / noindex 設定無誤"),
    ]
    if issues.get("redirect_chain"):
        day2.append(task(f"縮短重新導向鏈（{issues['redirect_chain']} 頁）"))
    if issues.get("orphan_page"):
        day2.append(task(f"為孤立頁補內鏈或調整 sitemap（{issues['orphan_page']} 頁）"))

    day3 = [task("Money Page：補齊 title / meta / H1（每頁唯一）")]
    if money_hint:
        day3.append(task(money_hint))

    day4 = []
    if issues.get("missing_meta_description"):
        day4.append(task(f"全站補 meta description（約 {issues['missing_meta_description']} 頁）"))
    if issues.get("duplicate_title"):
        day4.append(task(f"處理重複 title（{issues['duplicate_title']} 頁）"))
    if issues.get("multiple_h1") or issues.get("missing_h1"):
        day4.append(
            task(
                f"統一 H1 結構（缺 H1 {issues.get('missing_h1', 0)} · "
                f"多 H1 {issues.get('multiple_h1', 0)}）"
            )
        )
    if not day4:
        day4.append(task("抽查 title / meta 長度與重複（見 page_titles.csv）"))

    day5 = []
    if issues.get("missing_alt"):
        day5.append(task(f"圖片補 alt（約 {issues['missing_alt']} 頁）"))
    if issues.get("image_missing_dimensions"):
        day5.append(task(f"圖片補 width/height（約 {issues['image_missing_dimensions']} 頁）"))
    if not day5:
        day5.append(task("抽查 images.csv，優化 LCP 相關圖片"))

    llms = report.llms_info or {}
    day6 = [
        task("補 html lang、Open Graph（全站模板或 CMS 預設）"),
    ]
    if llms.get("llms.txt", {}).get("status") != 200:
        day6.append(task("建立或修正 `/llms.txt`（GEO / AI 引用）"))
    if llms.get("llms-full.txt", {}).get("status") != 200:
        day6.append(task("建立或修正 `/llms-full.txt`"))
    if issues.get("missing_json_ld") or issues.get("json_ld_missing_type"):
        day6.append(task("補 JSON-LD（Product / FAQ / LocalBusiness 等，依頁型）"))
    else:
        day6.append(task("依 structured_data.csv 補強 FAQ / HowTo schema（GEO）"))

    day7 = []
    if issues.get("duplicate_meta_description") or issues.get("duplicate_h2"):
        day7.append(
            task(
                f"去重 meta / H2（meta {issues.get('duplicate_meta_description', 0)} · "
                f"H2 {issues.get('duplicate_h2', 0)}）"
            )
        )
    if issues.get("hreflang_target_error") or issues.get("hreflang_missing_self"):
        day7.append(task("修正 hreflang 互指（多語站）"))
    if issues.get("thin_content"):
        day7.append(task(f"加強內容過薄頁（{issues['thin_content']} 頁，目標 ≥300 字）"))
    day7.append(task("重跑 SiteSpider 比對修復前後（compare / diff-csv）"))

    return [
        ("Day 1 · 阻斷與索引基礎", day1),
        ("Day 2 · 索引與內鏈結構", day2),
        ("Day 3 · Money Page On-Page", day3),
        ("Day 4 · 全站 Title / Meta / H1", day4),
        ("Day 5 · 圖片與媒體", day5),
        ("Day 6 · GEO / 結構化資料", day6),
        ("Day 7 · 去重與驗收", day7),
    ]


def export_priority_summary_md(report: CrawlReport, path: Path, *, top_n: int = 10) -> None:
    rows = compute_priority_rows(report)
    top = rows[: max(1, int(top_n))]
    if not top:
        path.write_text("# Priority Summary\n\n無可用資料。\n", encoding="utf-8")
        return

    money_count = sum(1 for r in top if r.money_page)
    avg_score = round(sum(r.score for r in top) / len(top), 1)
    idx_count = sum(1 for r in top if r.indexability == "Indexable")
    llms = report.llms_info or {}

    lines = [
        "# Priority Summary",
        "",
        f"- Top {len(top)} 平均 Priority Score：**{avg_score}**",
        f"- Top {len(top)} Money Page：**{money_count}**",
        f"- Top {len(top)} Indexable：**{idx_count}**",
        "",
        "## 建議先處理",
    ]
    for i, r in enumerate(top, 1):
        lines.append(
            f"{i}. `{r.url}` · Score {r.score} · {r.segment} · "
            f"{'Money' if r.money_page else 'General'} · {r.indexability}"
        )
        if r.top_issues:
            lines.append(f"   - {r.top_issues}")

    def _llms_line(name: str) -> str:
        info = llms.get(name) or {}
        status = info.get("status") or 0
        if status == 200:
            return f"- {name}: OK 200 ({info.get('bytes') or 0} bytes)"
        if status:
            return f"- {name}: HTTP {status}"
        return f"- {name}: 不可達"

    lines.extend(
        [
            "",
            "## 7 日執行排程（建議）",
            "",
            "> 依本次爬取問題分佈自動生成，可依團隊人力合併或調序。",
            "",
        ]
    )
    for day_title, tasks in _build_seven_day_plan(report, top_rows=top):
        lines.append(f"### {day_title}")
        for t in tasks:
            lines.append(f"- {t}")
        lines.append("")

    lines.extend(
        [
            "## GEO / LLM 可引用檢查",
            _llms_line("llms.txt"),
            _llms_line("llms-full.txt"),
            "",
            "## 相關檔案",
            "- `priority_pages.csv` — 頁級優先順序（含 Money Page）",
            "- `actions.csv` — 站級修復主題",
            "- `geo.csv` — GEO 分數與 schema 覆蓋",
            "- `dashboard.html` — 圖表總覽",
            "- `link_graph.html` — 內鏈視覺化",
            "- `ngrams.csv` / `spelling.csv` — N-gram 與拼寫提示",
            "- `rich_results.csv` — Rich Results 啟發式檢查",
            "- `outlinks.csv` / `robots.csv` / `duplicate_content.csv` — SF 對齊匯出",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
