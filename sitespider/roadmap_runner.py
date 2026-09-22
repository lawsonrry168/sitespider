"""
FEATURE_ROADMAP Phase 1–4 稽核與匯出編排（依 config 旗標呼叫各模組）。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def _cfg(config: Any, name: str, default: Any = False) -> Any:
    return getattr(config, name, default)


def run_roadmap_audits(report: CrawlReport, *, config) -> None:
    """依 config 旗標執行 Phase 1–4 稽核（順序固定）。"""
    if _cfg(config, "audit_near_duplicates", True):
        from sitespider.similarity import audit_near_duplicates

        audit_near_duplicates(
            report,
            threshold=float(_cfg(config, "near_duplicate_threshold", 0.90)),
        )

    if _cfg(config, "audit_security_headers", True):
        from sitespider.security_headers import audit_security_headers

        audit_security_headers(report)

    from sitespider.heading_audit import audit_heading_hierarchy

    audit_heading_hierarchy(report)

    from sitespider.url_quality import audit_url_quality

    audit_url_quality(report)

    from sitespider.insecure_forms import audit_insecure_forms

    audit_insecure_forms(report)

    if _cfg(config, "audit_readability", True):
        from sitespider.readability import audit_readability

        audit_readability(report)

    if _cfg(config, "audit_keyword_density", True):
        from sitespider.keyword_density import audit_keyword_density

        audit_keyword_density(report)

    ga4_property_id = _cfg(config, "ga4_property_id", None)
    if ga4_property_id:
        from sitespider.ga4_api import run_ga4_merge

        run_ga4_merge(
            report,
            str(ga4_property_id),
            str(_cfg(config, "ga4_credentials", "") or ""),
            date_range=tuple(_cfg(config, "ga4_date_range", ("30daysAgo", "today"))),
        )

    provider = _cfg(config, "backlink_provider", None)
    api_key = _cfg(config, "backlink_api_key", None)
    if provider and api_key:
        from sitespider.backlink_api import run_backlink_fetch

        run_backlink_fetch(
            report,
            str(provider),
            str(api_key),
            max_urls=int(_cfg(config, "backlink_max_urls", 200)),
        )

    crux_key = _cfg(config, "crux_api_key", None)
    if crux_key:
        from sitespider.crux_api import run_crux_audit

        run_crux_audit(report, str(crux_key), max_origins=int(_cfg(config, "crux_max_origins", 5)))

    if _cfg(config, "audit_amp", False):
        from sitespider.amp_validate import audit_amp_pages

        audit_amp_pages(report)

    if _cfg(config, "grammar_check", False):
        api_url = _cfg(config, "grammar_api_url", None)
        if api_url:
            from sitespider.grammar_check import run_grammar_audit

            run_grammar_audit(
                report,
                str(api_url),
                max_pages=int(_cfg(config, "grammar_max_pages", 50)),
            )

    if _cfg(config, "audit_tracking", True):
        from sitespider.tracking_audit import (
            apply_site_tracking_issues,
            compute_locale_tracking_comparison,
            scan_report_tracking,
        )

        scan_report_tracking(report)
        apply_site_tracking_issues(report)
        if _cfg(config, "locale_tracking_compare", True):
            compute_locale_tracking_comparison(report)

    if _cfg(config, "a11y_audit", False):
        from sitespider.a11y_audit import audit_accessibility

        audit_accessibility(report)


def _has_ga4_sessions(report: CrawlReport) -> bool:
    return any(
        getattr(p, "ga4_sessions", None) is not None for p in report.pages.values()
    )


def _has_backlink_data(report: CrawlReport) -> bool:
    return any(
        getattr(p, "backlinks_count", None) is not None for p in report.pages.values()
    )


def export_roadmap_reports(report: CrawlReport, out_dir: str | Path, *, config) -> list[str]:
    """匯出 Phase 1–4 報表；回傳已寫入的相對檔名。"""
    from sitespider.sf_reports import (
        export_csv_accessibility,
        export_csv_analytics,
        export_csv_backlinks,
        export_csv_crux,
        export_csv_grammar,
        export_csv_near_duplicates,
        export_csv_readability,
    )

    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    export_csv_near_duplicates(report, base / "near_duplicates.csv")
    written.append("near_duplicates.csv")

    export_csv_readability(report, base / "readability.csv")
    written.append("readability.csv")

    from sitespider.keyword_density import export_keyword_density_csv

    export_keyword_density_csv(report, base / "keyword_density.csv")
    written.append("keyword_density.csv")

    if getattr(report, "a11y_violations", None):
        export_csv_accessibility(report, base / "accessibility.csv")
        written.append("accessibility.csv")

    if _has_ga4_sessions(report):
        export_csv_analytics(report, base / "analytics.csv")
        written.append("analytics.csv")

    if _has_backlink_data(report):
        export_csv_backlinks(report, base / "backlinks.csv")
        written.append("backlinks.csv")

    if getattr(report, "crux_metrics", None):
        export_csv_crux(report, base / "crux.csv")
        written.append("crux.csv")

    if getattr(report, "grammar_issues", None):
        export_csv_grammar(report, base / "grammar.csv")
        written.append("grammar.csv")

    if _cfg(config, "export_directory_tree", True):
        from sitespider.directory_tree import export_html_tree

        export_html_tree(report, base / "directory_tree.html")
        written.append("directory_tree.html")

    if _cfg(config, "export_looker", False):
        from sitespider.looker_connector import export_looker_bundle

        written.extend(export_looker_bundle(report, base))

    if _cfg(config, "audit_tracking", True):
        from sitespider.tracking_audit import export_tracking_bundle

        written.extend(export_tracking_bundle(report, base))

    sheets_id = _cfg(config, "sheets_id", None)
    if _cfg(config, "export_sheets", False) and sheets_id:
        from sitespider.sheets_export import export_to_sheets

        export_to_sheets(
            report,
            str(sheets_id),
            credentials_path=_cfg(config, "sheets_credentials", None),
        )

    return written
