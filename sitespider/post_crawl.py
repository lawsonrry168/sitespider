"""
爬取結束後的全站稽核（Security、Sitemap 差異、內容重複、URL、Pagination 等）。
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from urllib.parse import parse_qs, urlparse

from sitespider.crawler import CrawlReport, PageResult, _canonical_for_compare, _is_html_url
from sitespider.link_metrics import normalize_page_key
from sitespider.pixel_width import META_MAX_PX, TITLE_MAX_PX, serp_pixel_width
from sitespider.robots import meta_robots_noindex

_NON_DESCRIPTIVE_ANCHORS = frozenset(
    {
        "click here",
        "click",
        "here",
        "read more",
        "more",
        "learn more",
        "link",
        "點此",
        "點擊",
        "更多",
        "詳情",
        "了解更多",
        "此處",
        "這裡",
    }
)

URL_MAX_LEN = 115
URL_MAX_PARAMS = 3


def normalize_content_hash(text: str) -> str:
    t = re.sub(r"\s+", " ", text.strip().lower())
    if not t:
        return ""
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def compute_content_hash_from_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    return normalize_content_hash(soup.get_text(separator=" "))


def enrich_page_metrics(page: PageResult) -> None:
    page.serp_title_pixels = serp_pixel_width(page.title or "")
    page.serp_meta_pixels = serp_pixel_width(page.meta_description or "")
    parsed = urlparse(page.url)
    page.is_https = parsed.scheme == "https"
    http_assets = 0
    for link in page.links:
        if link.resolved.startswith("http://"):
            http_assets += 1
    for img in page.images:
        if img.resolved.startswith("http://"):
            http_assets += 1
    page.mixed_content_count = http_assets


def audit_page_extras(page: PageResult, *, mode: str) -> None:
    """單頁 Security / URL / SERP 像素 / Pagination 問題。"""
    if page.blocked_by_robots or page.status >= 400:
        return
    if meta_robots_noindex(page.meta_robots):
        return

    enrich_page_metrics(page)

    if mode == "http" and not page.is_https:
        _issue(page, "insecure_page")
    if page.is_https and page.mixed_content_count > 0:
        _issue(page, "mixed_content")

    if page.serp_title_pixels > TITLE_MAX_PX:
        _issue(page, "title_pixels_too_wide")
    if page.meta_description and page.serp_meta_pixels > META_MAX_PX:
        _issue(page, "meta_pixels_too_wide")

    if len(page.url) > URL_MAX_LEN:
        _issue(page, "url_too_long")
    qs = parse_qs(urlparse(page.url).query)
    if len(qs) > URL_MAX_PARAMS:
        _issue(page, "url_many_parameters")

    if not page.h2 and page.word_count > 400:
        _issue(page, "missing_h2")


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def audit_sitemap_diff(
    report: CrawlReport,
    *,
    canonical_fn,
) -> None:
    """sitemap 有但未爬到 / 爬到但不在 sitemap（僅 HTML 200 頁）。"""
    crawled_html = {
        canonical_fn(url)
        for url, p in report.pages.items()
        if p.status == 200 and _is_html_url(url)
    }
    sitemap_norm = set()
    for raw in report.sitemap_urls:
        sitemap_norm.add(canonical_fn(raw))

    report.sitemap_not_crawled = sorted(sitemap_norm - crawled_html)
    report.sitemap_not_in_sitemap = sorted(crawled_html - sitemap_norm)


def audit_content_duplicates(report: CrawlReport) -> None:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for url, page in report.pages.items():
        if page.status != 200 or not page.content_hash:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        by_hash[page.content_hash].append(url)
    for urls in by_hash.values():
        if len(urls) < 2:
            continue
        for u in urls:
            _issue(report.pages[u], "duplicate_content")


def audit_pagination(report: CrawlReport, *, canonical_fn) -> None:
    for url, page in report.pages.items():
        if page.status != 200:
            continue
        for target, attr in (
            (page.pagination_next, "pagination_next"),
            (page.pagination_prev, "pagination_prev"),
        ):
            if not target:
                continue
            norm = canonical_fn(target)
            if norm not in report.pages:
                _issue(page, "pagination_target_missing")
            elif report.pages[norm].status >= 400:
                _issue(page, "pagination_target_error")


def audit_duplicate_h2(report: CrawlReport) -> None:
    h2_map: dict[str, list[str]] = defaultdict(list)
    for url, page in report.pages.items():
        if not page.h2:
            continue
        key = page.h2[0].strip().lower()
        if key:
            h2_map[key].append(url)
    for urls in h2_map.values():
        if len(urls) < 2:
            continue
        for u in urls:
            _issue(report.pages[u], "duplicate_h2")


def audit_directives(page: PageResult) -> dict[str, str]:
    """解析 meta robots 指令供 directives.csv。"""
    raw = (page.meta_robots or "").lower()
    flags = {
        "noindex": "noindex" in raw,
        "nofollow": "nofollow" in raw,
        "noarchive": "noarchive" in raw,
        "nosnippet": "nosnippet" in raw,
        "noimageindex": "noimageindex" in raw,
    }
    xrt = (page.response_headers.get("x-robots-tag") or "").lower()
    if xrt:
        for k in flags:
            if k in xrt:
                flags[k] = True
    return {k: ("Yes" if v else "") for k, v in flags.items()}


def audit_images(report: CrawlReport) -> None:
    """圖片尺寸與 alt 相關問題（頁面級）。"""
    max_dim = 2500
    for page in report.pages.values():
        if page.status >= 400 or page.blocked_by_robots:
            continue
        for img in page.images:
            if not img.resolved or img.issue == "missing_src":
                continue
            if img.width is None and img.height is None:
                _issue(page, "image_missing_dimensions")
            elif (img.width or 0) > max_dim or (img.height or 0) > max_dim:
                _issue(page, "image_oversized")


def audit_anchor_text(report: CrawlReport) -> None:
    """同一錨文字指向多個不同 URL、空錨文字、非描述性錨文字。"""
    anchor_dests: dict[str, set[str]] = defaultdict(set)
    anchor_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for source, page in report.pages.items():
        if page.status >= 400:
            continue
        for link in page.links:
            if link.link_type != "internal":
                continue
            dest = normalize_page_key(link.resolved, report)
            if not dest:
                continue
            raw = (link.text or "").strip()
            if not raw:
                _issue(page, "empty_anchor_text")
                continue
            key = raw.lower()
            anchor_dests[key].add(dest)
            anchor_edges[key].append((source, dest))
            if key in _NON_DESCRIPTIVE_ANCHORS or len(raw) <= 2:
                _issue(page, "non_descriptive_anchor")

    for key, dests in anchor_dests.items():
        if len(dests) < 2:
            continue
        for source, _dest in anchor_edges[key]:
            if source in report.pages:
                _issue(report.pages[source], "duplicate_anchor_text")


def run_post_crawl_audits(
    report: CrawlReport,
    *,
    mode: str,
    canonical_fn,
    config=None,
) -> None:
    for page in report.pages.values():
        audit_page_extras(page, mode=mode)

    if report.sitemap_urls:
        audit_sitemap_diff(report, canonical_fn=canonical_fn)

    audit_content_duplicates(report)
    audit_pagination(report, canonical_fn=canonical_fn)
    audit_duplicate_h2(report)
    audit_anchor_text(report)
    audit_images(report)

    if mode == "http":
        _audit_llms_txt(report)
        _maybe_run_gsc_inspection(report, config)


def _maybe_run_gsc_inspection(report: CrawlReport, config) -> None:
    if not config or getattr(config, "gsc_inspect_max", 0) <= 0:
        return
    try:
        from sitespider.gsc_inspection import gsc_available, run_gsc_rich_inspections

        if not gsc_available():
            report.errors.append(
                'GSC Rich Results：請安裝 pip install "sitespider[gsc]"'
            )
            return
        site = getattr(config, "gsc_site_url", None) or report.start_url
        run_gsc_rich_inspections(
            report,
            site_url=site,
            max_urls=config.gsc_inspect_max,
        )
    except Exception as e:
        report.errors.append(f"GSC Rich Results：{e}")


def _audit_llms_txt(report: CrawlReport) -> None:
    """檢查 llms.txt / llms-full.txt 存在性（GEO 常用）。"""
    import requests

    base = report.start_url.rstrip("/")
    urls = {
        "llms.txt": base + "/llms.txt",
        "llms-full.txt": base + "/llms-full.txt",
    }
    out = {}
    for name, url in urls.items():
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "SiteSpider"})
            out[name] = {
                "url": url,
                "status": r.status_code,
                "bytes": len(r.content or b""),
            }
        except requests.RequestException as e:
            out[name] = {"url": url, "status": 0, "error": str(e)}
    report.llms_info = out
