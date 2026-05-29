"""
robots.txt 解析與允許檢查（模擬搜尋引擎爬蟲行為）。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests


@dataclass
class RobotsInfo:
    source: str
    crawl_delay: float | None = None
    disallowed_paths: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    raw_exists: bool = True


class RobotsManager:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        *,
        site_root: Path | None = None,
        mode: str = "http",
        session: requests.Session | None = None,
        enabled: bool = True,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.user_agent = user_agent
        self.site_root = site_root
        self.mode = mode
        self.session = session or requests.Session()
        self.enabled = enabled
        self._parser = RobotFileParser()
        self._parser.set_url(urljoin_robots(base_url))
        self.info = RobotsInfo(source="")
        self._last_fetch: float = 0.0
        self._load()

    def _load(self) -> None:
        content = ""
        if self.mode == "file" and self.site_root:
            path = self.site_root / "robots.txt"
            self.info.source = str(path)
            if path.exists():
                content = path.read_text(encoding="utf-8", errors="replace")
            else:
                self.info.raw_exists = False
                if not self.enabled:
                    return
                self._parser.parse([])
                return
        else:
            robots_url = urljoin_robots(self.base_url)
            self.info.source = robots_url
            try:
                r = self.session.get(robots_url, timeout=10, headers={"User-Agent": self.user_agent})
                if r.status_code == 404:
                    self.info.raw_exists = False
                    self._parser.parse([])
                    return
                r.raise_for_status()
                content = r.text
            except requests.RequestException:
                self.info.raw_exists = False
                self._parser.parse([])
                return

        self._parser.parse(content.splitlines())
        self._extract_meta(content)

    def _extract_meta(self, content: str) -> None:
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            low = line.lower()
            if low.startswith("crawl-delay:"):
                try:
                    self.info.crawl_delay = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif low.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    self.info.disallowed_paths.append(path)
            elif low.startswith("sitemap:"):
                self.info.sitemap_urls.append(line.split(":", 1)[1].strip())

    def _site_relative_path(self, url: str) -> str:
        path = urlparse(url).path
        if self.mode == "file" and self.site_root:
            try:
                rel = Path(path).resolve().relative_to(self.site_root.resolve())
                return "/" + rel.as_posix()
            except ValueError:
                return "/" + Path(path).name
        return urlparse(url).path or "/"

    def _path_disallowed(self, site_path: str) -> bool:
        for rule in self.info.disallowed_paths:
            if not rule:
                continue
            if rule.endswith("*"):
                if site_path.startswith(rule.rstrip("*")):
                    return True
            elif site_path == rule or site_path.startswith(rule.rstrip("/") + "/"):
                return True
        return False

    def allowed(self, url: str) -> bool:
        if not self.enabled:
            return True
        if not self.info.raw_exists and self.mode == "file":
            return True

        site_path = self._site_relative_path(url)
        if self.info.disallowed_paths and self._path_disallowed(site_path):
            return False

        if self.mode == "file":
            return True

        return self._parser.can_fetch(self.user_agent, url) and self._parser.can_fetch(
            self.user_agent, site_path
        )

    def wait_crawl_delay(self) -> None:
        delay = self.info.crawl_delay
        if delay and delay > 0:
            elapsed = time.time() - self._last_fetch
            if elapsed < delay:
                time.sleep(delay - elapsed)
        self._last_fetch = time.time()


def urljoin_robots(base: str) -> str:
    p = urlparse(base)
    return f"{p.scheme}://{p.netloc}/robots.txt"


def meta_robots_noindex(content: str | None) -> bool:
    if not content:
        return False
    c = content.lower()
    return "noindex" in c or "none" in c
