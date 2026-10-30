"""
Pydantic v2 schemas for investigation requests and responses.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.agents.data_analyst import DataAnalysisResult
from app.agents.missing_data import MissingDataResult
from app.agents.planner import ExecutionPlan


class AnalyzeRequest(BaseModel):
    """Payload for the POST /investigations/analyze endpoint."""
    question: str
    dataset_ids: list[int]


class AnalyzeResponse(BaseModel):
    """Response from the POST /investigations/analyze endpoint."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    plan: ExecutionPlan
    analysis: Optional[list[DataAnalysisResult]] = None


class InvestigationResponse(BaseModel):
    """Full investigation details returned from GET /investigations/{id}."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    question: str
    status: str
    hypotheses: list[dict]         # parsed from hypotheses_json
    missing_datasets: list[str]    # parsed from missing_datasets_json
    follow_up_questions: list[str] # parsed from follow_up_questions_json
    dataset_ids: list[int]         # linked dataset IDs
    created_at: datetime
    updated_at: datetime


class ContinueInvestigationRequest(BaseModel):
    """Payload for POST /investigations/continue."""
    investigation_id: int
    new_dataset_ids: list[int]  # newly uploaded dataset IDs to add


class ContinueInvestigationResponse(BaseModel):
    """Response from POST /investigations/continue."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    investigation: InvestigationResponse
    new_validations: Optional[MissingDataResult] = None
    message: str

