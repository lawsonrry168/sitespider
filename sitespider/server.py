#!/usr/bin/env python3
"""
SiteSpider Web 控制台 — 深度限制與爬取選項的 GUI。
"""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sitespider.crawler import CrawlConfig, SeoCrawler, report_to_dict
from sitespider.lighthouse_runner import lighthouse_available
from sitespider.report import write_all_reports

PACKAGE_DIR = Path(__file__).resolve().parent
UI_DIR = PACKAGE_DIR / "ui"
DEFAULT_ROOT = Path.cwd()

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def _set_job(job_id: str, data: dict) -> None:
    with _jobs_lock:
        _jobs[job_id] = data


def _run_crawl(job_id: str, payload: dict) -> None:
    site_root = Path(payload.get("root", str(DEFAULT_ROOT))).resolve()
    mode = payload.get("mode", "file")
    start_url = payload.get("url", "http://localhost:8080/")
    if mode == "file":
        start_url = (site_root / "index.html").as_uri()

    config = CrawlConfig(
        max_pages=int(payload.get("max_pages", 500)),
        max_depth=int(payload.get("max_depth", 10)),
        workers=int(payload.get("workers", 4)),
        respect_robots=bool(payload.get("respect_robots", True)),
        use_sitemap=bool(payload.get("use_sitemap", True)),
        check_external=bool(payload.get("check_external", False)),
        run_lighthouse=bool(payload.get("lighthouse", False)),
        lighthouse_max=int(payload.get("lighthouse_max", 5)),
    )

    out_dir = (Path.cwd() / "reports" / job_id).resolve()

    def progress(done: int, total: int, url: str) -> None:
        _set_job(
            job_id,
            {
                **_get_job(job_id),
                "progress": {"done": done, "total": max(total, done), "current": url},
            },
        )

    try:
        crawler = SeoCrawler(
            start_url,
            mode=mode,
            site_root=site_root,
            config=config,
            on_progress=progress,
            lighthouse_out=out_dir / "lighthouse",
        )
        report = crawler.crawl()
        write_all_reports(report, out_dir, site_root=site_root)
        _set_job(
            job_id,
            {
                "status": "done",
                "progress": {"done": len(report.pages), "total": len(report.pages), "current": ""},
                "report_dir": str(out_dir),
                "summary": {
                    "pages": len(report.pages),
                    "blocked": len(report.blocked_urls),
                    "issues": report.summary_issues(),
                    "duration": (report.finished_at or 0) - report.started_at,
                },
                "report_json": report_to_dict(report),
            },
        )
    except Exception as e:
        _set_job(job_id, {"status": "error", "error": str(e)})


class CrawlerHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path in ("/", "/dashboard", "/dashboard.html"):
            return self._send_file(UI_DIR / "dashboard.html", "text/html; charset=utf-8")

        if path == "/api/info":
            return self._send_json(
                {
                    "lighthouse_available": lighthouse_available(),
                    "default_root": str(DEFAULT_ROOT),
                }
            )

        if path.startswith("/api/job/"):
            job_id = path.split("/")[-1]
            job = _get_job(job_id)
            if not job:
                return self._send_json({"error": "job not found"}, 404)
            return self._send_json(job)

        if path.startswith("/reports/"):
            rel = path[len("/reports/") :]
            fp = Path.cwd() / "reports" / rel
            if fp.suffix == ".html":
                return self._send_file(fp, "text/html; charset=utf-8")
            if fp.suffix == ".json":
                return self._send_file(fp, "application/json; charset=utf-8")

        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/crawl":
            return self.send_error(404)

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._send_json({"error": "invalid json"}, 400)

        job_id = str(uuid.uuid4())[:8]
        _set_job(
            job_id,
            {
                "status": "running",
                "progress": {"done": 0, "total": 1, "current": "啟動中…"},
            },
        )
        threading.Thread(target=_run_crawl, args=(job_id, payload), daemon=True).start()
        self._send_json({"job_id": job_id, "status": "running"})


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SiteSpider Web 控制台")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), CrawlerHandler)
    print(f"SiteSpider 控制台：http://{args.host}:{args.port}/")
    print("  深度限制、robots、sitemap、並行、Lighthouse 皆可於 UI 設定")
    print("  按 Ctrl+C 結束")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
