"""爬取 checkpoint — 暫停後可從佇列與已爬頁面恢復（借鑑 Scrapling crawldir）。"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, fields
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

CHECKPOINT_VERSION = 1
CHECKPOINT_NAME = "crawl-checkpoint.json"


def checkpoint_path(crawldir: Path) -> Path:
    return crawldir.resolve() / CHECKPOINT_NAME


def _page_from_dict(data: dict) -> PageResult:
    field_names = {f.name for f in fields(PageResult)}
    kwargs = {k: v for k, v in data.items() if k in field_names}
    if "images" in data:
        kwargs["images"] = [ImageInfo(**img) for img in data["images"]]
    if "links" in data:
        kwargs["links"] = [LinkInfo(**lnk) for lnk in data["links"]]
    if data.get("lighthouse"):
        kwargs["lighthouse"] = LighthouseResult(**data["lighthouse"])
    return PageResult(**kwargs)


def save_checkpoint(
    crawldir: Path,
    *,
    report: CrawlReport,
    seen: set[str],
    queue: deque,
    completed: bool = False,
) -> Path:
    crawldir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_path(crawldir)
    payload: dict[str, Any] = {
        "version": CHECKPOINT_VERSION,
        "completed": completed,
        "saved_at": time.time(),
        "start_url": report.start_url,
        "mode": report.mode,
        "config": asdict(report.config),
        "seen": sorted(seen),
        "queue": list(queue),
        "pages": {u: asdict(p) for u, p in report.pages.items()},
        "errors": list(report.errors),
        "robots_info": report.robots_info,
        "sitemap_urls": report.sitemap_urls,
        "blocked_urls": report.blocked_urls,
        "started_at": report.started_at,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def load_checkpoint(crawldir: Path) -> dict[str, Any] | None:
    path = checkpoint_path(crawldir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("version") != CHECKPOINT_VERSION:
        return None
    if data.get("completed"):
        return None
    return data


def restore_from_checkpoint(
    data: dict[str, Any],
) -> tuple[CrawlReport, set[str], deque, int]:
    cfg_raw = data.get("config") or {}
    cfg_fields = {f.name for f in fields(CrawlConfig)}
    config = CrawlConfig(**{k: v for k, v in cfg_raw.items() if k in cfg_fields})
    report = CrawlReport(
        start_url=str(data.get("start_url") or ""),
        mode=data.get("mode") or "http",
        config=config,
        errors=list(data.get("errors") or []),
        robots_info=dict(data.get("robots_info") or {}),
        sitemap_urls=list(data.get("sitemap_urls") or []),
        blocked_urls=list(data.get("blocked_urls") or []),
        started_at=float(data.get("started_at") or time.time()),
    )
    for url, raw in (data.get("pages") or {}).items():
        report.pages[str(url)] = _page_from_dict(raw)
    seen = set(data.get("seen") or [])
    queue: deque = deque()
    for item in data.get("queue") or []:
        if isinstance(item, (list, tuple)) and len(item) >= 4:
            queue.append(tuple(item))
    crawled = len(report.pages)
    return report, seen, queue, crawled
