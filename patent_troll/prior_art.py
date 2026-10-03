from __future__ import annotations

import math
import re
from typing import Any

import httpx

from patent_troll.config import PatentTrollConfig
from patent_troll.models import (
    IdeaDisclosure,
    PriorArtCandidate,
    PriorArtResult,
    PriorArtSearchResult,
    ProviderSearchStatus,
    SearchMetadata,
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def idea_query(idea: IdeaDisclosure) -> str:
    return " ".join(
        [
            idea.title,
            idea.problem,
            idea.mechanism,
            idea.data_flow,
            idea.algorithm,
            idea.technical_novelty,
        ]
    )


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()) if token not in STOP_WORDS}


def similarity(query: str, candidate: PriorArtCandidate) -> float:
    query_tokens = tokenize(query)
    candidate_tokens = tokenize(f"{candidate.title} {candidate.abstract}")
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = len(query_tokens & candidate_tokens)
    score = overlap / math.sqrt(len(query_tokens) * len(candidate_tokens))
    return round(min(score, 1.0), 3)


async def search_prior_art(
    idea: IdeaDisclosure,
    config: PatentTrollConfig,
    limit: int = 8,
) -> list[PriorArtResult]:
    return (await search_prior_art_with_metadata(idea, config, limit=limit)).results


async def search_prior_art_with_metadata(
    idea: IdeaDisclosure,
    config: PatentTrollConfig,
    limit: int = 8,
) -> PriorArtSearchResult:
    query = idea_query(idea)
    candidates: list[PriorArtCandidate] = []
    statuses: list[ProviderSearchStatus] = []

    async with httpx.AsyncClient(timeout=18) as client:
        if config.uspto_odp_api_key:
            try:
                uspto_results = await search_uspto_odp(client, config, query, limit=limit)
                candidates.extend(uspto_results)
                statuses.append(provider_status("USPTO ODP", uspto_results, configured=True))
            except Exception as exc:
                statuses.append(provider_error_status("USPTO ODP", exc))
        else:
            statuses.append(ProviderSearchStatus("USPTO ODP", "skipped", 0, "USPTO_ODP_API_KEY is not configured."))

    demo_fallback_used = False
    if not candidates and config.enable_demo_fallback:
        candidates = demo_prior_art(idea)
        demo_fallback_used = True
        statuses.append(ProviderSearchStatus("Demo fallback", "used", len(candidates), "No live prior-art results were available."))
    elif not candidates:
        statuses.append(ProviderSearchStatus("Demo fallback", "disabled", 0, "Demo fallback is disabled."))
    else:
        statuses.append(ProviderSearchStatus("Demo fallback", "not_used", 0, "Live provider results were available."))

    deduped: dict[str, PriorArtCandidate] = {}
    for candidate in candidates:
        key = f"{candidate.source}:{candidate.external_id or candidate.title.lower()}"
        deduped[key] = candidate

    ranked = sorted(
        [
            PriorArtResult(
                source=candidate.source,
                external_id=candidate.external_id,
                title=candidate.title,
                abstract=candidate.abstract,
                publication_date=candidate.publication_date,
                assignee=candidate.assignee,
                link=candidate.link,
                similarity_score=similarity(query, candidate),
                raw_payload=candidate.raw_payload,
            )
            for candidate in deduped.values()
        ],
        key=lambda item: item.similarity_score,
        reverse=True,
    )[:limit]
    metadata = SearchMetadata(
        query=query,
        providers=statuses,
        demo_fallback_used=demo_fallback_used,
        requested_limit=limit,
        returned_count=len(ranked),
    )
    return PriorArtSearchResult(results=ranked, metadata=metadata)


async def search_uspto_odp(
    client: httpx.AsyncClient,
    config: PatentTrollConfig,
    query: str,
    limit: int,
) -> list[PriorArtCandidate]:
    if not config.uspto_odp_api_key:
        return []

    payload = {
        "q": query[:900],
        "pagination": {"offset": 0, "limit": limit},
    }
    headers = {"X-API-KEY": config.uspto_odp_api_key}
    response = await client.post(
        "https://api.uspto.gov/api/v1/patent/applications/search",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()

    data = response.json()
    items = data.get("results") or data.get("patentFileWrapperDataBag") or []
    candidates = []
    for item in items[:limit]:
        publication = item.get("publicationNumber") or item.get("applicationNumberText") or item.get("applicationNumber", "")
        title = item.get("inventionTitle") or item.get("title") or "Untitled USPTO result"
        abstract = item.get("abstractText") or item.get("abstract") or ""
        candidates.append(
            PriorArtCandidate(
                source="USPTO ODP",
                external_id=str(publication),
                title=str(title),
                abstract=str(abstract),
                publication_date=str(item.get("publicationDate") or item.get("filingDate") or ""),
                assignee=str(item.get("assigneeEntityName") or item.get("applicantName") or ""),
                link=f"https://patentscope.uspto.gov/search/en/detail.jsf?docId={publication}" if publication else "",
                raw_payload=item,
            )
        )
    return candidates


def demo_prior_art(idea: IdeaDisclosure) -> list[PriorArtCandidate]:
    mechanism = idea.mechanism[:220]
    algorithm = idea.algorithm[:220]
    return [
        PriorArtCandidate(
            source="Demo fallback",
            external_id="DEMO-001",
            title=f"System for automated software workflow recommendation related to {idea.title}",
            abstract=(
                "A computer-implemented platform receives software project metadata, compares the metadata "
                f"against stored workflow patterns, and recommends configuration changes. Mechanism overlap: {mechanism}"
            ),
            publication_date="demo",
            assignee="Demo only",
        ),
        PriorArtCandidate(
            source="Demo fallback",
            external_id="DEMO-002",
            title="Technique for ranking technical artifacts using graph-derived similarity scores",
            abstract=(
                "The disclosed method builds a graph of technical artifacts, computes relevance scores from node "
                f"relationships, and returns ranked items to a user interface. Algorithm overlap: {algorithm}"
            ),
            publication_date="demo",
            assignee="Demo only",
        ),
        PriorArtCandidate(
            source="Demo fallback",
            external_id="DEMO-003",
            title="Interactive capture of implementation details for invention disclosure management",
            abstract=(
                "An invention disclosure tool prompts a user for problem statements, data flows, implementation "
                "constraints, and differentiating technical features before generating a research report."
            ),
            publication_date="demo",
            assignee="Demo only",
        ),
    ]


def provider_status(provider: str, results: list[PriorArtCandidate], configured: bool) -> ProviderSearchStatus:
    if not configured:
        return ProviderSearchStatus(provider, "skipped", 0, f"{provider} API key is not configured.")
    if results:
        return ProviderSearchStatus(provider, "ok", len(results), "Provider returned results.")
    return ProviderSearchStatus(provider, "empty", 0, "Provider returned no results.")


def provider_error_status(provider: str, exc: Exception) -> ProviderSearchStatus:
    detail = str(exc).strip() or exc.__class__.__name__
    return ProviderSearchStatus(provider, "error", 0, f"{exc.__class__.__name__}: {detail[:200]}")
