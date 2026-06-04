"""
產生可交付客戶的繁中 Markdown SEO 稽核報告。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sitespider.issues import ISSUE_LABELS


def _load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _priority(issue: str) -> str:
    high = {
        "canonical_mismatch",
        "missing_canonical",
        "http_error",
        "broken_internal_link",
        "meta_noindex",
        "blocked_by_robots",
    }
    medium = {
        "missing_title",
        "missing_meta_description",
        "missing_h1",
        "multiple_h1",
        "duplicate_title",
        "redirect_chain",
    }
    if issue in high:
        return "高"
    if issue in medium:
        return "中"
    return "低"


def generate_client_markdown(report: dict, *, site_label: str | None = None) -> str:
    start = report.get("start_url", "")
    label = site_label or start
    pages = report.get("pages") or {}
    n = report.get("page_count") or len(pages)
    duration = report.get("duration_sec", 0)
    issues = report.get("summary_issues") or {}

    idx = Counter()
    idx_status = Counter()
    status_codes = Counter()
    for p in pages.values():
        idx[p.get("indexability", "?")] += 1
        st = p.get("indexability_status") or ""
        if st:
            idx_status[st] += 1
        status_codes[p.get("status", 0)] += 1

    lines = [
        f"# SEO 稽核報告 — {label}",
        "",
        f"- **稽核時間（UTC）**：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        f"- **起始 URL**：{start}",
        f"- **已爬取 URL 數**：{n}",
        f"- **耗時**：{duration:.1f} 秒",
        f"- **工具**：SiteSpider（對照 Screaming Frog Internal / Indexability 欄位）",
        "",
        "---",
        "",
        "## 執行摘要",
        "",
    ]

    non_idx = idx.get("Non-Indexable", 0)
    canon = idx_status.get("Canonicalised", 0)
    if canon > n * 0.5:
        lines.extend(
            [
                f"本次抽樣 **{n}** 個 URL 中，**{non_idx}** 個標記為 **Non-Indexable**，"
                f"其中 **{canon}** 個原因為 **Canonicalised**（canonical 指向與實際 URL 不一致或設定錯誤）。",
                "此為 **優先修復項目**，建議在 Webflow（或 CMS）後台檢查全站 Canonical URL。",
                "",
            ]
        )
    else:
        lines.append(f"共發現 **{len(issues)}** 類問題，詳見下方清單。")
        lines.append("")

    lines.extend(
        [
            "### Indexability 分佈",
            "",
            "| 類型 | 數量 |",
            "|------|------|",
        ]
    )
    for k, v in idx.most_common():
        lines.append(f"| {k} | {v} |")
    if idx_status:
        lines.extend(["", "### Indexability Status（前 10）", "", "| 狀態 | 數量 |", "|------|------|"])
        for k, v in idx_status.most_common(10):
            lines.append(f"| {k} | {v} |")

    lines.extend(
        [
            "",
            "### HTTP 狀態碼",
            "",
            "| 狀態碼 | 數量 |",
            "|--------|------|",
        ]
    )
    for code, count in sorted(status_codes.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"| {code} | {count} |")

    lines.extend(["", "---", "", "## 問題清單（依影響排序）", ""])
    if not issues:
        lines.append("未偵測到設定內的 SEO 問題。")
    else:
        lines.append("| 優先級 | 問題 | 影響頁數 | 說明 |")
        lines.append("|--------|------|----------|------|")
        sorted_issues = sorted(issues.items(), key=lambda x: -len(set(x[1])))
        for key, urls in sorted_issues:
            label_zh = ISSUE_LABELS.get(key, key)
            pri = _priority(key)
            note = _issue_note(key)
            lines.append(f"| {pri} | {label_zh} | {len(set(urls))} | {note} |")

    lines.extend(["", "---", "", "## 建議修復步驟", ""])
    if canon:
        lines.extend(
            [
                "1. **Canonical URL**：在 Webflow → 各頁 Page settings → SEO settings，將 Canonical 設為該頁正式網址（勿重複網域，例如勿出現 `https://www.example.com/www.example.com`）。",
                "2. **全站檢查**：優先處理首頁、服務分類、優惠 `/treatments`、中英文對應頁。",
                "3. **重新稽核**：修正後再次執行 SiteSpider，並以 `sitespider compare` 比對修正前後差異。",
                "",
            ]
        )
    lines.extend(
        [
            "- 為主要圖片補上 **alt** 文字（目前多頁缺少）。",
            "- 在 `<html>` 加上 **lang**（例如 `zh-HK` 或 `en`）。",
            "- 補齊缺少的 **meta description** 與 **Open Graph**（利於搜尋摘要與分享）。",
            "- 避免多個 **H1**；服務頁 title 應具區隔，減少 **重複 title**。",
            "- 提交正確的 **sitemap.xml**（目前可能回傳 404，影響收錄）。",
            "",
        ]
    )

    lines.extend(["---", "", "## 範例 URL（各問題最多 5 筆）", ""])
    for key, urls in sorted(issues.items(), key=lambda x: -len(set(x[1])))[:8]:
        label_zh = ISSUE_LABELS.get(key, key)
        lines.append(f"### {label_zh}")
        for u in sorted(set(urls))[:5]:
            lines.append(f"- {u}")
        if len(set(urls)) > 5:
            lines.append(f"- …及其他 {len(set(urls)) - 5} 頁")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "*本報告由 SiteSpider 自動產生，僅供內部 SEO 改善參考；對外發送前請由負責人覆核。*",
        ]
    )
    return "\n".join(lines) + "\n"


def _issue_note(issue: str) -> str:
    notes = {
        "canonical_mismatch": "Canonical 與實際 URL 不符，常導致 Canonicalised",
        "missing_canonical": "未宣告 canonical",
        "missing_meta_description": "搜尋結果摘要可能不佳",
        "missing_og_tags": "社群分享預覽不完整",
        "missing_alt": "無障礙與圖片搜尋不利",
        "missing_html_lang": "語言標記缺失",
        "duplicate_title": "多頁 title 相同，不利區隔",
        "multiple_h1": "一頁多個 H1",
        "missing_h1": "缺少主標題",
        "thin_content": "字數過少",
        "redirect_chain": "多段重新導向",
    }
    return notes.get(issue, "見 issues.csv")


def write_client_report(
    crawl_json: Path,
    output: Path,
    *,
    site_label: str | None = None,
) -> Path:
    report = _load_report(crawl_json)
    md = generate_client_markdown(report, site_label=site_label)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    return output
