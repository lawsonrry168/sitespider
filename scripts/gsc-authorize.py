#!/usr/bin/env python3
"""僅執行 GSC OAuth 授權（不爬站）。用法：source scripts/gsc-env.sh && python scripts/gsc-authorize.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sitespider.gsc_inspection import _build_service, _credentials_path, gsc_available


def main() -> int:
    if not gsc_available():
        print('請先：pip install "sitespider[gsc]"', file=sys.stderr)
        return 1
    path = _credentials_path()
    if not path:
        print(
            "請先：source scripts/gsc-env.sh\n"
            "  或 export GSC_OAUTH_CLIENT_JSON=/path/to/client_secret.json",
            file=sys.stderr,
        )
        return 1
    print(f"憑證檔：{path}", file=sys.stderr)
    _build_service()
    print("GSC API 連線成功，可開始爬取（--gsc-inspect-max 或設定檔 gsc.inspect_max）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
