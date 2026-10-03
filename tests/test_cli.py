import json
import asyncio
from pathlib import Path

from patent_troll.cli import doctor, load_idea, main, parse_sections, read_env_file
from patent_troll.diagnostics import ProviderCheck
from patent_troll.providers import MissingProviderDependency


def test_parse_markdown_sections() -> None:
    sections = parse_sections(
        """# Widget Router

## Problem
Static routing is stale.

## Mechanism
A graph index routes changes.

## Data Flow
Webhook in, ranked reviewers out.

## Algorithm
Expand graph nodes and score reviewers.

## Technical Novelty
Incident-weighted graph edges.
"""
    )

    assert sections["problem"] == "Static routing is stale."
    assert sections["mechanism"] == "A graph index routes changes."
    assert sections["data_flow"] == "Webhook in, ranked reviewers out."
    assert sections["technical_novelty"] == "Incident-weighted graph edges."


def test_load_json_idea_supports_camel_case(tmp_path: Path) -> None:
    path = tmp_path / "idea.json"
    path.write_text(
        json.dumps(
            {
                "title": "JSON Idea",
                "problem": "Problem",
                "mechanism": "Mechanism",
                "dataFlow": "Data flow",
                "algorithm": "Algorithm",
                "technicalNovelty": "Novelty",
                "implementationNotes": "Notes",
            }
        ),
        encoding="utf-8",
    )

    idea = load_idea(path)

    assert idea.title == "JSON Idea"
    assert idea.data_flow == "Data flow"
    assert idea.technical_novelty == "Novelty"
    assert idea.implementation_notes == "Notes"


def test_configure_non_interactive_writes_env(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"

    exit_code = main(["configure", "--non-interactive", "--provider", "anthropic", "--env-file", str(env_path)])

    assert exit_code == 0
    values = read_env_file(env_path)
    assert values["PATENT_TROLL_LLM_PROVIDER"] == "anthropic"
    assert "ANTHROPIC_API_KEY" in values
    assert "USPTO_ODP_API_KEY" in values


def test_init_creates_starter_idea_and_env(tmp_path: Path, capsys) -> None:
    exit_code = main(["init", "--dir", str(tmp_path), "--provider", "openai"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Initialized Patent Troll project." in output
    assert (tmp_path / "idea.md").exists()
    values = read_env_file(tmp_path / ".env.example")
    assert values["PATENT_TROLL_LLM_PROVIDER"] == "openai"
    assert "OPENAI_API_KEY" in values
    assert "USPTO_ODP_API_KEY" in values


def test_init_refuses_existing_files_without_force(tmp_path: Path, capsys) -> None:
    idea_path = tmp_path / "idea.md"
    idea_path.write_text("keep me", encoding="utf-8")

    exit_code = main(["init", "--dir", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "already exists" in captured.err
    assert idea_path.read_text(encoding="utf-8") == "keep me"
    assert not (tmp_path / ".env.example").exists()


def test_init_can_create_github_action(tmp_path: Path) -> None:
    exit_code = main(["init", "--dir", str(tmp_path), "--github-action", "--idea-file", "docs/idea.md"])
    workflow = tmp_path / ".github" / "workflows" / "patentability.yml"

    assert exit_code == 0
    assert (tmp_path / "docs" / "idea.md").exists()
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "uses: varunmurthy23-boop/patent-troll@v0" in text
    assert "idea-file: docs/idea.md" in text
    assert "${{ secrets.OPENAI_API_KEY }}" in text


def test_action_template_writes_custom_workflow(tmp_path: Path, capsys) -> None:
    workflow = tmp_path / "patentability.yml"

    exit_code = main(
        [
            "action-template",
            str(workflow),
            "--idea-file",
            "docs/idea.md",
            "--provider",
            "anthropic",
            "--output-file",
            "reports/patent.md",
            "--action-ref",
            "varunmurthy23-boop/patent-troll@v0.1.0",
            "--no-strict",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Configure GitHub secrets" in output
    text = workflow.read_text(encoding="utf-8")
    assert "uses: varunmurthy23-boop/patent-troll@v0.1.0" in text
    assert "idea-file: docs/idea.md" in text
    assert "provider: anthropic" in text
    assert "strict: false" in text
    assert "output-file: reports/patent.md" in text
    assert "path: reports/patent.md" in text


def test_action_template_refuses_overwrite_without_force(tmp_path: Path, capsys) -> None:
    workflow = tmp_path / "patentability.yml"
    workflow.write_text("keep me", encoding="utf-8")

    exit_code = main(["action-template", str(workflow)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "already exists" in captured.err
    assert workflow.read_text(encoding="utf-8") == "keep me"


def test_template_refuses_overwrite_without_force(tmp_path: Path) -> None:
    template_path = tmp_path / "idea.md"
    assert main(["template", str(template_path)]) == 0

    assert main(["template", str(template_path)]) == 1


def test_doctor_reports_missing_keys(tmp_path: Path, capsys) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("PATENT_TROLL_LLM_PROVIDER=auto\nPATENT_TROLL_DEMO_FALLBACK=true\n", encoding="utf-8")

    exit_code = asyncio.run(doctor(type("Args", (), {"env_file": str(env_path), "live": False, "format": "text"})()))
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Selected LLM provider: none" in output
    assert "OpenAI key: missing" in output
    assert "Warning: no LLM provider is configured" in output


def test_doctor_live_uses_provider_checks(tmp_path: Path, capsys, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("PATENT_TROLL_LLM_PROVIDER=auto\nOPENAI_API_KEY=test\n", encoding="utf-8")

    async def fake_live_checks(_config):
        return [ProviderCheck("OpenAI", True, True, "Mock ok.")]

    monkeypatch.setattr("patent_troll.cli.run_live_checks", fake_live_checks)

    exit_code = main(["doctor", "--env-file", str(env_path), "--live"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Live provider checks" in output
    assert "OpenAI: ok - Mock ok." in output


def test_validate_command_strict_fails_for_template(tmp_path: Path, capsys) -> None:
    path = tmp_path / "idea.md"
    assert main(["template", str(path)]) == 0

    exit_code = main(["validate", str(path), "--strict"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Validation warnings" in output
    assert "template placeholder" in output


def test_analyze_strict_stops_for_template(tmp_path: Path, capsys) -> None:
    path = tmp_path / "idea.md"
    assert main(["template", str(path)]) == 0

    exit_code = main(["analyze", str(path), "--provider", "none", "--strict"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Analysis stopped" in captured.err


def test_analyze_github_format_outputs_snapshot(capsys) -> None:
    exit_code = main(["analyze", "examples/idea.md", "--provider", "none", "--format", "github"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "## Patentability Snapshot" in output
    assert "**Search provenance**" in output


def test_analyze_reports_missing_provider_extra(monkeypatch, capsys) -> None:
    def missing_openai():
        raise MissingProviderDependency(
            'OpenAI support is not installed. Run: pip install "patent-troll[openai]"'
        )

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("patent_troll.analysis.load_openai_client_class", missing_openai)

    exit_code = main(["analyze", "examples/idea.md", "--provider", "openai"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert 'pip install "patent-troll[openai]"' in captured.err
