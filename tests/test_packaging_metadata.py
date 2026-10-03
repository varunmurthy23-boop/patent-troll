from pathlib import Path

from patent_troll import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_pyproject() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert f'version = "{__version__}"' in pyproject


def test_llm_sdks_are_optional_extras() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_metadata, optional_dependencies = pyproject.split("[project.optional-dependencies]", 1)

    assert '"openai>=' not in project_metadata
    assert '"anthropic>=' not in project_metadata
    assert "openai = [" in optional_dependencies
    assert "anthropic = [" in optional_dependencies
    assert "llm = [" in optional_dependencies
    assert '"openai>=3.0.0,<4"' in optional_dependencies
    assert '"anthropic>=1.0.0,<2"' in optional_dependencies


def test_package_requires_supported_python_baseline() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'requires-python = ">=3.10"' in pyproject
    assert '"Programming Language :: Python :: 3.9"' not in pyproject


def test_manifest_includes_release_support_files() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include ACTION_ITEMS.md" in manifest
    assert "include RELEASE.md" in manifest
    assert "include action.yml" in manifest
    assert "recursive-include examples" in manifest
    assert "recursive-include scripts" in manifest
    assert "recursive-include .github/workflows" in manifest


def test_release_workflow_uses_trusted_publishing() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "id-token: write" in workflow
    assert "python -m twine check dist/*" in workflow


def test_ci_smoke_tests_installed_wheel() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python scripts/smoke_wheel_install.py dist/*.whl" in workflow


def test_repository_urls_are_not_placeholders() -> None:
    searched_files = [
        ROOT / "pyproject.toml",
        ROOT / "README.md",
        ROOT / "examples" / "github-action.yml",
        ROOT / "RELEASE.md",
    ]

    for path in searched_files:
        text = path.read_text(encoding="utf-8")
        assert "your-org/patent-troll" not in text
        assert "github.com/your-org" not in text
