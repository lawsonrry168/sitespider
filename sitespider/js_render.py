"""
Playwright JavaScript 渲染 — 取得執行 JS 後的 DOM（Webflow、SPA 等）。

安裝：
  pip install "sitespider[browser]"
  playwright install chromium
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Literal

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]


@dataclass
class RenderedPage:
    status: int
    final_url: str
    html: str
    error: str | None = None
    console_messages: list[str] = field(default_factory=list)


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


class PlaywrightRenderer:
    """每執行緒一組 browser，供並行爬取使用。"""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_ms: int = 30_000,
        wait_until: WaitUntil = "domcontentloaded",
        extra_wait_ms: int = 500,
        capture_console: bool = True,
    ):
        self.user_agent = user_agent
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self.extra_wait_ms = extra_wait_ms
        self.capture_console = capture_console
        self._local = threading.local()
        self._install_lock = threading.Lock()

    def _ensure_browser(self) -> None:
        if getattr(self._local, "ready", False):
            return
        with self._install_lock:
            if getattr(self._local, "ready", False):
                return
            from playwright.sync_api import sync_playwright

            self._local.pw = sync_playwright().start()
            self._local.browser = self._local.pw.chromium.launch(headless=True)
            self._local.context = self._local.browser.new_context(
                user_agent=self.user_agent,
                ignore_https_errors=True,
            )
            self._local.ready = True

    def fetch(
        self,
        url: str,
        *,
        screenshot_path: str | None = None,
    ) -> RenderedPage:
        self._ensure_browser()
        page = self._local.context.new_page()
        console: list[str] = []

        def _on_console(msg) -> None:
            if self.capture_console:
                console.append(f"{msg.type}: {msg.text}")

        page.on("console", _on_console)
        try:
            resp = page.goto(
                url,
                wait_until=self.wait_until,
                timeout=self.timeout_ms,
            )
            if self.extra_wait_ms > 0:
                page.wait_for_timeout(self.extra_wait_ms)
            status = resp.status if resp else 200
            if screenshot_path:
                from pathlib import Path

                Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=screenshot_path, full_page=True)
            return RenderedPage(
                status=status,
                final_url=page.url,
                html=page.content(),
                console_messages=console[:50],
            )
        except Exception as e:
            return RenderedPage(status=0, final_url=url, html="", error=str(e), console_messages=console)
        finally:
            page.close()

    def close(self) -> None:
        if not getattr(self._local, "ready", False):
            return
        try:
            self._local.context.close()
            self._local.browser.close()
            self._local.pw.stop()
        except Exception:
            pass
        self._local.ready = False


def close_all_renderers(renderers: list[PlaywrightRenderer]) -> None:
    seen: set[int] = set()
    for r in renderers:
        key = id(r)
        if key in seen:
            continue
        seen.add(key)
        r.close()
