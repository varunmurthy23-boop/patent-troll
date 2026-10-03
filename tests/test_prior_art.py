import asyncio
from typing import Optional

import httpx
import pytest

from patent_troll import IdeaDisclosure, PatentTrollConfig
from patent_troll.models import PriorArtCandidate
import patent_troll.prior_art as prior_art
from patent_troll.prior_art import search_prior_art, search_prior_art_with_metadata, search_uspto_odp, similarity


class MockResponse:
    def __init__(self, payload, error: Optional[Exception] = None) -> None:
        self.payload = payload
        self.error = error

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error

    def json(self):
        return self.payload


class MockClient:
    def __init__(self, response: MockResponse) -> None:
        self.response = response
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


def idea() -> IdeaDisclosure:
    return IdeaDisclosure(
        title="Adaptive Code Review Risk Router",
        problem="Static reviewer routing misses runtime incidents and coverage risk.",
        mechanism="A typed dependency graph connects changed files, incidents, owners, and test coverage.",
        data_flow="Pull request events update graph nodes and output ranked reviewer plans.",
        algorithm="Expand graph paths, apply incident decay and coverage penalties, and score reviewers.",
        technical_novelty="Incident-weighted graph edges alter reviewer selection using current runtime risk.",
    )


def test_uspto_missing_key_returns_empty() -> None:
    client = MockClient(MockResponse({"results": []}))

    results = asyncio.run(search_uspto_odp(client, PatentTrollConfig(), "query", limit=5))

    assert results == []
    assert client.calls == []


def test_uspto_parses_results_and_headers() -> None:
    client = MockClient(
        MockResponse(
            {
                "results": [
                    {
                        "publicationNumber": "US20240000001A1",
                        "inventionTitle": "Graph-based reviewer routing",
                        "abstractText": "A graph routes code reviews using incident-weighted edges.",
                        "publicationDate": "2024-01-04",
                        "assigneeEntityName": "Example Corp",
                    }
                ]
            }
        )
    )

    results = asyncio.run(search_uspto_odp(client, PatentTrollConfig(uspto_odp_api_key="odp-key"), "graph routing", limit=5))

    assert len(results) == 1
    assert results[0].source == "USPTO ODP"
    assert results[0].external_id == "US20240000001A1"
    assert results[0].title == "Graph-based reviewer routing"
    assert results[0].assignee == "Example Corp"
    assert client.calls[0]["headers"]["X-API-KEY"] == "odp-key"
    assert client.calls[0]["json"]["pagination"]["limit"] == 5


def test_uspto_http_error_is_not_silently_converted_to_empty_results() -> None:
    client = MockClient(MockResponse({}, httpx.HTTPStatusError("bad", request=None, response=None)))

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(search_uspto_odp(client, PatentTrollConfig(uspto_odp_api_key="odp-key"), "query", limit=5))


def test_search_prior_art_uses_demo_when_no_provider_results() -> None:
    results = asyncio.run(search_prior_art(idea(), PatentTrollConfig(enable_demo_fallback=True), limit=3))

    assert len(results) == 3
    assert all(result.source == "Demo fallback" for result in results)
    assert results == sorted(results, key=lambda result: result.similarity_score, reverse=True)


def test_search_prior_art_metadata_records_skips_and_demo() -> None:
    search = asyncio.run(search_prior_art_with_metadata(idea(), PatentTrollConfig(enable_demo_fallback=True), limit=3))

    assert len(search.results) == 3
    assert search.metadata.demo_fallback_used is True
    assert search.metadata.returned_count == 3
    statuses = {status.provider: status for status in search.metadata.providers}
    assert statuses["USPTO ODP"].status == "skipped"
    assert statuses["Demo fallback"].status == "used"


def test_search_metadata_exposes_uspto_failure(monkeypatch) -> None:
    async def failed_search(*_args, **_kwargs):
        raise httpx.ConnectError("ODP unavailable")

    monkeypatch.setattr(prior_art, "search_uspto_odp", failed_search)

    search = asyncio.run(
        search_prior_art_with_metadata(
            idea(),
            PatentTrollConfig(uspto_odp_api_key="odp-key", enable_demo_fallback=False),
            limit=3,
        )
    )

    status = search.metadata.providers[0]
    assert status.provider == "USPTO ODP"
    assert status.status == "error"
    assert "ConnectError" in status.message
    assert "ODP unavailable" in status.message


def test_search_prior_art_can_disable_demo_fallback() -> None:
    results = asyncio.run(search_prior_art(idea(), PatentTrollConfig(enable_demo_fallback=False), limit=3))

    assert results == []


def test_search_prior_art_metadata_records_demo_disabled() -> None:
    search = asyncio.run(search_prior_art_with_metadata(idea(), PatentTrollConfig(enable_demo_fallback=False), limit=3))

    assert search.results == []
    assert search.metadata.demo_fallback_used is False
    assert search.metadata.returned_count == 0
    assert search.metadata.providers[-1].provider == "Demo fallback"
    assert search.metadata.providers[-1].status == "disabled"


def test_similarity_ranks_related_candidate_higher() -> None:
    query = "graph reviewer routing incident coverage"
    related = PriorArtCandidate(
        source="Test",
        external_id="1",
        title="Graph reviewer routing",
        abstract="Incident coverage graph routes reviewers.",
    )
    unrelated = PriorArtCandidate(
        source="Test",
        external_id="2",
        title="Image compression",
        abstract="Transforms pixels using cosine blocks.",
    )

    assert similarity(query, related) > similarity(query, unrelated)
