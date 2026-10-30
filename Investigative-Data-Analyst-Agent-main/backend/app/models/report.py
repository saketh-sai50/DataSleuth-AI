"""
SQLAlchemy 2.0 ORM model for the reports table.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Report(Base):
    """
    Represents a generated business report with executive summary,
    evidence, hypotheses evaluations, limitations, and recommendations.
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_causes_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of dicts
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)      # JSON list of strings
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False)   # JSON list of strings
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=False) # JSON list of strings
    missing_info_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list of strings
    next_steps_json: Mapped[str] = mapped_column(Text, nullable=False)    # JSON list of strings
    charts_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Optional JSON list of charts
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} investigation_id={self.investigation_id} confidence={self.overall_confidence}>"
