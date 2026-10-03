# Patent Troll

Developer-native invention disclosure, prior art search, and patentability risk analysis tooling for software ideas.

Patent Troll is an open-source Python library that helps a software builder turn a raw technical idea into a structured invention disclosure, search for relevant prior art, and generate an analysis report with separate novelty, obviousness, and US software-patent eligibility risk surfaces.

It is built for developers who want to bring better technical material to a patent attorney, patent agent, internal IP review process, or pro se filing workflow.

## Important Disclaimer

Patent Troll is not a law firm, does not provide legal advice, does not represent users before the USPTO, does not submit patent filings, and does not guarantee patentability or grant.

Only registered USPTO patent attorneys and agents can prosecute applications on behalf of someone else. Review by a registered USPTO patent attorney or agent is strongly recommended before filing anything.

Patent Center is a human web portal, not a public filing API. This project will not automate USPTO submission or browser-drive Patent Center.

## What It Does

Phase 1 focuses on the core loop:

1. Capture a structured software invention disclosure.
2. Search prior art sources.
3. Rank and dedupe results.
4. Compare the idea against the closest results.
5. Produce a report with:
   - novelty score, framed around 35 U.S.C. Section 102 risk
   - obviousness risk, framed around 35 U.S.C. Section 103
   - eligibility risk, framed around 35 U.S.C. Section 101 and Alice/Mayo
   - overlapping references
   - concrete technical tweak suggestions

The current package is intentionally useful without a web app. A FastAPI/Next.js reference app is included, but the library is the center of gravity.

## What It Does Not Do

- It does not file anything with the USPTO.
- It does not automate Patent Center.
- It does not replace legal counsel.
- It does not create filing-ready patent drawings.
- It does not guarantee novelty, non-obviousness, eligibility, allowance, or grant.
- It does not currently generate provisional or non-provisional applications. That is planned for later phases.

## Keys You May Need

You can run the library with no keys for local development. In that mode it uses demo prior art and a heuristic analysis fallback, clearly marked as such.

For real usage, users supply their own API keys:

| Key | Required? | Used For | Notes |
| --- | --- | --- | --- |
| `PATENT_TROLL_LLM_PROVIDER` | Optional | Choose `auto`, `openai`, `anthropic`, or `none` | Defaults to `auto`, which tries OpenAI first, then Anthropic, then heuristic fallback. |
| `OPENAI_API_KEY` | Optional | ChatGPT/OpenAI patentability analysis | Needed when using `openai`; install `patent-troll[openai]`. |
| `OPENAI_MODEL` | Optional | OpenAI model selection | Defaults to `gpt-4.1-mini`. |
| `ANTHROPIC_API_KEY` | Optional | Anthropic/Claude patentability analysis | Needed when using `anthropic`; install `patent-troll[anthropic]`. |
| `ANTHROPIC_MODEL` | Optional | Anthropic model selection | Defaults to `claude-sonnet-5`. |
| `USPTO_ODP_API_KEY` | Recommended | USPTO Open Data Portal patent/application search | Requires a USPTO.gov account and ODP API registration. |
| `PATENT_TROLL_DEMO_FALLBACK` | Optional | Demo behavior | Defaults to `true`; set to `false` to return no demo results when search keys are absent. |

The legacy PatentsView REST API is not used. USPTO migrated PatentsView data to ODP in March 2026 and paused the old API during that transition. Use `USPTO_ODP_API_KEY` for live patent search.

Planned later:

| Source | Status | Notes |
| --- | --- | --- |
| OpenAlex | Planned | Open non-patent literature search. |
| Google Patents Public Datasets | Later | Requires BigQuery, GCP project, and billing. |
| Lens.org | Later | Paid API, useful for non-patent literature. |

## Install

From PyPI, once the package is published:

```bash
pip install patent-troll
```

The base install supports idea parsing, prior-art search, validation, reporting, and heuristic analysis. Install only the LLM provider you plan to use:

```bash
# OpenAI only
pip install "patent-troll[openai]"

# Anthropic only
pip install "patent-troll[anthropic]"

# Both providers (useful with PATENT_TROLL_LLM_PROVIDER=auto)
pip install "patent-troll[llm]"
```

