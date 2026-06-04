"""
內鏈圖指標：All Inlinks 匯出、內部 PageRank（Link Score）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


@dataclass(frozen=True)
class InlinkRow:
    source: str
    destination: str
    anchor: str
    dest_status: int
    nofollow: bool = False
    link_position: str = "Content"


@dataclass(frozen=True)
class PageLinkStats:
    inlinks: int
    unique_inlinks: int
    outlinks: int
    unique_outlinks: int
    link_score: float
    follow_inlinks: int = 0
    nofollow_inlinks: int = 0
    nofollow_outlinks: int = 0


def normalize_page_key(url: str, report: CrawlReport) -> str | None:
    """將連結目標 URL 對應到 report.pages 的 key。"""
    from sitespider.page_url_match import resolve_page_url

    if url in report.pages:
        return url
    cfg = report.config
    p = urlparse(url)
    if cfg and cfg.strip_query_string:
        url = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
        if url in report.pages:
            return url
    return resolve_page_url(url, report.pages)


def collect_internal_inlinks(report: CrawlReport) -> list[InlinkRow]:
    rows: list[InlinkRow] = []
    for source, page in report.pages.items():
        seen: set[str] = set()
        for link in page.links:
            if link.link_type != "internal":
                continue
            dest = normalize_page_key(link.resolved, report)
            if not dest or dest in seen:
                continue
            seen.add(dest)
            dest_page = report.pages[dest]
            rows.append(
                InlinkRow(
                    source=source,
                    destination=dest,
                    anchor=link.text or "",
                    dest_status=dest_page.status,
                    nofollow=link.nofollow,
                    link_position=link.link_position,
                )
            )
    rows.sort(key=lambda r: (r.destination, r.source))
    return rows


def compute_page_link_stats(report: CrawlReport) -> dict[str, PageLinkStats]:
    pages = list(report.pages.keys())
    n = len(pages)
    if not n:
        return {}

    out_map: dict[str, list[str]] = {u: [] for u in pages}
    follow_out_map: dict[str, list[str]] = {u: [] for u in pages}
    for src, page in report.pages.items():
        seen: set[str] = set()
        seen_follow: set[str] = set()
        for link in page.links:
            if link.link_type != "internal":
                continue
            dest = normalize_page_key(link.resolved, report)
            if dest and dest not in seen:
                seen.add(dest)
                out_map[src].append(dest)
            if dest and not link.nofollow and dest not in seen_follow:
                seen_follow.add(dest)
                follow_out_map[src].append(dest)

    in_map: dict[str, list[str]] = {u: [] for u in pages}
    follow_in_map: dict[str, list[str]] = {u: [] for u in pages}
    nofollow_in_map: dict[str, list[str]] = {u: [] for u in pages}
    for src, dests in out_map.items():
        by_dest: dict[str, list] = {}
        for l in report.pages[src].links:
            if l.link_type != "internal":
                continue
            d = normalize_page_key(l.resolved, report)
            if d:
                by_dest.setdefault(d, []).append(l)
        for d in dests:
            in_map[d].append(src)
            links_to_d = by_dest.get(d, [])
            if any(not x.nofollow for x in links_to_d):
                follow_in_map[d].append(src)
            if any(x.nofollow for x in links_to_d):
                nofollow_in_map[d].append(src)

    damping = 0.85
    iterations = 25
    rank = {u: 1.0 / n for u in pages}
    for _ in range(iterations):
        new_rank = {u: (1.0 - damping) / n for u in pages}
        for src, dests in follow_out_map.items():
            if not dests:
                continue
            share = damping * rank[src] / len(dests)
            for d in dests:
                new_rank[d] += share
        rank = new_rank

    peak = max(rank.values()) or 1.0
    scores = {u: round(100.0 * rank[u] / peak, 2) for u in pages}

    stats: dict[str, PageLinkStats] = {}
    for u in pages:
        ins = in_map[u]
        outs = out_map[u]
        nf_out_seen: set[str] = set()
        for l in report.pages[u].links:
            if l.link_type != "internal" or not l.nofollow:
                continue
            d = normalize_page_key(l.resolved, report)
            if d:
                nf_out_seen.add(d)
        nofollow_out = len(nf_out_seen)
        stats[u] = PageLinkStats(
            inlinks=len(ins),
            unique_inlinks=len(set(ins)),
            outlinks=len(outs),
            unique_outlinks=len(set(outs)),
            link_score=scores[u],
            follow_inlinks=len(set(follow_in_map[u])),
            nofollow_inlinks=len(set(nofollow_in_map[u])),
            nofollow_outlinks=nofollow_out,
        )
    return stats


def link_stats_for_page(report: CrawlReport, url: str) -> PageLinkStats | None:
    all_stats = compute_page_link_stats(report)
    return all_stats.get(url)


def inlinks_for_destination(report: CrawlReport, destination: str) -> list[InlinkRow]:
    return [r for r in collect_internal_inlinks(report) if r.destination == destination]
