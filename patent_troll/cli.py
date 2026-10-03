from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from patent_troll import IdeaDisclosure, PatentTrollConfig, PatentabilityWorkflow
from patent_troll.diagnostics import ProviderCheck, run_live_checks
from patent_troll.providers import MissingProviderDependency
from patent_troll.reporting import render_github_markdown, render_json, render_markdown
from patent_troll.validation import ValidationIssue, has_errors, validate_idea


SECTION_ALIASES = {
    "title": "title",
    "problem": "problem",
    "technical problem": "problem",
    "mechanism": "mechanism",
    "how it works": "mechanism",
    "data flow": "data_flow",
    "dataflow": "data_flow",
    "algorithm": "algorithm",
    "technical novelty": "technical_novelty",
    "novelty": "technical_novelty",
    "implementation notes": "implementation_notes",
    "notes": "implementation_notes",
}


IDEA_TEMPLATE = """# Invention Title

## Problem
What technical problem does this solve?

## Mechanism
How does the system actually work? Name components, state, data structures, and control flow.

## Data Flow
What enters the system, what transforms, and what comes out?

## Algorithm
Describe the ordered steps, scoring rules, thresholds, update rules, or other concrete logic.

## Technical Novelty
What is technically different from generic automation or static rules?

## Implementation Notes
Latency, memory, throughput, deployment, hardware, sensors, protocols, or other constraints.
"""

