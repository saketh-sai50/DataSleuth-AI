"""
Repository for Report database operations using SQLAlchemy 2.0 style.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.report import Report
from loguru import logger


class ReportRepository:
    """
    Provides database operations for the Report model.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, investigation_id: int, report_data: dict) -> Report:
        """Create and persist a new Report record."""
        # Convert any incoming lists to JSON if they aren't serialized already,
        # but in services we'll serialize them first.
        report = Report(investigation_id=investigation_id, **report_data)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        logger.info(f"Report created: id={report.id} for investigation_id={investigation_id}")
        return report

    def get_by_id(self, report_id: int) -> Optional[Report]:
        """Retrieve a single Report by its primary key."""
        stmt = select(Report).where(Report.id == report_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_by_investigation_id(self, investigation_id: int) -> Optional[Report]:
        """Retrieve a single Report linked to a specific investigation."""
        stmt = select(Report).where(Report.investigation_id == investigation_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_all(self) -> list[Report]:
        """Retrieve all Report records ordered by created_at descending."""
        stmt = select(Report).order_by(Report.created_at.desc())
        results = self.db.execute(stmt).scalars().all()
        return list(results)
