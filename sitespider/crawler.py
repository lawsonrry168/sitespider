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
from typing import Any, Callable, Literal
from urllib.parse import urlparse, urljoin, urlunparse

import requests
from bs4 import BeautifulSoup

from sitespider.issues import ISSUE_LABELS
from sitespider.lighthouse_runner import LighthouseScores, run_lighthouse_batch
from sitespider.robots import RobotsManager, meta_robots_noindex
from sitespider.sitemap import fetch_sitemap_urls, file_urls_from_sitemap

_AUDIT_ISSUE_CODES = frozenset(ISSUE_LABELS.keys())

SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".avif")


@dataclass
class ImageInfo:
    src: str
    alt: str | None
    resolved: str
    status: int | None
    issue: str | None = None
    width: int | None = None
    height: int | None = None
    loading: str | None = None
    content_type: str | None = None
    byte_size: int | None = None
    local_file: str | None = None


@dataclass
class LinkInfo:
    href: str
    text: str
    resolved: str
    link_type: Literal["internal", "external", "asset", "anchor", "other"]
    status: int | None = None
    issue: str | None = None
    nofollow: bool = False
    link_position: str = "Content"


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
    html_lang: str | None = None
    request_url: str | None = None
    redirect_chain: list[str] = field(default_factory=list)
    has_viewport: bool = False
    indexability: str = "Indexable"
    indexability_status: str = ""
    hreflangs: list[dict[str, str]] = field(default_factory=list)
    response_headers: dict[str, str] = field(default_factory=dict)
    meta_keywords: str | None = None
    pagination_prev: str | None = None
    pagination_next: str | None = None
    content_hash: str = ""
    serp_title_pixels: int = 0
    serp_meta_pixels: int = 0
    mixed_content_count: int = 0
    is_https: bool = False
    rendered_with_js: bool = False
    amp_html_url: str | None = None
    console_messages: list[str] = field(default_factory=list)
    screenshot_path: str | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)


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
    require_json_ld: bool = False
    thin_content_min_words: int = 300
    sitemap_path_prefixes: tuple[str, ...] = ()
    exclude_path_prefixes: tuple[str, ...] = ()
    defer_link_checks: bool = True
    check_images_on_fetch: bool = False
    audit_hreflang: bool = True
    json_ld_rules: tuple[tuple[str, tuple[str, ...]], ...] = ()
    finalize_check_workers: int = 8
    render_javascript: bool = False
    render_wait_until: str = "domcontentloaded"
    render_extra_wait_ms: int = 500
    render_timeout_ms: int = 30_000
    list_mode: bool = False
    seed_urls: tuple[str, ...] = ()
    crawl_list_only: bool = False
    strip_query_string: bool = False
    custom_extractions: tuple = ()  # tuple[ExtractionRule,...] loaded at runtime
    save_screenshots: bool = False
    capture_console: bool = True
    download_images: bool = False
    max_images_download: int = 300
    images_same_host_only: bool = True
    gsc_site_url: str | None = None
    gsc_inspect_max: int = 0
    fetch_policy: str = "http"  # http | js | auto
    auto_js_path_patterns: tuple[str, ...] = ()
    cache_responses: bool = False
    cache_dir: str | None = None
    crawldir: str | None = None
    resume_crawl: bool = False
    checkpoint_interval: int = 25
    adaptive_extractions: bool = False
    stealth_headers: bool = False
    use_scrapling: bool = False


