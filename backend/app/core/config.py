from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./patent_troll.db"
    patent_troll_llm_provider: str = "auto"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-5"
    uspto_odp_api_key: Optional[str] = None
    patent_troll_demo_fallback: bool = True
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
