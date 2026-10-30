"""
FastAPI router for Report generation, retrieval, and chat endpoints.
"""
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.db.session import get_db
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    ReportResponse,
    GenerateReportRequest,
    ChatRequest,
    ChatResponse,
    RootCauseEntry
)
from app.services.report_service import ReportService
from app.models.report import Report

router = APIRouter()


def _to_response(report: Report) -> ReportResponse:
    """Helper to convert Report DB model to ReportResponse schema."""
    try:
        root_causes_raw = json.loads(report.root_causes_json)
        root_causes = [RootCauseEntry(**rc) for rc in root_causes_raw]
    except Exception:
        root_causes = []

    try:
        evidence = json.loads(report.evidence_json)
    except Exception:
        evidence = []

    try:
        limitations = json.loads(report.limitations_json)
    except Exception:
        limitations = []

    try:
        recommendations = json.loads(report.recommendations_json)
    except Exception:
        recommendations = []

    try:
        missing_info = json.loads(report.missing_info_json)
    except Exception:
        missing_info = []

    try:
        next_steps = json.loads(report.next_steps_json)
    except Exception:
        next_steps = []

    charts = None
    if report.charts_json:
        try:
            charts = json.loads(report.charts_json)
        except Exception:
            charts = []

    return ReportResponse(
        id=report.id,
        investigation_id=report.investigation_id,
        executive_summary=report.executive_summary,
        root_causes=root_causes,
        evidence=evidence,
        limitations=limitations,
        recommendations=recommendations,
        missing_info=missing_info,
        next_steps=next_steps,
        charts=charts,
        overall_confidence=report.overall_confidence,
        created_at=report.created_at,
    )


@router.post(
    "/generate",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist a business report",
)
def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db)
) -> ReportResponse:
    """
    Triggers report generation for the given investigation,
    saves it to SQLite, and updates the investigation status.
    """
    logger.info(f"Generating report for investigation_id={req.investigation_id}")
    service = ReportService(db)
    try:
        report = service.generate_report(req.investigation_id)
        return _to_response(report)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
    except Exception as exc:
        logger.error(f"Failed to generate report: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(exc)}"
        )


@router.get(
    "/",
    response_model=list[ReportResponse],
    summary="List all reports",
)
def list_reports(db: Session = Depends(get_db)) -> list[ReportResponse]:
    """Retrieve all reports saved in the system."""
    repo = ReportRepository(db)
    reports = repo.get_all()
    return [_to_response(r) for r in reports]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Retrieve a report by ID",
)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportResponse:
    """Get metadata and content for a single report by ID."""
    repo = ReportRepository(db)
    report = repo.get_by_id(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id={report_id} not found."
        )
    return _to_response(report)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Factual data chat context",
)
def chat_with_data(
    req: ChatRequest,
    db: Session = Depends(get_db)
) -> ChatResponse:
    """
    Query the assistant with a conversational question,
    optionally incorporating investigation context.
    """
    service = ReportService(db)
    try:
        res = service.chat(
            message=req.message,
            investigation_id=req.investigation_id,
            context=req.context
        )
        return ChatResponse(
            response=res["response"],
            investigation_id=res["investigation_id"],
            suggested_actions=res["suggested_actions"]
        )
    except Exception as exc:
        logger.error(f"Chat failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
