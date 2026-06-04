"""List 模式 — 僅爬取指定 URL 清單（對應 SF List Mode）。"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin, urlparse


def load_url_list(path: Path, *, base_url: str | None = None) -> list[str]:
    """
    每行一個 URL；`#` 開頭為註解。
    相對路徑會以 base_url 為基準 join。
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    urls: list[str] = []
    base = (base_url or "").rstrip("/") + "/" if base_url else ""
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
        elif base:
            urls.append(urljoin(base, line.lstrip("/")))
        else:
            raise ValueError(f"相對 URL 需指定 --url 或 site_url：{line}")
    return list(dict.fromkeys(urls))


def filter_same_host(urls: list[str], start_url: str) -> list[str]:
    host = urlparse(start_url).netloc
    if not host:
        return urls
    return [u for u in urls if urlparse(u).netloc in ("", host)]
