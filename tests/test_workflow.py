import asyncio

from patent_troll import IdeaDisclosure, PatentTrollConfig, PatentabilityWorkflow
from patent_troll.reporting import render_github_markdown, render_json, render_markdown


def sample_idea() -> IdeaDisclosure:
    return IdeaDisclosure(
        title="Adaptive Code Review Risk Router",
        problem="Static code review routing misses runtime risk.",
        mechanism="A typed dependency graph connects changed files, incidents, owners, and coverage.",
        data_flow="Pull request events update graph nodes and produce ranked reviewer plans.",
        algorithm="Expand graph nodes, apply incident decay and coverage penalties, and score reviewers.",
        technical_novelty="Runtime incident proximity changes graph edge weights for reviewer selection.",
        implementation_notes="Incremental graph recomputation keeps latency low.",
    )


def test_workflow_uses_demo_and_heuristic_without_keys() -> None:
    config = PatentTrollConfig(llm_provider="none", enable_demo_fallback=True)
    result = asyncio.run(PatentabilityWorkflow(config).run(sample_idea()))

    assert result.prior_art
    assert result.search_metadata is not None
    assert result.search_metadata.demo_fallback_used is True
    assert result.prior_art[0].source == "Demo fallback"
    assert result.analysis.generated_by == "heuristic"
    assert result.analysis.disclaimer.startswith("Not legal advice")


def test_workflow_can_disable_demo_fallback() -> None:
    config = PatentTrollConfig(llm_provider="none", enable_demo_fallback=False)
    result = asyncio.run(PatentabilityWorkflow(config).run(sample_idea()))

    assert result.prior_art == []
    assert result.analysis.generated_by == "heuristic"


def test_renderers_include_expected_sections() -> None:
    config = PatentTrollConfig(llm_provider="none", enable_demo_fallback=True)
    result = asyncio.run(PatentabilityWorkflow(config).run(sample_idea()))

    markdown = render_markdown(result)
    json_text = render_json(result)

    assert "| Signal | Score | Meaning |" in markdown
    assert "## Search Metadata" in markdown
    assert "Demo fallback used: yes" in markdown
    assert "## Section 101 Flags" in markdown
    assert "Not legal advice" in markdown
    assert '"search_metadata"' in json_text
    assert '"generated_by": "heuristic"' in json_text

    github_markdown = render_github_markdown(result)
    assert "## Patentability Snapshot" in github_markdown
    assert "**Search provenance**" in github_markdown
    assert "**Top overlaps**" in github_markdown
    assert "Scores are product signals" in github_markdown
