import asyncio
from types import SimpleNamespace

import patent_troll.diagnostics as diagnostics
from patent_troll import PatentTrollConfig


def test_openai_live_check_skips_without_key() -> None:
    check = asyncio.run(diagnostics.check_openai(PatentTrollConfig()))

    assert check.name == "OpenAI"
    assert check.configured is False
    assert check.reachable is None


def test_openai_live_check_success(monkeypatch) -> None:
    captured = {}

    class MockModels:
        async def retrieve(self, model):
            captured["model"] = model
            return SimpleNamespace(id=model)

    class MockOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = MockModels()

    monkeypatch.setattr(diagnostics, "load_openai_client_class", lambda: MockOpenAI)

    check = asyncio.run(diagnostics.check_openai(PatentTrollConfig(openai_api_key="key", openai_model="gpt-test")))

    assert check.configured is True
    assert check.reachable is True
    assert captured == {"api_key": "key", "model": "gpt-test"}


def test_anthropic_live_check_success(monkeypatch) -> None:
    captured = {}

    class MockMessages:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(content=[])

    class MockAnthropic:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.messages = MockMessages()

    monkeypatch.setattr(diagnostics, "load_anthropic_client_class", lambda: MockAnthropic)

    check = asyncio.run(
        diagnostics.check_anthropic(PatentTrollConfig(anthropic_api_key="key", anthropic_model="claude-test"))
    )

    assert check.configured is True
    assert check.reachable is True
    assert captured["api_key"] == "key"
    assert captured["model"] == "claude-test"
    assert captured["max_tokens"] == 1


class MockResponse:
    def __init__(self, error=None) -> None:
        self.error = error

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error


class MockAsyncClient:
    calls = []
    response = MockResponse()

    def __init__(self, *args, **kwargs) -> None:
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, **kwargs):
        self.__class__.calls.append({"url": url, **kwargs})
        return self.__class__.response


def test_uspto_live_check_success(monkeypatch) -> None:
    MockAsyncClient.calls = []
    MockAsyncClient.response = MockResponse()
    monkeypatch.setattr(diagnostics.httpx, "AsyncClient", MockAsyncClient)

    check = asyncio.run(diagnostics.check_uspto_odp(PatentTrollConfig(uspto_odp_api_key="odp")))

    assert check.configured is True
    assert check.reachable is True
    assert MockAsyncClient.calls[0]["headers"]["X-API-KEY"] == "odp"
    assert MockAsyncClient.calls[0]["json"]["pagination"]["limit"] == 1


def test_run_live_checks_returns_all_providers(monkeypatch) -> None:
    async def fake_openai(_config):
        return diagnostics.ProviderCheck("OpenAI", False, None, "missing")

    async def fake_anthropic(_config):
        return diagnostics.ProviderCheck("Anthropic", False, None, "missing")

    async def fake_uspto(_config):
        return diagnostics.ProviderCheck("USPTO ODP", False, None, "missing")

    monkeypatch.setattr(diagnostics, "check_openai", fake_openai)
    monkeypatch.setattr(diagnostics, "check_anthropic", fake_anthropic)
    monkeypatch.setattr(diagnostics, "check_uspto_odp", fake_uspto)
    checks = asyncio.run(diagnostics.run_live_checks(PatentTrollConfig()))

    assert [check.name for check in checks] == ["OpenAI", "Anthropic", "USPTO ODP"]
