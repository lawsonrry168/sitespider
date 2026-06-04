"""
產生客戶交付用的一頁說明（README-客戶.txt），避免技術術語。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def _load_report_meta(report_dir: Path) -> dict:
    cr = report_dir / "crawl-report.json"
    if not cr.is_file():
        return {}
    try:
        return json.loads(cr.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def build_client_readme_text(
    report_dir: Path,
    *,
    site_label: str | None = None,
) -> str:
    """繁中一頁說明，供 ZIP 內附。"""
    meta = _load_report_meta(report_dir)
    start = meta.get("start_url") or ""
    host = urlparse(start).netloc or site_label or report_dir.name
    label = site_label or host
    pages = meta.get("page_count") or len(meta.get("pages") or {})
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "═══════════════════════════════════════════════════",
        "  網站 SEO 檢查報告 — 閱讀說明",
        "═══════════════════════════════════════════════════",
        "",
        f"網站：{label}",
        f"檢查日期：{stamp}（UTC）",
        f"已檢查頁面數：約 {pages} 頁",
        "",
        "【這份資料是什麼？】",
        "我們用專業工具掃描您網站的主要頁面，整理成表格與圖表，",
        "方便您或團隊依優先順序改善搜尋能見度與使用者體驗。",
        "",
        "【建議閱讀順序】",
        "1. client-report.html — 單一 HTML，雙擊即可離線閱讀摘要（適合 email 傳客戶）",
        "2. REPORT-zh.html（或 REPORT-zh.md）— 完整交付導覽與各報告入口",
        "3. dashboard.html — 用瀏覽器開啟，看整體圖表（雙擊即可）",
        "4. index.html — 各頁面明細，類似常見 SEO 桌面軟體報表",
        "5. seo-briefs.html — 文案改善建議（無 AI 亦可閱讀）",
        "6. ai-hub.html — 若含 AI 文案產物，從此進入 Title/Meta、FAQ 草稿",
        "7. priority_pages.csv — 建議優先處理的網址清單",
        "",
        "【常見檔案說明】",
        "· actions.csv / geo.csv — 建議動作與 AI 搜尋可見度相關項目",
        "· issues.csv — 需要留意的問題類型",
        "· link_graph.html — 網站內部連結關係圖（可拖曳節點）",
        "· sitemap_generated.xml — 依本次掃描產生的網站地圖草稿",
        "",
    ]
    images_dir = report_dir / "images"
    if images_dir.is_dir() and any(images_dir.iterdir()):
        n = sum(1 for fp in images_dir.rglob("*") if fp.is_file())
        lines.extend(
            [
                "【圖片打包】",
                f"· images/ — 已下載 {n} 張站內圖片（離線可開）",
                "· images-gallery.html — 圖片稽核頁（縮圖、alt、問題標記）",
                "· images.csv — 圖片清單與本機檔名對照",
                "",
            ]
        )
    lines.extend(
        [
        "【使用方式】",
        "· 請將整個資料夾解壓到電腦，用 Chrome / Edge / Safari 開啟 .html 檔案。",
        "· .csv 可用 Excel 或 Google 試算表開啟。",
        "· 不需安裝額外軟體；不需 Google 帳號即可閱讀大部分內容。",
        "",
        "【注意】",
        "· 報告反映「掃描當下」的網站狀態，上線改版後建議重新掃描比對。",
        "· 若資料夾內沒有 rich_results_gsc.csv，表示本次未使用 Search Console API，",
        "  不影響其他報告的完整性。",
        "",
        "如有疑問，請聯絡提供本報告的顧問或技術窗口。",
        "",
        ]
    )
    return "\n".join(lines)


def write_client_readme(report_dir: Path, *, site_label: str | None = None) -> Path:
    path = report_dir / "README-客戶.txt"
    path.write_text(
        build_client_readme_text(report_dir, site_label=site_label),
        encoding="utf-8",
    )
    return path
