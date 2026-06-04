"""
交付檔案清單 — 與爬取中心 DELIVERY_GROUPS、REPORT-zh 導覽一致。
"""

from __future__ import annotations

from pathlib import Path

from sitespider.package_report import count_downloaded_images

# (檔名, 標題, 分組, 簡短說明)
CATALOG: tuple[tuple[str, str, str, str], ...] = (
    ("client-report.html", "客戶單檔報告", "客戶交付", "離線 HTML · 可 email"),
    ("REPORT-zh.html", "交付導覽", "客戶交付", "建議從這裡開始"),
    ("delivery-summary.html", "一頁摘要", "客戶交付", "可列印 · PDF"),
    ("seo-briefs.html", "SEO Brief", "客戶交付", "Title · Meta · H1"),
    ("ai-hub.html", "AI 交付", "客戶交付", "FAQ · llms.txt"),
    ("ai-page-copy.html", "AI 標題與描述", "客戶交付", "各頁文案建議"),
    ("ai-faq.html", "AI 常見問答", "客戶交付", "FAQ + Schema"),
    ("ai-faq-cms.html", "FAQ 貼上", "客戶交付", "CMS 貼上版"),
    ("priority_summary.md", "修復優先順序", "客戶交付", "7 日排程"),
    ("issue_heatmap.html", "問題熱力圖", "客戶交付", "依路徑前綴"),
    ("ai-suggestions.md", "綜合建議", "AI 文案", "Markdown"),
    ("ai-polish-meta.html", "AI 執行紀錄", "AI 文案", "產出清單"),
    ("ai-polish-meta.json", "AI 執行紀錄", "AI 文案", "JSON"),
    ("ai-page-copy.csv", "標題描述", "AI 文案", "試算表"),
    ("llms.txt.draft", "llms.txt 草稿", "AI 文案", ""),
    ("llms-full.txt.draft", "llms-full 草稿", "AI 文案", ""),
    ("dashboard.html", "分析圖表", "圖表分析", "健康分 · 問題分佈"),
    ("index.html", "站內技術報告", "圖表分析", "Internal · Titles"),
    ("link_graph.html", "內鏈關係圖", "圖表分析", "D3 互動"),
    ("link_graph_webgl.html", "內鏈圖（3D）", "圖表分析", "WebGL"),
    ("inspector.html", "單頁檢視", "圖表分析", "URL 詳情"),
    ("images-gallery.html", "圖片稽核", "圖表分析", "alt · 尺寸 · 縮圖"),
    ("REPORT-zh.md", "交付導覽", "其他", "Markdown"),
    ("README-客戶.txt", "客戶說明", "其他", "文字版"),
    ("geo.csv", "GEO 分數", "資料匯出", ""),
    ("rich_results.csv", "複合式搜尋結果", "資料匯出", ""),
    ("internal.csv", "Internal", "資料匯出", "SF 對照"),
    ("issues.csv", "Issues", "資料匯出", ""),
)

GROUP_ORDER: tuple[str, ...] = ("客戶交付", "圖表分析", "AI 文案", "資料匯出", "其他")

CORE_DELIVERY_FILES: frozenset[str] = frozenset(
    {
        "REPORT-zh.html",
        "summary.json",
        "issues.csv",
        "priority_summary.md",
        "dashboard.html",
    }
)

# REPORT-zh.html 交付磁貼（檔名, 標題, 說明）
DELIVERY_TILES: tuple[tuple[str, str, str], ...] = tuple(
    (f, t, d) for f, t, g, d in CATALOG if g in ("客戶交付", "圖表分析") and f.endswith(".html")
)


def files_in_report(report_dir: Path) -> list[dict]:
    """扁平清單（相容 /api/demo、portal）。"""
    report_dir = report_dir.resolve()
    out: list[dict] = []
    for fname, title, _group, desc in CATALOG:
        if (report_dir / fname).is_file():
            entry: dict = {"file": fname, "title": title}
            if desc:
                entry["desc"] = desc
            out.append(entry)
    return out


def delivery_checklist(report_dir: Path) -> dict:
    """交付清單完成度（控制台 Step 3 用）。"""
    report_dir = report_dir.resolve()
    catalog_names = {fname for fname, *_ in CATALOG}
    items: list[dict] = []
    for fname, title, group, desc in CATALOG:
        present = (report_dir / fname).is_file()
        core = fname in CORE_DELIVERY_FILES
        entry: dict = {
            "file": fname,
            "title": title,
            "group": group,
            "present": present,
            "core": core,
        }
        if desc:
            entry["desc"] = desc
        items.append(entry)
    for fname in sorted(CORE_DELIVERY_FILES - catalog_names):
        present = (report_dir / fname).is_file()
        items.append(
            {
                "file": fname,
                "title": fname,
                "group": "核心",
                "present": present,
                "core": True,
            }
        )
    core_total = len(CORE_DELIVERY_FILES)
    present_core = sum(
        1 for fname in CORE_DELIVERY_FILES if (report_dir / fname).is_file()
    )
    present_any = sum(1 for i in items if i["present"])
    images_count = count_downloaded_images(report_dir)
    return {
        "items": items,
        "present_count": present_any,
        "catalog_count": len(CATALOG),
        "core_present": present_core,
        "core_total": core_total,
        "core_complete": present_core >= core_total,
        "images": {
            "downloaded_count": images_count,
            "gallery_present": (report_dir / "images-gallery.html").is_file(),
            "zip_available": images_count > 0,
        },
    }


def grouped_files_in_report(report_dir: Path) -> list[dict]:
    """分組清單（範例報告頁、portal）。"""
    report_dir = report_dir.resolve()
    by_group: dict[str, list[dict]] = {g: [] for g in GROUP_ORDER}
    for fname, title, group, desc in CATALOG:
        if not (report_dir / fname).is_file():
            continue
        item: dict = {"file": fname, "title": title}
        if desc:
            item["desc"] = desc
        by_group.setdefault(group, []).append(item)
    return [{"name": g, "files": by_group[g]} for g in GROUP_ORDER if by_group.get(g)]
