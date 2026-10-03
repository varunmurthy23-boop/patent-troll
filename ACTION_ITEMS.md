# Open Action Items

This file tracks known follow-up work for Patent Troll.

## Release Blockers

- [x] Create the GitHub repository at `varunmurthy23-boop/patent-troll` and update the repository slug throughout the project.
- [x] Add the git remote:

```bash
git remote add origin https://github.com/varunmurthy23-boop/patent-troll.git
```

- [ ] Configure PyPI trusted publishing:
  - repository: `varunmurthy23-boop/patent-troll`
  - workflow: `release.yml`
  - environment: `pypi`
- [ ] Confirm the package name `patent-troll` is available on PyPI before the first publish.
- [x] Create an initial commit, push to GitHub, and confirm CI passes.
- [ ] Tag the first release, likely `v0.1.0`, after CI is green.

## Pre-Release Polish

- [x] Add `patent-troll init` to create a starter idea file and optional `.env`/`.env.example`.
- [x] Add `patent-troll action-template` to write a ready-to-use GitHub workflow into a user repo.
- [x] Make OpenAI and Anthropic dependencies optional extras with lazy provider loading.
- [ ] Add badges to `README.md` after the GitHub repo exists.
- [ ] Replace `varunmurthy23-boop/patent-troll@v0` examples with the exact stable tag after release.

## Product / Library Next Steps

- [x] Remove the retired PatentsView REST integration and expose USPTO ODP request failures in search metadata.
- [x] Modernize OpenAI and Anthropic adapters with typed structured outputs and current SDK ranges.
- [x] Raise the supported Python baseline to 3.10 and update CI coverage.
- [x] Patch the reference frontend to a non-vulnerable Next.js 15 release.
- [ ] Add richer prior-art deduping and ranking tests with mocked USPTO ODP edge cases.
- [ ] Add multi-query planning, canonical patent-number deduplication, and optional semantic reranking.
- [ ] Add OpenAlex as an optional non-patent-literature provider.
- [ ] Add live-provider documentation for safe local testing with user-supplied keys.
- [ ] Add a small sample JSON idea disclosure alongside the Markdown example.
- [ ] Add structured export examples for downstream tools: JSON report, Markdown report, GitHub summary.
- [ ] Revisit the package name and public-facing naming before publishing if desired.

## Compliance / Legal-Risk Follow-Ups

- [ ] Have disclaimer, Terms of Service, and public launch copy reviewed by a qualified attorney before letting external users rely on it.
- [ ] Keep the no-USPTO-submission boundary explicit in future UI, CLI, prompts, and docs.
- [ ] Keep "not legal advice" language visible in generated reports and any future web app screens.

## Later Phases

- [ ] Phase 2: provisional application drafting and DOCX generation.
- [ ] Phase 3: non-provisional claim tree, full specification, and illustrative drawing descriptions.
- [ ] Phase 4: multi-user web app hardening, auth, billing, Google Patents BigQuery, Lens.org, and fee schedule admin.
