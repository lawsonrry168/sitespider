"""HTTP smoke tests for console API."""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer
from pathlib import Path

from sitespider import server as srv


def _start_test_server(tmp_path: Path) -> tuple[HTTPServer, threading.Thread, int]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    httpd = HTTPServer(("127.0.0.1", 0), srv.CrawlerHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread, port


def test_api_info_and_plans(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    httpd, _thread, port = _start_test_server(tmp_path)
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/info", timeout=5) as resp:
            info = json.loads(resp.read().decode())
        assert "version" in info
        assert "strict_plan" in info
        assert "client_plan_selectable" in info

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/plans", timeout=5) as resp:
            data = json.loads(resp.read().decode())
        ids = {p["id"] for p in data["plans"]}
        assert {"free", "starter", "pro", "agency"} <= ids
    finally:
        httpd.shutdown()


def test_guide_html_served(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    httpd, _thread, port = _start_test_server(tmp_path)
    try:
        import urllib.request

        for path in ("/guide", "/guide/", "/help"):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                html = resp.read().decode()
            assert resp.status == 200
            assert "使用說明" in html
            assert "guide-body" in html
    finally:
        httpd.shutdown()


def test_running_job_pollable_without_crawl_json(tmp_path: Path, monkeypatch):
    """進行中任務在尚未寫入 crawl-report.json 時仍可 GET /api/job/{id}。"""
    monkeypatch.chdir(tmp_path)
    httpd, _thread, port = _start_test_server(tmp_path)
    try:
        import urllib.request

        body = json.dumps(
            {
                "mode": "http",
                "url": "https://example.com/",
                "max_pages": 1,
                "max_depth": 0,
            }
        ).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/crawl",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            created = json.loads(resp.read().decode())
        job_id = created["job_id"]
        req2 = urllib.request.Request(f"http://127.0.0.1:{port}/api/job/{job_id}")
        with urllib.request.urlopen(req2, timeout=5) as resp:
            job = json.loads(resp.read().decode())
        assert resp.status == 200
        assert job.get("status") in ("running", "exporting", "done", "error")
        assert "error" not in job or not str(job.get("error", "")).startswith("找不到任務")
    finally:
        httpd.shutdown()


def test_package_zip_resolves_reports_on_disk(tmp_path: Path, monkeypatch):
    """本機 reports/ 內的報告（未在 job-history）仍可打包 ZIP。"""
    report = tmp_path / "reports" / "smoke-job"
    report.mkdir(parents=True)
    (report / "crawl-report.json").write_text('{"start_url":"https://example.com/"}', encoding="utf-8")
    (report / "REPORT-zh.md").write_text("# demo", encoding="utf-8")
    (report / "issues.csv").write_text("x", encoding="utf-8-sig")
    monkeypatch.chdir(tmp_path)
    httpd, _thread, port = _start_test_server(tmp_path)
    try:
        import urllib.request

        url = f"http://127.0.0.1:{port}/api/job/smoke-job/package.zip"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
        assert resp.status == 200
        assert data[:2] == b"PK"
        assert "zip" in (resp.headers.get("Content-Type") or "").lower()
    finally:
        httpd.shutdown()


def test_sites_html_served(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    httpd, _thread, port = _start_test_server(tmp_path)
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/sites", timeout=5) as resp:
            html = resp.read().decode()
        assert "多站儀表板" in html
    finally:
        httpd.shutdown()
