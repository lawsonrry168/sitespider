"""
將爬取報告目錄打包為客戶交付 ZIP。
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sitespider.client_readme import build_client_readme_text

# 客戶交付建議包含的檔案（存在才打包）
DELIVERY_FILES: tuple[str, ...] = (
    "README-客戶.txt",
    "REPORT-zh.md",
    "REPORT-zh.html",
    "priority_summary.md",
    "SEO-AUDIT-zh.md",
    "dashboard.html",
    "index.html",
    "link_graph.html",
    "link_graph_simple.html",
    "inspector.html",
    "priority_pages.csv",
    "actions.csv",
    "geo.csv",
    "rich_results.csv",
    "rich_results_gsc.csv",
    "internal.csv",
    "issues.csv",
    "page_titles.csv",
    "canonicals.csv",
    "duplicate_content.csv",
    "sitemap_generated.xml",
    "crawl-report.json",
    "serp_snippets.csv",
    "link_graph_full.html",
    "issue_heatmap.html",
    "delivery-summary.html",
    "delivery-summary.pdf",
    "link_graph_webgl.html",
    "link_graph.gexf",
    "link_graph.graphml",
    "serp_rank.csv",
    "seo-briefs.html",
    "seo-briefs.md",
    "seo-briefs.json",
    "ai-hub.html",
    "ai-page-copy.html",
    "ai-page-copy.json",
    "ai-page-copy.csv",
    "ai-faq.html",
    "ai-faq-cms.html",
    "ai-faq.json",
    "ai-suggestions.md",
    "llms.txt.draft",
    "llms-full.txt.draft",
    "ai-polish-meta.json",
    "ai-polish-meta.html",
    "client-report.html",
    "images-gallery.html",
    "images.csv",
)


def _safe_zip_name(name: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", name).strip("_") or "report"


def count_downloaded_images(report_dir: Path) -> int:
    """報告目錄內 images/ 已下載檔案數。"""
    images_dir = report_dir.resolve() / "images"
    if not images_dir.is_dir():
        return 0
    return sum(1 for fp in images_dir.rglob("*") if fp.is_file())


def _zip_directory(
    zf: zipfile.ZipFile,
    source_dir: Path,
    arc_prefix: str,
) -> int:
    """將 source_dir 內所有檔案寫入 zip（保留子目錄結構）。"""
    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        return 0
    added = 0
    for fp in sorted(source_dir.rglob("*")):
        if not fp.is_file():
            continue
        rel = fp.relative_to(source_dir).as_posix()
        zf.write(fp, arcname=f"{arc_prefix}/{rel}")
        added += 1
    return added


def package_images_dir(
    report_dir: Path,
    zip_path: Path | None = None,
) -> Path:
    """僅打包報告內 images/ 與 images-gallery.html（離線圖庫交付）。"""
    report_dir = report_dir.resolve()
    images_dir = report_dir / "images"
    if not images_dir.is_dir() or not any(images_dir.iterdir()):
        raise ValueError(
            "此報告沒有已下載的圖片。請在爬取時勾選「下載站內圖片」後重新匯出。"
        )

    if zip_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        label = _safe_zip_name(report_dir.name)
        zip_path = report_dir.parent / f"{label}-images-{stamp}.zip"
    zip_path = zip_path.resolve()

    prefix = report_dir.name
    added = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        added += _zip_directory(zf, images_dir, f"{prefix}/images")
        gallery = report_dir / "images-gallery.html"
        if gallery.is_file():
            zf.write(gallery, arcname=f"{prefix}/images-gallery.html")
            added += 1
        csv_path = report_dir / "images.csv"
        if csv_path.is_file():
            zf.write(csv_path, arcname=f"{prefix}/images.csv")
            added += 1

    if added == 0:
        raise ValueError(f"images/ 內無可打包檔案：{report_dir}")

    return zip_path


def package_report_dir(
    report_dir: Path,
    zip_path: Path | None = None,
    *,
    extra_globs: tuple[str, ...] = (),
) -> Path:
    """打包 report_dir，回傳 zip 路徑。"""
    report_dir = report_dir.resolve()
    if not report_dir.is_dir():
        raise FileNotFoundError(f"找不到報告目錄：{report_dir}")

    if zip_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        label = _safe_zip_name(report_dir.name)
        zip_path = report_dir.parent / f"{label}-delivery-{stamp}.zip"
    zip_path = zip_path.resolve()

    added = 0
    readme_txt = build_client_readme_text(report_dir)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{report_dir.name}/README-客戶.txt", readme_txt)
        added += 1
        for name in DELIVERY_FILES:
            if name == "README-客戶.txt":
                continue
            fp = report_dir / name
            if fp.is_file():
                zf.write(fp, arcname=f"{report_dir.name}/{name}")
                added += 1
        for pattern in extra_globs:
            for fp in sorted(report_dir.glob(pattern)):
                if fp.is_file():
                    zf.write(fp, arcname=f"{report_dir.name}/{fp.name}")
                    added += 1
        added += _zip_directory(
            zf,
            report_dir / "images",
            f"{report_dir.name}/images",
        )

    if added == 0:
        raise ValueError(f"目錄內無可打包的交付檔：{report_dir}")

    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="將 SiteSpider 報告目錄打包為客戶交付 ZIP",
    )
    parser.add_argument(
        "report_dir",
        type=Path,
        help="報告目錄（含 crawl-report.json 或 REPORT-zh.md）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="輸出 zip 路徑（預設寫入報告目錄上一層）",
    )
    args = parser.parse_args(argv)
    try:
        out = package_report_dir(args.report_dir, args.output)
    except (OSError, ValueError) as e:
        print(f"錯誤：{e}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