@dataclass
class CrawlReport:
    start_url: str
    mode: Literal["http", "file"]
    config: CrawlConfig = field(default_factory=CrawlConfig)
    pages: dict[str, PageResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    robots_info: dict = field(default_factory=dict)
    llms_info: dict = field(default_factory=dict)
    sitemap_urls: list[str] = field(default_factory=list)
    blocked_urls: list[str] = field(default_factory=list)
    sitemap_not_crawled: list[str] = field(default_factory=list)
    sitemap_not_in_sitemap: list[str] = field(default_factory=list)
    js_rendered_pages: int = 0
    screenshot_dir: str | None = None
    lighthouse: dict[str, dict] = field(default_factory=dict)
    gsc_rich_inspections: dict[str, dict[str, str]] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def summary_issues(self) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = defaultdict(list)
        titles: dict[str, list[str]] = defaultdict(list)

        metas: dict[str, list[str]] = defaultdict(list)
        for url, page in self.pages.items():
            for issue in page.issues:
                buckets[issue].append(url)
            if page.title:
                titles[page.title.strip()].append(url)
            if page.meta_description and page.meta_description.strip():
                metas[page.meta_description.strip()].append(url)

        for _title, urls in titles.items():
            if len(urls) <= 1:
                continue
            if len({urlparse(u).path for u in urls}) <= 1:
                continue
            for u in urls:
                if "duplicate_title" not in self.pages[u].issues:
                    self.pages[u].issues.append("duplicate_title")
            buckets["duplicate_title"].extend(urls)

        for _meta, urls in metas.items():
            if len(urls) <= 1:
                continue
            for u in urls:
                if "duplicate_meta_description" not in self.pages[u].issues:
                    self.pages[u].issues.append("duplicate_meta_description")
            buckets["duplicate_meta_description"].extend(urls)

        return dict(buckets)


def _normalize_url(url: str, base: str) -> str | None:
    if not url or url.strip().startswith(SKIP_SCHEMES):
        return None
    raw = url.strip()
    # Webflow 等 CMS：canonical/href 常為 "www.example.com/path"（無 scheme）
    if "://" not in raw:
        if raw.startswith("//"):
            base_scheme = urlparse(base).scheme or "https"
            raw = f"{base_scheme}:{raw}"
        elif re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", raw, re.I):
            raw = "https://" + raw.lstrip("/")
    joined = urljoin(base, raw)
    parsed = urlparse(joined)
    if "://" in (parsed.path or ""):
        return None
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


def _parse_img_dimension(value) -> int | None:
    if value is None or value == "":
        return None
    s = str(value).strip()
    if not s or s.endswith("%"):
        return None
    try:
        n = int(float(s))
        return n if n > 0 else None
    except ValueError:
        return None


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


def _audit_page(page: PageResult, config: CrawlConfig | None = None) -> None:
    cfg = config or CrawlConfig()
    page.issues = [i for i in page.issues if i not in _AUDIT_ISSUE_CODES]
    issues = page.issues
    if page.blocked_by_robots:
        issues.append("blocked_by_robots")
    if meta_robots_noindex(page.meta_robots):
        issues.append("meta_noindex")
        return
    if not page.og_title:
        issues.append("missing_og_tags")
    if cfg.require_json_ld and not page.has_json_ld:
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
    elif len(page.meta_description.strip()) < 50:
        issues.append("meta_description_too_short")
    if not page.h1:
        issues.append("missing_h1")
    elif len(page.h1) > 1:
        issues.append("multiple_h1")
    if not page.canonical:
        issues.append("missing_canonical")
    elif page.canonical:
        page_norm = _canonical_for_compare(page.url)
        canon_norm = _canonical_for_compare(page.canonical)
        if page_norm and canon_norm and page_norm != canon_norm:
            issues.append("canonical_mismatch")
    thin_min = cfg.thin_content_min_words or 0
    if thin_min > 0 and page.word_count < thin_min:
        issues.append("thin_content")
    if not page.html_lang or not str(page.html_lang).strip():
        issues.append("missing_html_lang")
    if not page.has_viewport:
        issues.append("missing_viewport")
    if len(page.redirect_chain) > 1:
        issues.append("redirect_chain")
    if (
        page.title
        and page.h1
        and page.title.strip().lower() == page.h1[0].strip().lower()
    ):
        issues.append("title_equals_h1")
    for link in page.links:
        if link.link_type == "internal" and link.status is not None and link.status >= 400:
            issues.append("broken_internal_link")
            break
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

    from sitespider.indexability import apply_indexability

    apply_indexability(page)


def _path_excluded(url: str, prefixes: tuple[str, ...]) -> bool:
    if not prefixes:
        return False
    path = urlparse(url).path or "/"
    for raw in prefixes:
        p = raw.strip()
        if not p:
            continue
        if not p.startswith("/"):
            p = "/" + p
        if path.startswith(p):
            return True
    return False


def _canonical_for_compare(url: str) -> str:
    p = urlparse(url)
    path = p.path or "/"
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    return urlunparse((p.scheme, p.netloc, path, "", "", ""))


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
        crawldir: Path | None = None,
    ):
        self.start_url = start_url
        self.mode = mode
        self.site_root = (site_root or Path.cwd()).resolve()
        self.config = config or CrawlConfig()
        self.user_agent = user_agent
        self.on_progress = on_progress
        self.lighthouse_out = lighthouse_out
        self.crawldir = crawldir
        if self.crawldir is None and self.config.crawldir:
            self.crawldir = Path(self.config.crawldir)
        self.report: CrawlReport | None = None
        self._screenshot_dir = None
        if config.save_screenshots and lighthouse_out:
            self._screenshot_dir = lighthouse_out.parent / "screenshots"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._session_local = threading.local()
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
        self._js_renderer = None
        self._need_playwright = mode == "http" and (
            self.config.render_javascript
            or self.config.fetch_policy in ("js", "auto")
        )
        if self._need_playwright:
            from sitespider.js_render import playwright_available

            if not playwright_available():
                if self.config.render_javascript or self.config.fetch_policy == "js":
                    raise RuntimeError(
                        "已啟用 JS 渲染，但未安裝 Playwright。請執行：\n"
                        '  pip install "sitespider[browser]"\n'
                        "  playwright install chromium"
                    )
        from sitespider.response_cache import ResponseCache

        cache_root = Path(self.config.cache_dir) if self.config.cache_dir else (
            self.crawldir / ".cache" if self.crawldir else self.site_root / ".sitespider" / "cache"
        )
        self._response_cache = ResponseCache(
            cache_root,
            enabled=bool(self.config.cache_responses and mode == "http"),
        )
        self._extraction_rules = ()
        if config.custom_extractions:
            from sitespider.custom_extract import ExtractionRule

            rules = []
            for raw in config.custom_extractions:
                if isinstance(raw, dict):
                    r = ExtractionRule.from_dict(raw)
                    if r:
                        rules.append(r)
            self._extraction_rules = tuple(rules)

    def _close_js_renderer(self) -> None:
        if self._js_renderer is not None:
            self._js_renderer.close()
            self._js_renderer = None

    def _ensure_js_renderer(self) -> None:
        if self._js_renderer is not None or not self._need_playwright:
            return
        from sitespider.js_render import PlaywrightRenderer, playwright_available

        if not playwright_available():
            return
        self._js_renderer = PlaywrightRenderer(
            user_agent=self.user_agent,
            timeout_ms=self.config.render_timeout_ms,
            wait_until=self.config.render_wait_until,  # type: ignore[arg-type]
            extra_wait_ms=self.config.render_extra_wait_ms,
            capture_console=self.config.capture_console,
        )

    def _maybe_checkpoint(
        self,
        report: CrawlReport,
        seen: set[str],
        queue: deque,
        crawled: int,
        *,
        completed: bool = False,
    ) -> None:
        if not self.crawldir:
            return
        interval = max(1, int(self.config.checkpoint_interval or 25))
        if not completed and crawled % interval != 0:
            return
        from sitespider.crawl_checkpoint import save_checkpoint

        save_checkpoint(self.crawldir, report=report, seen=seen, queue=queue, completed=completed)

    def crawl(self) -> CrawlReport:
        cfg = self.config
        workers = cfg.workers
        if cfg.render_javascript or cfg.fetch_policy in ("js", "auto"):
            workers = min(workers, 2)
        report = CrawlReport(start_url=self.start_url, mode=self.mode, config=cfg)
        report.robots_info = {
            "source": self.robots.info.source,
            "crawl_delay": self.robots.info.crawl_delay,
            "disallowed": self.robots.info.disallowed_paths,
            "sitemaps": self.robots.info.sitemap_urls,
        }

        seen: set[str] = set()
        queue: deque[tuple[str, int, str | None, str]] = deque()

        try:
            return self._crawl_loop(report, cfg, workers, seen, queue)
        finally:
            self._close_js_renderer()

    def _crawl_loop(
        self,
        report: CrawlReport,
        cfg: CrawlConfig,
        workers: int,
        seen: set[str],
        queue: deque,
    ) -> CrawlReport:
        crawled = 0
        if self.crawldir and cfg.resume_crawl:
            from sitespider.crawl_checkpoint import load_checkpoint, restore_from_checkpoint

            ckpt = load_checkpoint(self.crawldir)
            if ckpt:
                report, seen, queue, crawled = restore_from_checkpoint(ckpt)
                report.errors.append(f"resumed_from_checkpoint: {crawled} pages")

        start = self._initial_start()
        if not report.pages and not start and not cfg.seed_urls:
            report.errors.append("找不到起始頁 index.html")
            return report

        if not queue and not report.pages:
            if cfg.seed_urls:
                for u in cfg.seed_urls:
                    norm = self._canonical_page_url(u)
                    if norm not in seen:
                        queue.append((u, 0, None, "list"))
            elif start:
                queue.append((start, 0, None, "start"))

            if cfg.use_sitemap and not cfg.list_mode:
                sitemap_seeds = self._sitemap_seeds(report)
                for u in sitemap_seeds:
                    norm = self._canonical_page_url(u)
                    if norm not in seen:
                        queue.append((u, 0, None, "sitemap"))

        self.report = report
        if not crawled:
            crawled = len(report.pages)
        total_estimate = max(cfg.max_pages, len(queue), crawled)

        while queue and crawled < cfg.max_pages:
            batch: list[tuple[str, int, str | None, str]] = []
            while queue and len(batch) < workers:
                item = queue.popleft()
                url, depth, referrer, seed = item
                norm = self._canonical_page_url(url)
                if norm in seen or depth > cfg.max_depth:
                    continue
                if _path_excluded(url, cfg.exclude_path_prefixes):
                    seen.add(norm)
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
                    from sitespider.indexability import apply_indexability

                    apply_indexability(blocked)
                    with self._pages_lock:
                        report.pages[norm] = blocked
                    continue
                seen.add(norm)
                batch.append((url, depth, referrer, seed))

            if not batch:
                continue

            with ThreadPoolExecutor(max_workers=min(workers, len(batch))) as pool:
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
                        self._maybe_checkpoint(report, seen, queue, crawled)

                    for link_url in new_links:
                        tnorm = self._canonical_page_url(link_url)
                        if tnorm not in seen and crawled + len(queue) < cfg.max_pages:
                            queue.append((link_url, depth + 1, norm, "link"))

                    total_estimate = max(total_estimate, crawled + len(queue))

        self._finalize_inlinks(report)
        self._finalize_resource_checks(report)
        self._mark_orphans(report)

        if cfg.run_lighthouse and self.mode == "http":
            self._run_lighthouse(report)

        from sitespider.post_crawl import run_post_crawl_audits

        run_post_crawl_audits(
            report,
            mode=self.mode,
            canonical_fn=self._canonical_page_url,
            config=cfg,
        )

        report.finished_at = time.time()
        report.js_rendered_pages = sum(
            1 for p in report.pages.values() if p.rendered_with_js
        )
        if self._screenshot_dir:
            report.screenshot_dir = str(self._screenshot_dir)
        report.summary_issues()
        self._maybe_checkpoint(report, seen, queue, crawled, completed=True)
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
                _audit_page(report.pages[norm], self.config)

    def _sitemap_seeds(self, report: CrawlReport) -> list[str]:
        extra = self.robots.info.sitemap_urls
        if self.mode == "file":
            urls = file_urls_from_sitemap(
                self.site_root,
                path_prefixes=self.config.sitemap_path_prefixes,
            )
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
            path_prefixes=self.config.sitemap_path_prefixes,
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
        if not self.config.crawl_list_only:
            base = self._base_scope()
            for link in page.links:
                if link.link_type == "internal" and _is_internal_html(link.resolved, base):
                    if self.config.respect_robots and not self.robots.allowed(link.resolved):
                        continue
                    new_links.append(link.resolved)
        return norm, page, new_links

    def _http_session(self) -> requests.Session:
        """並行爬取時每執行緒獨立 Session（requests.Session 非 thread-safe）。"""
        sess = getattr(self._session_local, "session", None)
        if sess is None:
            sess = requests.Session()
            sess.headers["User-Agent"] = self.user_agent
            self._session_local.session = sess
        return sess

    def _resolve_link_status(self, resolved: str, report: CrawlReport) -> int | None:
        target = self._canonical_page_url(resolved)
        if target in report.pages:
            return report.pages[target].status
        if self.mode == "http":
            return self._check_url(resolved)
        return None

    def _batch_check_urls(self, urls: set[str]) -> None:
        """並行 HEAD 尚未快取的 URL。"""
        pending = [u for u in urls if u and u not in self._checked_urls]
        if not pending:
            return
        workers = min(max(1, self.config.finalize_check_workers), len(pending))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(self._check_url, pending))

    def _finalize_resource_checks(self, report: CrawlReport) -> None:
        """爬取結束後批次檢查內鏈／圖片（預設爬取中不逐條 HEAD）。"""
        cfg = self.config
        pending_network: set[str] = set()

        for page in report.pages.values():
            for link in page.links:
                if link.link_type == "internal":
                    if not cfg.defer_link_checks and link.status is not None:
                        continue
                    target = self._canonical_page_url(link.resolved)
                    if target in report.pages:
                        link.status = report.pages[target].status
                    elif self.mode == "http":
                        pending_network.add(link.resolved)
                elif link.link_type == "external" and cfg.check_external:
                    pending_network.add(link.resolved)

            if self.mode == "http" and not cfg.check_images_on_fetch:
                for img in page.images:
                    if not img.resolved or img.resolved.startswith("data:"):
                        continue
                    pending_network.add(img.resolved)

        if self.mode == "http" and pending_network:
            self._batch_check_urls(pending_network)

        for page in report.pages.values():
            for link in page.links:
                if link.link_type == "internal":
                    if not cfg.defer_link_checks and link.status is not None:
                        continue
                    target = self._canonical_page_url(link.resolved)
                    if target in report.pages:
                        link.status = report.pages[target].status
                    elif link.status is None:
                        link.status = self._checked_urls.get(link.resolved)
                    if link.status is not None and link.status >= 400:
                        link.issue = "broken_link"
                    elif link.issue == "broken_link":
                        link.issue = None
                elif link.link_type == "external" and cfg.check_external:
                    if link.status is None:
                        link.status = self._checked_urls.get(link.resolved)
                    if link.status is not None and link.status >= 400:
                        link.issue = "broken_link"

            if self.mode == "http" and not cfg.check_images_on_fetch:
                for img in page.images:
                    if not img.resolved or img.resolved.startswith("data:"):
                        continue
                    if img.status is None:
                        img.status = self._checked_urls.get(img.resolved)
                    if img.status is not None and img.status >= 400:
                        img.issue = "broken_image"
                    elif img.alt is None or not str(img.alt).strip():
                        img.issue = (img.issue or "missing_alt").strip()

            _audit_page(page, self.config)

        if cfg.json_ld_rules:
            from sitespider.json_ld_audit import JsonLdRule, audit_json_ld_rules

            rules = tuple(
                JsonLdRule(types=types, path_contains=path)
                for path, types in cfg.json_ld_rules
                if path and types
            )
            audit_json_ld_rules(report, rules)

        if cfg.audit_hreflang and self.mode == "http":
            from sitespider.hreflang import audit_hreflang

            audit_hreflang(
                report,
                canonical_fn=self._canonical_page_url,
                check_url=self._check_url,
            )

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
        if self.config.strip_query_string:
            p = p._replace(query="", fragment="")
            url = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
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
            _audit_page(page, self.config)
            return page

        html = path.read_text(encoding="utf-8", errors="replace")
        base = path.parent.as_uri() + "/"
        self._parse_html(page, html, base)
        self._check_resources_file(page, path.parent)
        _audit_page(page, self.config)
        return page

    def _apply_html_body(self, page: PageResult, html_body: str, base_url: str) -> None:
        page.content_type = "text/html; charset=UTF-8"
        self._parse_html(page, html_body, base_url)
        from sitespider.post_crawl import compute_content_hash_from_html

        page.content_hash = compute_content_hash_from_html(html_body)
        if self._extraction_rules:
            if self.config.adaptive_extractions:
                from sitespider.adaptive_extract import apply_extractions_adaptive

                page.custom_fields = apply_extractions_adaptive(html_body, self._extraction_rules)
            else:
                from sitespider.custom_extract import apply_extractions

                page.custom_fields = apply_extractions(html_body, self._extraction_rules)
        if self.config.check_images_on_fetch:
            self._check_resources_http(page, base_url)

    def _fetch_http(self, url: str, depth: int, t0: float) -> PageResult:
        from sitespider.fetch_policy import resolve_fetch_mode, should_retry_with_js

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
        page.request_url = url
        try:
            if self.config.use_scrapling and _is_html_url(url):
                from sitespider.optional_scrapling import fetch_html

                ext = fetch_html(url, stealth=self.config.stealth_headers, timeout=self.config.timeout)
                page.response_ms = (time.perf_counter() - t0) * 1000
                if ext.error or not ext.html:
                    page.status = 0
                    page.issues.append(f"request_failed: {ext.error or 'scrapling empty'}")
                else:
                    page.status = ext.status or 200
                    page.url = ext.final_url
                    if ext.final_url != url:
                        page.redirect_chain = [url, ext.final_url]
                    self._apply_html_body(page, ext.html, ext.final_url)
                _audit_page(page, self.config)
                return page

            fetch_mode = resolve_fetch_mode(
                url,
                policy=self.config.fetch_policy,
                render_javascript=self.config.render_javascript,
                auto_patterns=self.config.auto_js_path_patterns,
            )
            if fetch_mode == "js" and _is_html_url(url):
                self._ensure_js_renderer()
                if not self._js_renderer:
                    fetch_mode = "http"
            if self._js_renderer and fetch_mode == "js" and _is_html_url(url):
                shot_path = None
                if self._screenshot_dir:
                    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", urlparse(url).path)[:80] or "root"
                    shot_path = str(self._screenshot_dir / f"{safe}.png")
                rendered = self._js_renderer.fetch(url, screenshot_path=shot_path)
                page.response_ms = (time.perf_counter() - t0) * 1000
                if rendered.error or not rendered.html:
                    page.status = 0
                    page.issues.append(f"request_failed: {rendered.error or 'empty render'}")
                else:
                    page.status = rendered.status or 200
                    page.url = rendered.final_url
                    if rendered.final_url != url:
                        page.redirect_chain = [url, rendered.final_url]
                    page.rendered_with_js = True
                    page.console_messages = list(rendered.console_messages or [])
                    if shot_path:
                        page.screenshot_path = shot_path
                    self._apply_html_body(page, rendered.html, rendered.final_url)
                _audit_page(page, self.config)
                return page

            cached = self._response_cache.get(url)
            if cached and "text/html" in cached.headers.get("content-type", "text/html"):
                page.status = cached.status
                page.content_type = cached.headers.get("content-type", "text/html")
                page.response_ms = (time.perf_counter() - t0) * 1000
                page.url = cached.final_url
                if cached.final_url != url:
                    page.redirect_chain = [url, cached.final_url]
                page.response_headers = dict(cached.headers)
                self._apply_html_body(page, cached.text, cached.final_url)
            else:
                headers = {"Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"}
                if self.config.stealth_headers:
                    headers.update(
                        {
                            "User-Agent": self.user_agent,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Sec-Fetch-Dest": "document",
                            "Sec-Fetch-Mode": "navigate",
                            "Upgrade-Insecure-Requests": "1",
                        }
                    )
                resp = self._http_session().get(
                    url, timeout=self.config.timeout, allow_redirects=True, headers=headers
                )
                page.status = resp.status_code
                page.content_type = resp.headers.get("Content-Type")
                page.response_ms = (time.perf_counter() - t0) * 1000
                page.url = resp.url
                if resp.history:
                    page.redirect_chain = [h.url for h in resp.history] + [resp.url]
                elif resp.url != url:
                    page.redirect_chain = [url, resp.url]
                if "text/html" in (page.content_type or ""):
                    page.response_headers = {k.lower(): v for k, v in resp.headers.items()}
                    self._apply_html_body(page, resp.text, resp.url)
                    self._response_cache.put(
                        url,
                        final_url=resp.url,
                        status=resp.status_code,
                        headers=page.response_headers,
                        text=resp.text,
                    )
                    if (
                        self.config.fetch_policy == "auto"
                        and not self.config.render_javascript
                        and should_retry_with_js(resp.text, word_count=page.word_count)
                    ):
                        self._ensure_js_renderer()
                        if self._js_renderer:
                            rendered = self._js_renderer.fetch(url)
                            if rendered.html and not rendered.error:
                                page.rendered_with_js = True
                                page.url = rendered.final_url
                                self._apply_html_body(page, rendered.html, rendered.final_url)

        except requests.RequestException as e:
            page.status = 0
            page.issues.append(f"request_failed: {e}")
        _audit_page(page, self.config)
        return page

    def _parse_html(self, page: PageResult, html: str, base: str) -> None:
        soup = BeautifulSoup(html, "lxml")
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            page.html_lang = str(html_tag["lang"]).strip()
        if soup.title and soup.title.string:
            page.title = soup.title.string.strip()
        desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if desc and desc.get("content"):
            page.meta_description = desc["content"].strip()
        robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots and robots.get("content"):
            page.meta_robots = robots["content"].strip()
        keywords = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
        if keywords and keywords.get("content"):
            page.meta_keywords = keywords["content"].strip()
        viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        if viewport and (viewport.get("content") or "").strip():
            page.has_viewport = True
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

        seen_hrefs: set[str] = set()

        from sitespider.link_context import detect_link_position, is_nofollow

        def _add_link(
            href: str,
            text: str = "",
            *,
            check_status: bool = True,
            anchor_el=None,
            rel: Any = None,
        ) -> None:
            if not href or href in seen_hrefs:
                return
            seen_hrefs.add(href)
            resolved = _normalize_url(href, base)
            if not resolved:
                return
            ltype = _classify_link(resolved, base)
            link = LinkInfo(
                href=href,
                text=(text or "")[:120],
                resolved=resolved,
                link_type=ltype,
                nofollow=is_nofollow(rel),
                link_position=detect_link_position(anchor_el) if anchor_el else "Content",
            )
            eager = not self.config.defer_link_checks
            if check_status and ltype == "internal" and eager:
                link.status = self._check_url(resolved)
                if link.status is not None and link.status >= 400:
                    link.issue = "broken_link"
            elif (
                check_status
                and ltype == "external"
                and self.config.check_external
            ):
                link.status = self._check_url(resolved)
                if link.status is not None and link.status >= 400:
                    link.issue = "broken_link"
            page.links.append(link)

        for a in soup.find_all("a", href=True):
            _add_link(
                a["href"],
                _strip_text(a),
                check_status=True,
                anchor_el=a,
                rel=a.get("rel"),
            )

        # 僅用於發現更多爬取種子，不對 rel canonical 做連結失效檢查（避免錯誤 canonical 誤報）
        for link_el in soup.find_all("link", href=True):
            rel = link_el.get("rel") or []
            if isinstance(rel, str):
                rel = [rel]
            rel_lower = " ".join(rel).lower()
            if any(
                token in rel_lower
                for token in ("alternate", "canonical", "next", "prev", "prefetch")
            ):
                hint = link_el.get("hreflang") or rel_lower
                resolved_alt = _normalize_url(link_el["href"], base)
                if resolved_alt:
                    if "next" in rel_lower:
                        page.pagination_next = resolved_alt
                    if "prev" in rel_lower:
                        page.pagination_prev = resolved_alt
                if "amphtml" in rel_lower and resolved_alt:
                    page.amp_html_url = resolved_alt
                if "alternate" in rel_lower and link_el.get("hreflang") and resolved_alt:
                    page.hreflangs.append(
                        {
                            "lang": str(link_el["hreflang"]).strip(),
                            "url": link_el["href"],
                            "resolved": resolved_alt,
                        }
                    )
                _add_link(link_el["href"], f"link {hint}", check_status=False)

        og_url = soup.find("meta", attrs={"property": re.compile(r"^og:url$", re.I)})
        if og_url and og_url.get("content"):
            _add_link(og_url["content"].strip(), "og:url", check_status=False)

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            srcset = img.get("srcset") or ""
            img_urls: list[str] = []
            if src:
                img_urls.append(src)
            for part in srcset.split(","):
                part = part.strip()
                if not part:
                    continue
                u = part.split()[0]
                if u and u not in img_urls:
                    img_urls.append(u)
            if not img_urls:
                page.images.append(
                    ImageInfo(src="", alt=img.get("alt"), resolved="", status=None, issue="missing_src")
                )
                continue
            alt = img.get("alt")
            w = _parse_img_dimension(img.get("width"))
            h = _parse_img_dimension(img.get("height"))
            loading = (img.get("loading") or "").strip().lower() or None
            for u in img_urls:
                resolved = _normalize_url(u, base) or u
                page.images.append(
                    ImageInfo(
                        src=u,
                        alt=alt,
                        resolved=resolved,
                        status=None,
                        width=w,
                        height=h,
                        loading=loading,
                    )
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
            sess = self._http_session()
            r = sess.head(url, timeout=self.config.timeout, allow_redirects=True)
            if r.status_code == 405:
                r = sess.get(url, timeout=self.config.timeout, stream=True)
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
        "sitemap_not_crawled": report.sitemap_not_crawled,
        "sitemap_not_in_sitemap": report.sitemap_not_in_sitemap,
        "js_rendered_pages": report.js_rendered_pages,
        "blocked_urls": report.blocked_urls,
        "lighthouse": report.lighthouse,
        "llms_info": report.llms_info,
        "gsc_rich_inspections": report.gsc_rich_inspections,
        "pages": {url: asdict(p) for url, p in report.pages.items()},
        "errors": report.errors,
    }
