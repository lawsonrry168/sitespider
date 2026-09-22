"""
Looker Studio 資料匯出 bundle（手動上傳 JSON，非 Community Connector）。

此模組產生 pages.json + schema.json 供 Looker Studio「上傳檔案 / BigQuery 外部表」
或 ETL 管線使用。它**不是** Google Looker Studio Community Connector，
無法在 Looker 介面內即時拉取 SiteSpider API。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def _page_record(url: str, page) -> dict[str, Any]:
    return {
        "url": url,
        "status": page.status,
        "title": page.title or "",
        "meta_description": page.meta_description or "",
        "indexability": page.indexability,
        "crawl_depth": page.crawl_depth,
        "word_count": page.word_count,
        "issue_count": len(page.issues or []),
        "issues": ";".join(page.issues or []),
        "inlinks": len(page.inlinks or []),
        "is_https": bool(page.is_https),
    }


def export_looker_bundle(report: CrawlReport, out_dir: str | Path) -> list[str]:
    """
    寫入 looker/pages.json 與 looker/schema.json。
    回傳相對於 out_dir 的檔名列表。
    """
    base = Path(out_dir)
    looker_dir = base / "looker"
    looker_dir.mkdir(parents=True, exist_ok=True)

    pages = [_page_record(url, page) for url, page in sorted(report.pages.items())]
    pages_path = looker_dir / "pages.json"
    pages_path.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")

    schema = {
        "description": "SiteSpider crawl pages — static JSON dump for Looker Studio import",
        "not_a_community_connector": True,
        "fields": [
            {"name": "url", "type": "STRING"},
            {"name": "status", "type": "INTEGER"},
            {"name": "title", "type": "STRING"},
            {"name": "meta_description", "type": "STRING"},
            {"name": "indexability", "type": "STRING"},
            {"name": "crawl_depth", "type": "INTEGER"},
            {"name": "word_count", "type": "INTEGER"},
            {"name": "issue_count", "type": "INTEGER"},
            {"name": "issues", "type": "STRING"},
            {"name": "inlinks", "type": "INTEGER"},
            {"name": "is_https", "type": "BOOLEAN"},
        ],
    }
    schema_path = looker_dir / "schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    return ["looker/pages.json", "looker/schema.json"]
