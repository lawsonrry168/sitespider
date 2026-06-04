"""
Screaming Frog 風格分頁 CSV 匯出（Security、External、URL、H2、Sitemap 等）。
"""

from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

from sitespider.crawler import CrawlReport
from sitespider.link_metrics import collect_internal_inlinks, compute_page_link_stats
from sitespider.post_crawl import audit_directives
from sitespider.report import _sf_row


def export_csv_h3(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "H3-1", "H3-1 Length", "H3-2", "Indexability"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "H3-1": p.h3[0] if p.h3 else "",
                    "H3-1 Length": len(p.h3[0]) if p.h3 else 0,
                    "H3-2": p.h3[1] if len(p.h3) > 1 else "",
                    "Indexability": p.indexability,
                }
            )


def export_csv_outlinks(report: CrawlReport, path: Path) -> None:
    """SF Outlinks 分頁欄位（全站出站連結）。"""
    fields = [
        "Type",
        "Source",
        "Destination",
        "Anchor Text",
        "Status Code",
        "Follow",
        "Link Position",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for page_url, p in sorted(report.pages.items()):
            for link in p.links:
                lt = link.link_type
                type_label = {
                    "internal": "Internal",
                    "external": "External",
                }.get(lt, lt.capitalize() if lt else "")
                w.writerow(
                    {
                        "Type": type_label,
                        "Source": page_url,
                        "Destination": link.resolved,
                        "Anchor Text": link.text,
                        "Status Code": link.status if link.status is not None else "",
                        "Follow": "Nofollow" if link.nofollow else "Follow",
                        "Link Position": link.link_position,
                    }
                )


def export_csv_robots(report: CrawlReport, path: Path) -> None:
    fields = ["Rule Type", "Value", "Notes"]
    info = report.robots_info or {}
    rows: list[dict[str, str]] = [
        {"Rule Type": "robots.txt Source", "Value": str(info.get("source") or ""), "Notes": ""},
        {
            "Rule Type": "Crawl-Delay",
            "Value": str(info.get("crawl_delay") or ""),
            "Notes": "",
        },
    ]
    for sm in info.get("sitemaps") or []:
        rows.append({"Rule Type": "Sitemap", "Value": sm, "Notes": ""})
    for dis in info.get("disallowed") or []:
        rows.append({"Rule Type": "Disallow", "Value": dis, "Notes": "User-agent *"})
    for url, p in sorted(report.pages.items()):
        if p.blocked_by_robots:
            rows.append(
                {
                    "Rule Type": "Blocked URL",
                    "Value": url,
                    "Notes": "Disallowed by robots.txt",
                }
            )
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def export_csv_duplicate_content(report: CrawlReport, path: Path) -> None:
    """內容 hash 重複群組（SF 內容重複檢視）。"""
    from collections import defaultdict

    from sitespider.robots import meta_robots_noindex

    by_hash: dict[str, list[str]] = defaultdict(list)
    for url, page in report.pages.items():
        if page.status != 200 or not page.content_hash:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        by_hash[page.content_hash].append(url)

    fields = ["Content Hash", "URL Count", "Addresses", "Indexability Mix"]
    rows: list[dict[str, str | int]] = []
    for h, urls in sorted(by_hash.items(), key=lambda x: -len(x[1])):
        if len(urls) < 2:
            continue
        idx_mix = ", ".join(
            sorted({report.pages[u].indexability for u in urls if u in report.pages})
        )
        rows.append(
            {
                "Content Hash": h[:16] + "…" if len(h) > 16 else h,
                "URL Count": len(urls),
                "Addresses": " | ".join(urls[:20]) + (" …" if len(urls) > 20 else ""),
                "Indexability Mix": idx_mix,
            }
        )
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def export_csv_javascript(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Rendered with JS",
        "Console Messages",
        "Console Count",
        "Indexability",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            msgs = p.console_messages or []
            w.writerow(
                {
                    "Address": url,
                    "Rendered with JS": "Yes" if p.rendered_with_js else "",
                    "Console Messages": " | ".join(msgs[:15]),
                    "Console Count": len(msgs),
                    "Indexability": p.indexability,
                }
            )


def export_csv_h2(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "H2-1", "H2-1 Length", "H2-2", "Indexability"]
    h2_map: dict[str, list[str]] = {}
    for url, p in report.pages.items():
        if p.h2:
            h2_map.setdefault(p.h2[0].strip(), []).append(url)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "H2-1": p.h2[0] if p.h2 else "",
                    "H2-1 Length": len(p.h2[0]) if p.h2 else 0,
                    "H2-2": p.h2[1] if len(p.h2) > 1 else "",
                    "Indexability": p.indexability,
                }
            )


