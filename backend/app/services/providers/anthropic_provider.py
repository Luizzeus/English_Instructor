"""Kept available (not deleted) so the project can switch back to a paid,
higher-quality provider later without rebuilding this integration from scratch
— see docs/architecture.md section 1.1 for why Ollama is the default now."""

from anthropic import Anthropic

from app.core.config import get_settings


class AnthropicProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        self._client = Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def generate(self, system: str, messages: list[dict[str, str]], max_tokens: int = 400) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return response.content[0].text
