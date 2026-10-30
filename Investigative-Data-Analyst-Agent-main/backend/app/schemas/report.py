"""
Pydantic v2 schemas for the Report model.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict



class RootCauseEntry(BaseModel):
    cause: str
    confidence: float
    evidence: str
    hypothesis_id: str


class ReportResponse(BaseModel):
    id: int
    investigation_id: int
    executive_summary: str
    root_causes: list[RootCauseEntry]
    evidence: list[str]
    limitations: list[str]
    recommendations: list[str]
    missing_info: list[str]
    next_steps: list[str]
    charts: Optional[list[dict[str, Any]]] = None
    overall_confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class GenerateReportRequest(BaseModel):
    investigation_id: int


class ChatRequest(BaseModel):
    message: str
    investigation_id: Optional[int] = None
    context: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    investigation_id: Optional[int] = None
    suggested_actions: list[str] = Field(default_factory=list)
