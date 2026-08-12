from functools import lru_cache

from app.core.config import get_settings
from app.services.providers.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        from app.services.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    from app.services.providers.ollama_provider import OllamaProvider

    return OllamaProvider()
