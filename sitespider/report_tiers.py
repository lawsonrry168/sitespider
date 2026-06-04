"""分層報告匯出：Fast → Standard → Pro（速度與體感）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


@dataclass
class ExportOptions:
    site_root: Path | None = None
    export_xlsx: bool = False
    client_report: bool = False
    client_report_label: str | None = None
    branding: object | None = None
    plan_id: str | None = None
    tenant_id: str = "default"


def export_summary_json(
    report: CrawlReport,
    path: Path,
    *,
    site_label: str | None = None,
) -> None:
    from sitespider.report_analytics import compute_analytics

    data = compute_analytics(report, site_label=site_label)
    subset = {
        "site_label": data.get("site_label"),
        "health_score": data.get("health_score"),
        "health_grade_label": data.get("health_grade_label"),
        "url_count": data.get("url_count"),
        "indexable": data.get("indexable"),
        "non_indexable": data.get("non_indexable"),
        "duration_sec": data.get("duration_sec"),
        "top_issues": (data.get("issues") or [])[:8],
        "actions": (data.get("actions") or [])[:5],
    }
    path.write_text(json.dumps(subset, ensure_ascii=False, indent=2), encoding="utf-8")


def export_fast_tier(report: CrawlReport, out_dir: Path, opts: ExportOptions) -> list[str]:
    """立即可交付（通常數秒內）。"""
    from sitespider.branding import Branding
    from sitespider.client_readme import write_client_readme
    from sitespider.priority import export_priority_pages_csv, export_priority_summary_md
    from sitespider.report import export_csv_issues, export_html, export_json
    from sitespider.report_readme import export_report_readme_html, export_report_readme_md

    out_dir.mkdir(parents=True, exist_ok=True)
    brand = opts.branding if isinstance(opts.branding, Branding) else Branding.from_dict(
        opts.branding if isinstance(opts.branding, dict) else None
    )
    label = opts.client_report_label

    export_json(report, out_dir / "crawl-report.json")
    export_summary_json(report, out_dir / "summary.json", site_label=label)
    export_csv_issues(report, out_dir / "issues.csv")
    export_priority_pages_csv(report, out_dir / "priority_pages.csv")
    export_priority_summary_md(report, out_dir / "priority_summary.md")
    export_report_readme_md(report, out_dir / "REPORT-zh.md", site_label=label, branding=brand)
    export_report_readme_html(
        report, out_dir / "REPORT-zh.html", site_label=label, branding=brand, out_dir=out_dir
    )
    write_client_readme(out_dir, site_label=label)
    export_html(report, out_dir / "index.html", site_root=opts.site_root)
    from sitespider.report_theme import export_ai_placeholders

    export_ai_placeholders(out_dir)

    return [
        "crawl-report.json",
        "summary.json",
        "issues.csv",
        "priority_pages.csv",
        "priority_summary.md",
        "REPORT-zh.md",
        "REPORT-zh.html",
        "README-客戶.txt",
        "index.html",
        "ai-hub.html",
        "ai-faq-cms.html",
    ]


def export_standard_tier(report: CrawlReport, out_dir: Path, opts: ExportOptions) -> list[str]:
    """SF CSV、dashboard、交付視覺化。"""
    from sitespider.branding import Branding
    from sitespider.delivery_summary import export_delivery_summary_html
    from sitespider.geo_audit import export_geo_csv
    from sitespider.issue_heatmap import export_issue_heatmap_html
    from sitespider.link_graph import export_link_graph_html, export_link_graph_simple_html
    from sitespider.page_inspector import export_page_inspector
    from sitespider.report import (
        export_csv_actions,
        export_csv_blocked,
        export_csv_canonicals,
        export_csv_h1,
        export_csv_images,
        export_csv_links,
        export_csv_llms,
        export_csv_pages,
        export_csv_redirects,
        export_csv_response_codes,
        export_csv_page_titles,
        export_csv_lighthouse,
    )
    from sitespider.report_analytics import export_dashboard_html
    from sitespider.rich_results import export_rich_results_csv
    from sitespider.seo_briefs import export_seo_briefs_bundle
    from sitespider.sf_reports import export_all_sf_reports
    from sitespider.sitemap_export import export_sitemap_xml

    brand = opts.branding if isinstance(opts.branding, Branding) else Branding.from_dict(
        opts.branding if isinstance(opts.branding, dict) else None
    )
    label = opts.client_report_label
    written = list(export_all_sf_reports(report, out_dir))

    export_geo_csv(report, out_dir / "geo.csv")
    export_csv_llms(report, out_dir / "llms.csv")
    export_csv_actions(report, out_dir / "actions.csv")
    export_issue_heatmap_html(report, out_dir / "issue_heatmap.html", branding=brand)
    export_delivery_summary_html(
        report, out_dir / "delivery-summary.html", site_label=label, branding=brand
    )
    export_link_graph_html(report, out_dir / "link_graph.html")
    export_link_graph_simple_html(report, out_dir / "link_graph_simple.html")
    export_rich_results_csv(report, out_dir / "rich_results.csv")
    if report.gsc_rich_inspections:
        from sitespider.gsc_inspection import export_gsc_rich_results_csv

        export_gsc_rich_results_csv(report, out_dir / "rich_results_gsc.csv")
        written.append("rich_results_gsc.csv")

    for name, fn in [
        ("canonicals.csv", export_csv_canonicals),
        ("response_codes.csv", export_csv_response_codes),
        ("page_titles.csv", export_csv_page_titles),
        ("h1.csv", export_csv_h1),
        ("pages.csv", export_csv_pages),
        ("links.csv", export_csv_links),
        ("images.csv", export_csv_images),
        ("blocked.csv", export_csv_blocked),
        ("redirects.csv", export_csv_redirects),
        ("lighthouse.csv", export_csv_lighthouse),
    ]:
        fn(report, out_dir / name)
        written.append(name)

    from sitespider.image_export import download_report_images, export_images_gallery_html

    cfg = report.config
    if cfg.download_images:
        download_report_images(
            report,
            out_dir,
            max_images=cfg.max_images_download,
            same_host_only=cfg.images_same_host_only,
        )
        if (out_dir / "images").is_dir() and any((out_dir / "images").iterdir()):
            written.append("images/")
    export_images_gallery_html(report, out_dir / "images-gallery.html")
    written.append("images-gallery.html")

    export_dashboard_html(report, out_dir / "dashboard.html", site_label=label)
    export_page_inspector(report, out_dir / "inspector.html")
    written.extend(
        export_seo_briefs_bundle(report, out_dir, site_label=label)
    )
    from sitespider.report_readme import export_report_readme_html

    export_report_readme_html(
        report, out_dir / "REPORT-zh.html", site_label=label, branding=brand, out_dir=out_dir
    )
    from sitespider.standalone_client_report import export_standalone_client_html

    export_standalone_client_html(
        out_dir, site_label=label, report=report, branding=brand
    )
    written.append("client-report.html")
    if export_sitemap_xml(report, out_dir / "sitemap_generated.xml") > 0:
        written.append("sitemap_generated.xml")

    written.extend(
        [
            "geo.csv",
            "llms.csv",
            "actions.csv",
            "issue_heatmap.html",
            "delivery-summary.html",
            "link_graph.html",
            "link_graph_simple.html",
            "rich_results.csv",
            "dashboard.html",
            "inspector.html",
            "images-gallery.html",
            "seo-briefs.html",
            "seo-briefs.md",
            "seo-briefs.json",
        ]
    )
    return written


def export_pro_tier(report: CrawlReport, out_dir: Path, opts: ExportOptions) -> list[str]:
    """進階分析、方案限定匯出。"""
    from sitespider.branding import Branding
    from sitespider.delivery_summary import export_delivery_pdf
    from sitespider.link_graph import export_link_graph_full_html
    from sitespider.ngrams import export_ngrams_csv
    from sitespider.saas_exports import export_plan_features
    from sitespider.serp_export import export_serp_snippets_csv
    from sitespider.spelling_check import export_spelling_csv

    brand = opts.branding if isinstance(opts.branding, Branding) else Branding.from_dict(
        opts.branding if isinstance(opts.branding, dict) else None
    )
    label = opts.client_report_label
    written: list[str] = []

    export_ngrams_csv(report, out_dir / "ngrams.csv")
    export_spelling_csv(report, out_dir / "spelling.csv")
    export_serp_snippets_csv(report, out_dir / "serp_snippets.csv")
    written.extend(["ngrams.csv", "spelling.csv", "serp_snippets.csv"])

    if len(report.pages) >= 80:
        export_link_graph_full_html(report, out_dir / "link_graph_full.html")
        written.append("link_graph_full.html")

    if export_delivery_pdf(report, out_dir / "delivery-summary.pdf", site_label=label, branding=brand):
        written.append("delivery-summary.pdf")

    extra, _ = export_plan_features(
        report,
        out_dir,
        plan_id=opts.plan_id,
        tenant_id=opts.tenant_id,
        base=out_dir.parent.parent if out_dir.parent.name != "reports" else out_dir.parent,
    )
    written.extend(extra)

    if opts.export_xlsx:
        from sitespider.report_xlsx import export_xlsx as write_xlsx

        write_xlsx(report, out_dir / "crawl-report.xlsx")
        written.append("crawl-report.xlsx")

    if opts.client_report:
        from sitespider.client_report import write_client_report

        write_client_report(
            out_dir / "crawl-report.json",
            out_dir / "SEO-AUDIT-zh.md",
            site_label=label or report.start_url,
        )
        written.append("SEO-AUDIT-zh.md")

    return written


def export_all_tiers(report: CrawlReport, out_dir: Path, opts: ExportOptions) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for batch in (
        export_fast_tier(report, out_dir, opts),
        export_standard_tier(report, out_dir, opts),
        export_pro_tier(report, out_dir, opts),
    ):
        for name in batch:
            if name not in seen:
                seen.add(name)
                out.append(name)
    return out