DEFAULT_ENV_VALUES = {
    "PATENT_TROLL_LLM_PROVIDER": "auto",
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "gpt-4.1-mini",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_MODEL": "claude-sonnet-5",
    "USPTO_ODP_API_KEY": "",
    "PATENT_TROLL_DEMO_FALLBACK": "true",
}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="patent-troll",
        description="Developer-native invention disclosure, prior art search, and patentability risk analysis.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create starter files for a new Patent Troll project.")
    init_parser.add_argument("--dir", default=".", help="Directory to initialize. Defaults to the current directory.")
    init_parser.add_argument("--idea-file", default="idea.md", help="Idea disclosure file path relative to --dir.")
    init_parser.add_argument("--env-file", default=".env.example", help="Environment example path relative to --dir.")
    init_parser.add_argument(
        "--provider",
        choices=["auto", "openai", "anthropic", "none"],
        default="auto",
        help="Default provider written to the env example.",
    )
    init_parser.add_argument("--no-env", action="store_true", help="Skip writing the env example file.")
    init_parser.add_argument("--github-action", action="store_true", help="Also write a GitHub Actions workflow.")
    init_parser.add_argument(
        "--workflow-file",
        default=".github/workflows/patentability.yml",
        help="Workflow path relative to --dir when --github-action is set.",
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")

    configure_parser = subparsers.add_parser("configure", help="Create or update a local .env file with provider keys.")
    configure_parser.add_argument("--env-file", default=".env", help="Path to write. Defaults to .env in the current directory.")
    configure_parser.add_argument(
        "--provider",
        choices=["auto", "openai", "anthropic", "none"],
        default=None,
        help="LLM provider preference. Defaults to interactive prompt.",
    )
    configure_parser.add_argument("--non-interactive", action="store_true", help="Write placeholders without prompting for secrets.")

    template_parser = subparsers.add_parser("template", help="Create a Markdown idea disclosure template.")
    template_parser.add_argument("path", help="Where to write the template, for example idea.md.")
    template_parser.add_argument("--force", action="store_true", help="Overwrite an existing file.")

    action_template_parser = subparsers.add_parser(
        "action-template",
        help="Create a GitHub Actions workflow for Patent Troll analysis.",
    )
    action_template_parser.add_argument(
        "path",
        nargs="?",
        default=".github/workflows/patentability.yml",
        help="Where to write the workflow. Defaults to .github/workflows/patentability.yml.",
    )
    action_template_parser.add_argument("--idea-file", default="idea.md", help="Idea file path used by the workflow.")
    action_template_parser.add_argument(
        "--provider",
        choices=["auto", "openai", "anthropic", "none"],
        default="auto",
        help="Analysis provider used by the workflow.",
    )
    action_template_parser.add_argument(
        "--output-file",
        default="patent-troll-report.md",
        help="Report path produced by the workflow.",
    )
    action_template_parser.add_argument(
        "--action-ref",
        default="varunmurthy23-boop/patent-troll@v0",
        help="GitHub Action reference to use in the workflow.",
    )
    action_template_parser.add_argument("--no-strict", action="store_true", help="Do not fail on idea validation errors.")
    action_template_parser.add_argument("--force", action="store_true", help="Overwrite an existing workflow file.")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze an idea from a JSON, Markdown, or text file.")
    analyze_parser.add_argument("idea_file", help="Path to an idea file.")
    analyze_parser.add_argument("--env-file", default=None, help="Optional .env file to load before running.")
    analyze_parser.add_argument("--provider", choices=["auto", "openai", "anthropic", "none"], default=None)
    analyze_parser.add_argument("--format", choices=["json", "markdown", "github"], default="markdown")
    analyze_parser.add_argument("--output", "-o", default=None, help="Write report to a file instead of stdout.")
    analyze_parser.add_argument("--limit", type=int, default=8, help="Maximum prior art results to analyze.")
    analyze_parser.add_argument("--no-demo-fallback", action="store_true", help="Disable demo prior art when search keys are absent.")
    analyze_parser.add_argument("--strict", action="store_true", help="Stop before analysis if validation finds errors.")

    validate_parser = subparsers.add_parser("validate", help="Check whether an idea file is detailed enough to analyze.")
    validate_parser.add_argument("idea_file", help="Path to a JSON, Markdown, or text idea file.")
    validate_parser.add_argument("--format", choices=["text", "json"], default="text")
    validate_parser.add_argument("--strict", action="store_true", help="Exit nonzero when validation errors are found.")

    doctor_parser = subparsers.add_parser("doctor", help="Check local configuration without printing secret values.")
    doctor_parser.add_argument("--env-file", default=None, help="Optional .env file to load before checking.")
    doctor_parser.add_argument("--live", action="store_true", help="Run explicit network checks against configured providers.")
    doctor_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    if args.command == "init":
        return init_project(args)
    if args.command == "configure":
        return configure(args)
    if args.command == "template":
        return write_template(args)
    if args.command == "action-template":
        return write_action_template(args)
    if args.command == "analyze":
        try:
            return asyncio.run(analyze(args))
        except MissingProviderDependency as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "validate":
        return validate(args)
    if args.command == "doctor":
        return asyncio.run(doctor(args))
    parser.print_help()
    return 1


def init_project(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    root.mkdir(parents=True, exist_ok=True)

    idea_path = root / args.idea_file
    targets: list[tuple[Path, str]] = [(idea_path, IDEA_TEMPLATE)]

    if not args.no_env:
        env_values = {**DEFAULT_ENV_VALUES, "PATENT_TROLL_LLM_PROVIDER": args.provider}
        targets.append((root / args.env_file, render_env_file(env_values)))

    if args.github_action:
        targets.append((root / args.workflow_file, render_github_action_template(args.idea_file, provider=args.provider)))

    blocked = [path for path, _text in targets if path.exists()]
    if blocked and not args.force:
        for path in blocked:
            print(f"{path} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1

    created: list[Path] = []
    for path, text in targets:
        write_if_allowed(path, text, args.force)
        created.append(path)

    print("Initialized Patent Troll project.")
    for path in created:
        print(f"- Wrote {path}")
    if not created:
        print("- No files changed.")
    print("")
    print("Keys users can provide when they are ready:")
    print("- OPENAI_API_KEY for OpenAI/ChatGPT analysis")
    print("- ANTHROPIC_API_KEY for Anthropic/Claude analysis")
    print("- USPTO_ODP_API_KEY for USPTO Open Data Portal prior-art search")
    print("")
    print(f"Try: patent-troll analyze {idea_path} --provider none")
    return 0


def configure(args: argparse.Namespace) -> int:
    env_path = Path(args.env_file)
    existing = read_env_file(env_path)
    provider = args.provider or prompt_choice(
        "LLM provider",
        ["auto", "openai", "anthropic", "none"],
        existing.get("PATENT_TROLL_LLM_PROVIDER", "auto"),
        args.non_interactive,
    )

    updates = {
        "PATENT_TROLL_LLM_PROVIDER": provider,
        "OPENAI_MODEL": existing.get("OPENAI_MODEL", "gpt-4.1-mini"),
        "ANTHROPIC_MODEL": existing.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
        "PATENT_TROLL_DEMO_FALLBACK": existing.get("PATENT_TROLL_DEMO_FALLBACK", "true"),
    }

    if args.non_interactive:
        updates["OPENAI_API_KEY"] = existing.get("OPENAI_API_KEY", "")
        updates["ANTHROPIC_API_KEY"] = existing.get("ANTHROPIC_API_KEY", "")
        updates["USPTO_ODP_API_KEY"] = existing.get("USPTO_ODP_API_KEY", "")
    else:
        if provider in {"auto", "openai"}:
            updates["OPENAI_API_KEY"] = prompt_secret("OpenAI API key", existing.get("OPENAI_API_KEY"))
        if provider in {"auto", "anthropic"}:
            updates["ANTHROPIC_API_KEY"] = prompt_secret("Anthropic API key", existing.get("ANTHROPIC_API_KEY"))
        updates["USPTO_ODP_API_KEY"] = prompt_secret("USPTO ODP API key", existing.get("USPTO_ODP_API_KEY"))

    merged = {**existing, **updates}
    write_env_file(env_path, merged)
    print(f"Wrote {env_path}")
    print("Keep this file out of git. It may contain API keys.")
    return 0


def write_template(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"{path} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1
    path.write_text(IDEA_TEMPLATE, encoding="utf-8")
    print(f"Wrote {path}")
    return 0


def write_action_template(args: argparse.Namespace) -> int:
    path = Path(args.path)
    text = render_github_action_template(
        args.idea_file,
        provider=args.provider,
        output_file=args.output_file,
        strict=not args.no_strict,
        action_ref=args.action_ref,
    )
    if not write_if_allowed(path, text, args.force):
        print(f"{path} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1
    print(f"Wrote {path}")
    print("Configure GitHub secrets for any providers you want to use:")
    print("- OPENAI_API_KEY")
    print("- ANTHROPIC_API_KEY")
    print("- USPTO_ODP_API_KEY")
    return 0


async def doctor(args: argparse.Namespace) -> int:
    if args.env_file:
        load_env_file(Path(args.env_file))
    config = PatentTrollConfig.from_env()
    selected = config.selected_llm_provider()
    live_checks = await run_live_checks(config) if args.live else None
    if args.format == "json":
        payload = {
            "llm_provider_preference": config.llm_provider,
            "selected_llm_provider": selected,
            "openai_key": present(config.openai_api_key),
            "openai_model": config.openai_model,
            "anthropic_key": present(config.anthropic_api_key),
            "anthropic_model": config.anthropic_model,
            "uspto_odp_key": present(config.uspto_odp_api_key),
            "demo_fallback": config.enable_demo_fallback,
            "live_checks": [check.to_dict() for check in live_checks] if live_checks is not None else None,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_doctor(config, selected, live_checks))
    return 0


def validate(args: argparse.Namespace) -> int:
    idea = load_idea(Path(args.idea_file))
    issues = validate_idea(idea)
    if args.format == "json":
        print(json.dumps([issue.to_dict() for issue in issues], indent=2))
    else:
        print(render_validation(issues))
    return 1 if args.strict and has_errors(issues) else 0


async def analyze(args: argparse.Namespace) -> int:
    if args.env_file:
        load_env_file(Path(args.env_file))
    idea = load_idea(Path(args.idea_file))
    config = PatentTrollConfig.from_env()
    if args.provider:
        config = PatentTrollConfig(
            llm_provider=args.provider,
            openai_api_key=config.openai_api_key,
            openai_model=config.openai_model,
            anthropic_api_key=config.anthropic_api_key,
            anthropic_model=config.anthropic_model,
            uspto_odp_api_key=config.uspto_odp_api_key,
            enable_demo_fallback=config.enable_demo_fallback,
        )
    if args.no_demo_fallback:
        config = PatentTrollConfig(
            llm_provider=config.llm_provider,
            openai_api_key=config.openai_api_key,
            openai_model=config.openai_model,
            anthropic_api_key=config.anthropic_api_key,
            anthropic_model=config.anthropic_model,
            uspto_odp_api_key=config.uspto_odp_api_key,
            enable_demo_fallback=False,
        )

    issues = validate_idea(idea)
    if issues:
        print(render_validation(issues), file=sys.stderr)
        if args.strict and has_errors(issues):
            print("Analysis stopped because --strict was set and validation found errors.", file=sys.stderr)
            return 1

    result = await PatentabilityWorkflow(config).run(idea, limit=args.limit)
    rendered = render_report(result, args.format)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(rendered)
    return 0


def load_idea(path: Path) -> IdeaDisclosure:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        return IdeaDisclosure(
            title=data.get("title", path.stem),
            problem=data.get("problem", ""),
            mechanism=data.get("mechanism", ""),
            data_flow=data.get("data_flow", data.get("dataFlow", "")),
            algorithm=data.get("algorithm", ""),
            technical_novelty=data.get("technical_novelty", data.get("technicalNovelty", "")),
            implementation_notes=data.get("implementation_notes", data.get("implementationNotes", "")),
        )
    sections = parse_sections(text)
    title = sections.get("title") or first_heading(text) or path.stem.replace("-", " ").replace("_", " ").title()
    body = clean_body(text)
    return IdeaDisclosure(
        title=title,
        problem=sections.get("problem", body[:1000]),
        mechanism=sections.get("mechanism", body),
        data_flow=sections.get("data_flow", sections.get("mechanism", body)),
        algorithm=sections.get("algorithm", sections.get("mechanism", body)),
        technical_novelty=sections.get("technical_novelty", sections.get("mechanism", body)),
        implementation_notes=sections.get("implementation_notes", ""),
    )


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in text.splitlines():
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        plain_heading = re.match(r"^\s*([A-Za-z][A-Za-z ]{2,40}):\s*$", line)
        if heading or plain_heading:
            raw = (heading or plain_heading).group(1).strip().lower()
            key = SECTION_ALIASES.get(raw)
            if key:
                current = key
                sections.setdefault(current, [])
                continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items() if "\n".join(lines).strip()}


def first_heading(text: str) -> Optional[str]:
    match = re.search(r"^\s{0,3}#\s+(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def clean_body(text: str) -> str:
    return re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE).strip()


def render_validation(issues: list[ValidationIssue]) -> str:
    if not issues:
        return "Validation passed. The disclosure has enough structure for an initial analysis."
    lines = ["Validation warnings:"]
    for issue in issues:
        lines.append(f"- [{issue.severity}] {issue.field}: {issue.message} {issue.suggestion}")
    return "\n".join(lines)


def render_doctor(
    config: PatentTrollConfig,
    selected: str,
    live_checks: Optional[list[ProviderCheck]] = None,
) -> str:
    lines = [
        "Patent Troll configuration",
        f"- LLM provider preference: {config.llm_provider}",
        f"- Selected LLM provider: {selected}",
        f"- OpenAI key: {present(config.openai_api_key)}",
        f"- OpenAI model: {config.openai_model}",
        f"- Anthropic key: {present(config.anthropic_api_key)}",
        f"- Anthropic model: {config.anthropic_model}",
        f"- USPTO ODP key: {present(config.uspto_odp_api_key)}",
        f"- Demo fallback: {'enabled' if config.enable_demo_fallback else 'disabled'}",
    ]
    if selected == "none":
        lines.append("Warning: no LLM provider is configured; analysis will use the heuristic fallback.")
    if not config.uspto_odp_api_key:
        lines.append("Warning: no prior-art API keys are configured; search will use demo fallback when enabled.")
    if live_checks is not None:
        lines.extend(["", "Live provider checks:"])
        for check in live_checks:
            if not check.configured:
                status = "skipped"
            elif check.reachable:
                status = "ok"
            else:
                status = "failed"
            lines.append(f"- {check.name}: {status} - {check.message}")
    else:
        lines.append("Live checks not run. Use --live to test configured provider credentials.")
    return "\n".join(lines)


def render_report(result, output_format: str) -> str:
    if output_format == "json":
        return render_json(result)
    if output_format == "github":
        return render_github_markdown(result)
    return render_markdown(result)


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_file(path: Path, values: dict[str, str]) -> None:
    path.write_text(render_env_file(values), encoding="utf-8")


def render_env_file(values: dict[str, str]) -> str:
    ordered_keys = [
        "PATENT_TROLL_LLM_PROVIDER",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "USPTO_ODP_API_KEY",
        "PATENT_TROLL_DEMO_FALLBACK",
    ]
    lines = []
    for key in ordered_keys:
        if key in values:
            lines.append(f"{key}={values[key]}")
    for key in sorted(set(values) - set(ordered_keys)):
        lines.append(f"{key}={values[key]}")
    return "\n".join(lines).strip() + "\n"


def write_if_allowed(path: Path, text: str, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def render_github_action_template(
    idea_file: str,
    *,
    provider: str = "auto",
    output_file: str = "patent-troll-report.md",
    strict: bool = True,
    action_ref: str = "varunmurthy23-boop/patent-troll@v0",
) -> str:
    strict_value = "true" if strict else "false"
    return f"""name: Patentability Scan

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
      - name: Check out repository
        uses: actions/checkout@v5

      - name: Run Patent Troll
        uses: {action_ref}
        with:
          idea-file: {idea_file}
          provider: {provider}
          strict: {strict_value}
          output-file: {output_file}
        env:
          OPENAI_API_KEY: ${{{{ secrets.OPENAI_API_KEY }}}}
          ANTHROPIC_API_KEY: ${{{{ secrets.ANTHROPIC_API_KEY }}}}
          USPTO_ODP_API_KEY: ${{{{ secrets.USPTO_ODP_API_KEY }}}}

      - name: Upload report artifact
        uses: actions/upload-artifact@v4
        with:
          name: patent-troll-report
          path: {output_file}
"""


def load_env_file(path: Path) -> None:
    for key, value in read_env_file(path).items():
        os.environ.setdefault(key, value)


def prompt_choice(label: str, choices: list[str], default: str, non_interactive: bool) -> str:
    if non_interactive:
        return default
    answer = input(f"{label} {choices} [{default}]: ").strip().lower()
    return answer if answer in choices else default


def prompt_secret(label: str, existing: Optional[str]) -> str:
    suffix = " [keep existing]" if existing else " [blank to skip]"
    value = getpass.getpass(f"{label}{suffix}: ").strip()
    return value if value else existing or ""


def present(value: Optional[str]) -> str:
    return "configured" if value else "missing"


if __name__ == "__main__":
    raise SystemExit(main())
