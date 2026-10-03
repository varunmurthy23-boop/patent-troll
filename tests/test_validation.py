from patent_troll import IdeaDisclosure, validate_idea
from patent_troll.validation import has_errors


def strong_idea() -> IdeaDisclosure:
    return IdeaDisclosure(
        title="Adaptive Code Review Risk Router",
        problem="Engineering teams route pull requests with static ownership rules that miss runtime failure risk and coverage gaps.",
        mechanism=(
            "The system maintains a typed dependency graph that links changed files, service incidents, code owners, "
            "coverage deltas, and runtime ownership edges in a persistent graph index."
        ),
        data_flow=(
            "A pull request webhook enters a queue, changed files map to graph nodes, incident and coverage events "
            "update edge weights, and ranked reviewer plans are written back to the code host."
        ),
        algorithm=(
            "For each changed node, bounded graph expansion identifies affected paths, applies exponential incident "
            "decay, adds coverage penalties above a threshold, and scores reviewers by path coverage."
        ),
        technical_novelty=(
            "Incident-weighted graph edges reduce reviewer routing latency in milliseconds while reflecting current "
            "runtime risk instead of static ownership alone."
        ),
        implementation_notes="Incremental graph recomputation keeps latency below two seconds for typical pull requests.",
    )


def test_validate_strong_idea_passes() -> None:
    issues = validate_idea(strong_idea())

    assert issues == []


def test_validate_template_text_returns_errors() -> None:
    idea = IdeaDisclosure(
        title="Invention Title",
        problem="What technical problem does this solve?",
        mechanism="How does the system actually work? Name components, state, data structures, and control flow.",
        data_flow="What enters the system, what transforms, and what comes out?",
        algorithm="Describe the ordered steps, scoring rules, thresholds, update rules, or other concrete logic.",
        technical_novelty="What is technically different from generic automation or static rules?",
    )

    issues = validate_idea(idea)

    assert has_errors(issues)
    assert any("template placeholder" in issue.message for issue in issues)


def test_validate_vague_idea_warns_about_mechanism() -> None:
    idea = IdeaDisclosure(
        title="Smart AI Platform",
        problem="Users need a smart AI system that improves productivity and automates their workflows.",
        mechanism="The platform uses AI to automate everything and provide a seamless solution.",
        data_flow="User data goes in and better recommendations come out.",
        algorithm="The system optimizes the result with AI.",
        technical_novelty="The system is smarter and improves workflow automation.",
    )

    issues = validate_idea(idea)

    assert any(issue.field == "idea" for issue in issues)
    assert any(issue.field == "mechanism" for issue in issues)