From a cloned repo:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[llm]"
```

Python 3.10 or newer is required. OpenAI and Anthropic remain optional extras so a provider-free installation does not install either SDK.

Use `pip install -e .` for a provider-free development install, or replace `llm` with `openai` or `anthropic`. If a configured provider's SDK is missing, the CLI exits with an installation command for the required extra.

For the included reference API:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

For the included reference UI:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Library Usage

```python
import asyncio
import json

from patent_troll import IdeaDisclosure, PatentTrollConfig, PatentabilityWorkflow


async def main():
    workflow = PatentabilityWorkflow(PatentTrollConfig.from_env())

    result = await workflow.run(
        IdeaDisclosure(
            title="Adaptive code review risk router",
            problem="Pull requests are routed with static ownership rules that miss implementation risk.",
            mechanism="Build a typed dependency graph from changed files, incidents, owners, and coverage.",
            data_flow="PR webhook events update graph nodes and edge weights, then write reviewer plans back.",
            algorithm="Expand changed graph nodes, apply incident decay and coverage penalties, then choose reviewers.",
            technical_novelty="Reviewer routing reflects current runtime risk rather than static ownership alone.",
            implementation_notes="Persistent graph index with incremental recomputation for low latency.",
        )
    )

    print(json.dumps(result.to_dict(), indent=2))


asyncio.run(main())
```

Or run the included example:

```bash
python examples/basic_usage.py
```

## CLI Usage

After installing the package, the `patent-troll` command is available.

Start a new project:

```bash
patent-troll init
patent-troll init --github-action
patent-troll action-template
```

`init` writes a starter `idea.md` and `.env.example`. With `--github-action`, it also writes `.github/workflows/patentability.yml`. Existing files are left untouched unless you pass `--force`.

`action-template` can be run later in an existing repository to add or refresh only the GitHub workflow:

```bash
patent-troll action-template .github/workflows/patentability.yml --idea-file docs/idea.md --provider auto
```

Create a local `.env` file:

```bash
patent-troll configure
```

Check which keys are configured without printing secret values:

```bash
patent-troll doctor
patent-troll doctor --env-file .env
patent-troll doctor --env-file .env --format json
```

Run explicit live provider checks only when you want network calls:

```bash
patent-troll doctor --env-file .env --live
```

`doctor --live` attempts small readiness checks against configured providers. It is opt-in so the default `doctor` command never spends LLM tokens or calls external patent APIs.

Validate an idea file before spending API calls:

```bash
patent-troll validate idea.md
patent-troll validate idea.md --strict
```

Create a Markdown idea template:

```bash
patent-troll template idea.md
```

Analyze a JSON, Markdown, or text idea file:

```bash
patent-troll analyze idea.md
patent-troll analyze examples/idea.md
```

Write JSON output:

```bash
patent-troll analyze idea.md --format json --output report.json
```

Generate compact GitHub-flavored Markdown for PR comments or workflow summaries:

```bash
patent-troll analyze idea.md --format github --output patent-summary.md
```

Force a provider for one run:

```bash
patent-troll analyze idea.md --provider anthropic
patent-troll analyze idea.md --provider openai
patent-troll analyze idea.md --provider none
```

The Markdown parser recognizes headings such as `# Title`, `## Problem`, `## Mechanism`, `## Data Flow`, `## Algorithm`, `## Technical Novelty`, and `## Implementation Notes`.

`analyze` runs validation first and prints warnings for thin or placeholder sections. Use `--strict` to stop analysis when validation errors are found:

```bash
patent-troll analyze idea.md --strict
```

If no LLM key is configured, `doctor` will warn that analysis uses the heuristic fallback. If no USPTO ODP key is configured, `doctor` will warn that search uses demo fallback when enabled. Provider request and parsing failures are shown in report provenance instead of being treated as empty successful responses.

## GitHub Action

This repo also ships a composite GitHub Action that runs the same CLI in CI. It validates an idea file, generates a report, and can append the report to the Actions job summary.

The action automatically installs the extra matching `provider`. `auto` installs both LLM SDKs, while `none` installs neither. Advanced callers can override this with the `install-command` input.

