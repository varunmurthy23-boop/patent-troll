from __future__ import annotations

import json
from typing import Any

from patent_troll.config import PatentTrollConfig
from patent_troll.models import (
    IdeaDisclosure,
    Overlap,
    PatentabilityReport,
    PriorArtResult,
    Section101Flag,
    SuggestedTweak,
)
from patent_troll.providers import load_anthropic_client_class, load_openai_client_class


SYSTEM_PROMPT = """You analyze US software patent drafting risk for a pro se inventor.
You are not a lawyer and must not imply legal representation or guaranteed patentability.
Return strict JSON only with keys:
summary, novelty_score, obviousness_risk, eligibility_risk, overlaps, section_101_flags, suggested_tweaks.
Scores are 0-100. novelty_score means higher is more novel. obviousness_risk and eligibility_risk mean higher risk.
Analyze Section 101 eligibility separately from Section 102 novelty and Section 103 obviousness.
For Section 101, flag abstract idea / mental process / generic computer implementation risk and suggest specific technical improvements."""


class ProviderAnalysisError(RuntimeError):
    def __init__(self, provider: str, cause: Exception) -> None:
        self.provider = provider
        self.cause = cause
        detail = str(cause).strip() or cause.__class__.__name__
        super().__init__(f"{provider} analysis failed: {detail[:220]}")


async def analyze_idea(
    idea: IdeaDisclosure,
    prior_art: list[PriorArtResult],
    config: PatentTrollConfig,
) -> PatentabilityReport:
    provider = config.selected_llm_provider()
    if provider == "openai" and config.openai_api_key:
        try:
            return await analyze_with_openai(idea, prior_art, config)
        except ProviderAnalysisError as exc:
            return heuristic_analysis(idea, prior_art, fallback_reason=str(exc))
    if provider == "anthropic" and config.anthropic_api_key:
        try:
            return await analyze_with_anthropic(idea, prior_art, config)
        except ProviderAnalysisError as exc:
            return heuristic_analysis(idea, prior_art, fallback_reason=str(exc))
    return heuristic_analysis(idea, prior_art)


async def analyze_with_openai(
    idea: IdeaDisclosure,
    prior_art: list[PriorArtResult],
    config: PatentTrollConfig,
) -> PatentabilityReport:
    AsyncOpenAI = load_openai_client_class()
    from patent_troll.provider_models import PatentabilityReportPayload

    client = AsyncOpenAI(api_key=config.openai_api_key)
    payload = {
        "idea": idea.to_dict(),
        "prior_art": [serialize_prior_art(result) for result in prior_art[:8]],
    }
    try:
        response = await client.responses.parse(
            model=config.openai_model,
            instructions=SYSTEM_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": (
                        "Compare this structured software invention idea against the prior art. "
                        "Return only valid JSON.\n\n"
                        + json.dumps(payload)
                    ),
                }
            ],
            max_output_tokens=1800,
            text_format=PatentabilityReportPayload,
            store=False,
        )
        if response.output_parsed is None:
            raise ValueError("OpenAI returned no parsed patentability report.")
        return report_from_dict(response.output_parsed.model_dump(), generated_by="openai")
    except Exception as exc:
        raise ProviderAnalysisError("OpenAI", exc) from exc


async def analyze_with_anthropic(
    idea: IdeaDisclosure,
    prior_art: list[PriorArtResult],
    config: PatentTrollConfig,
) -> PatentabilityReport:
    AsyncAnthropic = load_anthropic_client_class()
    from patent_troll.provider_models import PatentabilityReportPayload

    client = AsyncAnthropic(api_key=config.anthropic_api_key)
    payload = {
        "idea": idea.to_dict(),
        "prior_art": [serialize_prior_art(result) for result in prior_art[:8]],
    }
    try:
        response = await client.messages.parse(
            model=config.anthropic_model,
            max_tokens=1800,
            system=SYSTEM_PROMPT,
            output_format=PatentabilityReportPayload,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Compare this structured software invention idea against the prior art. "
                        "Return a structured patentability report.\n\n"
                        + json.dumps(payload)
                    ),
                }
            ],
        )
        if response.parsed_output is None:
            raise ValueError("Anthropic returned no parsed patentability report.")
        return report_from_dict(response.parsed_output.model_dump(), generated_by="anthropic")
    except Exception as exc:
        raise ProviderAnalysisError("Anthropic", exc) from exc


