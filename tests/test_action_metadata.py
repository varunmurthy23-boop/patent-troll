from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_action_metadata_wraps_cli() -> None:
    action = (ROOT / "action.yml").read_text(encoding="utf-8")

    assert "using: composite" in action
    assert "actions/setup-python@v6" in action
    assert 'description: "Analysis provider to use: auto, openai, anthropic, or none."' in action
    assert 'description: "Report format to generate: github, markdown, or json."' in action
    assert "patent-troll validate" in action
    assert "patent-troll analyze" in action
    assert "GITHUB_STEP_SUMMARY" in action
    assert "report-file:" in action
    assert 'openai) extra="[openai]"' in action
    assert 'anthropic) extra="[anthropic]"' in action
    assert 'auto) extra="[llm]"' in action
    assert 'none) extra=""' in action
    assert '${{ github.action_path }}${extra}' in action


def test_github_action_documents_user_supplied_keys_without_secrets() -> None:
    example = (ROOT / "examples" / "github-action.yml").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in example
    assert "ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}" in example
    assert "USPTO_ODP_API_KEY: ${{ secrets.USPTO_ODP_API_KEY }}" in example
    assert "PATENTSVIEW_API_KEY" not in example
    assert "sk-" not in example
