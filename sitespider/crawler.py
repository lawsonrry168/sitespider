"""
SEO 網站爬蟲核心 — 並行爬取、robots.txt、sitemap 種子、Lighthouse。
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlparse, urljoin, urlunparse

import requests
from bs4 import BeautifulSoup

from sitespider.lighthouse_runner import LighthouseScores, run_lighthouse_batch
from sitespider.robots import RobotsManager, meta_robots_noindex
from sitespider.sitemap import fetch_sitemap_urls, file_urls_from_sitemap

SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".avif")


@dataclass
class ImageInfo:
    src: str
    alt: str | None
    resolved: str
    status: int | None
    issue: str | None = None


@dataclass
class LinkInfo:
    href: str
    text: str
    resolved: str
    link_type: Literal["internal", "external", "asset", "anchor", "other"]
    status: int | None = None
    issue: str | None = None


@dataclass
class LighthouseResult:
    performance: float | None = None
    accessibility: float | None = None
    best_practices: float | None = None
    seo: float | None = None
    error: str | None = None


@dataclass
class PageResult:
    url: str
    status: int
    content_type: str | None
    response_ms: float
    title: str | None
    meta_description: str | None
    meta_robots: str | None
    canonical: str | None
    h1: list[str] = field(default_factory=list)
    h2: list[str] = field(default_factory=list)
    h3: list[str] = field(default_factory=list)
    word_count: int = 0
    images: list[ImageInfo] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    inlinks: list[str] = field(default_factory=list)
    crawl_depth: int = 0
    source: Literal["http", "file"] = "http"
    blocked_by_robots: bool = False
    seed_source: str = "link"
    lighthouse: LighthouseResult | None = None
    og_title: str | None = None
    og_description: str | None = None
    has_json_ld: bool = False
    json_ld_types: list[str] = field(default_factory=list)


PAGES_EXPECT_JSON_LD = frozenset(
    {
        "index.html",
        "products.html",
        "product.html",
        "blog.html",
        "blog-post.html",
        "faq.html",
        "about.html",
        "guide.html",
        "nutrition.html",
        "contact.html",
    }
)


@dataclass
class CrawlConfig:
    max_pages: int = 500
    max_depth: int = 10
    workers: int = 4
    respect_robots: bool = True
    use_sitemap: bool = True
    check_external: bool = False
    run_lighthouse: bool = False
    lighthouse_max: int = 10
    timeout: float = 15.0


@dataclass
class CrawlReport:
    start_url: str
    mode: Literal["http", "file"]
    config: CrawlConfig = field(default_factory=CrawlConfig)
    pages: dict[str, PageResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    robots_info: dict = field(default_factory=dict)
    sitemap_urls: list[str] = field(default_factory=list)
    blocked_urls: list[str] = field(default_factory=list)
    lighthouse: dict[str, dict] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def summary_issues(self) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = defaultdict(list)
        titles: dict[str, list[str]] = defaultdict(list)

        for url, page in self.pages.items():
            for issue in page.issues:
                buckets[issue].append(url)
            if page.title:
                titles[page.title.strip()].append(url)

        for _title, urls in titles.items():
            if len(urls) <= 1:
                continue
            if len({urlparse(u).path for u in urls}) <= 1:
                continue
            for u in urls:
                if "duplicate_title" not in self.pages[u].issues:
                    self.pages[u].issues.append("duplicate_title")
            buckets["duplicate_title"].extend(urls)

        return dict(buckets)


def _normalize_url(url: str, base: str) -> str | None:
    if not url or url.strip().startswith(SKIP_SCHEMES):
        return None
    joined = urljoin(base, url.strip())
    parsed = urlparse(joined)
    if parsed.scheme not in ("http", "https", "file", ""):
        return None
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, "")
    )


def _same_site(url: str, base_parsed) -> bool:
    p = urlparse(url)
    if p.scheme == "file":
        return True
    return p.netloc == base_parsed.netloc or not p.netloc


def _is_html_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path.endswith((".css", ".js", ".json", ".xml", ".pdf", ".zip", ".woff", ".woff2")):
        return False
    if any(path.endswith(ext) for ext in IMAGE_EXTENSIONS if ext):
        return False
    return (
        not path
        or path.endswith("/")
        or path.endswith((".html", ".htm"))
        or "." not in Path(path).name
    )


def _is_internal_html(url: str, base: str) -> bool:
    if not _same_site(url, urlparse(base)):
        return False
    return _is_html_url(url)


def _strip_text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(separator=" ", strip=True))


def _word_count(soup: BeautifulSoup) -> int:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return len(re.findall(r"[\w\u4e00-\u9fff]+", text))


def _classify_link(resolved: str, base: str) -> Literal["internal", "external", "asset", "anchor", "other"]:
    p = urlparse(resolved)
    path = p.path.lower()
    if path.endswith(
        (".css", ".js", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".pdf")
    ) or any(path.endswith(ext) for ext in IMAGE_EXTENSIONS if ext):
        return "asset"
    if _same_site(resolved, urlparse(base)):
        return "internal"
    if p.scheme in ("http", "https") and p.netloc:
        return "external"
    return "other"


def _page_filename(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name
    return name if name else "index.html"


def _audit_page(page: PageResult) -> None:
    issues = page.issues
    if page.blocked_by_robots:
        issues.append("blocked_by_robots")
    if meta_robots_noindex(page.meta_robots):
        issues.append("meta_noindex")
        return
    if not page.og_title:
        issues.append("missing_og_tags")
    fname = _page_filename(page.url)
    if fname in PAGES_EXPECT_JSON_LD and not page.has_json_ld:
        issues.append("missing_json_ld")
    if page.status >= 400:
        issues.append("http_error")
    if not page.title or not page.title.strip():
        issues.append("missing_title")
    elif len(page.title) > 60:
        issues.append("title_too_long")
    elif len(page.title) < 10:
        issues.append("title_too_short")
    if not page.meta_description or not page.meta_description.strip():
        issues.append("missing_meta_description")
    elif len(page.meta_description) > 160:
        issues.append("meta_description_too_long")
    if not page.h1:
        issues.append("missing_h1")
    elif len(page.h1) > 1:
        issues.append("multiple_h1")
    for img in page.images:
        if img.status and img.status >= 400:
            issues.append("broken_image")
            break
        if img.alt is None or not str(img.alt).strip():
            issues.append("missing_alt")
            break
    if page.lighthouse and page.lighthouse.seo is not None and page.lighthouse.seo < 90:
        issues.append("lighthouse_seo_low")
    if page.lighthouse and page.lighthouse.performance is not None and page.lighthouse.performance < 50:
        issues.append("lighthouse_perf_low")


class SeoCrawler:
    def __init__(
        self,
        start_url: str,
        *,
        mode: Literal["http", "file"] = "http",
        site_root: Path | None = None,
        config: CrawlConfig | None = None,
        user_agent: str = "SiteSpider/1.0 (+https://github.com/sitespider/seo-crawl)",
        on_progress: Callable[[int, int, str], None] | None = None,
        lighthouse_out: Path | None = None,
    ):
        self.start_url = start_url
        self.mode = mode
        self.site_root = (site_root or Path.cwd()).resolve()
        self.config = config or CrawlConfig()
        self.user_agent = user_agent
        self.on_progress = on_progress
        self.lighthouse_out = lighthouse_out
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._checked_urls: dict[str, int | None] = {}
        self._check_lock = threading.Lock()
        self._pages_lock = threading.Lock()

        base_for_robots = start_url
        if mode == "file":
            base_for_robots = (self.site_root / "index.html").as_uri()

        self.robots = RobotsManager(
            base_for_robots,
            user_agent,
            site_root=self.site_root,
            mode=mode,
            session=self.session,
            enabled=self.config.respect_robots,
        )

    def crawl(self) -> CrawlReport:
        cfg = self.config
        report = CrawlReport(start_url=self.start_url, mode=self.mode, config=cfg)
        report.robots_info = {
            "source": self.robots.info.source,
            "crawl_delay": self.robots.info.crawl_delay,
            "disallowed": self.robots.info.disallowed_paths,
            "sitemaps": self.robots.info.sitemap_urls,
        }

        base_scope = self._base_scope()
        seen: set[str] = set()
        queue: deque[tuple[str, int, str | None, str]] = deque()

        start = self._initial_start()
        if not start:
            report.errors.append("找不到起始頁 index.html")
            return report

        queue.append((start, 0, None, "start"))

        if cfg.use_sitemap:
            sitemap_seeds = self._sitemap_seeds(report)
            for u in sitemap_seeds:
                norm = self._canonical_page_url(u)
                if norm not in seen:
                    queue.append((u, 0, None, "sitemap"))

        crawled = 0
        total_estimate = max(cfg.max_pages, len(queue))

        while queue and crawled < cfg.max_pages:
            batch: list[tuple[str, int, str | None, str]] = []
            while queue and len(batch) < cfg.workers:
                item = queue.popleft()
                url, depth, referrer, seed = item
                norm = self._canonical_page_url(url)
                if norm in seen or depth > cfg.max_depth:
                    continue
                if cfg.respect_robots and not self.robots.allowed(url):
                    report.blocked_urls.append(norm)
                    seen.add(norm)
                    blocked = PageResult(
                        url=url,
                        status=0,
                        content_type=None,
                        response_ms=0,
                        title=None,
                        meta_description=None,
                        meta_robots=None,
                        canonical=None,
                        crawl_depth=depth,
                        source=self.mode,
                        blocked_by_robots=True,
                        seed_source=seed,
                    )
                    blocked.issues.append("blocked_by_robots")
                    with self._pages_lock:
                        report.pages[norm] = blocked
                    continue
                seen.add(norm)
                batch.append((url, depth, referrer, seed))

            if not batch:
                continue

            with ThreadPoolExecutor(max_workers=min(cfg.workers, len(batch))) as pool:
                futures = {
                    pool.submit(self._process_one, url, depth, referrer, seed): (
                        url,
                        depth,
                        referrer,
                        seed,
                    )
                    for url, depth, referrer, seed in batch
                }
                for fut in as_completed(futures):
                    url, depth, referrer, seed = futures[fut]
                    try:
                        norm, page, new_links = fut.result()
                    except Exception as e:
                        report.errors.append(f"{url}: {e}")
                        continue

                    with self._pages_lock:
                        report.pages[norm] = page
                        crawled += 1
                        if self.on_progress:
                            self.on_progress(crawled, total_estimate, norm)

                    for link_url in new_links:
                        tnorm = self._canonical_page_url(link_url)
                        if tnorm not in seen and crawled + len(queue) < cfg.max_pages:
                            queue.append((link_url, depth + 1, norm, "link"))

                    total_estimate = max(total_estimate, crawled + len(queue))

        self._finalize_inlinks(report)
        self._mark_orphans(report)

        if cfg.run_lighthouse and self.mode == "http":
            self._run_lighthouse(report)

        report.finished_at = time.time()
        report.summary_issues()
        return report

    def _run_lighthouse(self, report: CrawlReport) -> None:
        out = self.lighthouse_out or Path("reports/lighthouse")
        http_urls = []
        for url, page in report.pages.items():
            if page.blocked_by_robots or page.status >= 400:
                continue
            if url.startswith("http"):
                http_urls.append(url)

        def lh_progress(cur, total, u):
            if self.on_progress:
                self.on_progress(cur, total, f"Lighthouse: {u}")

        scores = run_lighthouse_batch(
            http_urls,
            out,
            max_urls=self.config.lighthouse_max,
            on_progress=lh_progress,
        )
        for url, sc in scores.items():
            norm = self._canonical_page_url(url)
            report.lighthouse[url] = asdict(sc)
            if norm in report.pages:
                report.pages[norm].lighthouse = LighthouseResult(
                    performance=sc.performance,
                    accessibility=sc.accessibility,
                    best_practices=sc.best_practices,
                    seo=sc.seo,
                    error=sc.error,
                )
                _audit_page(report.pages[norm])

    def _sitemap_seeds(self, report: CrawlReport) -> list[str]:
        extra = self.robots.info.sitemap_urls
        if self.mode == "file":
            urls = file_urls_from_sitemap(self.site_root)
            report.sitemap_urls = urls
            return urls

        base = self.start_url
        urls, errs = fetch_sitemap_urls(
            base,
            site_root=self.site_root,
            mode=self.mode,
            session=self.session,
            extra_sitemap_urls=extra,
            user_agent=self.user_agent,
        )
        report.errors.extend(errs)
        report.sitemap_urls = urls
        return urls

    def _process_one(
        self, url: str, depth: int, referrer: str | None, seed: str
    ) -> tuple[str, PageResult, list[str]]:
        if self.config.respect_robots:
            self.robots.wait_crawl_delay()
        page = self._fetch_and_parse(url, depth)
        page.seed_source = seed
        norm = self._canonical_page_url(page.url)
        new_links: list[str] = []
        base = self._base_scope()
        for link in page.links:
            if link.link_type == "internal" and _is_internal_html(link.resolved, base):
                if self.config.respect_robots and not self.robots.allowed(link.resolved):
                    continue
                new_links.append(link.resolved)
        return norm, page, new_links

    def _finalize_inlinks(self, report: CrawlReport) -> None:
        graph: dict[str, list[str]] = defaultdict(list)
        for page_url, page in report.pages.items():
            for link in page.links:
                if link.link_type != "internal":
                    continue
                target = self._canonical_page_url(link.resolved)
                if target in report.pages:
                    graph[target].append(page_url)
        for target, sources in graph.items():
            report.pages[target].inlinks = sorted(set(sources))

    def _mark_orphans(self, report: CrawlReport) -> None:
        start_norm = self._canonical_page_url(self._initial_start() or "")
        for page_url, page in report.pages.items():
            if page_url == start_norm or page.blocked_by_robots:
                continue
            if page.seed_source == "sitemap" and not page.inlinks:
                continue
            if not page.inlinks:
                page.issues.append("orphan_page")

    def _initial_start(self) -> str | None:
        if self.mode == "file":
            p = self.site_root / "index.html"
            return p.as_uri() if p.exists() else None
        return self.start_url

    def _base_scope(self) -> str:
        if self.mode == "file":
            return (self.site_root / "index.html").as_uri()
        return self.start_url

    def _canonical_page_url(self, url: str) -> str:
        p = urlparse(url)
        path = p.path or "/"
        if path in ("/", ""):
            path = "/index.html"
        elif path.endswith("/"):
            path = path + "index.html"
        if self.mode == "file":
            return urlunparse(("file", "", path, "", p.query, ""))
        return urlunparse((p.scheme, p.netloc, path, "", p.query, ""))

    def _fetch_and_parse(self, url: str, depth: int) -> PageResult:
        t0 = time.perf_counter()
        if self.mode == "file":
            return self._fetch_file(url, depth, t0)
        return self._fetch_http(url, depth, t0)

    def _fetch_file(self, url: str, depth: int, t0: float) -> PageResult:
        if url.startswith("file:"):
            path = Path(urlparse(url).path)
        else:
            rel = urlparse(url).path.lstrip("/") or "index.html"
            path = (self.site_root / rel).resolve()

        page = PageResult(
            url=url,
            status=200 if path.exists() else 404,
            content_type="text/html",
            response_ms=(time.perf_counter() - t0) * 1000,
            title=None,
            meta_description=None,
            meta_robots=None,
            canonical=None,
            crawl_depth=depth,
            source="file",
        )
        if not path.exists():
            _audit_page(page)
            return page

        html = path.read_text(encoding="utf-8", errors="replace")
        base = path.parent.as_uri() + "/"
        self._parse_html(page, html, base)
        self._check_resources_file(page, path.parent)
        _audit_page(page)
        return page

    def _fetch_http(self, url: str, depth: int, t0: float) -> PageResult:
        page = PageResult(
            url=url,
            status=0,
            content_type=None,
            response_ms=0,
            title=None,
            meta_description=None,
            meta_robots=None,
            canonical=None,
            crawl_depth=depth,
            source="http",
        )
        try:
            resp = self.session.get(url, timeout=self.config.timeout, allow_redirects=True)
            page.status = resp.status_code
            page.content_type = resp.headers.get("Content-Type")
            page.response_ms = (time.perf_counter() - t0) * 1000
            page.url = resp.url
            if "text/html" in (page.content_type or ""):
                self._parse_html(page, resp.text, resp.url)
                self._check_resources_http(page, resp.url)
        except requests.RequestException as e:
            page.status = 0
            page.issues.append(f"request_failed: {e}")
        _audit_page(page)
        return page

    def _parse_html(self, page: PageResult, html: str, base: str) -> None:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string:
            page.title = soup.title.string.strip()
        desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if desc and desc.get("content"):
            page.meta_description = desc["content"].strip()
        robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots and robots.get("content"):
            page.meta_robots = robots["content"].strip()
        canonical = soup.find("link", rel=re.compile(r"canonical", re.I))
        if canonical and canonical.get("href"):
            page.canonical = _normalize_url(canonical["href"], base)
        page.h1 = [_strip_text(h) for h in soup.find_all("h1")]
        page.h2 = [_strip_text(h) for h in soup.find_all("h2")]
        page.h3 = [_strip_text(h) for h in soup.find_all("h3")]
        page.word_count = _word_count(BeautifulSoup(html, "lxml"))

        og_t = soup.find("meta", attrs={"property": re.compile(r"^og:title$", re.I)})
        if og_t and og_t.get("content"):
            page.og_title = og_t["content"].strip()
        og_d = soup.find("meta", attrs={"property": re.compile(r"^og:description$", re.I)})
        if og_d and og_d.get("content"):
            page.og_description = og_d["content"].strip()

        types: list[str] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text()
            if not raw or not raw.strip():
                continue
            try:
                data = json.loads(raw)
                page.has_json_ld = True
                types.extend(_extract_schema_types(data))
            except json.JSONDecodeError:
                continue
        page.json_ld_types = list(dict.fromkeys(types))

        for a in soup.find_all("a", href=True):
            resolved = _normalize_url(a["href"], base)
            if not resolved:
                continue
            ltype = _classify_link(resolved, base)
            link = LinkInfo(
                href=a["href"],
                text=_strip_text(a)[:120],
                resolved=resolved,
                link_type=ltype,
            )
            if ltype in ("internal", "external") and (
                self.config.check_external or ltype == "internal"
            ):
                link.status = self._check_url(resolved)
                if link.status and link.status >= 400:
                    link.issue = "broken_link"
            page.links.append(link)

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                page.images.append(
                    ImageInfo(src="", alt=img.get("alt"), resolved="", status=None, issue="missing_src")
                )
                continue
            resolved = _normalize_url(src, base) or src
            page.images.append(
                ImageInfo(src=src, alt=img.get("alt"), resolved=resolved, status=None)
            )

    def _check_resources_file(self, page: PageResult, page_dir: Path) -> None:
        for img in page.images:
            if not img.resolved:
                continue
            if img.resolved.startswith("http"):
                img.status = self._check_url(img.resolved)
            else:
                p = Path(urlparse(img.resolved).path)
                if not p.is_absolute():
                    p = (page_dir / img.src).resolve()
                img.status = 200 if p.exists() else 404
            if img.status and img.status >= 400:
                img.issue = "broken_image"
            if img.alt is None or not str(img.alt).strip():
                img.issue = (img.issue or "missing_alt").strip()

    def _check_resources_http(self, page: PageResult, base: str) -> None:
        for img in page.images:
            if img.resolved.startswith("data:"):
                img.status = 200
                continue
            img.status = self._check_url(img.resolved)
            if img.status and img.status >= 400:
                img.issue = "broken_image"
            if img.alt is None or not str(img.alt).strip():
                img.issue = (img.issue or "missing_alt").strip()

    def _check_url(self, url: str) -> int | None:
        with self._check_lock:
            if url in self._checked_urls:
                return self._checked_urls[url]
        try:
            r = self.session.head(url, timeout=self.config.timeout, allow_redirects=True)
            if r.status_code == 405:
                r = self.session.get(url, timeout=self.config.timeout, stream=True)
            code = r.status_code
        except requests.RequestException:
            code = None
        with self._check_lock:
            self._checked_urls[url] = code
        return code


def _extract_schema_types(data) -> list[str]:
    found: list[str] = []
    if isinstance(data, dict):
        t = data.get("@type")
        if isinstance(t, str):
            found.append(t)
        elif isinstance(t, list):
            found.extend(x for x in t if isinstance(x, str))
        for key in ("@graph", "mainEntity", "itemListElement"):
            child = data.get(key)
            if isinstance(child, list):
                for item in child:
                    found.extend(_extract_schema_types(item))
            elif child:
                found.extend(_extract_schema_types(child))
    elif isinstance(data, list):
        for item in data:
            found.extend(_extract_schema_types(item))
    return found


def discover_html_files(site_root: Path) -> list[str]:
    return sorted(str(p.relative_to(site_root)) for p in site_root.glob("*.html"))


def report_to_dict(report: CrawlReport) -> dict:
    return {
        "start_url": report.start_url,
        "mode": report.mode,
        "config": asdict(report.config),
        "page_count": len(report.pages),
        "duration_sec": (report.finished_at or time.time()) - report.started_at,
        "summary_issues": report.summary_issues(),
        "robots_info": report.robots_info,
        "sitemap_urls": report.sitemap_urls,
        "blocked_urls": report.blocked_urls,
        "lighthouse": report.lighthouse,
        "pages": {url: asdict(p) for url, p in report.pages.items()},
        "errors": report.errors,
    }
