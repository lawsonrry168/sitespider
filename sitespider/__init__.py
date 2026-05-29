"""
SiteSpider — 專業 SEO 站內爬蟲（Screaming Frog / SEMrush 風格）
"""

__version__ = "1.0.0"

from sitespider.crawler import CrawlConfig, CrawlReport, SeoCrawler, report_to_dict
from sitespider.report import write_all_reports

__all__ = [
    "CrawlConfig",
    "CrawlReport",
    "SeoCrawler",
    "report_to_dict",
    "write_all_reports",
    "__version__",
]
