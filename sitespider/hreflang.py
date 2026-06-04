"""
hreflang 互指稽核（爬取結束後執行）。
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from sitespider.crawler import CrawlReport, PageResult, _canonical_for_compare


@dataclass(frozen=True)
class HreflangEntry:
    lang: str
    url: str
    resolved: str


def _norm_key(url: str, canonical_fn) -> str:
    return canonical_fn(url)


def audit_hreflang(
    report: CrawlReport,
    *,
    canonical_fn,
    check_url: callable | None = None,
) -> None:
    """
    檢查 hreflang 自引用、目標可達性、雙向互指。
    check_url: 對未爬取到的站內 URL 做 HEAD（可選）。
    """
    pages = report.pages
    # page_key -> list[HreflangEntry]
    by_page: dict[str, list[HreflangEntry]] = {}
    # target_key -> {source_key: lang}
    backlinks: dict[str, dict[str, str]] = {}

    for page_key, page in pages.items():
        entries: list[HreflangEntry] = []
        for item in page.hreflangs:
            lang = (item.get("lang") or "").strip()
            resolved = item.get("resolved") or item.get("url") or ""
            if not lang or not resolved:
                continue
            entries.append(HreflangEntry(lang=lang, url=item.get("url", resolved), resolved=resolved))
        if entries:
            by_page[page_key] = entries

    if not by_page:
        return

    for page_key, entries in by_page.items():
        page = pages[page_key]
        self_langs = {_canonical_for_compare(page.url), _canonical_for_compare(page.canonical or "")}
        self_langs.discard("")

        has_self = False
        for ent in entries:
            target_key = _norm_key(ent.resolved, canonical_fn)
            if not target_key:
                continue
            if _canonical_for_compare(ent.resolved) in self_langs or target_key == page_key:
                has_self = True
            backlinks.setdefault(target_key, {})[page_key] = ent.lang

            if target_key in pages:
                if pages[target_key].status >= 400:
                    _add_issue(page, "hreflang_target_error")
            elif check_url and urlparse(ent.resolved).netloc == urlparse(page.url).netloc:
                code = check_url(ent.resolved)
                if code is None or code >= 400:
                    _add_issue(page, "hreflang_target_error")

        if len(entries) >= 2 and not has_self:
            _add_issue(page, "hreflang_missing_self")

    for page_key, entries in by_page.items():
        page = pages[page_key]
        for ent in entries:
            target_key = _norm_key(ent.resolved, canonical_fn)
            if target_key not in pages:
                continue
            # 目標頁應有指回來的 hreflang
            reverse = backlinks.get(page_key, {})
            target_entries = by_page.get(target_key, [])
            target_langs = {e.lang.lower() for e in target_entries}
            if ent.lang.lower() not in target_langs and page_key not in reverse:
                _add_issue(page, "hreflang_no_return")


def _add_issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)
