#!/usr/bin/env python3
"""
SiteSpider 本機桌面啟動器 — 內建伺服器 + 內嵌視窗（pywebview）或系統瀏覽器。

開發：
  python -m sitespider.desktop_launcher

打包後（見 docs/DESKTOP.md）：
  macOS：SiteSpider.app
  Windows：SiteSpider.exe
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer

from sitespider.paths import apply_desktop_environment


def _port_free(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
        return True
    except OSError:
        return False


def _pick_port(host: str, preferred: int) -> int:
    if _port_free(host, preferred):
        return preferred
    for p in range(preferred + 1, preferred + 20):
        if _port_free(host, p):
            return p
    raise RuntimeError(f"無法在 {host} 上找到可用埠（已試 {preferred}–{preferred + 19}）")


def _wait_http_ok(url: str, timeout_sec: float = 12.0) -> bool:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if 200 <= resp.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def _with_desktop_query(path: str) -> str:
    if "desktop=" in path:
        return path
    sep = "&" if "?" in path else "?"
    return path + sep + "desktop=1"


def _open_ui(
    url: str,
    *,
    ui_mode: str,
    window_title: str,
    width: int,
    height: int,
) -> str:
    """回傳實際使用的 UI 模式：webview | browser | none。"""
    if ui_mode == "none":
        return "none"
    if ui_mode in ("auto", "webview"):
        from sitespider.desktop_webview import run_webview, webview_available

        if webview_available():
            print(f"  內嵌視窗：{url}")
            run_webview(url, title=window_title, width=width, height=height)
            return "webview"
        if ui_mode == "webview":
            print("pywebview 未安裝，請執行：pip install \"sitespider[desktop]\"", file=sys.stderr)
            return "none"
    webbrowser.open(url)
    return "browser"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SiteSpider 本機桌面版")
    parser.add_argument("--host", default="127.0.0.1", help="監聽位址（預設僅本機）")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SITESPIDER_PORT", "8765")))
    parser.add_argument(
        "--ui",
        choices=("auto", "webview", "browser", "none"),
        default="auto",
        help="auto=優先內嵌視窗，否則系統瀏覽器",
    )
    parser.add_argument("--no-browser", action="store_true", help="同 --ui none")
    parser.add_argument("--window-width", type=int, default=1440)
    parser.add_argument("--window-height", type=int, default=920)
    parser.add_argument(
        "--open",
        default="/",
        help="啟動後開啟的路徑，例如 / 或 /guide",
    )
    args = parser.parse_args(argv)

    reports_dir = apply_desktop_environment()
    os.environ["SITESPIDER_DEFAULT_PLAN"] = os.environ.get("SITESPIDER_DEFAULT_PLAN", "pro")

    from sitespider.server import CrawlerHandler

    host = args.host
    port = _pick_port(host, args.port)
    base_url = f"http://{host}:{port}"
    open_path = args.open if args.open.startswith("/") else "/" + args.open
    open_path = _with_desktop_query(open_path)
    open_url = base_url + open_path

    httpd = ThreadingHTTPServer((host, port), CrawlerHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    if not _wait_http_ok(base_url + "/api/info"):
        print("SiteSpider 控制台啟動失敗，請檢查埠是否被佔用。", file=sys.stderr)
        httpd.shutdown()
        return 1

    print("SiteSpider 本機版已啟動")
    print(f"  控制台：{base_url}/?desktop=1")
    print(f"  使用說明：{base_url}/guide?desktop=1")
    print(f"  報告目錄：{reports_dir}")

    ui_mode = "none" if args.no_browser else args.ui
    used = "none"
    if ui_mode != "none":
        used = _open_ui(
            open_url,
            ui_mode=ui_mode,
            window_title="SiteSpider",
            width=args.window_width,
            height=args.window_height,
        )

    if used == "browser":
        print("  關閉此終端機視窗即停止服務（瀏覽器分頁可關閉）。")
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    elif used == "webview":
        print("  已關閉內嵌視窗。")
    elif used == "none":
        print(f"  請手動開啟：{open_url}")
        try:
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    httpd.shutdown()
    print("\n已停止 SiteSpider。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
