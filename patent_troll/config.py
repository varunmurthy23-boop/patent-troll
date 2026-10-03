from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PatentTrollConfig:
    llm_provider: str = "auto"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-5"
    uspto_odp_api_key: Optional[str] = None
    enable_demo_fallback: bool = True

    @classmethod
    def from_env(cls) -> "PatentTrollConfig":
        return cls(
            llm_provider=os.getenv("PATENT_TROLL_LLM_PROVIDER", "auto").lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
            uspto_odp_api_key=os.getenv("USPTO_ODP_API_KEY"),
            enable_demo_fallback=os.getenv("PATENT_TROLL_DEMO_FALLBACK", "true").lower() != "false",
        )

    def selected_llm_provider(self) -> str:
        provider = self.llm_provider.lower()
        if provider == "auto":
            if self.openai_api_key:
                return "openai"
            if self.anthropic_api_key:
                return "anthropic"
            return "none"
        return provider
