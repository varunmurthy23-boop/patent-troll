# Release Checklist

Patent Troll releases the Python package and GitHub Action together.

## Before Tagging

- Confirm the GitHub repository slug in `pyproject.toml`, `README.md`, and `examples/github-action.yml`.
- Configure PyPI trusted publishing for this repository:
  - repository: `varunmurthy23-boop/patent-troll`
  - workflow: `release.yml`
  - environment: `pypi`
- Update the version in `pyproject.toml` and `patent_troll/__init__.py`.
- Run the release verification commands:

```bash
pytest
python -m build
python -m twine check dist/*
python scripts/smoke_wheel_install.py dist/*.whl
```

## Tagging

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `Release` workflow publishes to PyPI only for tags matching `v*.*.*`.

## After Release

- Confirm the package installs with `pip install patent-troll`.
- Confirm the GitHub Action can be referenced as `varunmurthy23-boop/patent-troll@v0.1.0`.
- Create or update the GitHub release notes.
