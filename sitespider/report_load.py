"""從 crawl-report.json 還原 CrawlReport（供 export / 重生報告）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sitespider.crawler import (
    CrawlConfig,
    CrawlReport,
    ImageInfo,
    LighthouseResult,
    LinkInfo,
    PageResult,
)


def _link_from_dict(d: dict) -> LinkInfo:
    return LinkInfo(
        href=d.get("href", ""),
        text=d.get("text", ""),
        resolved=d.get("resolved", ""),
        link_type=d.get("link_type", "other"),
        status=d.get("status"),
        issue=d.get("issue"),
        nofollow=bool(d.get("nofollow", False)),
        link_position=d.get("link_position") or "Content",
    )


def _image_from_dict(d: dict) -> ImageInfo:
    return ImageInfo(
        src=d.get("src", ""),
        alt=d.get("alt"),
        resolved=d.get("resolved", ""),
        status=d.get("status"),
        issue=d.get("issue"),
        width=d.get("width"),
        height=d.get("height"),
        loading=d.get("loading"),
        content_type=d.get("content_type"),
        byte_size=d.get("byte_size"),
        local_file=d.get("local_file"),
    )


def _lighthouse_from_dict(d: dict | None) -> LighthouseResult | None:
    if not d:
        return None
    return LighthouseResult(
        performance=d.get("performance"),
        accessibility=d.get("accessibility"),
        best_practices=d.get("best_practices"),
        seo=d.get("seo"),
        error=d.get("error"),
    )


def page_from_dict(d: dict, *, url: str | None = None) -> PageResult:
    page_url = url or d.get("url", "")
    links = [_link_from_dict(x) for x in d.get("links") or []]
    images = [_image_from_dict(x) for x in d.get("images") or []]
    return PageResult(
        url=page_url,
        status=int(d.get("status", 0)),
        content_type=d.get("content_type"),
        response_ms=float(d.get("response_ms", 0)),
        title=d.get("title"),
        meta_description=d.get("meta_description"),
        meta_robots=d.get("meta_robots"),
        canonical=d.get("canonical"),
        h1=list(d.get("h1") or []),
        h2=list(d.get("h2") or []),
        h3=list(d.get("h3") or []),
        word_count=int(d.get("word_count", 0)),
        images=images,
        links=links,
        issues=list(d.get("issues") or []),
        inlinks=list(d.get("inlinks") or []),
        crawl_depth=int(d.get("crawl_depth", 0)),
        source=d.get("source", "http"),
        blocked_by_robots=bool(d.get("blocked_by_robots", False)),
        seed_source=d.get("seed_source", "link"),
        lighthouse=_lighthouse_from_dict(d.get("lighthouse")),
        og_title=d.get("og_title"),
        og_description=d.get("og_description"),
        has_json_ld=bool(d.get("has_json_ld", False)),
        json_ld_types=list(d.get("json_ld_types") or []),
        html_lang=d.get("html_lang"),
        request_url=d.get("request_url"),
        redirect_chain=list(d.get("redirect_chain") or []),
        has_viewport=bool(d.get("has_viewport", False)),
        indexability=d.get("indexability", "Indexable"),
        indexability_status=d.get("indexability_status", ""),
        hreflangs=list(d.get("hreflangs") or []),
        response_headers=dict(d.get("response_headers") or {}),
        meta_keywords=d.get("meta_keywords"),
        pagination_prev=d.get("pagination_prev"),
        pagination_next=d.get("pagination_next"),
        content_hash=str(d.get("content_hash") or ""),
        serp_title_pixels=int(d.get("serp_title_pixels") or 0),
        serp_meta_pixels=int(d.get("serp_meta_pixels") or 0),
        mixed_content_count=int(d.get("mixed_content_count") or 0),
        is_https=bool(d.get("is_https", False)),
        rendered_with_js=bool(d.get("rendered_with_js", False)),
        amp_html_url=d.get("amp_html_url"),
        console_messages=list(d.get("console_messages") or []),
        screenshot_path=d.get("screenshot_path"),
        custom_fields=dict(d.get("custom_fields") or {}),
    )


def report_from_dict(data: dict[str, Any]) -> CrawlReport:
    cfg_raw = data.get("config") or {}
    allowed = {f.name for f in CrawlConfig.__dataclass_fields__.values()}
    config = CrawlConfig(**{k: v for k, v in cfg_raw.items() if k in allowed})

    report = CrawlReport(
        start_url=data.get("start_url", ""),
        mode=data.get("mode", "http"),
        config=config,
        robots_info=dict(data.get("robots_info") or {}),
        llms_info=dict(data.get("llms_info") or {}),
        gsc_rich_inspections=dict(data.get("gsc_rich_inspections") or {}),
        sitemap_urls=list(data.get("sitemap_urls") or []),
        blocked_urls=list(data.get("blocked_urls") or []),
        lighthouse=dict(data.get("lighthouse") or {}),
        errors=list(data.get("errors") or []),
    )

    for page_url, pdata in (data.get("pages") or {}).items():
        if not isinstance(pdata, dict):
            continue
        report.pages[page_url] = page_from_dict(pdata, url=page_url)

    report.sitemap_not_crawled = list(data.get("sitemap_not_crawled") or [])
    report.sitemap_not_in_sitemap = list(data.get("sitemap_not_in_sitemap") or [])
    report.summary_issues()
    return report


def load_report_json(path: Path) -> CrawlReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"報告須為 JSON 物件：{path}")
    return report_from_dict(data)
