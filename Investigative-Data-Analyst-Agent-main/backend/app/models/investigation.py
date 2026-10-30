"""
SQLAlchemy 2.0 ORM models for the investigations and investigation_datasets tables.
"""
import enum
from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class InvestigationStatus(str, enum.Enum):
    """Enumeration of possible investigation lifecycle states."""
    INITIATED = "initiated"
    ANALYZING = "analyzing"
    WAITING_FOR_DATA = "waiting_for_data"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class Investigation(Base):
    """
    Represents a user investigation session: tracks the question, status,
    and all intermediate results (hypotheses, validations, missing data).
    """
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=InvestigationStatus.INITIATED.value,
    )

    # JSON-serialised intermediate results
    hypotheses_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    validations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_datasets_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_questions_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional FK to a future reports table
    report_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to associated datasets
    investigation_datasets: Mapped[list["InvestigationDataset"]] = relationship(
        "InvestigationDataset",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Investigation id={self.id} status={self.status!r} "
            f"question={self.question[:40]!r}>"
        )


class InvestigationDataset(Base):
    """
    Join table linking investigations to datasets (many-to-many).
    Tracks when each dataset was added to an investigation.
    """
    __tablename__ = "investigation_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="investigation_datasets",
    )

    def __repr__(self) -> str:
        return (
            f"<InvestigationDataset investigation_id={self.investigation_id} "
            f"dataset_id={self.dataset_id}>"
        )
