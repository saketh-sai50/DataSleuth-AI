"""
FastAPI router for investigation orchestration.
Implements the full investigation lifecycle: start, continue, retrieve.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.investigation import Investigation
from app.repositories.investigation_repository import InvestigationRepository
from app.schemas.investigation import (
    AnalyzeRequest,
    AnalyzeResponse,
    ContinueInvestigationRequest,
    ContinueInvestigationResponse,
    InvestigationResponse,
)
from app.services.investigation_service import InvestigationService

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: Convert ORM Investigation → InvestigationResponse
# ---------------------------------------------------------------------------
def _to_response(investigation: Investigation, db: Session) -> InvestigationResponse:
    """
    Convert an Investigation ORM object into an InvestigationResponse schema.
    Parses JSON fields back to Python objects.
    """
    repo = InvestigationRepository(db)

    hypotheses: list[dict] = []
    if investigation.hypotheses_json:
        try:
            hypotheses = json.loads(investigation.hypotheses_json)
        except (json.JSONDecodeError, TypeError):
            hypotheses = []

    missing_datasets: list[str] = []
    if investigation.missing_datasets_json:
        try:
            missing_datasets = json.loads(investigation.missing_datasets_json)
        except (json.JSONDecodeError, TypeError):
            missing_datasets = []

    follow_up_questions: list[str] = []
    if investigation.follow_up_questions_json:
        try:
            follow_up_questions = json.loads(investigation.follow_up_questions_json)
        except (json.JSONDecodeError, TypeError):
            follow_up_questions = []

    # Linked dataset IDs
    links = repo.get_datasets(investigation.id)
    dataset_ids = [link.dataset_id for link in links]

    return InvestigationResponse(
        id=investigation.id,
        question=investigation.question,
        status=investigation.status,
        hypotheses=hypotheses,
        missing_datasets=missing_datasets,
        follow_up_questions=follow_up_questions,
        dataset_ids=dataset_ids,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a new investigation: plan + analyse + hypothesise + validate",
)
def analyze(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
) -> AnalyzeResponse:
    """
    Accept a user question and dataset IDs, run the full investigation
    pipeline (plan → analysis → hypotheses → validation), persist the
    investigation to the database, and return the plan + analysis results.
    """
    logger.info(
        f"Analyze request: question={request.question!r} "
        f"dataset_ids={request.dataset_ids}"
    )

    service = InvestigationService(db)
    try:
        (
            investigation,
            plan,
            analysis_results,
            root_cause_result,
            missing_data_result,
        ) = service.start_investigation(
            question=request.question,
            dataset_ids=request.dataset_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Investigation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {exc}",
        )

    return AnalyzeResponse(
        plan=plan,
        analysis=analysis_results if analysis_results else None,
    )


@router.get(
    "/",
    response_model=list[InvestigationResponse],
    summary="List all investigation sessions",
)
def list_investigations(
    db: Session = Depends(get_db),
) -> list[InvestigationResponse]:
    """Return all investigations from the database, newest first."""
    repo = InvestigationRepository(db)
    investigations = repo.get_all()
    return [_to_response(inv, db) for inv in investigations]


@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    summary="Get a single investigation by ID",
)
def get_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    """Retrieve details for a specific investigation including hypotheses and status."""
    repo = InvestigationRepository(db)
    investigation = repo.get_by_id(investigation_id)
    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation id={investigation_id} not found.",
        )
    return _to_response(investigation, db)


@router.post(
    "/continue",
    response_model=ContinueInvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Continue an investigation with newly uploaded datasets",
)
def continue_investigation(
    request: ContinueInvestigationRequest,
    db: Session = Depends(get_db),
) -> ContinueInvestigationResponse:
    """
    Add new datasets to an existing investigation and re-run the missing
    data validation to check if hypotheses can now be confirmed.
    """
    logger.info(
        f"Continue request: investigation_id={request.investigation_id} "
        f"new_dataset_ids={request.new_dataset_ids}"
    )

    service = InvestigationService(db)
    try:
        investigation, new_validations = service.continue_investigation(
            investigation_id=request.investigation_id,
            new_dataset_ids=request.new_dataset_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Continue investigation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Continue investigation failed: {exc}",
        )

    inv_response = _to_response(investigation, db)
    return ContinueInvestigationResponse(
        investigation=inv_response,
        new_validations=new_validations,
        message=(
            f"Investigation updated with {len(request.new_dataset_ids)} new dataset(s). "
            f"Status: {investigation.status}."
        ),
    )
