from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from patent_troll.config import PatentTrollConfig
from patent_troll.providers import load_anthropic_client_class, load_openai_client_class


@dataclass(frozen=True)
class ProviderCheck:
    name: str
    configured: bool
    reachable: Optional[bool]
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "configured": self.configured,
            "reachable": self.reachable,
            "message": self.message,
        }


async def run_live_checks(config: PatentTrollConfig) -> list[ProviderCheck]:
    checks = [
        await check_openai(config),
        await check_anthropic(config),
        await check_uspto_odp(config),
    ]
    return checks


async def check_openai(config: PatentTrollConfig) -> ProviderCheck:
    if not config.openai_api_key:
        return ProviderCheck("OpenAI", False, None, "OPENAI_API_KEY is not configured.")
    try:
        AsyncOpenAI = load_openai_client_class()
        client = AsyncOpenAI(api_key=config.openai_api_key)
        await client.models.retrieve(config.openai_model)
        return ProviderCheck("OpenAI", True, True, f"Reached model metadata for {config.openai_model}.")
    except Exception as exc:
        return ProviderCheck("OpenAI", True, False, short_error(exc))


async def check_anthropic(config: PatentTrollConfig) -> ProviderCheck:
    if not config.anthropic_api_key:
        return ProviderCheck("Anthropic", False, None, "ANTHROPIC_API_KEY is not configured.")
    try:
        AsyncAnthropic = load_anthropic_client_class()
        client = AsyncAnthropic(api_key=config.anthropic_api_key)
        await client.messages.create(
            model=config.anthropic_model,
            max_tokens=1,
            messages=[{"role": "user", "content": "Reply with OK."}],
        )
        return ProviderCheck("Anthropic", True, True, f"Reached {config.anthropic_model}.")
    except Exception as exc:
        return ProviderCheck("Anthropic", True, False, short_error(exc))


async def check_uspto_odp(config: PatentTrollConfig) -> ProviderCheck:
    if not config.uspto_odp_api_key:
        return ProviderCheck("USPTO ODP", False, None, "USPTO_ODP_API_KEY is not configured.")
    payload = {"q": "computer", "pagination": {"offset": 0, "limit": 1}}
    headers = {"X-API-KEY": config.uspto_odp_api_key}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                "https://api.uspto.gov/api/v1/patent/applications/search",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        return ProviderCheck("USPTO ODP", True, True, "Search endpoint accepted a one-result test query.")
    except Exception as exc:
        return ProviderCheck("USPTO ODP", True, False, short_error(exc))

def short_error(exc: Exception) -> str:
    text = str(exc).strip()
    return text[:220] if text else exc.__class__.__name__
