"""HTTP 回應磁碟快取（開發／重跑 parser 時不重打目標站）。"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CachedResponse:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    text: str
    fetched_at: float


class ResponseCache:
    def __init__(self, root: Path | None, *, enabled: bool = True):
        self.enabled = enabled and root is not None
        self.root = (root or Path(".sitespider/cache")).resolve()
        if self.enabled:
            (self.root / "responses").mkdir(parents=True, exist_ok=True)

    def _path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.root / "responses" / f"{digest}.json"

    def get(self, url: str) -> CachedResponse | None:
        if not self.enabled:
            return None
        path = self._path(url)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CachedResponse(
                url=data.get("url") or url,
                final_url=data.get("final_url") or url,
                status=int(data.get("status") or 0),
                headers={str(k).lower(): str(v) for k, v in (data.get("headers") or {}).items()},
                text=str(data.get("text") or ""),
                fetched_at=float(data.get("fetched_at") or 0),
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return None

    def put(
        self,
        url: str,
        *,
        final_url: str,
        status: int,
        headers: dict[str, str],
        text: str,
    ) -> None:
        if not self.enabled:
            return
        path = self._path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": url,
            "final_url": final_url,
            "status": status,
            "headers": headers,
            "text": text,
            "fetched_at": time.time(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