def export_csv_meta_descriptions(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Meta Description 1",
        "Meta Description 1 Length",
        "Meta Description 1 Pixel Width",
        "Indexability",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            meta = p.meta_description or ""
            w.writerow(
                {
                    "Address": url,
                    "Meta Description 1": meta,
                    "Meta Description 1 Length": len(meta),
                    "Meta Description 1 Pixel Width": p.serp_meta_pixels,
                    "Indexability": p.indexability,
                }
            )


def export_csv_meta_keywords(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Meta Keywords 1", "Meta Keywords 1 Length", "Indexability"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            mk = p.meta_keywords or ""
            w.writerow(
                {
                    "Address": url,
                    "Meta Keywords 1": mk,
                    "Meta Keywords 1 Length": len(mk),
                    "Indexability": p.indexability,
                }
            )


def export_csv_external(report: CrawlReport, path: Path) -> None:
    fields = [
        "Source",
        "Destination",
        "Anchor Text",
        "Status Code",
        "Follow",
        "Link Position",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for page_url, p in sorted(report.pages.items()):
            for link in p.links:
                if link.link_type != "external":
                    continue
                w.writerow(
                    {
                        "Source": page_url,
                        "Destination": link.resolved,
                        "Anchor Text": link.text,
                        "Status Code": link.status if link.status is not None else "",
                        "Follow": "Nofollow" if link.nofollow else "Follow",
                        "Link Position": link.link_position,
                    }
                )


def export_csv_security(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Scheme",
        "Mixed Content Count",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "Issues",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            sec_issues = [i for i in p.issues if i in ("insecure_page", "mixed_content")]
            w.writerow(
                {
                    "Address": url,
                    "Scheme": "HTTPS" if p.is_https else "HTTP",
                    "Mixed Content Count": p.mixed_content_count,
                    "Strict-Transport-Security": p.response_headers.get(
                        "strict-transport-security", ""
                    ),
                    "Content-Security-Policy": p.response_headers.get(
                        "content-security-policy", ""
                    )[:80],
                    "Issues": "; ".join(sec_issues),
                }
            )


def export_csv_url_audit(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "URL Length",
        "Path",
        "Query Params",
        "Issues",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            parsed = urlparse(url)
            qs = parsed.query
            param_count = len(qs.split("&")) if qs else 0
            url_issues = [
                i
                for i in p.issues
                if i in ("url_too_long", "url_many_parameters")
            ]
            w.writerow(
                {
                    "Address": url,
                    "URL Length": len(url),
                    "Path": parsed.path,
                    "Query Params": param_count,
                    "Issues": "; ".join(url_issues),
                }
            )


def export_csv_pagination(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Pagination Prev",
        "Pagination Next",
        "Issues",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            pag_issues = [
                i
                for i in p.issues
                if i.startswith("pagination_")
            ]
            w.writerow(
                {
                    "Address": url,
                    "Pagination Prev": p.pagination_prev or "",
                    "Pagination Next": p.pagination_next or "",
                    "Issues": "; ".join(pag_issues),
                }
            )


def export_csv_directives(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Meta Robots 1",
        "X-Robots-Tag 1",
        "Noindex",
        "Nofollow",
        "Noarchive",
        "Nosnippet",
        "Indexability",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            flags = audit_directives(p)
            w.writerow(
                {
                    "Address": url,
                    "Meta Robots 1": p.meta_robots or "",
                    "X-Robots-Tag 1": p.response_headers.get("x-robots-tag", ""),
                    "Noindex": flags.get("noindex", ""),
                    "Nofollow": flags.get("nofollow", ""),
                    "Noarchive": flags.get("noarchive", ""),
                    "Nosnippet": flags.get("nosnippet", ""),
                    "Indexability": p.indexability,
                }
            )


def export_csv_structured_data(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Has JSON-LD", "JSON-LD Types", "Indexability"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "Has JSON-LD": "Yes" if p.has_json_ld else "",
                    "JSON-LD Types": "; ".join(p.json_ld_types),
                    "Indexability": p.indexability,
                }
            )


def export_csv_content(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Word Count",
        "Content Hash",
        "Near Duplicate",
        "Indexability",
    ]
    hash_urls: dict[str, list[str]] = {}
    for url, p in report.pages.items():
        if p.content_hash:
            hash_urls.setdefault(p.content_hash, []).append(url)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            dup = len(hash_urls.get(p.content_hash, [])) > 1 if p.content_hash else False
            w.writerow(
                {
                    "Address": url,
                    "Word Count": p.word_count,
                    "Content Hash": p.content_hash,
                    "Near Duplicate": "Yes" if dup else "",
                    "Indexability": p.indexability,
                }
            )


def export_csv_sitemap_diff(report: CrawlReport, path: Path) -> None:
    fields = ["URL", "In Sitemap", "Crawled", "Notes"]
    rows: list[dict] = []
    crawled = set(report.pages.keys())
    sitemap_set = set(report.sitemap_urls)
    all_urls = sorted(sitemap_set | crawled)
    for u in all_urls:
        in_sm = u in sitemap_set or any(
            u.rstrip("/") == s.rstrip("/") for s in sitemap_set
        )
        in_cr = u in crawled
        note = ""
        if in_sm and not in_cr:
            note = "In sitemap, not crawled"
        elif in_cr and not in_sm:
            note = "Crawled, not in sitemap"
        rows.append(
            {
                "URL": u,
                "In Sitemap": "Yes" if in_sm else "",
                "Crawled": "Yes" if in_cr else "",
                "Notes": note,
            }
        )
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def export_csv_hreflang(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Hreflang", "Target URL", "Indexability"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            if not p.hreflangs:
                w.writerow({"Address": url, "Hreflang": "", "Target URL": "", "Indexability": p.indexability})
                continue
            for h in p.hreflangs:
                w.writerow(
                    {
                        "Address": url,
                        "Hreflang": h.get("lang", ""),
                        "Target URL": h.get("resolved", h.get("url", "")),
                        "Indexability": p.indexability,
                    }
                )


def export_csv_orphan_pages(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Crawl Depth", "Seed Source", "Indexability", "Inlinks"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            if "orphan_page" not in p.issues:
                continue
            w.writerow(
                {
                    "Address": url,
                    "Crawl Depth": p.crawl_depth,
                    "Seed Source": p.seed_source,
                    "Indexability": p.indexability,
                    "Inlinks": len(p.inlinks),
                }
            )


def export_csv_broken_external(report: CrawlReport, path: Path) -> None:
    fields = ["Source", "Destination", "Anchor Text", "Status Code", "Link Position"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for page_url, p in sorted(report.pages.items()):
            for link in p.links:
                if link.link_type != "external":
                    continue
                if link.status is None or link.status < 400:
                    continue
                w.writerow(
                    {
                        "Source": page_url,
                        "Destination": link.resolved,
                        "Anchor Text": link.text,
                        "Status Code": link.status,
                        "Link Position": link.link_position,
                    }
                )


def export_csv_anchor_text(report: CrawlReport, path: Path) -> None:
    """錨文字衝突：同一文字指向多個 URL。"""
    from collections import defaultdict

    from sitespider.link_metrics import normalize_page_key

    anchor_dests: dict[str, set[str]] = defaultdict(set)
    anchor_label: dict[str, str] = {}
    for _src, page in report.pages.items():
        for link in page.links:
            if link.link_type != "internal":
                continue
            dest = normalize_page_key(link.resolved, report)
            text = (link.text or "").strip()
            if not dest or not text:
                continue
            key = text.lower()
            anchor_dests[key].add(dest)
            anchor_label.setdefault(key, text)

    fields = ["Anchor Text", "Destination Count", "Sample Destinations"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for key, dests in sorted(anchor_dests.items(), key=lambda x: -len(x[1])):
            if len(dests) < 2:
                continue
            sample = " | ".join(sorted(dests)[:5])
            w.writerow(
                {
                    "Anchor Text": anchor_label.get(key, key)[:200],
                    "Destination Count": len(dests),
                    "Sample Destinations": sample[:500],
                }
            )


def export_csv_all_inlinks(report: CrawlReport, path: Path) -> None:
    """Screaming Frog「All Inlinks」風格：內鏈來源 → 目標與錨文字。"""
    fields = [
        "Type",
        "Source",
        "Destination",
        "Anchor Text",
        "Status Code",
        "Follow",
        "Link Position",
        "Path Type",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in collect_internal_inlinks(report):
            w.writerow(
                {
                    "Type": "Hyperlink",
                    "Source": row.source,
                    "Destination": row.destination,
                    "Anchor Text": row.anchor[:500],
                    "Status Code": row.dest_status,
                    "Follow": "Nofollow" if row.nofollow else "Follow",
                    "Link Position": row.link_position,
                    "Path Type": "Path",
                }
            )


def export_sf_internal_enhanced(report: CrawlReport, path: Path) -> None:
    """覆寫 internal.csv，含 Title Pixel Width、Link Score。"""
    link_stats = compute_page_link_stats(report)
    fields = [
        "Address",
        "Content Type",
        "Status Code",
        "Indexability",
        "Indexability Status",
        "Title 1",
        "Title 1 Length",
        "Title 1 Pixel Width",
        "Meta Description 1",
        "Meta Description 1 Length",
        "H1-1",
        "H1-1 Length",
        "Canonical Link Element 1",
        "Crawl Depth",
        "Inlinks",
        "Unique Inlinks",
        "Outlinks",
        "Unique Outlinks",
        "Link Score",
        "Follow Inlinks",
        "Nofollow Inlinks",
        "Nofollow Outlinks",
        "Response Time (ms)",
        "Rendered with JS",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            row = _sf_row(url, p)
            st = link_stats.get(url)
            w.writerow(
                {
                    **row,
                    "Title 1 Pixel Width": p.serp_title_pixels,
                    "Unique Inlinks": st.unique_inlinks if st else len(p.inlinks),
                    "Outlinks": st.outlinks if st else 0,
                    "Unique Outlinks": st.unique_outlinks if st else 0,
                    "Link Score": st.link_score if st else 0,
                    "Follow Inlinks": st.follow_inlinks if st else len(p.inlinks),
                    "Nofollow Inlinks": st.nofollow_inlinks if st else 0,
                    "Nofollow Outlinks": st.nofollow_outlinks if st else 0,
                    "Rendered with JS": "Yes" if p.rendered_with_js else "",
                }
            )


def export_csv_headers(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Status Code", "Content-Type", "X-Robots-Tag", "Strict-Transport-Security", "Cache-Control"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "Status Code": p.status,
                    "Content-Type": p.response_headers.get("content-type", p.content_type or ""),
                    "X-Robots-Tag": p.response_headers.get("x-robots-tag", ""),
                    "Strict-Transport-Security": p.response_headers.get("strict-transport-security", ""),
                    "Cache-Control": p.response_headers.get("cache-control", ""),
                }
            )


def export_csv_amp(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "AMP HTML URL", "Indexability"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "AMP HTML URL": p.amp_html_url or "",
                    "Indexability": p.indexability,
                }
            )


def export_csv_custom(report: CrawlReport, path: Path) -> None:
    names: set[str] = set()
    for p in report.pages.values():
        names.update(p.custom_fields.keys())
    if not names:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            f.write("Address\n")
        return
    fields = ["Address", *sorted(names)]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            row = {"Address": url, **{n: p.custom_fields.get(n, "") for n in names}}
            w.writerow(row)


def export_csv_console(report: CrawlReport, path: Path) -> None:
    fields = ["Address", "Console Messages"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, p in sorted(report.pages.items()):
            w.writerow(
                {
                    "Address": url,
                    "Console Messages": " | ".join(p.console_messages[:20]),
                }
            )


def export_all_sf_reports(report: CrawlReport, out_dir: Path) -> list[str]:
    """匯出 SF 對齊分頁 CSV，回傳檔名列表。"""
    mapping = {
        "internal.csv": export_sf_internal_enhanced,
        "all_inlinks.csv": export_csv_all_inlinks,
        "outlinks.csv": export_csv_outlinks,
        "anchor_text.csv": export_csv_anchor_text,
        "orphan_pages.csv": export_csv_orphan_pages,
        "broken_external.csv": export_csv_broken_external,
        "h2.csv": export_csv_h2,
        "h3.csv": export_csv_h3,
        "robots.csv": export_csv_robots,
        "duplicate_content.csv": export_csv_duplicate_content,
        "javascript.csv": export_csv_javascript,
        "meta_descriptions.csv": export_csv_meta_descriptions,
        "meta_keywords.csv": export_csv_meta_keywords,
        "external.csv": export_csv_external,
        "security.csv": export_csv_security,
        "url.csv": export_csv_url_audit,
        "pagination.csv": export_csv_pagination,
        "directives.csv": export_csv_directives,
        "structured_data.csv": export_csv_structured_data,
        "content.csv": export_csv_content,
        "sitemap_diff.csv": export_csv_sitemap_diff,
        "hreflang.csv": export_csv_hreflang,
        "headers.csv": export_csv_headers,
        "amp.csv": export_csv_amp,
        "custom.csv": export_csv_custom,
        "console.csv": export_csv_console,
    }
    names = []
    for name, fn in mapping.items():
        fn(report, out_dir / name)
        names.append(name)
    return names
