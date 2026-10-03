from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


LEGAL_DISCLAIMER = (
    "Not legal advice. This tool is a drafting and research aid only, does not represent users "
    "before the USPTO, does not submit filings, and does not guarantee patentability or grant. "
    "Review by a registered USPTO patent attorney or agent is strongly recommended before filing."
)


class IdeaCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    problem: str = Field(min_length=10)
    mechanism: str = Field(min_length=10)
    data_flow: str = Field(min_length=10)
    algorithm: str = Field(min_length=10)
    technical_novelty: str = Field(min_length=10)
    implementation_notes: str = ""


class IdeaRead(IdeaCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PriorArtRead(BaseModel):
    id: str
    source: str
    external_id: str
    title: str
    abstract: str
    publication_date: str
    assignee: str
    link: str
    similarity_score: float

    model_config = {"from_attributes": True}


class AnalysisReportRead(BaseModel):
    id: str
    novelty_score: int
    obviousness_risk: int
    eligibility_risk: int
    summary: str
    overlaps: list[dict[str, Any]]
    section_101_flags: list[dict[str, Any]]
    suggested_tweaks: list[dict[str, Any]]
    generated_by: str
    disclaimer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EndToEndResponse(BaseModel):
    idea: IdeaRead
    prior_art: list[PriorArtRead]
    search_metadata: Optional[dict[str, Any]] = None
    analysis: AnalysisReportRead
    disclaimer: str = LEGAL_DISCLAIMER
