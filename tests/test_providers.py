import asyncio
from types import SimpleNamespace

import patent_troll.analysis as analysis
from patent_troll import IdeaDisclosure, PatentTrollConfig, PriorArtResult
from patent_troll.provider_models import PatentabilityReportPayload


def idea() -> IdeaDisclosure:
    return IdeaDisclosure(
        title="Provider Test",
        problem="Static routing misses risk.",
        mechanism="A graph index maps changes to runtime incidents.",
        data_flow="Webhook in, ranked plan out.",
        algorithm="Score graph paths and select reviewers.",
        technical_novelty="Incident-weighted edges alter reviewer selection.",
    )


def prior_art() -> list[PriorArtResult]:
    return [
        PriorArtResult(
            source="Mock",
            external_id="MOCK-1",
            title="Mock graph routing patent",
            abstract="A graph ranking system for routing work items.",
            similarity_score=0.42,
        )
    ]


def report_payload() -> dict:
    return {
        "summary": "Mock structured analysis.",
        "novelty_score": 71,
        "obviousness_risk": 33,
        "eligibility_risk": 44,
        "overlaps": [
            {
                "reference_id": "MOCK-1",
                "source": "Mock",
                "title": "Mock graph routing patent",
                "overlap": "Graph-based routing overlap.",
                "risk": "medium",
            }
        ],
        "section_101_flags": [
            {
                "flag": "Technical-improvement framing needed",
                "detail": "Tie the graph update rule to measurable system behavior.",
            }
        ],
        "suggested_tweaks": [
            {
                "title": "Quantify latency",
                "detail": "Add measured recomputation latency and update complexity.",
            }
        ],
    }


def test_openai_provider_parses_structured_response(monkeypatch) -> None:
    captured = {}

    class MockResponses:
        async def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_parsed=PatentabilityReportPayload.model_validate(report_payload()))

    class MockOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.responses = MockResponses()

    monkeypatch.setattr(analysis, "load_openai_client_class", lambda: MockOpenAI)

    report = asyncio.run(
        analysis.analyze_with_openai(
            idea(),
            prior_art(),
            PatentTrollConfig(llm_provider="openai", openai_api_key="openai-key", openai_model="gpt-test"),
        )
    )

    assert report is not None
    assert report.generated_by == "openai"
    assert report.novelty_score == 71
    assert report.overlaps[0].reference_id == "MOCK-1"
    assert captured["api_key"] == "openai-key"
    assert captured["model"] == "gpt-test"
    assert captured["text_format"] is PatentabilityReportPayload
    assert captured["store"] is False


def test_anthropic_provider_parses_structured_response(monkeypatch) -> None:
    captured = {}

    class MockMessages:
        async def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(parsed_output=PatentabilityReportPayload.model_validate(report_payload()))

    class MockAnthropic:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.messages = MockMessages()

    monkeypatch.setattr(analysis, "load_anthropic_client_class", lambda: MockAnthropic)

    report = asyncio.run(
        analysis.analyze_with_anthropic(
            idea(),
            prior_art(),
            PatentTrollConfig(llm_provider="anthropic", anthropic_api_key="anthropic-key", anthropic_model="claude-test"),
        )
    )

    assert report is not None
    assert report.generated_by == "anthropic"
    assert report.eligibility_risk == 44
    assert report.section_101_flags[0].flag == "Technical-improvement framing needed"
    assert captured["api_key"] == "anthropic-key"
    assert captured["model"] == "claude-test"
    assert captured["output_format"] is PatentabilityReportPayload
    assert "temperature" not in captured


def test_analyze_idea_exposes_provider_failure_before_fallback(monkeypatch) -> None:
    async def broken_provider(_idea, _prior_art, _config):
        raise analysis.ProviderAnalysisError("OpenAI", RuntimeError("mock outage"))

    monkeypatch.setattr(analysis, "analyze_with_openai", broken_provider)

    report = asyncio.run(
        analysis.analyze_idea(
            idea(),
            prior_art(),
            PatentTrollConfig(llm_provider="openai", openai_api_key="openai-key"),
        )
    )

    assert report.generated_by == "heuristic"
    assert "OpenAI analysis failed" in report.summary
    assert "mock outage" in report.summary
    assert "Heuristic fallback used" in report.summary
