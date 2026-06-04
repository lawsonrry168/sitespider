"""主流 AI 平台預設（OpenAI 相容或原生 Messages API）。

模型 ID 依各平台官方文件整理（2026-05）；實際可用性以 API 回應為準。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiProvider:
    id: str
    name: str
    base_url: str
    default_model: str
    models: tuple[str, ...]
    api_style: str = "openai"  # openai | anthropic
    key_env: str = "SITESPIDER_AI_API_KEY"
    key_hint: str = "API Key"
    docs_url: str = ""

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "default_model": self.default_model,
            "models": list(self.models),
            "api_style": self.api_style,
            "key_hint": self.key_hint,
            "docs_url": self.docs_url,
            "custom_base_url": self.id == "custom",
        }


AI_PROVIDERS: dict[str, AiProvider] = {
    "openai": AiProvider(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        default_model="gpt-5.4-mini",
        models=(
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.4-pro",
            "gpt-5.3-codex",
            "gpt-5.2",
            "gpt-5.2-chat",
            "gpt-5.1",
            "gpt-5.1-codex",
            "gpt-5.1-codex-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "o3",
            "o3-mini",
            "o4-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ),
        key_env="OPENAI_API_KEY",
        key_hint="sk-…",
        docs_url="https://platform.openai.com/docs/models",
    ),
    "anthropic": AiProvider(
        id="anthropic",
        name="Anthropic Claude",
        base_url="https://api.anthropic.com",
        default_model="claude-sonnet-4-6",
        models=(
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-opus-4-5-20251101",
            "claude-opus-4-1-20250805",
            "claude-sonnet-4-6",
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
        ),
        api_style="anthropic",
        key_env="ANTHROPIC_API_KEY",
        key_hint="sk-ant-…",
        docs_url="https://platform.claude.com/docs/en/about-claude/models/overview",
    ),
    "google": AiProvider(
        id="google",
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.5-flash",
        models=(
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ),
        key_env="GEMINI_API_KEY",
        key_hint="AIza…",
        docs_url="https://ai.google.dev/gemini-api/docs/models",
    ),
    "deepseek": AiProvider(
        id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-v4-flash",
        models=(
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "deepseek-chat",
            "deepseek-reasoner",
            "deepseek-v3.2",
        ),
        key_env="DEEPSEEK_API_KEY",
        key_hint="sk-…",
        docs_url="https://api-docs.deepseek.com/quick_start/pricing",
    ),
    "groq": AiProvider(
        id="groq",
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="openai/gpt-oss-20b",
        models=(
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
            "groq/compound",
            "groq/compound-mini",
        ),
        key_env="GROQ_API_KEY",
        key_hint="gsk_…",
        docs_url="https://console.groq.com/docs/models",
    ),
    "openrouter": AiProvider(
        id="openrouter",
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-5.4-mini",
        models=(
            "openai/gpt-5.5",
            "openai/gpt-5.4-mini",
            "openai/gpt-4.1-mini",
            "anthropic/claude-opus-4.8",
            "anthropic/claude-sonnet-4.6",
            "google/gemini-3.5-flash",
            "google/gemini-2.5-flash",
            "deepseek/deepseek-v4-flash",
            "deepseek/deepseek-chat",
            "meta-llama/llama-4-scout",
            "qwen/qwen3.6-plus",
            "moonshotai/kimi-k2.5",
            "mistralai/mistral-medium-3.5",
            "mistralai/mistral-small-3.2-24b-instruct",
        ),
        key_env="OPENROUTER_API_KEY",
        key_hint="sk-or-…",
        docs_url="https://openrouter.ai/models",
    ),
    "moonshot": AiProvider(
        id="moonshot",
        name="Moonshot（Kimi）",
        base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2.5",
        models=(
            "kimi-k2.6",
            "kimi-k2.5",
            "kimi-k2-0905-preview",
            "kimi-k2-0711-preview",
            "moonshot-v1-128k-vision-preview",
            "moonshot-v1-32k-vision-preview",
            "moonshot-v1-8k-vision-preview",
            "moonshot-v1-128k",
            "moonshot-v1-32k",
            "moonshot-v1-8k",
        ),
        key_env="MOONSHOT_API_KEY",
        key_hint="sk-…",
        docs_url="https://platform.moonshot.cn/docs/api/list-models",
    ),
    "qwen": AiProvider(
        id="qwen",
        name="阿里通義（DashScope）",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen3.6-plus",
        models=(
            "qwen3.6-max-preview",
            "qwen3.6-plus",
            "qwen3.6-flash",
            "qwen3-max",
            "qwen3-coder-plus",
            "qwen3-coder-next",
            "qwen-max",
            "qwen-plus",
            "qwen-turbo",
            "qwen-long",
            "qwen2.5-72b-instruct",
        ),
        key_env="DASHSCOPE_API_KEY",
        key_hint="sk-…",
        docs_url="https://help.aliyun.com/zh/model-studio/models",
    ),
    "zhipu": AiProvider(
        id="zhipu",
        name="智譜 GLM",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4.7-flash",
        models=(
            "glm-5.1",
            "glm-5",
            "glm-4.7",
            "glm-4.7-flash",
            "glm-4.7-flashx",
            "glm-4-plus",
            "glm-4-flash",
            "glm-4-air",
        ),
        key_env="ZHIPU_API_KEY",
        key_hint="…",
        docs_url="https://open.bigmodel.cn/dev/api",
    ),
    "mistral": AiProvider(
        id="mistral",
        name="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-small-latest",
        models=(
            "mistral-medium-latest",
            "mistral-small-latest",
            "mistral-large-latest",
            "devstral-2512",
            "codestral-latest",
            "ministral-3b-2512",
            "ministral-8b-2512",
            "ministral-14b-2512",
            "mistral-medium-2508",
            "mistral-small-2506",
            "mistral-large-2512",
        ),
        key_env="MISTRAL_API_KEY",
        key_hint="…",
        docs_url="https://docs.mistral.ai/getting-started/models",
    ),
    "siliconflow": AiProvider(
        id="siliconflow",
        name="SiliconFlow",
        base_url="https://api.siliconflow.cn/v1",
        default_model="deepseek-ai/DeepSeek-V3.2",
        models=(
            "deepseek-ai/DeepSeek-V3.2",
            "Pro/deepseek-ai/DeepSeek-R1",
            "deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "Qwen/Qwen3-32B",
            "Qwen/Qwen2.5-72B-Instruct",
            "THUDM/GLM-4-9B-0414",
            "moonshotai/Kimi-K2-Instruct",
            "meta-llama/Llama-3.3-70B-Instruct",
        ),
        key_env="SILICONFLOW_API_KEY",
        key_hint="sk-…",
        docs_url="https://cloud.siliconflow.cn/models",
    ),
    "minimax": AiProvider(
        id="minimax",
        name="MiniMax",
        base_url="https://api.minimax.chat/v1",
        default_model="MiniMax-M2.7",
        models=(
            "MiniMax-M2.7",
            "MiniMax-M2.7-Highspeed",
            "MiniMax-M2.5",
            "MiniMax-M2.5-Highspeed",
            "MiniMax-Text-01",
            "abab7-chat-preview",
        ),
        key_env="MINIMAX_API_KEY",
        key_hint="…",
        docs_url="https://platform.minimaxi.com/document/guides/chat",
    ),
    "ollama": AiProvider(
        id="ollama",
        name="Ollama（本機）",
        base_url="http://localhost:11434/v1",
        default_model="llama3.3",
        models=(
            "llama4",
            "llama3.3",
            "llama3.2",
            "qwen3",
            "qwen2.5",
            "deepseek-r1",
            "deepseek-v3",
            "mistral",
            "gemma3",
            "phi4",
            "command-r7b",
            "glm4",
        ),
        key_env="",
        key_hint="本機通常免 Key",
        docs_url="https://ollama.com/library",
    ),
    "custom": AiProvider(
        id="custom",
        name="自訂 OpenAI 相容端點",
        base_url="",
        default_model="",
        models=(),
        key_hint="依服務商",
        docs_url="",
    ),
}


# Google OpenAI 相容端點常見的已下線型號 → 建議替代（避免 404/503）
_GEMINI_MODEL_ALIASES: dict[str, str] = {
    "gemini-pro": "gemini-2.0-flash",
    "gemini-1.0-pro": "gemini-2.0-flash",
    "gemini-1.5-flash": "gemini-2.0-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-1.5-flash-8b": "gemini-2.0-flash",
}


def normalize_model_name(provider_id: str | None, model: str | None) -> str:
    """將已下線或 OpenAI 相容端點不支援的模型對應到可用型號。"""
    return resolve_model_names(provider_id, model)[1]


def resolve_model_names(provider_id: str | None, model: str | None) -> tuple[str, str]:
    """回傳 (使用者選擇的 model, 實際呼叫 API 的 model)。"""
    requested = (model or "").strip()
    if not requested:
        return "", ""
    pid = (provider_id or "").strip().lower()
    resolved = requested
    if pid == "google":
        low = requested.lower()
        resolved = _GEMINI_MODEL_ALIASES.get(low, requested)
        if low.startswith("gemini-1.5") and resolved == requested:
            resolved = "gemini-2.0-flash"
    return requested, resolved


def get_provider(provider_id: str | None) -> AiProvider:
    pid = (provider_id or "").strip().lower()
    if pid in AI_PROVIDERS:
        return AI_PROVIDERS[pid]
    return AI_PROVIDERS["openai"]


def provider_display_name(provider_id: str | None) -> str:
    return get_provider(provider_id).name


def providers_public_json() -> list[dict]:
    return [p.to_public() for p in AI_PROVIDERS.values()]
