from __future__ import annotations

from typing import Any


class MissingProviderDependency(RuntimeError):
    """Raised when a configured LLM provider's optional SDK is unavailable."""


def load_openai_client_class() -> Any:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise MissingProviderDependency(
            'OpenAI support is not installed. Run: pip install "patent-troll[openai]"'
        ) from exc
    return AsyncOpenAI


def load_anthropic_client_class() -> Any:
    try:
        from anthropic import AsyncAnthropic
    except ImportError as exc:
        raise MissingProviderDependency(
            'Anthropic support is not installed. Run: pip install "patent-troll[anthropic]"'
        ) from exc
    return AsyncAnthropic
