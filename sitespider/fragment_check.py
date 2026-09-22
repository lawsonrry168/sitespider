"""
頁內 fragment（#anchor）有效性檢查。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse, urldefrag

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

_FRAGMENT_JS = """
(ids) => {
  const broken = [];
  for (const id of ids) {
    if (!id) continue;
    const byId = document.getElementById(id);
    const byName = document.getElementsByName(id);
    const byAttrId = document.querySelector('[id="' + id.replace(/"/g, '\\\\"') + '"]');
    const byAttrName = document.querySelector('[name="' + id.replace(/"/g, '\\\\"') + '"]');
    if (!byId && (!byName || byName.length === 0) && !byAttrId && !byAttrName) {
      broken.push(id);
    }
  }
  return broken;
}
"""


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _fragment_from_href(href: str) -> str | None:
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    _, frag = urldefrag(href)
    return frag or None


def _is_internalish_href(href: str, page_url: str) -> bool:
    if not href:
        return False
    if href.startswith("#"):
        return True
    parsed_h = urlparse(href)
    if not parsed_h.scheme and not parsed_h.netloc:
        return True
    parsed_p = urlparse(page_url)
    if parsed_h.netloc and parsed_h.netloc.lower() == parsed_p.netloc.lower():
        base_path = (parsed_p.path or "/").rstrip("/") or "/"
        link_path = (parsed_h.path or "/").rstrip("/") or "/"
        return link_path == base_path or link_path == parsed_p.path
    return False


def collect_fragment_hrefs_from_html(html: str) -> list[str]:
    """從 HTML 解析含 fragment 的 href（HTTP 模式後備）。"""
    soup = BeautifulSoup(html or "", "lxml")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        frag = _fragment_from_href(href)
        if frag:
            out.append(href)
    return out


def check_fragments_on_page(page_obj: Any, url: str, links: list) -> list[str]:
    """
    依 links（每項需有 .href）收集頁內 fragment，在 page_obj（Playwright Page）上驗證。
    回傳無法對應的 fragment id 列表。
    """
    fragments: list[str] = []
    seen: set[str] = set()
    for link in links:
        href = getattr(link, "href", None) or (link.get("href") if isinstance(link, dict) else "")
        href = str(href or "").strip()
        if not _is_internalish_href(href, url):
            continue
        frag = _fragment_from_href(href)
        if frag and frag not in seen:
            seen.add(frag)
            fragments.append(frag)
    if not fragments:
        return []
    broken = page_obj.evaluate(_FRAGMENT_JS, fragments)
    return list(broken or [])


def mark_broken_fragments(report: CrawlReport, url: str, broken: list[str]) -> None:
    page = report.pages.get(url)
    if not page:
        return
    page.broken_fragments = list(broken)
    if broken:
        _issue(page, "broken_fragment")


def check_fragments_in_soup(soup, url: str, links: list) -> list[str]:
    """HTTP fallback：以 BeautifulSoup 檢查同頁 fragment id/name（無 Playwright）。"""
    fragments: list[str] = []
    seen: set[str] = set()
    for link in links:
        href = getattr(link, "href", None) or (
            link.get("href") if isinstance(link, dict) else ""
        )
        href = str(href or "").strip()
        if not _is_internalish_href(href, url):
            continue
        frag = _fragment_from_href(href)
        if frag and frag not in seen:
            seen.add(frag)
            fragments.append(frag)
    if not fragments:
        return []
    broken: list[str] = []
    for frag in fragments:
        if soup.find(id=frag) or soup.find(attrs={"name": frag}):
            continue
        broken.append(frag)
    return broken
