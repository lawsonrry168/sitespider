"""
Playwright 表單登入 — 爬取前注入已登入 session（搭配 cookie_store）。
"""

from __future__ import annotations

from typing import Any


def login_with_form(
    context: Any,
    login_url: str,
    username: str,
    password: str,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    *,
    wait_until: str = "domcontentloaded",
    post_login_wait_ms: int = 1500,
) -> None:
    """
    以 CSS selector 填寫登入表單並提交。
    context: playwright.sync_api.BrowserContext
    """
    page = context.new_page()
    try:
        page.goto(login_url, wait_until=wait_until, timeout=60_000)
        page.fill(username_selector, username)
        page.fill(password_selector, password)
        with page.expect_navigation(wait_until=wait_until, timeout=60_000):
            page.click(submit_selector)
        if post_login_wait_ms > 0:
            page.wait_for_timeout(post_login_wait_ms)
    finally:
        page.close()
