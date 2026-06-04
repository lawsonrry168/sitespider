"""多平台 AI client（OpenAI 相容 + Anthropic Messages）。"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, TypeVar

from sitespider.ai_providers import AiProvider, get_provider, resolve_model_names

T = TypeVar("T")

_RETRYABLE_HTTP = frozenset({429, 500, 502, 503, 504})
_RETRY_BACKOFF_SEC = (2.0, 4.0, 8.0, 16.0)
_MAX_ATTEMPTS = 4

_DEFAULT_SYSTEM = (
    "你是繁體中文 SEO / GEO 顧問。輸出精準、可執行，勿編造優惠或數據。"
)


@dataclass(frozen=True)
class AiConfig:
    api_key: str
    base_url: str
    model: str
    provider_id: str = "openai"
    api_style: str = "openai"
    model_requested: str = ""


def _env_key(provider: AiProvider) -> str:
    generic = os.environ.get("SITESPIDER_AI_API_KEY", "").strip()
    if generic:
        return generic
    if provider.key_env:
        val = os.environ.get(provider.key_env, "").strip()
        if val:
            return val
    if provider.id == "openai":
        return os.environ.get("SITESPIDER_OPENAI_API_KEY", "").strip() or os.environ.get(
            "OPENAI_API_KEY", ""
        ).strip()
    return ""


def resolve_ai_config(
    *,
    api_key: str | None = None,
    model: str | None = None,
    provider_id: str | None = None,
    base_url: str | None = None,
) -> AiConfig | None:
    provider = get_provider(provider_id or os.environ.get("SITESPIDER_AI_PROVIDER"))
    key = (api_key or "").strip() or _env_key(provider)
    if not key and provider.id != "ollama":
        return None

    resolved_base = (
        (base_url or "").strip()
        or os.environ.get("SITESPIDER_AI_BASE_URL", "").strip()
        or provider.base_url
    ).rstrip("/")
    if not resolved_base:
        return None

    raw_model = (
        (model or "").strip()
        or os.environ.get("SITESPIDER_AI_MODEL", "").strip()
        or provider.default_model
    )
    requested_model, resolved_model = resolve_model_names(provider.id, raw_model)
    if not resolved_model:
        return None

    return AiConfig(
        api_key=key or "ollama",
        base_url=resolved_base,
        model=resolved_model,
        provider_id=provider.id,
        api_style=provider.api_style,
        model_requested=requested_model or resolved_model,
    )


def ai_configured() -> bool:
    return resolve_ai_config() is not None


def _anthropic_completion(
    prompt: str,
    cfg: AiConfig,
    *,
    system: str | None = None,
    temperature: float = 0.35,
    timeout: int = 120,
) -> str:
    url = cfg.base_url.rstrip("/") + "/v1/messages"
    body = json.dumps(
        {
            "model": cfg.model,
            "max_tokens": 4096,
            "system": system or _DEFAULT_SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    def _once() -> str:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "x-api-key": cfg.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        blocks = data.get("content") or []
        for block in blocks:
            if block.get("type") == "text":
                return block.get("text") or ""
        return ""

    return _call_with_retry(_once)


def friendly_ai_error(exc: BaseException) -> str:
    """供 UI 顯示的可讀錯誤（繁中提示）。"""
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        if code == 401:
            return "API 金鑰無效或與平台不符（401）"
        if code == 403:
            return "API 金鑰無權限或配額用盡（403）"
        if code == 404:
            return "模型不存在或端點不支援此型號（404），請在「AI 文案」改用建議型號"
        if code in (429, 503):
            return f"AI 服務忙碌（HTTP {code}），請稍後重試或改用 gemini-2.5-flash"
        if code >= 500:
            return f"AI 服務暫時異常（HTTP {code}），請稍後重試"
        return f"HTTP Error {code}: {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        msg = str(reason or exc).lower()
        if "timed out" in msg or "timeout" in msg:
            return "連線逾時，請稍後重試"
        if "closed" in msg or "reset" in msg:
            return "連線被中斷（服務忙碌或網路不穩），請稍後重試"
        return f"連線失敗：{reason or exc}"
    return str(exc)


def _call_with_retry(fn: Callable[[], T]) -> T:
    last: BaseException | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in _RETRYABLE_HTTP and attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_BACKOFF_SEC[attempt])
                continue
            raise RuntimeError(friendly_ai_error(e)) from e
        except (urllib.error.URLError, TimeoutError, ConnectionResetError) as e:
            last = e
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_BACKOFF_SEC[attempt])
                continue
            raise RuntimeError(friendly_ai_error(e)) from e
    assert last is not None
    raise RuntimeError(friendly_ai_error(last)) from last


def _openai_completion(
    prompt: str,
    cfg: AiConfig,
    *,
    system: str | None = None,
    temperature: float = 0.35,
    timeout: int = 120,
) -> str:
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key and cfg.api_key != "ollama":
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    body = json.dumps(
        {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": system or _DEFAULT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    def _once() -> str:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""

    return _call_with_retry(_once)


def chat_completion(
    prompt: str,
    cfg: AiConfig,
    *,
    system: str | None = None,
    temperature: float = 0.35,
    timeout: int = 120,
) -> str:
    if cfg.api_style == "anthropic":
        return _anthropic_completion(
            prompt, cfg, system=system, temperature=temperature, timeout=timeout
        )
    return _openai_completion(
        prompt, cfg, system=system, temperature=temperature, timeout=timeout
    )


def parse_json_blob(text: str):
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t)
    if fence:
        t = fence.group(1).strip()
    return json.loads(t)


def chat_json(prompt: str, cfg: AiConfig, **kwargs):
    raw = chat_completion(prompt + "\n\n只回傳 JSON，勿加 markdown 說明。", cfg, **kwargs)
    return parse_json_blob(raw)
