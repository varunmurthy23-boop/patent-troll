from __future__ import annotations

import re
from dataclasses import dataclass

from patent_troll.models import IdeaDisclosure


TEMPLATE_PHRASES = [
    "what technical problem does this solve",
    "how does the system actually work",
    "what enters the system",
    "describe the ordered steps",
    "what is technically different",
    "latency, memory, throughput",
]

VAGUE_TERMS = [
    "ai system",
    "automates",
    "automation",
    "platform",
    "solution",
    "optimize",
    "improve",
    "smart",
    "intelligent",
    "seamless",
]

TECHNICAL_TERMS = [
    "algorithm",
    "data structure",
    "graph",
    "index",
    "cache",
    "queue",
    "state",
    "protocol",
    "latency",
    "throughput",
    "memory",
    "sensor",
    "compiler",
    "schema",
    "threshold",
    "scoring",
    "update rule",
]

MEASURABLE_TERMS = [
    "latency",
    "throughput",
    "memory",
    "accuracy",
    "percent",
    "ms",
    "seconds",
    "complexity",
    "resource",
    "bandwidth",
    "false positive",
    "false negative",
]


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    field: str
    message: str
    suggestion: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "field": self.field,
            "message": self.message,
            "suggestion": self.suggestion,
        }


def validate_idea(idea: IdeaDisclosure) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    fields = {
        "title": idea.title,
        "problem": idea.problem,
        "mechanism": idea.mechanism,
        "data_flow": idea.data_flow,
        "algorithm": idea.algorithm,
        "technical_novelty": idea.technical_novelty,
        "implementation_notes": idea.implementation_notes,
    }

    required_min_words = {
        "title": 3,
        "problem": 10,
        "mechanism": 18,
        "data_flow": 18,
        "algorithm": 18,
        "technical_novelty": 14,
    }
    for field, minimum in required_min_words.items():
        value = fields[field]
        if word_count(value) < minimum:
            issues.append(
                ValidationIssue(
                    severity="error" if field in {"mechanism", "algorithm", "technical_novelty"} else "warning",
                    field=field,
                    message=f"{label(field)} is too thin for a useful patentability analysis.",
                    suggestion=f"Add at least {minimum} words with concrete technical detail.",
                )
            )

    for field, value in fields.items():
        lowered = value.lower()
        if any(phrase in lowered for phrase in TEMPLATE_PHRASES):
            issues.append(
                ValidationIssue(
                    severity="error",
                    field=field,
                    message=f"{label(field)} still appears to contain template placeholder text.",
                    suggestion="Replace template prompts with your actual invention details before analyzing.",
                )
            )

    combined = " ".join(fields.values()).lower()
    vague_hits = sorted({term for term in VAGUE_TERMS if term in combined})
    if vague_hits:
        issues.append(
            ValidationIssue(
                severity="warning",
                field="idea",
                message="The disclosure uses broad product language: " + ", ".join(vague_hits) + ".",
                suggestion="Replace broad result language with components, data structures, ordered operations, thresholds, or update rules.",
            )
        )

    if not contains_any(idea.mechanism + " " + idea.algorithm + " " + idea.technical_novelty, TECHNICAL_TERMS):
        issues.append(
            ValidationIssue(
                severity="warning",
                field="mechanism",
                message="The disclosure does not clearly name a concrete technical mechanism.",
                suggestion="Name the data structure, graph, index, cache, protocol, state machine, scoring rule, or update rule that makes it work.",
            )
        )

    if not contains_any(idea.technical_novelty + " " + idea.implementation_notes, MEASURABLE_TERMS):
        issues.append(
            ValidationIssue(
                severity="warning",
                field="technical_novelty",
                message="The disclosure does not describe a measurable technical effect.",
                suggestion="Add latency, memory, throughput, accuracy, resource usage, complexity, or error-rate impact.",
            )
        )

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_'-]+", value))


def contains_any(value: str, terms: list[str]) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in terms)


def label(field: str) -> str:
    return field.replace("_", " ").title()
