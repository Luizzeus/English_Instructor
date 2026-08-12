from functools import lru_cache

from anthropic import Anthropic

from app.core.config import get_settings


@lru_cache
def get_anthropic_client() -> Anthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return Anthropic(api_key=settings.anthropic_api_key)
