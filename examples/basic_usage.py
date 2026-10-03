import asyncio
import json

from patent_troll import IdeaDisclosure, PatentTrollConfig, PatentabilityWorkflow


async def main() -> None:
    workflow = PatentabilityWorkflow(PatentTrollConfig.from_env())
    result = await workflow.run(
        IdeaDisclosure(
            title="Adaptive code review risk router",
            problem=(
                "Engineering teams waste reviewer time because pull requests are routed using static "
                "ownership rules that miss implementation risk."
            ),
            mechanism=(
                "The system builds a typed dependency graph from changed files, runtime incidents, code "
                "owners, and test coverage, then routes review requests based on graph paths affected by the change."
            ),
            data_flow=(
                "A pull request event enters an ingestion queue, changed files are mapped to graph nodes, "
                "incident and coverage signals update edge weights, and a ranked reviewer plan is written back."
            ),
            algorithm=(
                "For each changed node, the algorithm performs bounded graph expansion, applies decayed "
                "incident weights and coverage penalties, computes reviewer expertise scores, and selects a "
                "minimal reviewer set."
            ),
            technical_novelty=(
                "Graph edge weights are updated from production incident proximity and test coverage deltas "
                "so routing reflects current runtime risk instead of static ownership alone."
            ),
            implementation_notes="Uses a persistent graph index and incremental recomputation to keep latency low.",
        )
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
