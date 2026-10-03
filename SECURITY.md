# Security Policy

## Supported Versions

Patent Troll is pre-1.0. Security fixes target the latest commit on the default branch until release branches exist.

## Reporting a Vulnerability

Please do not open a public issue for secrets exposure, credential handling bugs, dependency compromise, prompt-injection vulnerabilities with security impact, or other sensitive reports.

Until a private disclosure channel is configured for this repository, contact the maintainers privately through the repository owner. Include:

- affected version or commit
- reproduction steps
- impact
- whether any API keys, user data, or generated reports may be exposed

## Secret Handling

The CLI may create `.env` files containing user-supplied API keys. `.env` is ignored by git and should not be committed.

Never include real API keys in tests, docs, examples, issues, screenshots, or pull requests.

## Scope Notes

Patent Troll does not submit filings to the USPTO, does not automate Patent Center, and should not collect production credentials unless the user explicitly configures a local or hosted deployment to do so.
