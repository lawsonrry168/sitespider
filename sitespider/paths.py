"""路徑解析：開發模式與 PyInstaller 打包後皆能定位 ui/ 與使用者資料目錄。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def package_dir() -> Path:
    """sitespider 套件目錄（內含 ui/）。"""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "sitespider"
    return Path(__file__).resolve().parent


def ui_dir() -> Path:
    return package_dir() / "ui"


def user_data_dir() -> Path:
    """桌面版／本機預設寫入：設定、用量、報告。"""
    raw = os.environ.get("SITESPIDER_DATA_DIR", "").strip()
    if raw:
        base = Path(raw)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "SiteSpider"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SiteSpider"
    else:
        base = Path.home() / ".local" / "share" / "SiteSpider"
    base.mkdir(parents=True, exist_ok=True)
    return base


def default_reports_dir() -> Path:
    reports = user_data_dir() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def apply_desktop_environment() -> Path:
    """桌面啟動前設定環境（資料目錄、預設工作目錄）。"""
    data = user_data_dir()
    reports = default_reports_dir()
    os.environ.setdefault("SITESPIDER_DATA_DIR", str(data))
    os.environ.setdefault("SITESPIDER_SKIP_QUOTA", "1")
    try:
        os.chdir(reports)
    except OSError:
        os.chdir(str(data))
    return reports
