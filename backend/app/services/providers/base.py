from typing import Protocol


class LLMProvider(Protocol):
    """Provider-agnostic chat completion. `messages` excludes the system prompt
    (passed separately) and follows {"role": "user"|"assistant", "content": str}."""

    def generate(self, system: str, messages: list[dict[str, str]], max_tokens: int = 400) -> str: ...
