from __future__ import annotations

from typing import Optional

from patent_troll.analysis import analyze_idea
from patent_troll.config import PatentTrollConfig
from patent_troll.models import IdeaDisclosure, PatentabilityWorkflowResult
from patent_troll.prior_art import search_prior_art, search_prior_art_with_metadata


class PatentabilityWorkflow:
    def __init__(self, config: Optional[PatentTrollConfig] = None) -> None:
        self.config = config or PatentTrollConfig.from_env()

    async def search(self, idea: IdeaDisclosure, limit: int = 8):
        return await search_prior_art(idea, self.config, limit=limit)

    async def analyze(self, idea: IdeaDisclosure, prior_art):
        return await analyze_idea(idea, prior_art, self.config)

    async def run(self, idea: IdeaDisclosure, limit: int = 8) -> PatentabilityWorkflowResult:
        search_result = await search_prior_art_with_metadata(idea, self.config, limit=limit)
        analysis = await self.analyze(idea, search_result.results)
        return PatentabilityWorkflowResult(
            idea=idea,
            prior_art=search_result.results,
            analysis=analysis,
            search_metadata=search_result.metadata,
        )
