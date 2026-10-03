from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


LEGAL_DISCLAIMER = (
    "Not legal advice. This tool is a drafting and research aid only, does not represent users "
    "before the USPTO, does not submit filings, and does not guarantee patentability or grant. "
    "Review by a registered USPTO patent attorney or agent is strongly recommended before filing."
)


@dataclass(frozen=True)
class IdeaDisclosure:
    title: str
    problem: str
    mechanism: str
    data_flow: str
    algorithm: str
    technical_novelty: str
    implementation_notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PriorArtResult:
    source: str
    external_id: str
    title: str
    abstract: str
    publication_date: str = ""
    assignee: str = ""
    link: str = ""
    similarity_score: float = 0.0
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PriorArtCandidate:
    source: str
    external_id: str
    title: str
    abstract: str
    publication_date: str = ""
    assignee: str = ""
    link: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderSearchStatus:
    provider: str
    status: str
    result_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SearchMetadata:
    query: str
    providers: list[ProviderSearchStatus]
    demo_fallback_used: bool = False
    requested_limit: int = 8
    returned_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "providers": [provider.to_dict() for provider in self.providers],
            "demo_fallback_used": self.demo_fallback_used,
            "requested_limit": self.requested_limit,
            "returned_count": self.returned_count,
        }


@dataclass(frozen=True)
class PriorArtSearchResult:
    results: list[PriorArtResult]
    metadata: SearchMetadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [result.to_dict() for result in self.results],
            "metadata": self.metadata.to_dict(),
        }


@dataclass(frozen=True)
class Overlap:
    reference_id: str
    source: str
    title: str
    overlap: str
    risk: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Section101Flag:
    flag: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SuggestedTweak:
    title: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PatentabilityReport:
    summary: str
    novelty_score: int
    obviousness_risk: int
    eligibility_risk: int
    overlaps: list[Overlap]
    section_101_flags: list[Section101Flag]
    suggested_tweaks: list[SuggestedTweak]
    generated_by: str = "heuristic"
    disclaimer: str = LEGAL_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "novelty_score": self.novelty_score,
            "obviousness_risk": self.obviousness_risk,
            "eligibility_risk": self.eligibility_risk,
            "overlaps": [item.to_dict() for item in self.overlaps],
            "section_101_flags": [item.to_dict() for item in self.section_101_flags],
            "suggested_tweaks": [item.to_dict() for item in self.suggested_tweaks],
            "generated_by": self.generated_by,
            "disclaimer": self.disclaimer,
        }


@dataclass(frozen=True)
class PatentabilityWorkflowResult:
    idea: IdeaDisclosure
    prior_art: list[PriorArtResult]
    analysis: PatentabilityReport
    search_metadata: Optional[SearchMetadata] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "idea": self.idea.to_dict(),
            "prior_art": [item.to_dict() for item in self.prior_art],
            "search_metadata": self.search_metadata.to_dict() if self.search_metadata else None,
            "analysis": self.analysis.to_dict(),
            "disclaimer": LEGAL_DISCLAIMER,
        }
