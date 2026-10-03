# Contributing

Thanks for helping make Patent Troll better.

This project is a developer tool for invention disclosure, prior art search, and patentability risk analysis. It is not a legal services product. Contributions must preserve that boundary.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The `dev` extra contains test and packaging tools. Use `pip install -e ".[dev,llm]"` when testing the live OpenAI or Anthropic integrations; the default mocked test suite does not require either SDK.

Reference API:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Reference UI:

```bash
cd frontend
npm install
npm run build
```

## Useful Commands

```bash
patent-troll init --dir /tmp/patent-troll-demo --github-action
patent-troll action-template /tmp/patentability.yml --idea-file examples/idea.md --provider none
patent-troll doctor --env-file .env.example
patent-troll analyze examples/idea.md --provider none
patent-troll analyze examples/idea.md --provider none --format github --output /tmp/patent-summary.md
python -m build
python scripts/smoke_wheel_install.py dist/*.whl
pytest
```

## Contribution Guidelines

- Keep provider integrations behind the library API.
- Do not add live-network tests to the default test suite.
- Mock OpenAI, Anthropic, USPTO, and PatentsView in tests.
- Keep generated text and UI copy clear that this is not legal advice.
- Do not add USPTO Patent Center automation.
- Do not imply representation before the USPTO or guarantee patentability.

## Pull Request Checklist

- Tests added or updated for behavior changes.
- `pytest` passes.
- Frontend build passes if UI code changed.
- README updated when CLI, env vars, output shape, or setup changes.
- No secrets, API keys, generated databases, or local `.env` files committed.
