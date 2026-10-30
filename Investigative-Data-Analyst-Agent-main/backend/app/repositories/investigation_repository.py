"""
Repository for Investigation and InvestigationDataset database operations
using SQLAlchemy 2.0 style.
"""
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.investigation import Investigation, InvestigationDataset, InvestigationStatus


class InvestigationRepository:
    """
    Provides CRUD and update operations for the Investigation and
    InvestigationDataset models.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Investigation CRUD
    # ------------------------------------------------------------------
    def create(self, question: str) -> Investigation:
        """Create a new Investigation record with INITIATED status."""
        investigation = Investigation(
            question=question,
            status=InvestigationStatus.INITIATED.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(investigation)
        self.db.commit()
        self.db.refresh(investigation)
        logger.info(f"Investigation created: id={investigation.id}")
        return investigation

    def get_by_id(self, investigation_id: int) -> Optional[Investigation]:
        """Retrieve a single Investigation by primary key."""
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self) -> list[Investigation]:
        """Retrieve all Investigations ordered by created_at descending."""
        stmt = select(Investigation).order_by(Investigation.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    # ------------------------------------------------------------------
    # Status + partial updates
    # ------------------------------------------------------------------
    def update_status(self, investigation_id: int, status: str) -> Investigation:
        """Update the status field of an existing investigation."""
        investigation = self._require(investigation_id)
        investigation.status = status
        investigation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(investigation)
        logger.info(f"Investigation id={investigation_id} status -> {status!r}")

        return investigation

    def update_hypotheses(
        self,
        investigation_id: int,
        hypotheses_json: str,
    ) -> Investigation:
        """Persist the JSON-serialised hypotheses list."""
        investigation = self._require(investigation_id)
        investigation.hypotheses_json = hypotheses_json
        investigation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(investigation)
        return investigation

    def update_validations(
        self,
        investigation_id: int,
        validations_json: str,
        missing_json: str,
        questions_json: str,
    ) -> Investigation:
        """Persist validation results, missing datasets, and follow-up questions."""
        investigation = self._require(investigation_id)
        investigation.validations_json = validations_json
        investigation.missing_datasets_json = missing_json
        investigation.follow_up_questions_json = questions_json
        investigation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(investigation)
        return investigation

    # ------------------------------------------------------------------
    # Dataset linkage
    # ------------------------------------------------------------------
    def add_dataset(self, investigation_id: int, dataset_id: int) -> InvestigationDataset:
        """
        Link a dataset to an investigation.
        Silently skips if the link already exists.
        """
        # Check if already linked
        stmt = select(InvestigationDataset).where(
            InvestigationDataset.investigation_id == investigation_id,
            InvestigationDataset.dataset_id == dataset_id,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing:
            logger.debug(
                f"Dataset id={dataset_id} already linked to investigation id={investigation_id}"
            )
            return existing

        link = InvestigationDataset(
            investigation_id=investigation_id,
            dataset_id=dataset_id,
            added_at=datetime.utcnow(),
        )
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        logger.info(f"Dataset id={dataset_id} linked to investigation id={investigation_id}")
        return link

    def get_datasets(self, investigation_id: int) -> list[InvestigationDataset]:
        """Retrieve all dataset links for an investigation."""
        stmt = select(InvestigationDataset).where(
            InvestigationDataset.investigation_id == investigation_id,
        )
        return list(self.db.execute(stmt).scalars().all())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _require(self, investigation_id: int) -> Investigation:
        """Retrieve an Investigation or raise ValueError if not found."""
        investigation = self.get_by_id(investigation_id)
        if investigation is None:
            raise ValueError(f"Investigation id={investigation_id} not found.")
        return investigation
