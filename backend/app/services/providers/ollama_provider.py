"""Local, open-weight LLM via Ollama — the default provider (docs/architecture.md
section 1.1). Runs entirely on this machine: no API key, no per-token cost, no
external network call. Trade-off accepted explicitly by the user: on a CPU-only
machine, replies take several seconds and are lower quality than Claude."""

import ollama

from app.core.config import get_settings


class OllamaProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = ollama.Client(host=settings.ollama_base_url)
        self._model = settings.ollama_model

    def generate(self, system: str, messages: list[dict[str, str]], max_tokens: int = 400) -> str:
        ollama_messages = [{"role": "system", "content": system}, *messages]
        response = self._client.chat(
            model=self._model,
            messages=ollama_messages,
            options={"num_predict": max_tokens},
        )
        return response["message"]["content"]