def heuristic_analysis(
    idea: IdeaDisclosure,
    prior_art: list[PriorArtResult],
    fallback_reason: str = "",
) -> PatentabilityReport:
    max_similarity = max([result.similarity_score for result in prior_art], default=0)
    novelty_score = max(15, min(92, int(88 - max_similarity * 65)))
    obviousness_risk = max(10, min(90, int(25 + max_similarity * 70)))
    eligibility_risk = section_101_risk(idea)

    overlaps = [
        Overlap(
            reference_id=result.external_id,
            source=result.source,
            title=result.title,
            overlap="Shares terminology or implementation surface with the submitted mechanism/data flow.",
            risk="high" if result.similarity_score >= 0.45 else "medium" if result.similarity_score >= 0.22 else "low",
        )
        for result in prior_art[:5]
    ]

    reason = (
        f"{fallback_reason} Heuristic fallback used."
        if fallback_reason
        else "Development analysis generated without a configured LLM API key."
    )
    return PatentabilityReport(
        summary=(
            f"{reason} Treat this as a workflow check, not a legal or final patentability opinion. "
            "The strongest next step is to sharpen the technical mechanism and compare it against the "
            "highest-scoring references."
        ),
        novelty_score=novelty_score,
        obviousness_risk=obviousness_risk,
        eligibility_risk=eligibility_risk,
        overlaps=overlaps,
        section_101_flags=section_101_flags(idea),
        suggested_tweaks=suggested_tweaks(max_similarity),
        generated_by="heuristic",
    )


def section_101_risk(idea: IdeaDisclosure) -> int:
    text = f"{idea.problem} {idea.mechanism} {idea.algorithm} {idea.technical_novelty}".lower()
    abstract_terms = ["organize", "rank", "recommend", "display", "match", "score", "business", "workflow", "automate"]
    technical_terms = ["latency", "memory", "data structure", "protocol", "sensor", "compiler", "cache", "throughput"]
    abstract_hits = sum(1 for term in abstract_terms if term in text)
    technical_hits = sum(1 for term in technical_terms if term in text)
    return max(15, min(88, 42 + abstract_hits * 7 - technical_hits * 8))


def section_101_flags(idea: IdeaDisclosure) -> list[Section101Flag]:
    text = f"{idea.mechanism} {idea.algorithm} {idea.technical_novelty}".lower()
    flags: list[Section101Flag] = []
    if any(term in text for term in ["recommend", "rank", "match", "organize", "workflow"]):
        flags.append(
            Section101Flag(
                flag="Potential abstract idea framing",
                detail="The invention may read as organizing, ranking, or recommending information unless tied to a concrete technical improvement.",
            )
        )
    if "computer" in text and not any(term in text for term in ["data structure", "latency", "throughput", "memory", "protocol"]):
        flags.append(
            Section101Flag(
                flag="Generic computer implementation risk",
                detail="The current wording mentions computer implementation without enough measurable technical effect.",
            )
        )
    if not flags:
        flags.append(
            Section101Flag(
                flag="No obvious Section 101 red flag in the heuristic pass",
                detail="Still validate eligibility with counsel and with claim language once drafted.",
            )
        )
    return flags


def suggested_tweaks(max_similarity: float) -> list[SuggestedTweak]:
    tweaks = [
        SuggestedTweak(
            title="Add a measurable technical effect",
            detail="Quantify latency, memory, throughput, accuracy, fault tolerance, or resource usage improvements caused by the specific mechanism.",
        ),
        SuggestedTweak(
            title="Name the concrete data structures",
            detail="Describe the schema, graph, index, embedding store, cache, queue, or state machine that makes the implementation work.",
        ),
        SuggestedTweak(
            title="Constrain the algorithmic steps",
            detail="Replace broad result language with ordered operations, inputs, transformations, thresholds, and outputs.",
        ),
    ]
    if max_similarity >= 0.35:
        tweaks.append(
            SuggestedTweak(
                title="Differentiate from the closest reference",
                detail="Add a technical limitation that the closest result does not teach, such as a new update rule, specialized data flow, or failure-handling path.",
            )
        )
    return tweaks


def report_from_dict(report: dict[str, Any], generated_by: str) -> PatentabilityReport:
    return PatentabilityReport(
        summary=str(report.get("summary", "")),
        novelty_score=int(report.get("novelty_score", 50)),
        obviousness_risk=int(report.get("obviousness_risk", 50)),
        eligibility_risk=int(report.get("eligibility_risk", 50)),
        overlaps=[
            Overlap(
                reference_id=str(item.get("reference_id", "")),
                source=str(item.get("source", "")),
                title=str(item.get("title", "")),
                overlap=str(item.get("overlap", "")),
                risk=str(item.get("risk", "")),
            )
            for item in report.get("overlaps", [])
        ],
        section_101_flags=[
            Section101Flag(flag=str(item.get("flag", "")), detail=str(item.get("detail", "")))
            for item in report.get("section_101_flags", [])
        ],
        suggested_tweaks=[
            SuggestedTweak(title=str(item.get("title", "")), detail=str(item.get("detail", "")))
            for item in report.get("suggested_tweaks", [])
        ],
        generated_by=generated_by,
    )


def serialize_prior_art(result: PriorArtResult) -> dict[str, Any]:
    return {
        "source": result.source,
        "external_id": result.external_id,
        "title": result.title,
        "abstract": result.abstract,
        "similarity_score": result.similarity_score,
        "link": result.link,
    }
