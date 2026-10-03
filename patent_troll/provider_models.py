from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OverlapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_id: str
    source: str
    title: str
    overlap: str
    risk: str


class Section101FlagPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag: str
    detail: str


class SuggestedTweakPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    detail: str


class PatentabilityReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    novelty_score: int = Field(ge=0, le=100)
    obviousness_risk: int = Field(ge=0, le=100)
    eligibility_risk: int = Field(ge=0, le=100)
    overlaps: list[OverlapPayload]
    section_101_flags: list[Section101FlagPayload]
    suggested_tweaks: list[SuggestedTweakPayload]
