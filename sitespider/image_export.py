"""下載爬取到的圖片並產生圖庫 HTML。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from sitespider.crawler import CrawlReport, ImageInfo

_CONTENT_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
    "image/x-icon": ".ico",
}


def _same_host(url: str, host: str) -> bool:
    netloc = urlparse(url).netloc
    return not netloc or netloc == host


def _guess_ext(url: str, content_type: str | None) -> str:
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in _CONTENT_EXT:
            return _CONTENT_EXT[ct]
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".avif"):
        return suffix if suffix != ".jpeg" else ".jpg"
    return ".bin"


def _safe_filename(url: str, ext: str, index: int) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(urlparse(url).path).name)[:40] or "image"
    if not base.lower().endswith(ext):
        base = f"{base}{ext}"
    return f"{index:04d}_{digest}_{base}"


def iter_unique_images(report: CrawlReport) -> list[tuple[str, list[tuple[ImageInfo, str]]]]:
    """resolved URL -> [(ImageInfo, source_page_url), ...]"""
    bucket: dict[str, list[tuple[ImageInfo, str]]] = {}
    for page_url, page in report.pages.items():
        for img in page.images:
            if not img.resolved or img.resolved.startswith("data:"):
                continue
            bucket.setdefault(img.resolved, []).append((img, page_url))
    return sorted(bucket.items(), key=lambda x: x[0])


def download_report_images(
    report: CrawlReport,
    out_dir: Path,
    *,
    max_images: int = 300,
    same_host_only: bool = True,
    timeout: float = 20.0,
) -> tuple[int, Path]:
    """
    下載唯一圖片 URL 至 out_dir/images/，並寫入各 ImageInfo.local_file。
    回傳 (成功數, images 目錄)。
    """
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    host = urlparse(report.start_url).netloc
    session = requests.Session()
    session.headers.update({"User-Agent": "SiteSpider-ImageExport/1.0"})
    ok = 0
    for idx, (resolved, refs) in enumerate(iter_unique_images(report)):
        if ok >= max_images:
            break
        if same_host_only and not _same_host(resolved, host):
            continue
        try:
            resp = session.get(resolved, timeout=timeout, stream=True)
            code = resp.status_code
            ctype = resp.headers.get("Content-Type")
            for img, _page in refs:
                img.status = code
                if ctype:
                    img.content_type = ctype.split(";")[0].strip()
            if code >= 400:
                for img, _page in refs:
                    img.issue = img.issue or "broken_image"
                continue
            ext = _guess_ext(resolved, ctype)
            fname = _safe_filename(resolved, ext, idx)
            dest = images_dir / fname
            size = 0
            with dest.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        size += len(chunk)
            rel = f"images/{fname}"
            for img, _page in refs:
                img.local_file = rel
                img.byte_size = size
                if img.issue == "broken_image":
                    img.issue = None
            ok += 1
        except requests.RequestException:
            for img, _page in refs:
                img.issue = img.issue or "broken_image"
    return ok, images_dir


def export_images_gallery_html(report: CrawlReport, path: Path) -> None:
    from sitespider.report_theme import REPORT_MAIN_OPEN, report_skip_link, report_styles_bundle, report_topbar

    rows: list[str] = []
    issue_count = 0
    downloaded = 0
    for page_url, page in sorted(report.pages.items()):
        for img in page.images:
            if not img.resolved and img.issue != "missing_src":
                continue
            if img.issue:
                issue_count += 1
            src = img.local_file or img.resolved
            if img.local_file:
                downloaded += 1
            alt = (img.alt or "").strip() or "（無 alt）"
            alt_cls = "" if (img.alt and str(img.alt).strip()) else " img-card--no-alt"
            issue_badge = f'<span class="img-issue">{img.issue}</span>' if img.issue else ""
            size_note = ""
            if img.byte_size:
                kb = img.byte_size / 1024
                size_note = f" · {kb:.1f} KB"
            rows.append(
                f'<article class="img-card{alt_cls}">'
                f'<a href="{_esc(src)}" target="_blank" rel="noopener">'
                f'<img src="{_esc(src)}" alt="{_esc(alt)}" loading="lazy"></a>'
                f"<p><strong>{_esc(alt)}</strong>{issue_badge}</p>"
                f'<p class="meta">{_esc(page_url)}</p>'
                f'<p class="meta">{img.width or "—"}×{img.height or "—"}'
                f"{size_note}</p></article>"
            )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>圖片稽核 — SiteSpider</title>
<style>
{report_styles_bundle()}
.img-gallery-stats {{ display:flex; gap:1rem; flex-wrap:wrap; margin:1rem 0; }}
.img-gallery-stats span {{ padding:0.35rem 0.75rem; border-radius:999px; border:1px solid var(--border); font-size:0.82rem; }}
.img-gallery-grid {{ display:grid; gap:1rem; grid-template-columns:repeat(auto-fill,minmax(11rem,1fr)); }}
.img-card {{ border:1px solid var(--border); border-radius:12px; overflow:hidden; background:var(--card); }}
.img-card img {{ width:100%; height:8rem; object-fit:cover; background:#111; display:block; }}
.img-card p {{ margin:0.35rem 0.5rem; font-size:0.78rem; }}
.img-card .meta {{ color:var(--muted); word-break:break-all; }}
.img-card--no-alt {{ border-color:var(--warn,#e8c468); }}
.img-issue {{ color:var(--danger,#e88a8a); font-size:0.72rem; margin-left:0.35rem; }}
</style>
</head>
<body class="report-page">
{report_skip_link()}
{report_topbar(path.parent, "圖片稽核", active="images-gallery.html", site_url=report.start_url)}
{REPORT_MAIN_OPEN}
<p class="lead">站內 <code>&lt;img&gt;</code> 與 srcset 圖片；可對照 alt、尺寸與失效連結。</p>
<div class="img-gallery-stats">
  <span>共 {len(rows)} 筆</span>
  <span>已下載 {downloaded}</span>
  <span>有問題 {issue_count}</span>
</div>
<div class="img-gallery-grid">
{"".join(rows) if rows else '<p class="meta">此站未發現可解析的圖片。</p>'}
</div>
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _esc(text: str) -> str:
    from html import escape

    return escape(text, quote=True)
