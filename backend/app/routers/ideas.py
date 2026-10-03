from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from patent_troll import IdeaDisclosure, PatentTrollConfig, PatentabilityWorkflow
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db import get_db
from app.models import AnalysisReport, Idea, PriorArtResult
from app.schemas import AnalysisReportRead, EndToEndResponse, IdeaCreate, IdeaRead, PriorArtRead
from app.services.users import get_or_create_dev_user

router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@router.post("", response_model=IdeaRead)
def create_idea(payload: IdeaCreate, db: Session = Depends(get_db)) -> Idea:
    user = get_or_create_dev_user(db)
    idea = Idea(user_id=user.id, **payload.model_dump())
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@router.get("/{idea_id}", response_model=IdeaRead)
def get_idea(idea_id: str, db: Session = Depends(get_db)) -> Idea:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.post("/{idea_id}/prior-art", response_model=list[PriorArtRead])
async def run_prior_art_search(
    idea_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[PriorArtResult]:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    db.query(PriorArtResult).filter(PriorArtResult.idea_id == idea.id).delete()
    workflow = PatentabilityWorkflow(config_from_settings(settings))
    results = await workflow.search(disclosure_from_idea(idea))
    records = [PriorArtResult(idea_id=idea.id, **result.to_dict()) for result in results]
    db.add_all(records)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


@router.post("/{idea_id}/analysis")
async def run_analysis(
    idea_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AnalysisReportRead:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    prior_art = (
        db.query(PriorArtResult)
        .filter(PriorArtResult.idea_id == idea.id)
        .order_by(PriorArtResult.similarity_score.desc())
        .all()
    )
    if not prior_art:
        raise HTTPException(status_code=400, detail="Run prior art search before analysis")

    workflow = PatentabilityWorkflow(config_from_settings(settings))
    report_payload = await workflow.analyze(disclosure_from_idea(idea), [library_prior_art(result) for result in prior_art])
    report = AnalysisReport(idea_id=idea.id, **report_payload.to_dict())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/end-to-end", response_model=EndToEndResponse)
async def create_search_analyze(
    payload: IdeaCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EndToEndResponse:
    user = get_or_create_dev_user(db)
    idea = Idea(user_id=user.id, **payload.model_dump())
    db.add(idea)
    db.commit()
    db.refresh(idea)

    workflow = PatentabilityWorkflow(config_from_settings(settings))
    workflow_result = await workflow.run(disclosure_from_idea(idea))
    prior_art = [PriorArtResult(idea_id=idea.id, **result.to_dict()) for result in workflow_result.prior_art]
    db.add_all(prior_art)
    db.commit()
    for result in prior_art:
        db.refresh(result)

    report = AnalysisReport(idea_id=idea.id, **workflow_result.analysis.to_dict())
    db.add(report)
    db.commit()
    db.refresh(report)

    return EndToEndResponse(
        idea=idea,
        prior_art=prior_art,
        search_metadata=workflow_result.search_metadata.to_dict() if workflow_result.search_metadata else None,
        analysis=report,
    )


def config_from_settings(settings: Settings) -> PatentTrollConfig:
    return PatentTrollConfig(
        llm_provider=settings.patent_troll_llm_provider,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        anthropic_api_key=settings.anthropic_api_key,
        anthropic_model=settings.anthropic_model,
        uspto_odp_api_key=settings.uspto_odp_api_key,
        enable_demo_fallback=settings.patent_troll_demo_fallback,
    )


def disclosure_from_idea(idea: Idea) -> IdeaDisclosure:
    return IdeaDisclosure(
        title=idea.title,
        problem=idea.problem,
        mechanism=idea.mechanism,
        data_flow=idea.data_flow,
        algorithm=idea.algorithm,
        technical_novelty=idea.technical_novelty,
        implementation_notes=idea.implementation_notes,
    )


def library_prior_art(result: PriorArtResult):
    from patent_troll import PriorArtResult as LibraryPriorArtResult

    return LibraryPriorArtResult(
        source=result.source,
        external_id=result.external_id,
        title=result.title,
        abstract=result.abstract,
        publication_date=result.publication_date,
        assignee=result.assignee,
        link=result.link,
        similarity_score=result.similarity_score,
        raw_payload=result.raw_payload,
    )
