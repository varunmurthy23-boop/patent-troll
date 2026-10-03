from patent_troll import PatentTrollConfig


def test_auto_selects_openai_before_anthropic() -> None:
    config = PatentTrollConfig(llm_provider="auto", openai_api_key="openai", anthropic_api_key="anthropic")

    assert config.selected_llm_provider() == "openai"


def test_auto_selects_anthropic_when_openai_missing() -> None:
    config = PatentTrollConfig(llm_provider="auto", anthropic_api_key="anthropic")

    assert config.selected_llm_provider() == "anthropic"


def test_auto_selects_none_without_llm_keys() -> None:
    config = PatentTrollConfig(llm_provider="auto")

    assert config.selected_llm_provider() == "none"


def test_explicit_provider_is_preserved() -> None:
    config = PatentTrollConfig(llm_provider="anthropic", openai_api_key="openai")

    assert config.selected_llm_provider() == "anthropic"


def test_current_anthropic_model_is_the_default() -> None:
    assert PatentTrollConfig().anthropic_model == "claude-sonnet-5"