```yaml
name: Patentability Scan

on:
  pull_request:
    types: [opened, synchronize, labeled]
  workflow_dispatch:

jobs:
  patentability:
    if: github.event_name == 'workflow_dispatch' || contains(github.event.pull_request.labels.*.name, 'patent-scan')
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - uses: actions/checkout@v5

      - uses: varunmurthy23-boop/patent-troll@v0
        with:
          idea-file: examples/idea.md
          provider: auto
          strict: true
          output-file: patent-troll-report.md
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          USPTO_ODP_API_KEY: ${{ secrets.USPTO_ODP_API_KEY }}
```

While developing this repository itself, use the local action path after checkout:

```yaml
- uses: ./
  with:
    idea-file: examples/idea.md
    provider: none
```

The action does not submit anything to the USPTO, does not automate Patent Center, and does not require repository maintainers to hold user keys. Callers provide their own provider credentials through GitHub secrets.

## Release Process

The Python package and GitHub Action are released together by tag.

1. Update the version in `pyproject.toml` and `patent_troll/__init__.py`.
2. Run `pytest`, `python -m build`, `python -m twine check dist/*`, and `python scripts/smoke_wheel_install.py dist/*.whl`.
3. Create and push a version tag such as `v0.1.0`.
4. The release workflow builds the source distribution and wheel, checks package metadata, and publishes to PyPI through trusted publishing.

Configure the PyPI project to trust this repository's `Release` workflow and `pypi` environment before the first tagged release.

See [RELEASE.md](RELEASE.md) for the full checklist.

## Environment Example

```bash
PATENT_TROLL_LLM_PROVIDER=auto
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5
USPTO_ODP_API_KEY=...
PATENT_TROLL_DEMO_FALLBACK=true
```

## Output Shape

`PatentabilityWorkflow.run(...)` returns a `PatentabilityWorkflowResult`:

```python
{
  "idea": {...},
  "prior_art": [
    {
      "source": "USPTO ODP",
      "external_id": "...",
      "title": "...",
      "abstract": "...",
      "similarity_score": 0.42,
      "link": "..."
    }
  ],
  "search_metadata": {
    "query": "...",
    "demo_fallback_used": false,
    "requested_limit": 8,
    "returned_count": 4,
    "providers": [
      {
        "provider": "USPTO ODP",
        "status": "ok",
        "result_count": 2,
        "message": "Provider returned results."
      }
    ]
  },
  "analysis": {
    "novelty_score": 62,
    "obviousness_risk": 48,
    "eligibility_risk": 57,
    "overlaps": [...],
    "section_101_flags": [...],
    "suggested_tweaks": [...],
    "generated_by": "openai",
    "disclaimer": "..."
  }
}
```

Scores are not legal conclusions. They are product signals to help developers sharpen an invention disclosure and identify questions for counsel.

OpenAI analysis uses the Responses API with typed structured output and `store=false`, so response objects are not retained by OpenAI through the API's default response-storage behavior. Anthropic analysis also uses SDK-native typed structured output. Users remain responsible for reviewing each provider's current data-handling terms before sending confidential invention material.

Markdown reports include a score table, search metadata, closest overlaps, Section 101 flags, and suggested technical tweaks. The `github` format is a shorter Markdown report intended for PR comments and GitHub Actions summaries.

## Reference App Architecture

- `patent_troll/`: reusable Python library.
- `backend/`: FastAPI reference API that persists ideas, prior art, and reports.
- `frontend/`: Next.js reference UI for the Phase 1 workflow.
- Database defaults to local SQLite in development. Postgres can be used by setting `DATABASE_URL`.

The backend installs the local library in editable mode through `backend/requirements.txt`, so app development exercises the same code that library users import.

## Roadmap

- Phase 1: library + prior art search + patentability analysis loop.
- Phase 2: provisional application drafting and DOCX export.
- Phase 3: non-provisional drafting with formal claim tree and drawing descriptions.
- Phase 4: GitHub Action, CLI, hosted multi-user app, billing, BigQuery, Lens.org, and fee schedule admin tools.

## Contributing

This project is early. The most valuable contributions are:

- additional prior art providers
- better ranking and deduping
- stronger Section 101 analysis prompts
- report exporters
- tests against mocked provider responses
- examples for real software development workflows

Keep compliance boundaries intact: no legal advice claims, no Patent Center automation, no guarantee language, and no suggestion that the tool represents a user before the USPTO.
